"""Sentiment scoring and news fetching."""
import asyncio

import pytest
import requests

import main

# Captured at import, before the autouse fixture swaps in a stub for each test
REAL_FETCH_STOCK_NEWS = main.fetch_stock_news


ALL_LABELS = [
    {"label": "positive", "score": 0.7},
    {"label": "negative", "score": 0.2},
    {"label": "neutral", "score": 0.1},
]


def use_classifier(monkeypatch, classifier):
    monkeypatch.setattr(main, "get_finbert", lambda: classifier)


def test_breakdown_counts_one_label_per_headline(monkeypatch):
    calls = []

    def classifier(texts, truncation):
        calls.append((list(texts), truncation))
        return [ALL_LABELS for _ in texts]

    use_classifier(monkeypatch, classifier)
    result = asyncio.run(main.SentimentAnalyzer().analyze_finbert(list("abcdefghij")))
    assert calls == [(list("abcdefgh"), True)]  # top 8 only, long headlines truncated
    assert result["breakdown"] == {"positive": 8, "negative": 0, "neutral": 0}
    assert result["sentiment"] == "Bullish"
    assert result["score"] == 0.5
    assert result["confidence"] == 70.0


def test_no_headlines_is_neutral(monkeypatch):
    use_classifier(monkeypatch, None)  # must not be called
    assert asyncio.run(main.SentimentAnalyzer().analyze_finbert([])) == main.neutral_sentiment()


def test_model_failure_raises(monkeypatch):
    def broken():
        raise ImportError("transformers not installed")

    monkeypatch.setattr(main, "get_finbert", broken)
    with pytest.raises(ImportError):
        asyncio.run(main.SentimentAnalyzer().analyze_finbert(["a"]))


def test_sentiment_failure_falls_back_to_neutral_with_news(monkeypatch):
    main._fetch_headlines.cache_clear()
    main._headline_sentiment.cache_clear()

    async def headlines(symbol, max_items):
        return [{"title": "T", "link": "l", "published": "p"}]

    def broken():
        raise RuntimeError("no model")

    monkeypatch.setattr(main, "_fetch_headlines", headlines)
    monkeypatch.setattr(main, "get_finbert", broken)
    result = asyncio.run(REAL_FETCH_STOCK_NEWS("SENT.NS"))
    assert result["news"][0]["title"] == "T"
    assert result["sentiment"] == main.neutral_sentiment()


def rss(*titles):
    items = "".join(
        f"<item><title>{t}</title><link>https://x/{i}</link><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item>"
        for i, t in enumerate(titles)
    )
    return f"<rss><channel>{items}</channel></rss>".encode()


class FakeResponse:
    content = rss("Test Co wins a large order - Reuters")

    def raise_for_status(self):
        pass


def test_headlines_use_timeout_and_failures_are_not_cached(monkeypatch):
    main._fetch_headlines.cache_clear()
    calls = []

    async def name(symbol):
        return "Test Co Limited"

    monkeypatch.setattr(main, "_company_name", name)

    def fake_get(url, timeout=None, **kwargs):
        calls.append(timeout)
        if len(calls) == 1:
            raise requests.Timeout("slow")
        return FakeResponse()

    monkeypatch.setattr(main.requests, "get", fake_get)

    async def fetch_twice():
        with pytest.raises(requests.Timeout):
            await main._fetch_headlines("NEWS.NS", 5)
        return await main._fetch_headlines("NEWS.NS", 5)

    news = asyncio.run(fetch_twice())
    assert calls == [10, 10]
    assert news[0]["title"] == "Test Co wins a large order - Reuters"


def test_fetch_stock_news_falls_back_when_fetch_fails():
    # Network is blocked by the autouse fixture, so the headline fetch fails
    main._fetch_headlines.cache_clear()
    result = asyncio.run(REAL_FETCH_STOCK_NEWS("FAIL.NS"))
    assert result == {"news": [], "sentiment": main.neutral_sentiment()}


# ---------- headline relevance ----------

@pytest.mark.parametrize(
    "symbol, name, expected",
    [
        # Bare 'Reliance' is excluded: it would match 'Reliance Power' and 'reliance on ...'
        ("RELIANCE.NS", "Reliance Industries Limited", ["RELIANCE", "Reliance Industries"]),
        # Brand differs from the legal name, so the ticker word is needed
        ("GROWW.NS", "Billionbrains Garage Ventures Limited", ["Billionbrains Garage Ventures", "GROWW", "Groww"]),
        ("HDFCBANK.NS", "HDFC Bank Ltd.", ["HDFC Bank", "HDFCBANK", "Hdfcbank"]),
        # Yahoo sometimes echoes the ticker instead of a name
        ("IDEA.NS", "IDEA.NS", ["IDEA", "Idea"]),
        ("TCS.NS", None, ["TCS", "Tcs"]),
    ],
)
def test_company_search_terms(symbol, name, expected):
    assert main.company_search_terms(symbol, name) == expected


def test_relevant_headlines_filters_noise():
    titles = [
        "Reliance Industries shares rebound 15% in November - Mint",
        "Reliance Industries (RELIANCE) Share Price Today (NSE) - TechGraph",  # quote page
        "ICICI Bank Limited (ICICIBANK.NS) stock price, news, quote and history - Yahoo Finance",  # other company
        "Reliance Power shares soar 8% on Wednesday - ET",  # different company
        "India garment makers rethink reliance on US after tariff shock - Reuters",  # not the company
        "Reliance Industries shares rebound 15% in November - Business Standard",  # same story, other source
        "RELIANCE: Jefferies lists 11 stocks that can benefit - CNBC",
    ]
    kept = main.relevant_headlines(titles, ["RELIANCE", "Reliance Industries"], max_items=8)
    assert kept == [
        "Reliance Industries shares rebound 15% in November - Mint",
        "RELIANCE: Jefferies lists 11 stocks that can benefit - CNBC",
    ]


def test_relevant_headlines_respects_max_items():
    titles = [f"Groww story {i}" for i in range(20)]
    assert len(main.relevant_headlines(titles, ["Groww"], max_items=8)) == 8


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Vodafone Idea shares decline 3.5% - The Economic Times", "Vodafone Idea shares decline 3.5%"),
        # Text after the dash is too long to be a source name, so it's part of the headline
        ("Q2 results - what changed for investors and why it matters to the long-term thesis",
         "Q2 results - what changed for investors and why it matters to the long-term thesis"),
        ("No source here", "No source here"),
    ],
)
def test_headline_text_strips_source(title, expected):
    assert main.headline_text(title) == expected

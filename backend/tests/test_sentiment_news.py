"""Sentiment scoring and news fetching."""
import asyncio

import pytest
import requests

import main

# Captured at import, before the autouse fixture swaps in a stub for each test
REAL_FETCH_STOCK_NEWS = main.fetch_stock_news


class FakeHF:
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    async def text_classification(self, text, model):
        self.calls += 1
        if self.error:
            raise Exception(self.error)
        return [
            {"label": "positive", "score": 0.7},
            {"label": "negative", "score": 0.2},
            {"label": "neutral", "score": 0.1},
        ]


def analyzer_with(client):
    analyzer = main.SentimentAnalyzer(None)
    analyzer.client = client
    return analyzer


def test_breakdown_counts_one_label_per_headline():
    result = asyncio.run(analyzer_with(FakeHF()).analyze_finbert(["a", "b", "c"]))
    assert result["breakdown"] == {"positive": 3, "negative": 0, "neutral": 0}
    assert result["sentiment"] == "Bullish"
    assert result["score"] == 0.5


def test_no_client_is_neutral():
    assert asyncio.run(main.SentimentAnalyzer(None).analyze_finbert(["a"]))["sentiment"] == "Neutral"


def test_raises_when_nothing_scored():
    with pytest.raises(RuntimeError):
        asyncio.run(analyzer_with(FakeHF(error="boom")).analyze_finbert(["a", "b"]))


def test_stops_after_rate_limit(monkeypatch):
    async def no_sleep(seconds):
        return None

    monkeypatch.setattr(main.asyncio, "sleep", no_sleep)
    client = FakeHF(error="429 Too Many Requests")
    with pytest.raises(RuntimeError):
        asyncio.run(analyzer_with(client).analyze_finbert(["a", "b", "c", "d", "e"]))
    assert client.calls == 3  # retries for the first headline only


class FakeResponse:
    content = (
        b"<rss><channel><item><title>Headline</title><link>https://x</link>"
        b"<pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item></channel></rss>"
    )

    def raise_for_status(self):
        pass


def test_headlines_use_timeout_and_failures_are_not_cached(monkeypatch):
    main._fetch_headlines.cache_clear()
    calls = []

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
    assert news[0]["title"] == "Headline"


def test_fetch_stock_news_falls_back_when_fetch_fails():
    # Network is blocked by the autouse fixture, so the headline fetch fails
    main._fetch_headlines.cache_clear()
    result = asyncio.run(REAL_FETCH_STOCK_NEWS("FAIL.NS"))
    assert result == {"news": [], "sentiment": main.neutral_sentiment()}

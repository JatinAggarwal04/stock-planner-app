import asyncio
import feedparser
from async_lru import alru_cache

# Mocking the function from main.py
async def fetch_stock_news(symbol: str, max_items: int = 5):
    """Fetches latest news"""
    try:
        loop = asyncio.get_event_loop()
        
        import urllib.parse
        search_query = urllib.parse.quote(f"{symbol} stock news India when:7d")
        rss_url = f"https://news.google.com/rss/search?q={search_query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        print(f"Fetching URL: {rss_url}")
        
        # Async Feed Fetch using Executor
        feed = await loop.run_in_executor(None, feedparser.parse, rss_url)
        
        if feed.bozo:
            print(f"Feed Bozo Error: {feed.bozo_exception}")
            
        print(f"Entries found: {len(feed.entries)}")
        
        news = [{"title": x.title, "link": x.link, "published": x.published} for x in feed.entries[:max_items]]
        return news
    except Exception as e:
        print(f"News fetch error: {e}")
        return []

async def main():
    print("Testing News Fetch for RELIANCE.NS...")
    news = await fetch_stock_news("RELIANCE.NS")
    print(f"News: {news}")

    print("\nTesting News Fetch for TATAMOTORS.NS...")
    news = await fetch_stock_news("TATAMOTORS.NS")
    print(f"News: {news}")

if __name__ == "__main__":
    asyncio.run(main())

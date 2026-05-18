# =============================================================================
# news_client.py
# =============================================================================
# PURPOSE:
#   Fetches recent company news headlines from Finnhub for use in Claude
#   signal generation.
#
# ANALYST NOTE:
#   This module fills the biggest gap in the bot's analysis pipeline.
#   Without news context, Claude was generating HOLD signals with 40-60%
#   confidence because it couldn't assess catalysts. With headlines and
#   sentiment, signals become substantively more actionable.
#
#   The Finnhub free tier allows 60 calls/min — plenty of headroom for
#   our typical run of 15-20 tickers.
#
# DEPENDENCIES:
#   pip install finnhub-python python-dotenv
#
# USAGE:
#   from news_client import get_recent_headlines
#   headlines = get_recent_headlines("AAPL", days_back=7, limit=5)
# =============================================================================

import os
import finnhub
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Pull API key from .env
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# Initialize Finnhub client once at module load
# ANALYST NOTE: Reusing a single client across calls is more efficient
# than creating new clients per request.
_client = None


def get_client():
    """
    Return the cached Finnhub client, creating one if needed.

    ANALYST NOTE:
        Lazy initialization — the client is only created on first use,
        which means the bot doesn't break at import time if the API key
        is missing. Better error messages downstream.
    """
    global _client
    if _client is None:
        if not FINNHUB_API_KEY:
            raise ValueError(
                "FINNHUB_API_KEY is not set in .env. "
                "Sign up at finnhub.io to get a free key."
            )
        _client = finnhub.Client(api_key=FINNHUB_API_KEY)
    return _client


# =============================================================================
# HEADLINE FETCHER
# =============================================================================

def get_recent_headlines(ticker: str, days_back: int = 7,
                         limit: int = 5) -> list:
    """
    Fetch recent news headlines for a ticker from Finnhub.

    ANALYST NOTE:
        Finnhub's company_news endpoint returns a list of articles for the
        specified ticker between two dates. Each article has datetime,
        headline, summary, source, and URL fields.

        We extract just the headline + source for token efficiency since
        we'll be passing these to Claude. Including full article summaries
        would dramatically increase Claude API costs without significantly
        improving signal quality at this stage.

    Args:
        ticker    (str): Stock symbol e.g. "AAPL"
        days_back (int): How many days of news to look back. Default 7.
        limit     (int): Max headlines to return. Default 5.

    Returns:
        list: List of headline strings, most recent first. Empty on failure.
    """
    try:
        client = get_client()

        # Build date range — Finnhub expects YYYY-MM-DD format
        today  = datetime.now()
        past   = today - timedelta(days=days_back)
        date_to   = today.strftime("%Y-%m-%d")
        date_from = past.strftime("%Y-%m-%d")

        # Fetch news from Finnhub
        # ANALYST NOTE: Finnhub returns articles in reverse chronological
        # order by default (newest first), so we can just slice off the
        # top N to get the most relevant recent items.
        articles = client.company_news(ticker, _from=date_from, to=date_to)

        if not articles:
            return []

        # Build headlines list — format as "Source: Headline"
        # ANALYST NOTE: Including the source gives Claude context about
        # credibility. A Bloomberg headline carries different weight than
        # a SeekingAlpha opinion piece.
        headlines = []
        for article in articles[:limit]:
            headline = article.get("headline", "").strip()
            source   = article.get("source", "Unknown").strip()
            if headline:
                headlines.append(f"[{source}] {headline}")

        return headlines

    except Exception as e:
        print(f"[news_client] Error fetching news for {ticker}: {e}")
        return []


def get_headlines_with_summaries(ticker: str, days_back: int = 7,
                                  limit: int = 3) -> list:
    """
    Fetch headlines WITH summaries — uses more Claude tokens but richer context.

    ANALYST NOTE:
        Use this version when you want Claude to have full article context
        instead of just headlines. Costs roughly 3x more Claude tokens per
        signal but produces substantially more nuanced analysis. Default
        is 3 articles vs 5 to balance the token increase.

    Args:
        ticker    (str): Stock symbol
        days_back (int): How many days back
        limit     (int): Max articles

    Returns:
        list: List of dicts with 'headline', 'summary', 'source'
    """
    try:
        client = get_client()

        today = datetime.now()
        past  = today - timedelta(days=days_back)
        date_to   = today.strftime("%Y-%m-%d")
        date_from = past.strftime("%Y-%m-%d")

        articles = client.company_news(ticker, _from=date_from, to=date_to)

        if not articles:
            return []

        results = []
        for article in articles[:limit]:
            results.append({
                "headline": article.get("headline", "").strip(),
                "summary" : article.get("summary", "").strip()[:300],  # Cap summary length
                "source"  : article.get("source", "Unknown").strip(),
                "url"     : article.get("url", ""),
            })

        return results

    except Exception as e:
        print(f"[news_client] Error fetching news with summaries for {ticker}: {e}")
        return []

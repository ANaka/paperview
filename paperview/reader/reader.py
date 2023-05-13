from typing import List, Dict
from datetime import datetime
from time import mktime
import time
from feedparser import parse
from models import Feed, Article, Subscription
from tortoise.exceptions import DoesNotExist
import feedparser

# A function to subscribe to a new feed
async def subscribe_to_feed(url: str) -> bool:
    parsed = feedparser.parse(url)
    if parsed.bozo:  # bozo flag is set when feedparser encounters an issue parsing the feed
        return False

    feed, _ = await Feed.get_or_create(url=url, title=parsed.feed.title)
    await Subscription.get_or_create(feed_id=feed.id)

    return True


# A function to get all feeds
async def get_all_feeds() -> list:
    feeds = await Feed.all().prefetch_related('subscriptions')
    return [feed.url for feed in feeds]


# A function to get latest articles
async def get_latest_articles() -> list:
    articles = await Article.all().order_by('-publication_date').limit(10)
    return [article.title for article in articles]


# A function to mark an article as interesting
async def mark_as_interesting(article_url: str, interesting: bool) -> bool:
    try:
        article = await Article.get(url=article_url)
    except DoesNotExist:
        return False

    article.interesting = interesting
    await article.save()

    return True


# A function to refresh feeds and add new articles

async def refresh_feeds():
    failed_feeds = []
    feeds = await Feed.all().prefetch_related('subscriptions')

    for feed in feeds:
        try:
            parsed = feedparser.parse(feed.url)
            for entry in parsed.entries:
                defaults = {
                    "title": entry.get("title", "No title provided"),
                    "summary": entry.get("summary", "No summary provided"),
                    "publication_date": datetime.fromtimestamp(mktime(entry.get("published_parsed", time.gmtime(0)))),
                    "author": entry.get("author", "No author provided"),
                    "url": entry.get("link", "No link provided"),
                }
                await Article.get_or_create(feed_id=feed.id, defaults=defaults)
        except Exception as e:
            failed_feeds.append({
                "feed_id": feed.id,
                "feed_url": feed.url,
                "error": str(e),
            })
    return failed_feeds
import time

from fastapi import FastAPI, HTTPException
from tortoise.contrib.fastapi import register_tortoise, HTTPNotFoundError
from pydantic import BaseModel
from typing import List, Optional
from celery import shared_task, Celery
from reader import subscribe_to_feed, get_all_feeds, get_latest_articles, mark_as_interesting, refresh_feeds

from config import settings

app = FastAPI()


celery = Celery(
    __name__,
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

@celery.task
def send_push_notification(device_token: str):
    time.sleep(10)  # simulates slow network call to firebase/sns
    with open("notification.log", mode="a") as notification_log:
        response = f"Successfully sent push notification to: {device_token}\n"
        notification_log.write(response)

@app.get("/push/{device_token}")
async def notify(device_token: str):
    send_push_notification.delay(device_token)
    return {"message": "Notification sent"}

# Register Tortoise ORM with FastAPI
register_tortoise(
    app,
    db_url='sqlite://db.sqlite3',
    modules={'models': ['models']},
    generate_schemas=True,
    add_exception_handlers=True,
)


class Feed(BaseModel):
    url: str

class Article(BaseModel):
    url: str
    interesting: Optional[bool] = None

@app.get("/")
def read_root():
    return {"message": "Welcome to PaperView, your personal scientific literature RSS reader."}


@app.post("/feeds/")
async def create_feed(feed: Feed):
    if not await subscribe_to_feed(feed.url):
        raise HTTPException(status_code=400, detail="Invalid RSS feed URL")
    return {"url": feed.url}

@app.get("/feeds/")
async def read_feeds():
    return {"feeds": await get_all_feeds()}

@app.get("/articles/")
async def read_articles():
    return {"articles": await get_latest_articles()}

@app.patch("/articles/")
async def update_article(article: Article):
    if not await mark_as_interesting(article.url, article.interesting):
        raise HTTPException(status_code=404, detail="Article not found")
    return {"url": article.url, "interesting": article.interesting}

@app.post("/refresh/")
async def refresh():
    resp = await refresh_feeds()
    return {"message": "Feeds refreshed successfully", "resp": resp}

from tortoise.models import Model
from tortoise import fields

class Feed(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(200)
    url = fields.CharField(500)

class Article(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(200)
    summary = fields.TextField()
    publication_date = fields.DatetimeField()
    author = fields.CharField(100)
    url = fields.CharField(500)
    feed = fields.ForeignKeyField('models.Feed', related_name='articles')

class Subscription(Model):
    id = fields.IntField(pk=True)
    feed = fields.ForeignKeyField('models.Feed', related_name='subscriptions')

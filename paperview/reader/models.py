from tortoise.models import Model
from tortoise import fields

class Feed(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(200)
    url = fields.CharField(500)

class Article(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(200, null=True)
    summary = fields.TextField(null=True)
    publication_date = fields.DatetimeField(null=True)
    author = fields.CharField(500, null=True)
    url = fields.CharField(500, null=True)
    feed = fields.ForeignKeyField('models.Feed', related_name='articles')

class Subscription(Model):
    id = fields.IntField(pk=True)
    feed = fields.ForeignKeyField('models.Feed', related_name='subscriptions')

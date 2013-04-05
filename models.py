from google.appengine.ext import db


class Message(db.Model):
  conversation_partner = db.StringProperty()
  author = db.StringProperty()
  content = db.TextProperty()
  creation_time = db.DateTimeProperty()


class User(db.Model):
  name = db.StringProperty()
  fb_id = db.StringProperty()
  access_token = db.StringProperty()

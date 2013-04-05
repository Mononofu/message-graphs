from google.appengine.ext import db


class User(db.Model):
  name = db.StringProperty()
  fb_id = db.StringProperty()
  access_token = db.StringProperty()


class Message(db.Model):
  owner = db.ReferenceProperty(reference_class=User)
  conversation_partner = db.StringProperty()
  conversation_partner_id = db.StringProperty()
  author = db.StringProperty()
  author_id = db.StringProperty()
  content = db.TextProperty()
  creation_time = db.DateTimeProperty()

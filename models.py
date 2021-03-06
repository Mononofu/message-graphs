import db

class User(db.Model):
  name = db.StringProperty(filename_pos=1)
  fb_id = db.StringProperty()
  access_token = db.StringProperty()


class Contact(db.Model):
  name = db.StringProperty()
  fb_id = db.StringProperty()
  gender = db.StringProperty()


class Message(db.Model):
  owner_id = db.StringProperty()
  conversation_partner = db.StringProperty(key_level=1)
  conversation_partner_id = db.StringProperty()
  author = db.StringProperty(filename_pos=2)
  author_id = db.StringProperty()
  content = db.TextProperty()
  creation_time = db.DateTimeProperty(filename_pos=1)

# -*- coding: utf-8 -*-
import db
import models
import unittest
import datetime

class TestDbModel(unittest.TestCase):
  def setUp(self):
    models.User.clear()
    models.Message.clear()

  def test_objectCreation(self):
    user = models.User(name="test")

  def test_objectFieldsPresent(self):
    user = models.User(name="test")
    self.assertEqual(user.name, "test")

  def test_objectHasKey(self):
    user = models.User(name="test")
    self.assertIsNotNone(user.key())

  def test_objectPut(self):
    user = models.User(name="test")
    user.put()

  def test_objectPutAndGet(self):
    user = models.User(name="test")
    key = user.key()
    user.put()
    restored_user = models.User.get(key)
    self.assertEqual(restored_user.name, user.name)

  def test_objectPutAndQuery(self):
    user = models.User(name="test")
    user.put()
    restored_user = models.User.all().filter("name =", "test").get()
    self.assertEqual(restored_user.name, user.name)

  def test_objectOrdered(self):
    models.User(name="john").put()
    models.User(name="alf").put()
    models.User(name="snow").put()
    first_user = models.User.all().order('name').get()
    last_user = models.User.all().order('-name').get()
    self.assertEqual(first_user.name, "alf")
    self.assertEqual(last_user.name, "snow")

  def test_objectPutAndQueryWithDate(self):
    msg = models.Message(author="Julian", creation_time=datetime.datetime.now())
    msg.put()
    restored_msg = models.Message.all().filter("author =", "Julian").get()
    self.assertEqual(restored_msg.author, msg.author)
    self.assertEqual(restored_msg.creation_time, msg.creation_time)

  def test_objectPutAndGetUnicode(self):
    user = models.User(name=u"test日本")
    key = user.key()
    user.put()
    restored_user = models.User.get(key)
    self.assertEqual(restored_user.name, user.name)

  def test_objectPutAndGetIdenticalKeys(self):
    user1 = models.User(name="test", fb_id="1")
    user1.put()
    user2 = models.User(name="test", fb_id="2")
    user2.put()
    self.assertEqual(models.User.get(user1.key()).fb_id, user1.fb_id)
    self.assertEqual(models.User.get(user2.key()).fb_id, user2.fb_id)

  def test_objectPutAndGetWithSpaces(self):
    user = models.User(name="Julian Schrittwieser", fb_id="1")
    user.put()
    self.assertEqual(models.User.get(user.key()).name, user.name)

if __name__ == '__main__':
  unittest.main()

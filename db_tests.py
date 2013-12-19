import db
import models
import unittest

class TestDbModel(unittest.TestCase):
  def setUp(self):
    models.User.clear()

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
    print key
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

if __name__ == '__main__':
  unittest.main()

import db
import models
import unittest

class TestDbModel(unittest.TestCase):
  def test_objectCreation(self):
    user = models.User(name="test")

  def test_objectFieldsPresent(self):
    user = models.User(name="test")
    self.assertEqual(user.name, "test")

  def test_objectPut(self):
    user = models.User(name="test")
    user.put()

  def test_objectPutAndLoad(self):
    user = models.User(name="test")
    user.put()
    restored_user = models.User.all().filter("name =", "test").get()
    self.assertEqual(restored_user.name, user.name)

if __name__ == '__main__':
  unittest.main()

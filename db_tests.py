import db
import models
import unittest

class TestDbModel(unittest.TestCase):
  def test_objectCreation(self):
    user = models.User(name="test")

  def test_objectFieldsPresent(self):
    user = models.User(name="test")
    self.assertEqual(user.name, "test")

if __name__ == '__main__':
  unittest.main()

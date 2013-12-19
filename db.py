import inspect
import json
import os

DB_PREFIX = "db"

class Filter(object):
  def __init__(self, property_name, operator, value):
    self.property_name = property_name
    self.operator = operator
    self.value = value

  def satisfied_by(self, instance):
    if self.operator == "=":
      return getattr(instance, self.property_name) == self.value
    else:
      raise RuntimeError("operator %s not implemented" % self.operator)

class Query(object):
  def __init__(self, model, filters = None):
    self.model = model
    if filters:
      self.filters = filters
    else:
      self.filters = []

  def filter(self, property_operator, value):
    name = property_operator
    operator = "="
    if " " in property_operator:
      name, operator = property_operator.split(" ", 1)
    return Query(self.model, self.filters + [Filter(name, operator, value)])

  def get(self):
    for instance in self._generate_instances():
      if self._satisfies_filters(instance):
        return instance
    return None

  def run(self):
    for instance in self._generate_instances():
      if self._satisfies_filters(instance):
        yield instance

  def _generate_instances(self):
    name = self.model.__name__
    path = os.path.join(DB_PREFIX, name)
    for (dirpath, dirnames, filenames) in os.walk(path):
      for filename in filenames:
        filepath = os.path.join(dirpath, filename)
        with open(filepath) as f:
          data = json.loads(f.read())
          instance = self.model()
          for name, value in data.iteritems():
            setattr(instance, name, value)
          yield instance

  def _satisfies_filters(self, instance):
    for filter in self.filters:
      if not filter.satisfied_by(instance):
        return False
    return True


class Property(object):
  def __init__(self, default=None, key_level=None):
    self.default = default
    self.key_level = key_level

class StringProperty(Property):
  pass

class TextProperty(Property):
  pass

class DateTimeProperty(Property):
  pass

class Model(object):
  def __init__(self, *args, **kwargs):
    self.properties = dict([(n, v) for n, v in inspect.getmembers(self)
                            if isinstance(v, Property)])
    for name, type in self.properties.iteritems():
      setattr(self, name, type.default)
    self.keys = [(n, v) for n, v in self.properties.iteritems() if v.key_level]
    self.keys = sorted(self.keys, key=lambda (n, v): v.key_level)
    for name, value in kwargs.iteritems():
      if name not in self.properties:
        raise RuntimeError("%s is not a property of %s" % (name, self.__class__.__name__))
      setattr(self, name, value)

  @classmethod
  def all(cls):
    return Query(cls)

  def put(self):
    name = self.__class__.__name__
    path = os.path.join(DB_PREFIX, name)
    for name, type in self.keys:
      path = os.path.join(path, getattr(self, name))

    d = os.path.dirname(path)
    if not os.path.exists(d):
      os.makedirs(d)
    with open(path, 'w') as f:
      data = {}
      for name in self.properties:
        data[name] = getattr(self, name)
      f.write(json.dumps(data))

  def __str__(self):
    return "%s(%s)" % (self.__class__.__name__,
      ', '.join(['%s=%s' % (n, getattr(self, n)) for n in self.properties]))

import inspect
import json
import shutil
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
  def __init__(self, instances):
    self.instances = instances

  def filter(self, property_operator, value):
    def _filter(instances):
      for instance in instances:
        if f.satisfied_by(instance):
          yield instance

    name = property_operator
    operator = "="
    if " " in property_operator:
      name, operator = property_operator.split(" ", 1)
    f = Filter(name, operator, value)

    return Query(_filter(self.instances))

  def order(self, property):
    instances = list(self.instances)
    reverse = property.startswith("-")
    property_name = property.strip("-")
    instances = sorted(instances, key=lambda i: getattr(i, property_name),
                       reverse=reverse)
    return Query(instances)

  def get(self):
    for instance in self.instances:
      return instance
    return None

  def run(self):
    for instance in self.instances:
      yield instance


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
  key_counter = 0

  def __init__(self, *args, **kwargs):
    self.properties = dict([(n, v) for n, v in inspect.getmembers(self)
                            if isinstance(v, Property)])
    for name, type in self.properties.iteritems():
      setattr(self, name, type.default)
    self.keys = [(n, v) for n, v in self.properties.iteritems() if v.key_level]
    self.keys = sorted(self.keys, key=lambda (n, v): v.key_level)
    for name, value in kwargs.iteritems():
      if name not in self.properties and name != "_key":
        raise RuntimeError("%s is not a property of %s" % (name, self.__class__.__name__))
      setattr(self, name, value)

    if '_key' not in kwargs:
      self._key = Model.key_counter
      Model.key_counter += 1
      self.properties["_key"] = StringProperty()

  @classmethod
  def clear(cls):
    shutil.rmtree(os.path.join(DB_PREFIX, cls.__name__), ignore_errors=True)

  @classmethod
  def from_string(cls, string):
    data = json.loads(string)
    return cls(**data)

  @classmethod
  def get(cls, key):
    name = cls.__name__
    path = os.path.join(DB_PREFIX, name)

    index_path = os.path.join(path, '_index')

    if not os.path.exists(index_path):
      return None

    # this reads the whole index on every get and reorganizes it. might be a bit
    # inefficent.
    files = {}
    with open(index_path) as f:
      for line in f.read().strip().split('\n'):
        key, path = line.split(":")
        files[key] = path
    with open(index_path, 'w') as f:
      for key, path in files.iteritems():
        f.write("%s:%s\n" % (key, path))

    if key not in files:
      return None

    with open(files[key]) as f:
      return cls.from_string(f.read())

  @classmethod
  def all(cls):
    return Query(cls._generate_instances())

  def key(self):
    return self._key

  def put(self):
    name = self.__class__.__name__
    path = os.path.join(DB_PREFIX, name)

    index_path = os.path.join(path, '_index')
    for name, type in self.keys:
      path = os.path.join(path, getattr(self, name))

    d = os.path.dirname(path)
    if not os.path.exists(d):
      os.makedirs(d)

    with open(index_path, 'a+') as f:
      f.write('%s:%s\n' % (self.key(), path))

    with open(path, 'w') as f:
      data = {}
      for name in self.properties:
        data[name] = getattr(self, name)
      f.write(json.dumps(data))

  def __str__(self):
    return "%s(%s)" % (self.__class__.__name__,
      ', '.join(['%s=%s' % (n, getattr(self, n)) for n in self.properties]))

  @classmethod
  def _generate_instances(cls):
    name = cls.__name__
    path = os.path.join(DB_PREFIX, name)
    for (dirpath, dirnames, filenames) in os.walk(path):
      for filename in filenames:
        if filename == "_index":
          continue

        filepath = os.path.join(dirpath, filename)
        with open(filepath) as f:
          yield cls.from_string(f.read())

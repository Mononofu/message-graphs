import inspect
import json
import shutil
import datetime
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

  def __call__(self):
    return self.run()


class Property(object):
  def __init__(self, default=None, key_level=None, filename_pos=None):
    self.default = default
    self.key_level = key_level
    self.filename_pos = filename_pos

  def serialize(self, data, pretty=False):
    return unicode(data)

  def deserialize(self, string):
    return string

class StringProperty(Property):
  pass

class TextProperty(Property):
  pass

class DateTimeProperty(Property):
  _date_format = "%Y-%m-%d_%H:%M:%S.%f"
  _date_format_pretty = "%Y-%m-%d_%H:%M:%S"

  def serialize(self, data, pretty=False):
    if pretty:
      return data.strftime(self._date_format_pretty)
    else:
      return data.strftime(self._date_format)

  def deserialize(self, string):
    return datetime.datetime.strptime(string, self._date_format)

class Model(object):
  key_counter = 0

  _key = StringProperty()

  def __init__(self, *args, **kwargs):
    self.properties = dict([(n, v) for n, v in inspect.getmembers(self)
                            if isinstance(v, Property)])
    for name, type in self.properties.iteritems():
      setattr(self, name, type.default)
    self.keys = [(n, v) for n, v in self.properties.iteritems() if v.key_level]
    self.keys = sorted(self.keys, key=lambda (n, v): v.key_level)
    self.filename_parts = [(n, v) for n, v in self.properties.iteritems()
                           if v.filename_pos]
    self.filename_parts = sorted(self.filename_parts,
                                 key=lambda (n, v): v.filename_pos)
    for name, value in kwargs.iteritems():
      if name not in self.properties:
        raise RuntimeError("%s is not a property of %s" % (name, self.__class__.__name__))
      setattr(self, name, value)

    if '_key' not in kwargs:
      self._key = Model.key_counter
      Model.key_counter += 1

  @classmethod
  def clear(cls):
    shutil.rmtree(os.path.join(DB_PREFIX, cls.__name__), ignore_errors=True)

  @classmethod
  def from_string(cls, string):
    raw_data = json.loads(string)
    data = {}
    for name, value in raw_data.iteritems():
      type = getattr(cls, name)
      data[name] = type.deserialize(value)
    return cls(**data)

  @classmethod
  def get(cls, target_key):
    index_path = cls._index_path()
    if not os.path.exists(index_path):
      return None

    # this reads the whole index on every get and reorganizes it. might be a bit
    # inefficent.
    files = {}
    with open(index_path) as f:
      for line in f.read().strip().split('\n'):
        key, path = line.split(":")
        files[int(key)] = path
    with open(index_path, 'w') as f:
      for key, path in files.iteritems():
        f.write("%s:%s\n" % (key, path))

    if target_key not in files:
      return None

    with open(files[target_key]) as f:
      return cls.from_string(f.read())

  @classmethod
  def all(cls):
    return Query(cls._generate_instances())

  @classmethod
  def delete(cls, key):
    instance = cls.get(key)
    if instance:
      instance.delete()

  def key(self):
    return self._key

  def put(self):
    path = self._path()
    d = os.path.dirname(path)
    if not os.path.exists(d):
      os.makedirs(d)

    with open(self._index_path(), 'a+') as f:
      f.write(u'{0}:{1}\n'.format(self.key(), path).encode("utf-8"))

    with open(path, 'w') as f:
      data = {}
      for name, type in self.properties.iteritems():
        data[name] = type.serialize(getattr(self, name))
      f.write(json.dumps(data).encode("utf-8"))

  def delete(self):
    if os.path.exists(self._path()):
      os.remove(self._path())

  def __str__(self):
    return u"%s(%s)" % (self.__class__.__name__,
      u', '.join([u'%s=%s' % (n, getattr(self, n)) for n in self.properties]))

  @classmethod
  def _generate_instances(cls):
    name = cls.__name__
    path = os.path.join(DB_PREFIX, name)
    for (dirpath, dirnames, filenames) in os.walk(path):
      for filename in filenames:
        if filename == u"_index":
          continue

        filepath = os.path.join(dirpath, filename)
        with open(filepath) as f:
          yield cls.from_string(f.read())

  @classmethod
  def _index_path(cls):
    path = os.path.join(DB_PREFIX, cls.__name__)
    return os.path.join(path, u'_index')

  def _path(self):
    path = os.path.join(DB_PREFIX, self.__class__.__name__)
    for name, type in self.keys:
      path = os.path.join(path, type.serialize(getattr(self, name), pretty=True))
    filename = u"_".join([type.serialize(getattr(self, name), pretty=True)
                         for name, type in self.filename_parts])
    path = os.path.join(path, u"%s_%s.json" % (filename, self.key()))
    return path


import inspect

class Filter(object):
  def __init__(self, filter, value):
    self.filter = filter
    self.value = value

class Query(object):
  def __init__(self, model, filters = None):
    self.model = model
    if filters:
      self.filters = filters
    else:
      self.filters = []

  def filter(self, filter, value):
    return Query(self.model, self.filters + [Filter(filter, value)])

  def get(self):
    return 0


class Property(object):
  def __init__(self, default=None):
    self.default = default

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
    for name, value in kwargs.iteritems():
      if name not in self.properties:
        raise RuntimeError("%s is not a property of %s" % (name, self.__class__.__name__))
      setattr(self, name, value)

  def all(self):
    return Query(self)

  def __str__(self):
    return "%s(%s)" % (self.__class__.__name__,
      ', '.join(['%s=%s' % (n, getattr(self, n)) for n in self.properties]))

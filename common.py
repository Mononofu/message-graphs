import urllib3
import logging
import inspect

from flask import Flask


class MyPoolManager(urllib3.PoolManager):
  def request(self, method, url, fields={}):
    f = inspect.currentframe().f_back
    mod = f.f_code.co_filename
    lineno = f.f_lineno

    logging.info("Calling %s with %s from %s.%d" % (url, fields, mod, lineno))
    r = super(MyPoolManager, self).request_encode_url(method, url, fields=fields)
    logging.info("Reply: %s" % r.data)
    return r


pool = MyPoolManager()

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_object('conf.Config')
app.debug = True

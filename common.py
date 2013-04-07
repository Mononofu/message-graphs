import urllib3
import logging
import inspect
from functools import wraps
from flask import Flask, session, redirect, url_for, render_template, request
import random

from conf import Config
from models import User


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


def render(template, **kwargs):
  return render_template(template, active_page=request.path, **kwargs)


def require_login():
  def wrapper(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
      if not 'user_key' in session:
        logging.info("Starting login")
        rand_state = str(random.randint(100, 10000000))
        oauth_url_code = "https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&state=%s&scope=read_mailbox" % (Config.FBAPI_APP_ID, "http://localhost:8888/fb_login", rand_state)
        session["state"] = rand_state
        return redirect(oauth_url_code)

      user = User.get(session['user_key'])
      if not user:
        session.pop('user_key', None)
        return redirect(url_for('index'))

      return f(*args, user=user, **kwargs)
    return wrapped
  return wrapper

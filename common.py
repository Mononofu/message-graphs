import urllib3
import logging
import inspect
from functools import wraps
from flask import Flask, session, redirect, url_for, render_template, request
import random
from celery import Celery

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

def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

pool = MyPoolManager()

app = Flask(__name__)
app.config.from_pyfile('conf.py')
app.debug = True
celery = make_celery(app)

def render(template, **kwargs):
  return render_template(template, active_page=request.path, **kwargs)

def require_login():
  def wrapper(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
      if not 'user_key' in session:
        logging.info("Starting login")
        rand_state = str(random.randint(100, 10000000))
        oauth_url_code = "https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&state=%s&scope=%s" % (
          app.config.get('FBAPI_APP_ID'), "http://localhost:%d/fb_login" % app.config.get('PORT'),
          rand_state,
          ",".join(app.config['FBAPI_SCOPE']))
        session["state"] = rand_state
        return redirect(oauth_url_code)

      user = User.get(session['user_key'])
      if not user:
        session.pop('user_key', None)
        return redirect(url_for('index'))

      return f(*args, user=user, **kwargs)
    return wrapped
  return wrapper

# -*- coding: utf-8 -*-
import json
import logging
import random
import urlparse
from functools import wraps

from flask import request, redirect, render_template, url_for, flash, session, abort

from common import pool, app
from fb_auth import get_token, fb_call
from conf import Config
from MessageFetcher import *
from models import *

from google.appengine.api import memcache

FB_APP_ID = Config.FBAPI_APP_ID
FB_APP_SECRET = Config.FBAPI_APP_SECRET


def require_login():
  def wrapper(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
      if not 'user_key' in session:
        logging.info("Starting login")
        rand_state = str(random.randint(100, 10000000))
        oauth_url_code = "https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&state=%s&scope=read_mailbox" % (FB_APP_ID, "http://localhost:8888/fb_login", rand_state)
        session["state"] = rand_state
        return redirect(oauth_url_code)
      return f(*args, user=User.get(session['user_key']), **kwargs)
    return wrapped
  return wrapper



@app.route('/fb_login/')
def fb_login():
  logging.info("callback from facebook")
  state = request.args.get('state')
  if not state:
    logging.error("state not present, possibly auth declined")
    abort(401)

  if session['state'] != state:
    logging.error("%s != %s, possible XSRF" % (session['state'], state))
    abort(401)

  code = request.args.get('code')
  oauth_url_access = "https://graph.facebook.com/oauth/access_token?client_id=%s&redirect_uri=%s&client_secret=%s&code=%s" % (FB_APP_ID, "http://localhost:8888/fb_login", FB_APP_SECRET, code)

  reply = urlparse.parse_qs(pool.request('GET', oauth_url_access).data)
  logging.info(reply)
  token = reply["access_token"][0]

  me = fb_call('me', args={'access_token': token,
                           'fields': 'id, name'})

  u = User.all().filter("id =", me["id"]).get()
  if u:
    u.access_token = token
    u.name = me["name"]
    u.put()
  else:
    # new user, create object
    u = User(name=me['name'], id=me['id'], access_token=token)
    u.put()
  session['user_key'] = str(u.key())
  return redirect(url_for('index'))


@app.route('/')
@require_login()
def index(user):
  #me = fb_call('me', args={'access_token': user.access_token})

  return render_template('index.html', app_id=FB_APP_ID, user_name=user.name)



@app.route('/drop/')
def drop():
  query = Message.all(keys_only=True)
  entries = query.fetch(5000)
  db.delete(entries)

  flash("Cleared messages")
  return redirect(url_for('index'))


@app.route('/download/', methods=['GET'])
@require_login()
def download(user):
  m = MessageFetcher(user.name)
  m.run()

  flash("Started download")
  return redirect(url_for('index'))


@app.route('/partners/')
@require_login()
def partners(user):
  partners = []
  for proj in db.Query(Message, projection=['conversation_partner'],
                       distinct=True):
    partners.append(proj.conversation_partner)
  return render_template('partners.html', partners=partners, app_id=FB_APP_ID,
                         user_name=user.name)


@app.route('/logout/')
@require_login()
def logout(user):
  session.pop('user_key', None)
  return redirect(url_for('index'))


if __name__ == '__main__':
  port = 3434
  if app.config.get('FB_APP_ID') and app.config.get('FB_APP_SECRET'):
    app.run(host='0.0.0.0', port=port)
  else:
    print 'Cannot start application without Facebook App Id and Secret set'

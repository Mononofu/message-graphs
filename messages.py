# -*- coding: utf-8 -*-
import logging
import urlparse
import re

from flask import request, redirect, url_for, flash, session, abort

from common import pool, app, require_login, render
from fb_auth import fb_call
from MessageFetcher import *
from models import *
from calculation import *
import graphs
import stats

FB_APP_ID = app.config.get('FBAPI_APP_ID')
FB_APP_SECRET = app.config.get('FBAPI_APP_SECRET')

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

  u = User.all().filter("fb_id =", me["id"]).get()
  if u:
    u.access_token = token
    u.name = me["name"]
    u.fb_id = me["id"]
    u.put()
  else:
    # new user, create object
    u = User(name=me['name'], fb_id=me['id'], access_token=token)
    u.put()
  session['user_key'] = str(u.key())
  return redirect(url_for('index'))


@app.route('/')
@require_login()
def index(user):
  logging.info(request.path)
  #me = fb_call('me', args={'access_token': user.access_token})

  return render('index.html', user_name=user.name)


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
  m = MessageFetcher(user)
  m.run()

  flash("Started download")
  return redirect(url_for('index'))


@app.route('/show/words/<fb_id>/')
@require_login()
def show_words_for(user, fb_id):
  word_list = memcache.get("word_list_" + fb_id + "-" + user.fb_id)

  if not word_list:
    url_re = """((http[s]?|ftp):\/)?\/?([^:\/\s]+)(:([^\/]*))?((\/\w+)*\/)([\w\-\.]+[^#?\s]+)(\?([^#]*))?(#(.*))?"""
    word_list = []
    for msg in Message.all().filter("conversation_partner_id =", fb_id):
      for word in msg.content.split(" "):
        if not re.match(url_re, word):
          word_list.append(word)
    memcache.put("word_list_" + fb_id + "-" + user.fb_id, word_list)

  return render('show.html', entries=word_list, user_name=user.name)


@app.route('/logout/')
@require_login()
def logout(user):
  session.pop('user_key', None)
  User.delete(user)
  return redirect(url_for('index'))


@app.route('/session/clear/')
def session_clear():
  session.pop('user_key', None)
  return redirect(url_for('index'))


if __name__ == '__main__':
  if app.config.get('FBAPI_APP_ID') and app.config.get('FBAPI_APP_SECRET'):
    app.run(host='0.0.0.0', port=app.config.get('PORT'), debug=True)
  else:
    print 'Cannot start application without Facebook App Id and Secret set'
    print app.config

# -*- coding: utf-8 -*-
import json
import logging
import random
import urlparse
from functools import wraps
from collections import defaultdict
import operator

from flask import request, redirect, render_template, url_for, flash, session, abort

from common import pool, app
from fb_auth import fb_call
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


def render(template, **kwargs):
  return render_template(template, active_page=request.path, **kwargs)


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


@app.route('/stats/partners/')
@require_login()
def partners(user):
  partners = memcache.get("partners" + user.fb_id)

  if not partners:
    partners = []
    for proj in db.Query(Message, projection=['conversation_partner'],
                         distinct=True).filter("owner =", user):
      partners.append(proj.conversation_partner)
    memcache.set(key="partners" + user.fb_id, value=partners)

  return render('partners.html', partners=partners, user_name=user.name)


@app.route('/stats/messages/count/')
@require_login()
def message_count(user):
  msg_cnt_lst = memcache.get("msg_cnt_lst" + user.fb_id)

  if not msg_cnt_lst:
    msg_cnt = defaultdict(int)
    for msg in Message.all():
      msg_cnt[msg.conversation_partner] += 1

    msg_cnt_lst = sorted(msg_cnt.iteritems(),
                         key=operator.itemgetter(1), reverse=True)
    memcache.set(key="msg_cnt_lst" + user.fb_id, value=msg_cnt_lst)

  return render('message_count.html', partners=msg_cnt_lst,
                user_name=user.name)


@app.route('/stats/messages/length/')
@require_login()
def message_length(user):
  msg_avg_len = memcache.get("msg_avg_len" + user.fb_id)
  msg_cnt = memcache.get("msg_cnt" + user.fb_id)

  if not msg_avg_len or not msg_cnt:
    msg_len = defaultdict(int)
    msg_cnt = defaultdict(int)
    for msg in Message.all():
      msg_len[msg.conversation_partner] += len(msg.content)
      msg_cnt[msg.conversation_partner] += 1

    msg_avg_len = {}
    for name, count in msg_cnt.iteritems():
      if count >= 10:
        msg_avg_len[name] = msg_len[name] / count

    msg_avg_len = sorted(msg_avg_len.iteritems(),
                         key=operator.itemgetter(1), reverse=True)
    memcache.set(key="msg_avg_len" + user.fb_id, value=msg_avg_len)
    memcache.set(key="msg_cnt" + user.fb_id, value=msg_cnt)

  return render('message_length.html', msg_avg_len=msg_avg_len,
                msg_cnt=msg_cnt, user_name=user.name)


@app.route('/stats/words/length/')
@require_login()
def word_length(user):
  word_avg_len = memcache.get("word_avg_len" + user.fb_id)
  word_cnt = memcache.get("word_cnt" + user.fb_id)

  if not word_avg_len or not word_cnt:
    word_len = defaultdict(int)
    word_cnt = defaultdict(int)
    msg_cnt = defaultdict(int)

    for msg in Message.all():
      for word in msg.content.split(" "):
        word_len[msg.conversation_partner] += len(word)
        word_cnt[msg.conversation_partner] += 1

      msg_cnt[msg.conversation_partner] += 1

    word_avg_len = {}
    for name, count in word_cnt.iteritems():
      if msg_cnt[name] >= 10:
        word_avg_len[name] = (1.0 * word_len[name]) / count

    word_avg_len = sorted(word_avg_len.iteritems(),
                          key=operator.itemgetter(1), reverse=True)
    memcache.set(key="word_avg_len" + user.fb_id, value=word_avg_len)
    memcache.set(key="word_cnt" + user.fb_id, value=word_cnt)

  return render('word_length.html', word_avg_len=word_avg_len,
                word_cnt=word_cnt, user_name=user.name)


@app.route('/logout/')
@require_login()
def logout(user):
  session.pop('user_key', None)
  db.delete(user)
  return redirect(url_for('index'))


if __name__ == '__main__':
  port = 3434
  if app.config.get('FB_APP_ID') and app.config.get('FB_APP_SECRET'):
    app.run(host='0.0.0.0', port=port)
  else:
    print 'Cannot start application without Facebook App Id and Secret set'

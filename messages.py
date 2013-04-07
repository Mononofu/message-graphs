# -*- coding: utf-8 -*-
import json
import logging
import random
import urlparse
from functools import wraps
from collections import defaultdict
import operator
import re

from flask import request, redirect, render_template, url_for, flash, session, abort
from werkzeug_debugger_appengine import get_debugged_app

from common import pool, app
from fb_auth import fb_call
from conf import Config
from MessageFetcher import *
from models import *
from calculation import *

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

      user = User.get(session['user_key'])
      if not user:
        session.pop('user_key', None)
        return redirect(url_for('index'))

      return f(*args, user=user, **kwargs)
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
  partners = chat_partners(user)
  return render('partners.html', partners=partners, user_name=user.name)


@app.route('/stats/messages/count/')
@require_login()
def message_count(user):
  msg_cnt = get_msg_cnt(user)
  msg_cnt_lst = sorted(msg_cnt.iteritems(),
                       key=operator.itemgetter(1), reverse=True)

  return render('message_count.html', partners=msg_cnt_lst,
                user_name=user.name)


@app.route('/stats/messages/length/')
@require_login()
def message_length(user):
  msg_cnt = get_msg_cnt(user)
  msg_avg_len = get_msg_avg_len(user)
  msg_avg_len_lst = sorted(msg_avg_len.iteritems(),
                           key=operator.itemgetter(1), reverse=True)

  return render('message_length.html', msg_avg_len=msg_avg_len_lst,
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
      url_re = """((http[s]?|ftp):\/)?\/?([^:\/\s]+)(:([^\/]*))?((\/\w+)*\/)([\w\-\.]+[^#?\s]+)(\?([^#]*))?(#(.*))?"""
      for word in msg.content.split(" "):
        if not re.match(url_re, word):
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


@app.route('/graph/messages/monthly/')
@require_login()
def messages_per_month(user):
  words_per_month = memcache.get("words_per_month" + user.fb_id)

  if not words_per_month:
    oldest = Message.all().order("creation_time").get().creation_time
    now = datetime.datetime.now()

    words_per_month = defaultdict(lambda: defaultdict(int))
    start_date = datetime.datetime(oldest.year, oldest.month, 1)
    end_date = datetime.datetime(oldest.year + (oldest.month / 12),
                                 (oldest.month % 12) + 1, 1)

    while start_date < now:
      q = (Message.all().filter("creation_time >", start_date)
                        .filter("creation_time <", end_date))
      month = start_date.strftime("%Y.%m")
      logging.info(month)
      for m in q:
        words_per_month[month][m.conversation_partner] += len(m.content.split(" "))

      start_date = datetime.datetime(start_date.year + (start_date.month / 12), (start_date.month) % 12 + 1, 1)
      end_date = datetime.datetime(end_date.year + (end_date.month / 12), (end_date.month % 12) + 1, 1)

    words_per_month_toplist = defaultdict(lambda: defaultdict(int))

    for month, partner_list in words_per_month.iteritems():
      top_contacts = sorted(partner_list.iteritems(), key=operator.itemgetter(1))[:5]
      for contact, num_counts in top_contacts:
        words_per_month_toplist[contact][month] = num_counts

    for contact in words_per_month_toplist.iterkeys():
      for month in words_per_month.iterkeys():
        if not month in words_per_month_toplist[contact]:
          words_per_month_toplist[contact][month] = 0

    for contact in words_per_month_toplist.iterkeys():
      words_per_month_toplist[contact] = sorted(words_per_month_toplist[contact].iteritems(),
                                                key=operator.itemgetter(0))

    words_per_month = sorted(words_per_month_toplist.iteritems(),
                             key=operator.itemgetter(0), reverse=True)
    memcache.set("words_per_month" + user.fb_id, words_per_month)

  return render('graph_words.html', words=words_per_month, user_name=user.name)


@app.route('/logout/')
@require_login()
def logout(user):
  session.pop('user_key', None)
  db.delete(user)
  return redirect(url_for('index'))


@app.route('/session/clear/')
def session_clear():
  session.pop('user_key', None)
  return redirect(url_for('index'))


if __name__ == '__main__':
  port = 3434
  app.wsgi_app = get_debugged_app(app)
  if app.config.get('FB_APP_ID') and app.config.get('FB_APP_SECRET'):
    app.run(host='0.0.0.0', port=port, debug=True)
  else:
    print 'Cannot start application without Facebook App Id and Secret set'

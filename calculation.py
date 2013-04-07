from google.appengine.api import memcache
from google.appengine.ext import db

from collections import defaultdict
import re

from models import *


# list of all chat partners
def chat_partners(user):
  partners = memcache.get("partners" + user.fb_id)

  if not partners:
    partners = []
    for proj in db.Query(Message, projection=['conversation_partner'],
                         distinct=True).filter("owner =", user):
      partners.append(proj.conversation_partner)
    memcache.set(key="partners" + user.fb_id, value=partners)

  return partners


def get_proper_words(words):
  url_re = """((http[s]?|ftp):\/)?\/?([^:\/\s]+)(:([^\/]*))?((\/\w+)*\/)([\w\-\.]+[^#?\s]+)(\?([^#]*))?(#(.*))?"""
  return [word for word in words if not re.match(url_re, word)]


def calc_message_stats(user):
  msg_avg_len = memcache.get("msg_avg_len" + user.fb_id)
  msg_cnt = memcache.get("msg_cnt" + user.fb_id)
  words_per_month = memcache.get("words_per_month" + user.fb_id)
  msgs_per_month = memcache.get("msgs_per_month" + user.fb_id)

  if not msg_avg_len or not msg_cnt or not words_per_month or not msgs_per_month:
    msg_len = defaultdict(int)
    msg_cnt = defaultdict(int)
    words_per_month = defaultdict(lambda: defaultdict(int))
    msgs_per_month = defaultdict(lambda: defaultdict(int))

    for msg in Message.all():
      msg_len[msg.conversation_partner] += len(msg.content)
      msg_cnt[msg.conversation_partner] += 1

      month = msg.creation_time.strftime("%Y.%m")
      words_per_month[month][msg.conversation_partner] += len(
          get_proper_words(msg.content.split(" ")))
      msgs_per_month[month][msg.conversation_partner] += 1

    msg_avg_len = {}
    for name, count in msg_cnt.iteritems():
      if count >= 10:
        msg_avg_len[name] = msg_len[name] / count

    words_per_month_dict = {}
    for month, word_dict in words_per_month.iteritems():
      words_per_month_dict[month] = dict(word_dict)

    msgs_per_month_dict = {}
    for month, msg_dict in msgs_per_month.iteritems():
      msgs_per_month_dict[month] = dict(msg_dict)

    memcache.set(key="msg_avg_len" + user.fb_id, value=msg_avg_len)
    memcache.set(key="msg_cnt" + user.fb_id, value=msg_cnt)
    memcache.set(key="words_per_month" + user.fb_id, value=words_per_month_dict)
    memcache.set(key="msgs_per_month" + user.fb_id, value=msgs_per_month_dict)


# dictionary of avergae message length per user (for those with at least 10 msgs)
def get_msg_avg_len(user):
  calc_message_stats(user)
  return memcache.get("msg_avg_len" + user.fb_id)


# dictionary of message count per user
def get_msg_cnt(user):
  calc_message_stats(user)
  return memcache.get("msg_cnt" + user.fb_id)


# Map[Month, Map[User, WordCount]]
def get_words_per_month(user):
  calc_message_stats(user)
  return memcache.get("words_per_month" + user.fb_id)


# Map[Month, Map[User, MsgCount]]
def get_msgs_per_month(user):
  calc_message_stats(user)
  return memcache.get("msgs_per_month" + user.fb_id)

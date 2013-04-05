import time
import logging
import json
import datetime
dt = datetime.datetime
from google.appengine.api import memcache
from google.appengine.ext import deferred

from common import pool
from models import *


class MessageFetcher(object):
  def __init__(self, user_name):
    self.user_name = user_name
    self.deleted_counter = 0

  def run(self):
    access_token = memcache.get('access_token')
    request_url = ("https://graph.facebook.com/me/inbox" +
                   "?format=json&access_token=%s&limit=200" % access_token)
    deferred.defer(self._continue, request_url)

  def _continue(self, next_url):
    logging.info(next_url)
    time.sleep(2)
    r = pool.request('GET', next_url)

    j = json.loads(r.data)

    for conversation in j["data"]:
      if "comments" not in conversation:
        continue

      contact = conversation["to"]["data"][0]["name"]
      if contact == self.user_name:
        if len(conversation["to"]["data"]) > 1:
          for other in conversation["to"]["data"][1:]:
            if other["name"] != self.user_name:
              contact = other["name"]
              break
        else:
          # seems we have a deleted account
          contact = "deleted_%d" % self.deleted_counter
          self.deleted_counter += 1

      comments = conversation["comments"]
      self._parse_messages(contact, comments["data"])

      if "paging" in comments:
        next_page = comments["paging"]["next"].replace("limit=25", "limit=200")
        deferred.defer(self._parse_thread, contact, next_page)

    if "paging" in j:
      request_url = j["paging"]["next"].replace("limit=25", "limit=200")
      deferred.defer(self._continue, request_url)

  def _parse_thread(self, partner, next_page):
    logging.info(next_page)
    time.sleep(2)
    comments = json.loads(pool.request('GET', next_page).data)
    self._parse_messages(partner, comments["data"])

    if "paging" in comments:
      next_page = comments["paging"]["next"].replace("limit=25", "limit=200")
      deferred.defer(self._parse_thread, partner, next_page)

  def _parse_messages(self, partner, messages):
    for message in messages:
      if "message" not in message:
        continue

      text = message["message"]
      time_obj = dt.strptime(message["created_time"],
                             "%Y-%m-%dT%H:%M:%S+0000")

      author = partner
      if message["from"]:
        author = message["from"]["name"]

      msg = Message(
          conversation_partner=partner,
          author=author,
          content=text,
          creation_time=time_obj)
      msg.put()

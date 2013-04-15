import time
import logging
import json
import datetime
dt = datetime.datetime
from google.appengine.ext import deferred

from common import pool
from models import *


class MessageFetcher(object):
  def __init__(self, user):
    self.user = user
    self.deleted_counter = 0

  def run(self):
    newest = Message.all().order("-creation_time").get()
    if newest:
      self.newest_msg = newest.creation_time
    else:
      self.newest_msg = dt(1970, 1, 1)

    request_url = ("https://graph.facebook.com/me/inbox" +
                   "?format=json&access_token=%s&limit=200" % self.user.access_token)
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
      contact_id = conversation["to"]["data"][0]["id"]
      if contact == self.user.name:
        if len(conversation["to"]["data"]) > 1:
          for other in conversation["to"]["data"][1:]:
            if other["name"] != self.user.name:
              contact = other["name"]
              contact_id = other["id"]
              break
        else:
          # seems we have a deleted account
          contact = "deleted_%d" % self.deleted_counter
          contact_id = "-1"
          self.deleted_counter += 1

      comments = conversation["comments"]
      new_msgs_left = self._parse_messages(contact, contact_id, comments["data"])

      if new_msgs_left and "paging" in comments:
        next_page = comments["paging"]["next"].replace("limit=25", "limit=200")
        deferred.defer(self._parse_thread, contact, contact_id, next_page)

    if "paging" in j:
      request_url = j["paging"]["next"].replace("limit=25", "limit=200")
      deferred.defer(self._continue, request_url)

  def _parse_thread(self, partner, partner_id, next_page):
    logging.info(next_page)
    time.sleep(2)
    comments = json.loads(pool.request('GET', next_page).data)
    new_msgs_left = self._parse_messages(partner, partner_id, comments["data"])

    if new_msgs_left and "paging" in comments:
      next_page = comments["paging"]["next"].replace("limit=25", "limit=200")
      deferred.defer(self._parse_thread, partner, partner_id, next_page)

  def _parse_messages(self, partner, partner_id, messages):
    new_msgs_left = True

    for message in messages:
      if "message" not in message:
        continue

      text = message["message"]
      time_obj = dt.strptime(message["created_time"],
                             "%Y-%m-%dT%H:%M:%S+0000")

      if time_obj < self.newest_msg:
        new_msgs_left = False
        continue

      author = partner
      author_id = partner_id
      if message["from"]:
        author = message["from"]["name"]
        author_id = message["from"]["id"]

      msg = Message(
          owner=self.user,
          conversation_partner=partner,
          conversation_partner_id=partner_id,
          author=author,
          author_id=author_id,
          content=text,
          creation_time=time_obj)
      msg.put()

    return new_msgs_left

import time
import json
import datetime
dt = datetime.datetime
import threading
import traceback

from common import pool, app
from models import *

class FacebookError(Exception):
  def __init__(self, value):
    self.value = value

  def __str__(self):
    return repr(self.value)

class FacebookRateLimit(FacebookError):
  pass

class MessageFetcher(object):
  def __init__(self, user):
    self.user = user
    self.deleted_counter = 0
    self.continuations = []
    self.delay = 2

  def run(self):
    self._add_continuation(self._initial_fetch, ())
    thread = threading.Thread(target=self._execute)
    thread.start()

  def _execute(self):
    while self.continuations:
      continuation, args = self.continuations.pop(0)
      try:
        continuation(*args)
      except FacebookRateLimit as e:
        app.logger.warn(("Exceeded the rate limit, consider increasing the delays " +
            "(currently %d s). Sleeping 1 minute and retrying.") % self.delay)
        self._add_continuation(continuation, args)
        time.sleep(60)
        app.logger.debug(".. continuing")
      except Exception as e:
        app.logger.warn("%s(%s) failed with %s" % (continuation, ", ".join(args),
            traceback.format_exc()))
    app.logger.debug("DONE!")

  def _add_continuation(self, method, args):
    self.continuations.append((method, args))

  def _fetch_json(self, url):
    time.sleep(self.delay) # prevent rate limiting
    r = pool.request('GET', url)
    j = json.loads(r.data)
    if "error" in j:
      error = j["error"]
      if "code" in error and error["code"] == 613:
        raise FacebookRateLimit(error["message"])
      raise FacebookError(error["message"])
    return j

  def _initial_fetch(self):
    newest = Message.all().order("-creation_time").get()
    if newest:
      self.newest_msg = newest.creation_time
    else:
      self.newest_msg = dt(1970, 1, 1)

    request_url = ("https://graph.facebook.com/me/inbox" +
                   "?format=json&access_token=%s&limit=200" % self.user.access_token)
    self._add_continuation(self._continue, (request_url,))

  def _continue(self, next_url):
    app.logger.debug(next_url)
    j = self._fetch_json(next_url)

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
        self._add_continuation(self._parse_thread, (contact, contact_id, next_page))

    if "paging" in j:
      request_url = j["paging"]["next"].replace("limit=25", "limit=200")
      self._add_continuation(self._continue, (request_url,))

  def _parse_thread(self, partner, partner_id, next_page):
    app.logger.debug(next_page)
    comments = self._fetch_json(next_page)
    if 'data' not in comments:
      app.logger.debug(comments)
    new_msgs_left = self._parse_messages(partner, partner_id, comments["data"])

    if new_msgs_left and "paging" in comments:
      next_page = comments["paging"]["next"].replace("limit=25", "limit=200")
      self._add_continuation(self._parse_thread, (partner, partner_id, next_page))

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
      if "from" in message:
        author = message["from"]["name"]
        author_id = message["from"]["id"]

      msg = Message(
          conversation_partner=partner,
          conversation_partner_id=partner_id,
          author=author,
          author_id=author_id,
          content=text,
          creation_time=time_obj)
      msg.put()

    return new_msgs_left

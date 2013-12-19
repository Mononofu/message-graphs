# from collections import defaultdict
# import re
# import logging

# from models import *
# from fb_auth import fb_call


# # list of all chat partners
# def chat_partners(user):
#   partners = memcache.get("partners" + user.fb_id)
#   partner_ids = memcache.get("partner_ids" + user.fb_id)

#   if not partners or not partner_ids:
#     partners = []
#     partner_ids = {}
#     for proj in db.Query(Message, projection=['conversation_partner', 'conversation_partner_id'],
#                          distinct=True).filter("owner_id =", user.fb_id):
#       partners.append(proj.conversation_partner)
#       partner_ids[proj.conversation_partner] = proj.conversation_partner_id

#     memcache.set(key="partners" + user.fb_id, value=partners)
#     memcache.set(key="partner_ids" + user.fb_id, value=partner_ids)

#   return partners


# def get_proper_words(words):
#   url_re = """((http[s]?|ftp):\/)?\/?([^:\/\s]+)(:([^\/]*))?((\/\w+)*\/)([\w\-\.]+[^#?\s]+)(\?([^#]*))?(#(.*))?"""
#   return [word for word in words if not re.match(url_re, word)]


# def calc_message_stats(user):
#   msg_avg_len = memcache.get("msg_avg_len" + user.fb_id)
#   msg_cnt = memcache.get("msg_cnt" + user.fb_id)
#   words_per_month = memcache.get("words_per_month" + user.fb_id)
#   msgs_per_month = memcache.get("msgs_per_month" + user.fb_id)
#   words_per_hour = memcache.get("words_per_hour" + user.fb_id)
#   msgs_per_hour = memcache.get("msgs_per_hour" + user.fb_id)

#   if (not msg_avg_len or not msg_cnt or not words_per_month or
#      not msgs_per_month or not words_per_hour):
#     msg_len = defaultdict(int)
#     msg_cnt = defaultdict(int)
#     words_per_month = defaultdict(lambda: defaultdict(int))
#     msgs_per_month = defaultdict(lambda: defaultdict(int))
#     words_per_hour = defaultdict(lambda: defaultdict(int))
#     msgs_per_hour = defaultdict(lambda: defaultdict(int))

#     for msg in Message.all():
#       msg_len[msg.conversation_partner] += len(msg.content)
#       msg_cnt[msg.conversation_partner] += 1

#       month = msg.creation_time.strftime("%Y.%m")
#       weekday_hour = msg.creation_time.strftime("%w-%H")
#       num_words = len(get_proper_words(msg.content.split(" ")))

#       words_per_month[month][msg.conversation_partner] += num_words
#       msgs_per_month[month][msg.conversation_partner] += 1
#       words_per_hour[weekday_hour][msg.conversation_partner] += num_words
#       msgs_per_hour[weekday_hour][msg.conversation_partner] += 1

#     msg_avg_len = {}
#     for name, count in msg_cnt.iteritems():
#       if count >= 10:
#         msg_avg_len[name] = msg_len[name] / count

#     words_per_month_dict = {}
#     for month, word_dict in words_per_month.iteritems():
#       words_per_month_dict[month] = dict(word_dict)

#     msgs_per_month_dict = {}
#     for month, msg_dict in msgs_per_month.iteritems():
#       msgs_per_month_dict[month] = dict(msg_dict)

#     words_per_hour_dict = {}
#     for hour, word_dict in words_per_hour.iteritems():
#       words_per_hour_dict[hour] = dict(word_dict)

#     msgs_per_hour_dict = {}
#     for hour, msg_dict in msgs_per_month.iteritems():
#       msgs_per_hour_dict[hour] = dict(msg_dict)

#     memcache.set(key="msg_avg_len" + user.fb_id, value=msg_avg_len)
#     memcache.set(key="msg_cnt" + user.fb_id, value=msg_cnt)
#     memcache.set(key="words_per_month" + user.fb_id, value=words_per_month_dict)
#     memcache.set(key="msgs_per_month" + user.fb_id, value=msgs_per_month_dict)
#     memcache.set(key="words_per_hour" + user.fb_id, value=words_per_hour_dict)
#     memcache.set(key="msgs_per_hour" + user.fb_id, value=msgs_per_hour_dict)


# # dictionary of avergae message length per user (for those with at least 10 msgs)
# def get_msg_avg_len(user):
#   calc_message_stats(user)
#   return memcache.get("msg_avg_len" + user.fb_id)


# # dictionary of message count per user
# def get_msg_cnt(user):
#   calc_message_stats(user)
#   return memcache.get("msg_cnt" + user.fb_id)


# # Map[Month, Map[User, WordCount]]
# def get_words_per_month(user):
#   calc_message_stats(user)
#   return memcache.get("words_per_month" + user.fb_id)


# # Map[Month, Map[User, MsgCount]]
# def get_msgs_per_month(user):
#   calc_message_stats(user)
#   return memcache.get("msgs_per_month" + user.fb_id)


# # Map[Day_Hour, Map[User, WordCount]]
# def get_words_per_hour(user):
#   calc_message_stats(user)
#   return memcache.get("words_per_hour" + user.fb_id)


# # Map[Day_Hour, Map[User, MsgCount]]
# def get_msgs_per_hour(user):
#   calc_message_stats(user)
#   return memcache.get("msgs_per_hour" + user.fb_id)


# def calc_word_stats(user):
#   word_avg_len = memcache.get("word_avg_len" + user.fb_id)
#   word_cnt = memcache.get("word_cnt" + user.fb_id)

#   if not word_avg_len or not word_cnt:
#     word_len = defaultdict(int)
#     word_cnt = defaultdict(int)
#     msg_cnt = defaultdict(int)

#     for msg in Message.all():
#       url_re = """((http[s]?|ftp):\/)?\/?([^:\/\s]+)(:([^\/]*))?((\/\w+)*\/)([\w\-\.]+[^#?\s]+)(\?([^#]*))?(#(.*))?"""
#       for word in msg.content.split(" "):
#         if not re.match(url_re, word):
#           word_len[msg.conversation_partner] += len(word)
#           word_cnt[msg.conversation_partner] += 1

#       msg_cnt[msg.conversation_partner] += 1

#     word_avg_len = {}
#     for name, count in word_cnt.iteritems():
#       if msg_cnt[name] >= 10:
#         word_avg_len[name] = (1.0 * word_len[name]) / count

#     memcache.set(key="word_avg_len" + user.fb_id, value=word_avg_len)
#     memcache.set(key="word_cnt" + user.fb_id, value=word_cnt)


# # average length of words by user
# def get_word_avg_len(user):
#   calc_word_stats(user)
#   return memcache.get("word_avg_len" + user.fb_id)


# # word count by user
# def get_word_cnt(user):
#   calc_word_stats(user)
#   return memcache.get("word_cnt" + user.fb_id)


# # return male/female for a name
# def get_gender(user, name):
#   gender = memcache.get("partner_%s_gender_%s" % (name, user.fb_id))

#   if not gender:
#     chat_partners(user)
#     partner_ids = memcache.get("partner_ids" + user.fb_id)
#     fb_id = partner_ids[name]

#     contact = Contact.all().filter("fb_id =", fb_id).get()
#     if not contact:
#       gender = "unknown"

#       if fb_id != "-1":
#         c = fb_call(fb_id, args={'access_token': user.access_token,
#                                  'fields': 'name,gender'})
#         if "gender" in c:
#           gender = c["gender"]

#       contact = Contact(name=name, fb_id=fb_id, gender=gender)
#       contact.put()
#     gender = contact.gender

#     memcache.set("partner_%s_gender_%s" % (name, user.fb_id), gender)

#   return gender

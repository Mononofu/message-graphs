from common import app, require_login, render
from calculation import *
import time
import operator
import datetime
import logging
dt = datetime.datetime


@app.route('/graph/words/monthly/')
@require_login()
def words_per_month(user):
  words_per_month = get_words_per_month(user)
  wordcount_per_month = {}

  for month, word_dict in words_per_month.iteritems():
    epoch = time.mktime(dt.strptime(month, "%Y.%m").timetuple())
    wordcount_per_month[epoch] = sum([count for (name, count) in word_dict.iteritems()])

  wordcount_per_month = sorted(wordcount_per_month.iteritems(),
                               key=operator.itemgetter(0), reverse=True)

  return render('graph_words.html', words=wordcount_per_month, user_name=user.name)


@app.route('/graph/words/monthly/user/')
@require_login()
def words_per_month_user(user):
  words_per_month = get_words_per_month(user)

  words_per_month_toplist = defaultdict(lambda: defaultdict(int))

  for month, partners in words_per_month.iteritems():
    top_contacts = sorted(partners.iteritems(), key=operator.itemgetter(1), reverse=True)
    logging.info(top_contacts)
    epoch = time.mktime(dt.strptime(month, "%Y.%m").timetuple())
    for contact, num_counts in top_contacts:
        words_per_month_toplist[contact][epoch] = num_counts

  for contact in words_per_month_toplist.iterkeys():
    for month in words_per_month.iterkeys():
      epoch = time.mktime(dt.strptime(month, "%Y.%m").timetuple())
      if not epoch in words_per_month_toplist[contact]:
        words_per_month_toplist[contact][epoch] = 0

  for contact in words_per_month_toplist.iterkeys():
    words_per_month_toplist[contact] = sorted(words_per_month_toplist[contact].iteritems(),
                                              key=operator.itemgetter(0))

  words_per_month = sorted(words_per_month_toplist.iteritems(),
                           key=operator.itemgetter(0), reverse=True)

  return render('graph_words_per_user.html', words=words_per_month, user_name=user.name)

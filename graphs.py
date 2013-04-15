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


@app.route('/graph/words/monthly/gender/')
@require_login()
def words_per_month_gender(user):
  words_per_month = get_words_per_month(user)
  words_per_month_genderlist = defaultdict(lambda: defaultdict(int))

  for month, partners in words_per_month.iteritems():
    epoch = time.mktime(dt.strptime(month, "%Y.%m").timetuple())
    for contact, num_words in partners.iteritems():
      words_per_month_genderlist[get_gender(user, contact)][epoch] += num_words

  for contact in words_per_month_genderlist.iterkeys():
    for month in words_per_month.iterkeys():
      epoch = time.mktime(dt.strptime(month, "%Y.%m").timetuple())
      if not epoch in words_per_month_genderlist[contact]:
        words_per_month_genderlist[contact][epoch] = 0

  for contact in words_per_month_genderlist.iterkeys():
    words_per_month_genderlist[contact] = sorted(
      words_per_month_genderlist[contact].iteritems(),
      key=operator.itemgetter(0))

  logging.info(words_per_month_genderlist)
  return render('graph_words_per_gender.html', words=words_per_month_genderlist, user_name=user.name)


@app.route('/graph/words/punchcard/')
@require_login()
def words_punchcard(user):
  words_per_hour = get_words_per_hour(user)
  logging.info(words_per_hour)
  words_per_hour_per_day = [[0 for j in range(24)] for i in range(7)]

  words_per_hour = sorted(words_per_hour.iteritems(),
                          key=operator.itemgetter(0))

  for day_hour, user_count in words_per_hour:
    day, hour = day_hour.split("-")
    # %w from strftime uses Sunday as first day of the week, but we want monday
    day, hour = ((int(day) - 1) % 7, int(hour))

    for _, count in user_count.iteritems():
      words_per_hour_per_day[day][hour] += count

  return render('graph_word_count_punchcard.html', words=words_per_hour_per_day,
                user_name=user.name)


@app.route('/graph/persons/monthly/')
@require_login()
def persons_per_month(user):
  words_per_month = get_words_per_month(user)
  persons_per_month = {}

  for month, partners in words_per_month.iteritems():
    epoch = time.mktime(dt.strptime(month, "%Y.%m").timetuple())
    persons_per_month[epoch] = len(partners)

  persons_per_month = sorted(persons_per_month.iteritems(), key=operator.itemgetter(0))

  logging.info(persons_per_month)
  return render('graph_persons_per_month.html', persons=persons_per_month, user_name=user.name)

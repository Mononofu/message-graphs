from common import app, require_login, render
from calculation import *
import operator


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
  word_avg_len = get_word_avg_len(user)
  word_cnt = get_word_cnt(user)

  word_avg_len = sorted(word_avg_len.iteritems(),
                        key=operator.itemgetter(1), reverse=True)

  return render('word_length.html', word_avg_len=word_avg_len,
                word_cnt=word_cnt, user_name=user.name)

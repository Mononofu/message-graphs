import base64
import urllib
import hmac
import hashlib
from base64 import urlsafe_b64decode, urlsafe_b64encode
import json

from flask import Flask, request, redirect, render_template, url_for
from common import pool, app

FB_APP_ID = app.config.get('FBAPI_APP_ID')
FB_APP_SECRET = app.config.get('FBAPI_APP_SECRET')


def oauth_login_url(preserve_path=True, next_url=None):
  fb_login_uri = ("https://www.facebook.com/dialog/oauth"
                  "?client_id=%s&redirect_uri=%s" %
                  (FB_APP_ID, get_home()))

  if app.config['FBAPI_SCOPE']:
    fb_login_uri += "&scope=%s" % ",".join(app.config['FBAPI_SCOPE'])
  return fb_login_uri


def simple_dict_serialisation(params):
  return "&".join(map(lambda k: "%s=%s" % (k, params[k]), params.keys()))


def base64_url_encode(data):
  return base64.urlsafe_b64encode(data).rstrip('=')


def fbapi_get_string(path, domain=u'graph', params=None, access_token=None,
                     encode_func=urllib.urlencode):
  """Make an API call"""

  if not params:
    params = {}
  params[u'method'] = u'GET'
  if access_token:
    params[u'access_token'] = access_token

  for k, v in params.iteritems():
    if hasattr(v, 'encode'):
      params[k] = v.encode('utf-8')

  url = u'https://' + domain + u'.facebook.com' + path
  params_encoded = encode_func(params)
  url = url + params_encoded
  result = pool.request('GET', url).data

  return result


def fbapi_auth(code):
  params = {'client_id': app.config['FB_APP_ID'],
            'redirect_uri': get_home(),
            'client_secret': app.config['FB_APP_SECRET'],
            'code': code}

  result = fbapi_get_string(path=u"/oauth/access_token?", fields=params,
                            encode_func=simple_dict_serialisation)
  pairs = result.split("&", 1)
  result_dict = {}
  for pair in pairs:
    (key, value) = pair.split("=")
    result_dict[key] = value
  return (result_dict["access_token"], result_dict["expires"])


def fbapi_get_application_access_token(id):
  token = fbapi_get_string(
      path=u"/oauth/access_token",
      params=dict(grant_type=u'client_credentials', client_id=id,
                  client_secret=app.config['FB_APP_SECRET']),
      domain=u'graph')

  token = token.split('=')[-1]
  if not str(id) in token:
    print 'Token mismatch: %s not in %s' % (id, token)
  return token


def fql(fql, token, args=None):
  if not args:
    args = {}

  args["query"], args["format"], args["access_token"] = fql, "json", token

  url = "https://api.facebook.com/method/fql.query"

  r = pool.request('GET', url, fields=args)
  return json.loads(r.data)


def fb_call(call, args={}):
  url = "https://graph.facebook.com/{0}".format(call)
  r = pool.request('GET', url, fields=args)
  return json.loads(r.data)


def get_home():
  return 'https://' + request.host + '/'


def get_token():

  if request.args.get('code', None):
    (token, expires) = fbapi_auth(request.args.get('code'))[0]
    if token:
      return token

  cookie_key = 'fbsr_{0}'.format(FB_APP_ID)

  if cookie_key in request.cookies:

    c = request.cookies.get(cookie_key)
    encoded_data = c.split('.', 2)

    sig = encoded_data[0]
    data = json.loads(urlsafe_b64decode(str(encoded_data[1]) +
                      (64 - len(encoded_data[1]) % 64) * "="))

    if not data['algorithm'].upper() == 'HMAC-SHA256':
      raise ValueError('unknown algorithm {0}'.format(data['algorithm']))

    h = hmac.new(FB_APP_SECRET, digestmod=hashlib.sha256)
    h.update(encoded_data[1])
    expected_sig = urlsafe_b64encode(h.digest()).replace('=', '')

    if sig != expected_sig:
      raise ValueError('bad signature')

    params = {
        'client_id': FB_APP_ID,
        'client_secret': FB_APP_SECRET,
        'redirect_uri': '',
        'code': data['code']
    }

    from urlparse import parse_qs
    r = pool.request('GET', 'https://graph.facebook.com/oauth/access_token',
                     fields=params)
    if "error" in r.data:
      return None

    token = parse_qs(r.data).get('access_token')

    return token[0]

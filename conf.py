import os


class Config(object):
    DEBUG = True
    TESTING = False
    SECRET_KEY = "asntoheusnatoehu" # TODO: make that a proper secret ^^ (possible to generate at startup?)
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    FBAPI_APP_ID = os.environ.get('FBAPI_APP_ID')
    FBAPI_APP_SECRET = os.environ.get('FBAPI_APP_SECRET')
    FBAPI_SCOPE = ['user_likes', 'user_photos', 'user_photo_video_tags', 'read_mailbox']

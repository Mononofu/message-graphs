import os


class Config(object):
    DEBUG = True
    TESTING = False
    SECRET_KEY = "asntoheusnatoehu"
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    FBAPI_APP_ID = '483391628381431'
    FBAPI_APP_SECRET = 'ffc510a57f1731e3129e0c85b239c854'
    FBAPI_SCOPE = ['user_likes', 'user_photos', 'user_photo_video_tags', 'read_mailbox']

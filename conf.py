import os

PORT = 8888
DEBUG = True
TESTING = False
SECRET_KEY = "asntoheusnatoehu"  # TODO: make that a proper secret ^^ (possible to generate at startup?)
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
FBAPI_APP_ID = "483391628381431"
FBAPI_APP_SECRET = "ffc510a57f1731e3129e0c85b239c854"
FBAPI_SCOPE = ['read_mailbox', 'friends_birthday']
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'

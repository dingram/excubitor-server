import os


DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Development') or 'test' in os.environ.get('HTTP_HOST', os.environ.get('SERVER_NAME'))
DEV_SERVER = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')

ALLOW_SIGNUPS = True

GAE_APP_STATS = not DEV_SERVER

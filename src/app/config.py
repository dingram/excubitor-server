import os

# Whether we are in debug mode, and whether we are on the local development server
DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Development') or 'test' in os.environ.get('HTTP_HOST', os.environ.get('SERVER_NAME'))
DEV_SERVER = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')

# Whether to record AppStats (annoying on the dev server)
GAE_APP_STATS = not DEV_SERVER

# Whether people are allowed to sign up to the service
ALLOW_SIGNUPS = True

# Google Analytics property ID (UA-xxxxxx-xx)
ANALYTICS_ID = None

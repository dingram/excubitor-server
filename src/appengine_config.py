appstats_CALC_RPC_COSTS = True
appstats_TZOFFSET = 0

def webapp_add_wsgi_middleware(wsgi_app):
	import app.config as config
	if config.GAE_APP_STATS:
		from google.appengine.ext.appstats import recording
		wsgi_app = recording.appstats_wsgi_middleware(wsgi_app)
	return wsgi_app

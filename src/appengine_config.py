appstats_CALC_RPC_COSTS = True
appstats_TZOFFSET = 0

def webapp_add_wsgi_middleware(app):
	import app.config
	if app.config.GAE_APP_STATS:
		from google.appengine.ext.appstats import recording
		app = recording.appstats_wsgi_middleware(app)
	return app

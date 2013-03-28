import logging
import os
import sys
import webapp2

sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'lib'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'app'))

import app.config
import app.views.simple


application = webapp2.WSGIApplication([
	webapp2.Route('/', app.views.simple.SimplePage, defaults={'_template': 'index.html'}),

	webapp2.Route('/login',  app.views.simple.Login),
	webapp2.Route('/logout', app.views.simple.Logout),

	(r'.*', app.views.simple.NotFound),
], debug=app.config.DEBUG)


def main():
	logging.getLogger().setLevel(logging.INFO)
	application.run()

if __name__ == "__main__":
	main()

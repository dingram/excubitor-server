import logging
import os
import sys
import webapp2
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'lib'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), 'app'))

import app.config
import app.views.simple


class LogMailHandler(InboundMailHandler):
	def receive(self, message):
		logging.info("Received a message from %s with subject %s" % (message.sender, message.subject))


application = webapp2.WSGIApplication([
	LogMailHandler.mapping()
], debug=app.config.DEBUG)


def main():
	logging.getLogger().setLevel(logging.INFO)
	application.run()

if __name__ == "__main__":
	main()

import logging

from google.appengine.api import users
from app.util.request import RequestHandler


class Login(RequestHandler):
	def _get(self):
		self.redirect(users.create_login_url('/'))

class Logout(RequestHandler):
	def _get(self):
		self.redirect(users.create_logout_url('/'))

class NotFound(RequestHandler):
	def _get(self):
		self.abort_not_found()


class SimplePage(RequestHandler):
	def _get(self):
		if hasattr(self, 'TEMPLATE'):
			self.render_page(self.TEMPLATE)
		elif '_template' in self.request.route_kwargs:
			self.render_page(self.request.route_kwargs['_template'])
		else:
			logging.error('No template to render as a simple page')
			self.abort(500)

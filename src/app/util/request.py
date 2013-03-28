import webapp2
import config
import os
import json

from google.appengine.ext.webapp import template
from app.util.helpers import JSONEncoder

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tpl')

class RequestHandler(webapp2.RequestHandler):
	def is_api(self):
		return ('text/html' not in self.request.accept) or ('_is_api' in self.request.route_kwargs and self.request.route_kwargs['_is_api'])

	def render_page(self, template_file, vars={}):
		params = vars or {}
		params['CONFIG'] = config
		params['CURRENT_PAGE'] = os.path.splitext(os.path.split(template_file)[1])[0]
		path = os.path.join(TEMPLATE_DIR, template_file)
		self.response.out.write(template.render(path, params))

	def render_json(self, result=None, error=None, exception=None):
		output = {}
		if result is not None:
			output['result'] = result
		if error is not None:
			if isinstance(error, basestring):
				raise ValueError('error should be an object, must not be a string')
			output['error'] = error
		if exception is not None:
			if not isinstance(exception, basestring):
				raise ValueError('exception must be a string')
			output['exception'] = exception

		self.response.content_type = 'application/json'
		self.response.charset = 'utf8'

		json.dump(output, self.response.out, separators=(',', ':'), cls=JSONEncoder)


	def abort_not_found(self, is_json=False):
		if is_json or self.is_api():
			self.render_json(exception='Not found')
		else:
			self.render_page('404.html')
		self.abort(404)

	def abort_wrong_method(self):
		# 405 Method Not Allowed.
		# The response MUST include an Allow header containing a
		# list of valid methods for the requested resource.
		# http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.6

		methods = []
		if hasattr(self, '_get') or hasattr(self, '_get_api'):
			methods.append('GET')
		if hasattr(self, '_post') or hasattr(self, '_post_api'):
			methods.append('POST')

		valid = ', '.join(methods)
		self.abort(405, headers=[('Allow', valid)])


	def get(self, *args, **kwargs):
		method = None

		if self.is_api():
			method = getattr(self, '_get_api', None)
			if method is not None:
				self.response.content_type = 'application/json'
				self.response.charset = 'utf8'

		if method is None:
			method = getattr(self, '_get', None)

		if method is None:
			self.abort_wrong_method()

		self.response.headers['Cache-Control'] = 'private'
		return method(*args, **kwargs)

	def post(self, *args, **kwargs):
		method = None

		if self.is_api():
			method = getattr(self, '_post_api', None)
			if method is not None:
				self.response.content_type = 'application/json'
				self.response.charset = 'utf8'

		if method is None:
			method = getattr(self, '_post', None)

		if method is None:
			self.abort_wrong_method()

		self.response.headers['Cache-Control'] = 'private'
		return method(*args, **kwargs)

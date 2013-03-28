import json

class JSONEncoder(json.JSONEncoder):
	def default(self, o):
		if hasattr(o, 'isoformat'):
			return o.isoformat()

		return super(JSONEncoder, self).default(o)

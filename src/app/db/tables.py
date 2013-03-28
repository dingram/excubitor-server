from google.appengine.api import users, memcache
from google.appengine.ext import db
from geo.geomodel import GeoModel
from app.util.helpers import TokenHelper, JSONEncoder
import app.util.memcache as mc
import logging
import webapp2
import datetime
import os
import json
import gzip
try:
	from cStringIO import StringIO
except:
	from StringIO import StringIO

import config

class UserLink(GeoModel):
	@staticmethod
	def PRIVATE():
		return 0

	@staticmethod
	def VERIFIER():
		return 100

	@staticmethod
	def PROTECTED():
		return 200

	@staticmethod
	def FACTION():
		return 300

	@staticmethod
	def LOGGED_IN():
		return 400

	@staticmethod
	def PUBLIC():
		return 500

	userid = db.StringProperty()
	email = db.EmailProperty()
	created = db.DateTimeProperty()
	last_web_login = db.DateTimeProperty()

	gplus_nickname = db.StringProperty()
	gplus_id = db.StringProperty()
	gplus_linked = db.DateTimeProperty()

	nemesis_guid = db.StringProperty()
	nemesis_nickname = db.StringProperty()
	nemesis_level = db.IntegerProperty()
	nemesis_ap = db.IntegerProperty()
	nemesis_faction = db.IntegerProperty()
	nemesis_linked = db.DateTimeProperty()
	nemesis_verified = db.DateTimeProperty()
	nemesis_synced = db.DateTimeProperty()

	profile_visibility         = db.IntegerProperty(default=0, indexed=False) #UserLink.PRIVATE
	profile_visibility_token   = db.StringProperty(indexed=False)
	ap_graph_visibility        = db.IntegerProperty(default=0, indexed=False) #UserLink.PRIVATE
	ap_graph_visibility_token  = db.StringProperty(indexed=False)
	inv_graph_visibility       = db.IntegerProperty(default=0, indexed=False) #UserLink.PRIVATE
	inv_graph_visibility_token = db.StringProperty(indexed=False)
	key_list_visibility        = db.IntegerProperty(default=0, indexed=False) #UserLink.PRIVATE
	key_list_visibility_token  = db.StringProperty(indexed=False)
	inventory_visibility       = db.IntegerProperty(default=0, indexed=False) #UserLink.PRIVATE
	inventory_visibility_token = db.StringProperty(indexed=False)

	inventory_cache = db.BlobProperty()
	portal_key_cache = db.BlobProperty()

	apk_beta_version = db.IntegerProperty(default=0, indexed=False)
	apk_beta_key = db.StringProperty(indexed=False)
	apk_newest_seen = db.IntegerProperty(default=0)

	last_known_country = db.StringProperty(indexed=False)
	last_known_region  = db.StringProperty(indexed=False)
	last_known_city    = db.StringProperty(indexed=False)

	@classmethod
	def memcache_key(cls, model):
		if isinstance(model, cls):
			return 'model:UserLink:%s' % (model.userid,)
		elif isinstance(model, int) or isinstance(model, str):
			return 'model:UserLink:%s' % (str(model),)
		else:
			raise ValueError('Unknown argument type')

	@classmethod
	def memcache_nemesis_key(cls, model):
		if isinstance(model, cls):
			if model.nemesis_nickname:
				return 'model:UserLink:u:%s' % (model.nemesis_nickname,)
			else:
				return None
		elif isinstance(model, str):
			return 'model:UserLink:u:%s' % (model,)
		else:
			raise ValueError('Unknown argument type')

	@classmethod
	def for_current_user(cls, allow_insert = False, empty_really_is_ok = False):
		if users.get_current_user() is None:
			return None

		user_id = users.get_current_user().user_id()

		user = mc.deserialize_entities(memcache.get(cls.memcache_key(user_id)))
		if not user:
			if allow_insert and config.ALLOW_SIGNUPS:
				user = cls.get_or_insert(user_id)
				if not user.userid:
					user.created = datetime.datetime.utcnow()
					user.userid = user_id
			else:
				user = cls.get_by_key_name(user_id)

			if user is not None:
				user.mc_put()

		if user is None:
			if not config.ALLOW_SIGNUPS and not empty_really_is_ok:
				# XXX: No longer allowed
				webapp2.redirect(users.create_logout_url('/statement'), abort=True, code=303)
			return None

		user.last_known_country = webapp2.get_request().headers.get('X-AppEngine-Country', None)
		user.last_known_region  = webapp2.get_request().headers.get('X-AppEngine-Region', None)
		user.last_known_city    = webapp2.get_request().headers.get('X-AppEngine-City', None)
		# NOTE: we do NOT save here, because this isn't critical but nice. Saves will generally happen anyway.

		cls.check_tokens(user)

		return user

	def to_dict(self):
		nemesis = {}
		gplus = {}

		if self.nemesis_guid:
			nemesis = {
				'guid': self.nemesis_guid,
				'nickname': self.nemesis_nickname,
				'level': self.nemesis_level,
				'ap': self.nemesis_ap,
				'faction': 'ENLIGHTENED' if self.nemesis_faction == 1 else 'RESISTANCE',
				'linked': self.nemesis_linked.isoformat(),
				'last_sync': self.nemesis_synced.isoformat(),
				}
			if self.nemesis_verified:
				nemesis['verified'] = self.nemesis_verified.isoformat()

		if self.gplus_id:
			gplus = {
					'id': self.gplus_id,
					'name': self.gplus_nickname,
					'linked': self.gplus_linked.isoformat(),
				}

		portal_cache = self.get_portal_key_cache()
		for key in portal_cache:
			if 'latE6' not in portal_cache[key]:
				import bitstring

				l = portal_cache[key]['location']
				portal_cache[key]['latE6'] = bitstring.BitArray(hex=l[0:8]).int
				portal_cache[key]['lngE6'] = bitstring.BitArray(hex=l[9:17]).int
				del portal_cache[key]['location']

		return {
				'user_id': self.userid,
				'email': self.email,
				'access_control': {
					'profile': [ self.profile_visibility, self.profile_visibility_token ],
					'ap_graph': [ self.ap_graph_visibility, self.ap_graph_visibility_token ],
					'inv_graph': [ self.inv_graph_visibility, self.inv_graph_visibility_token ],
					'key_list': [ self.key_list_visibility, self.key_list_visibility_token ],
					'inventory': [ self.inventory_visibility, self.inventory_visibility_token ],
				},
				'ingress': nemesis,
				'gplus': gplus,
				'inventory': self.get_inventory_cache(),
				'portal_keys': portal_cache,
			}

	def mc_put(self):
		memcache.set(self.memcache_key(self), mc.serialize_entities(self))

	def mc_put_nemesis(self):
		key = self.memcache_nemesis_key(self)
		if key:
			memcache.set(key, mc.serialize_entities(self))

	@classmethod
	def for_nemesis_user(cls, nickname):
		user = None
		key = cls.memcache_nemesis_key(nickname)
		if key:
			user = mc.deserialize_entities(memcache.get(key))
		if user is None:
			user = cls.all().filter('nemesis_nickname =', nickname).get()
			if user is not None:
				user.mc_put_nemesis()
		return user


	@classmethod
	def check_tokens(cls, user):
		"""Verify that the user has all tokens set"""
		if user is None:
			return

		made_changes = False

		if not user.profile_visibility_token:
			user.profile_visibility_token = TokenHelper.generate_code()
			made_changes = True

		if not user.ap_graph_visibility_token:
			user.ap_graph_visibility_token = TokenHelper.generate_code()
			made_changes = True

		if not user.inv_graph_visibility_token:
			user.inv_graph_visibility_token = TokenHelper.generate_code()
			made_changes = True

		if not user.key_list_visibility_token:
			user.key_list_visibility_token = TokenHelper.generate_code()
			made_changes = True

		if not user.inventory_visibility_token:
			user.inventory_visibility_token = TokenHelper.generate_code()
			made_changes = True

		if made_changes:
			user.put()

	def put(self):
		self.mc_put()
		self.mc_put_nemesis()
		return super(UserLink, self).put()

	def get_profile_url(self):
		url = None

		if self.nemesis_nickname:
			url = '/u/%s' % (self.nemesis_nickname)

			if self.profile_visibility < self.FACTION:
				url += '?tok=' + self.profile_visibility_token

		return url

	def _format_date(self, date):
			return date.strftime('%H:%M, %d %b %Y GMT')

	def get_formatted_synced(self):
			return self._format_date(self.nemesis_synced)

	def get_global_synced_url(self):
			return "http://www.timeanddate.com/worldclock/fixedtime.html?iso=%s" % self.nemesis_synced.strftime("%Y%m%dT%H%M")

	def get_inventory_cache(self):
		if self.inventory_cache is None or self.inventory_cache == '':
			return {}

		strbuf = StringIO(str(self.inventory_cache))
		zipper = gzip.GzipFile(filename='', mode='rb', fileobj=strbuf)
		try:
			return json.load(zipper)
		finally:
			zipper.close()
			strbuf.close()

	def set_inventory_cache(self, data):
		strbuf = StringIO()
		zipper = gzip.GzipFile(filename='', mode='wb', compresslevel=9, fileobj=strbuf)
		json.dump(data, zipper, separators=(',',':'))
		zipper.close()
		self.inventory_cache = db.Blob(strbuf.getvalue())
		strbuf.close()

	def get_portal_key_cache(self):
		if self.inventory_cache is None or self.inventory_cache == '':
			return {}

		strbuf = StringIO(str(self.portal_key_cache))
		zipper = gzip.GzipFile(filename='', mode='rb', fileobj=strbuf)
		try:
			return json.load(zipper)
		finally:
			zipper.close()
			strbuf.close()

	def set_portal_key_cache(self, data):
		strbuf = StringIO()
		zipper = gzip.GzipFile(filename='', mode='wb', compresslevel=9, fileobj=strbuf)
		json.dump(data, zipper, separators=(',',':'))
		zipper.close()
		self.portal_key_cache = db.Blob(strbuf.getvalue())
		strbuf.close()


class PortalInfo(GeoModel):
	guid = db.StringProperty()
	created_at = db.DateTimeProperty()
	updated_at = db.DateTimeProperty()
	name = db.StringProperty()
	address = db.StringProperty(indexed=False)


class PortalKeyHolder(db.Model):
	userid = db.StringProperty()
	portal_guid = db.StringProperty()
	count = db.IntegerProperty()
	known_at = db.DateTimeProperty()


class UserApUpdate(db.Model):
	userid = db.StringProperty()
	changed_at = db.DateTimeProperty()
	new_ap = db.IntegerProperty()


class UserInventoryUpdate(db.Model):
	@staticmethod
	def VERY_COMMON():
		return 0

	@staticmethod
	def COMMON():
		return 1

	@staticmethod
	def LESS_COMMON():
		return 2

	@staticmethod
	def RARE():
		return 3

	@staticmethod
	def VERY_RARE():
		return 4

	@staticmethod
	def EXTREMELY_RARE():
		return 5

	userid = db.StringProperty()
	changed_at = db.DateTimeProperty()
	resonators = db.ListProperty(long, default=[0,0,0,0,0,0,0,0], indexed=False)
	xmp = db.ListProperty(long, default=[0,0,0,0,0,0,0,0], indexed=False)
	media = db.ListProperty(str, default=[], indexed=False)
	shields = db.ListProperty(long, default=[0,0,0,0,0,0], indexed=False)


class UserLocationHistory(GeoModel):
	userid = db.StringProperty()
	as_at = db.DateTimeProperty()


class VerificationCode(db.Model):
	code = db.StringProperty()
	userid = db.StringProperty()
	created = db.DateTimeProperty()
	expires = db.DateTimeProperty()
	expiry_token = db.StringProperty(indexed=False)

	def get_expire_url(self):
		return '%s/expire?secret=%s' % (self.get_url(), self.expiry_token)

	def get_url(self):
		return '/%s' % (self.code)

	def get_global_expires_at_url(self):
		return "http://www.timeanddate.com/worldclock/fixedtime.html?iso=%s" % self.expires.strftime("%Y%m%dT%H%M")

	def _format_date(self, date):
		return date.strftime('%H:%M, %d %b %Y GMT')

	def get_formatted_created(self):
		return self._format_date(self.created)

	def get_formatted_expires(self):
		return self._format_date(self.expires)

	def invalidate_memcache(self):
		self.clear_memcache(self.userid)

	@classmethod
	def clear_memcache(cls, userid):
		memcache.delete('VerificationCodeList:%s' % userid)

	@classmethod
	def update_memcache(cls, userid):
		q = VerificationCode.all().filter('userid =', userid).order('created').fetch(100)
		memcache.set('VerificationCodeList:%s' % userid, mc.serialize_entities(q))
		return q

	@classmethod
	def fetch_from_memcache(cls, userid):
		codes = mc.deserialize_entities(memcache.get('VerificationCodeList:%s' % userid))
		if not codes:
			codes = cls.update_memcache(userid)

		if not codes:
			return []
		elif not isinstance(codes, list):
			return [codes]
		else:
			return codes

	def delete(self):
		self.invalidate_memcache()
		return super(VerificationCode, self).delete()



class BaseStat(db.Model):
	recorded_at = db.DateTimeProperty()
	user_agent = db.StringProperty()

	@classmethod
	def create(cls, *args, **kwargs):
		model = cls(**kwargs)
		model.recorded_at = datetime.datetime.utcnow()
		try:
			model.user_agent = webapp2.get_request().headers.get('User-Agent', None)
		except:
			pass
		return model

	@classmethod
	def record(cls, *args, **kwargs):
		model = cls.create(*args, **kwargs)
		model.put()
		return model

	def put(self):
		# log a message when recording a stat
		logging.info("Recording %s stat: %s" % (self.__class__.__name__, json.dumps(self.__dict__, cls=JSONEncoder)))
		if config.WRITE_STATS:
			return super(BaseStat, self).put()


class BaseUserStat(BaseStat):
	userid = db.StringProperty()

	@classmethod
	def create(cls, *args, **kwargs):
		model = super(BaseUserStat, cls).create(*args, **kwargs)
		try:
			model.userid = users.get_current_user().user_id()
		except:
			pass
		return model



class StatCodeCreated(BaseUserStat):
	source = db.StringProperty() # API or web


class StatUserDownload(BaseUserStat):
	version = db.IntegerProperty()


class StatUserGPlusLink(BaseUserStat):
	pass


class StatUserSync(BaseUserStat):
	faction = db.StringProperty()
	level = db.IntegerProperty()
	delta_level = db.IntegerProperty()
	ap = db.IntegerProperty()
	delta_ap = db.IntegerProperty()


class StatUserDevice(BaseUserStat):
	package_version = db.IntegerProperty()
	device = db.StringProperty()
	device_version = db.StringProperty()
	min_package_version = db.IntegerProperty()
	max_package_version = db.IntegerProperty()

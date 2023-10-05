from libsonic import (Connection as libsoniConn, API_VERSION as libsonicApiVersion)
from base64 import b64decode
from _config import cfg

class LibSoniConn:
	def __init__(self):
		self._conn = None

	@property
	def conn(self):
		if not self._conn:
			self._conn = libsoniConn(cfg.server['subsonic']['url'],
				cfg.server['subsonic']['user'], b64decode(cfg.server['subsonic']['pswd']).decode("utf-8"),
				port=cfg.server['subsonic']['port'], appName='foosonic', legacyAuth=cfg.server['subsonic']['legacyAuth'],
				apiVersion=libsonicApiVersion if not cfg.server['subsonic']['apiVersion'] else cfg.server['subsonic']['apiVersion']
			)
		return self._conn
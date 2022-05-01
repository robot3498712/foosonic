# foosonic config
class Object(object): pass
cfg = Object()

# path to local foobar2000.exe
cfg.foo = 'C:/Program Files/Foobar2000/foobar2000.exe'

'''
subsonic -> subsonic server
	password=base64-encoded
	apiVersion=None will use latest as supported by libsonic; specify old version like: 1.10
self -> foosonic/remote built-in server, contacted by remote foobar/cmdline
wsgi -> foosonic/wsgi built-in server, localhosted web app
foo_httpcontrol -> remote foobar
	password=base64-encoded
'''
cfg.server = {
	'subsonic': {
		'url': 'https://subson.ic',
		'port': 443,
		'user': '<user>',
		'pswd': '<BASE64=>',
		'legacyAuth': False,
		'apiVersion': None
	},
	'self': {
		'listen': '0.0.0.0',
		'ip': '192.168.0.1',
		'port': 8080,
	},
	'wsgi': {
		'listen': '0.0.0.0',
		'ip': '127.0.0.1',
		'port': 8081
	},
	'foo_httpcontrol': {
		'url': 'http://192.168.0.2:8080/default/',
		'user': '<user>',
		'pswd': '<BASE64=>',
	}
}

'''
network path map, used for filesystem playlists, "open dir" and such
	default -> key=\0
	keys are matched via path.startswith()
'''
cfg.pathmap = {
	"\0": '\\\\MAPPED_DRIVE/data_dir/',
	'Starts_with': '\\\\MAPPED_DRIVE/data_dir/Starts_with',
}

# station dict: key=label, value=url
cfg.radio = {
	'disco fetish': 'http://radio.intergalactic.fm/2.m3u',
	'dream machine': 'http://radio.intergalactic.fm/3.m3u',
	'cybernetic': 'http://radio.intergalactic.fm/1.m3u',
}

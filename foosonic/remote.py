from threading import Thread

server, m3ufile = None, None

'''
https://tedboy.github.io/flask/_modules/werkzeug/serving.html
https://github.com/colour-science/flask-compress
https://stackoverflow.com/a/45017691
https://stackoverflow.com/questions/14888799/disable-console-messages-in-flask-server
'''
class Server(Thread):
	def __init__(self, state):
		Thread.__init__(self)
		import logging, click
		from flask import Flask, send_file, after_this_request
		from flask_compress import Compress
		from werkzeug.serving import make_server

		self.after_this_request = after_this_request
		self.send_file = send_file

		app = Flask(__name__)
		compress = Compress()

		app.route('/cache/playlist.m3u8')(self._serve)

		compress.init_app(app)
		app.config['COMPRESS_MIMETYPES'].append('application/mpegurl')
		self.server = make_server(host=state.server['self']['listen'], port=state.server['self']['port'], app=app)
		self.ctx = app.app_context()
		self.ctx.push()

		log = logging.getLogger('werkzeug')
		log.disabled = True
		click.echo = self._echo
		click.secho = self._secho

	def _secho(self, text, file=None, nl=None, err=None, color=None, **styles): pass
	def _echo(self, text, file=None, nl=None, err=None, color=None, **styles): pass

	def _serve(self):
		@self.after_this_request
		def shutdown(response):
			Thread(target=server.shutdown).start()
			return response

		return self.send_file(
			m3ufile,
			as_attachment=True,
			mimetype='application/mpegurl; charset=utf-8'
		)

	def run(self): self.server.serve_forever()
	def shutdown(self): self.server.shutdown()
# end Server()

def _request(s):
	import requests
	from base64 import b64decode
	try:
		requests.get(
			url = s['foo_httpcontrol']['url'],
			auth = requests.auth.HTTPBasicAuth(s['foo_httpcontrol']['user'], b64decode(s['foo_httpcontrol']['pswd']).decode("utf-8")),
			params = {
				'cmd': 'CmdLine',
				'param1': f"/add http://{s['self']['ip']}:{s['self']['port']}/cache/playlist.m3u8",
			},
			timeout = 3,
		)
	except: # shut down the server gracefully
		print("adding playlist failed")
		server.shutdown()

def playlist(qin, qout, e, _):
	global m3ufile, server

	state = qin.get()
	m3ufile = state.serve

	req = Thread(target=_request, args=[state.server])
	req.daemon = True
	req.start()

	server = Server(state)
	server.start()
	server.join()

	qout.put("\x00\0served")
	e.set()

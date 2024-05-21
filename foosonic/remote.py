import requests, logging, click
from threading import Thread
from base64 import b64decode
from flask import Flask, send_file, after_this_request
from flask_compress import Compress
from werkzeug.serving import make_server

app, server, m3ufile = Flask(__name__), None, None
Compress(app)

'''
https://tedboy.github.io/flask/_modules/werkzeug/serving.html
https://stackoverflow.com/a/45017691
https://stackoverflow.com/questions/14888799/disable-console-messages-in-flask-server
'''
class Server(Thread):
	def __init__(self, app, state):
		Thread.__init__(self)
		self.server = make_server(host=state.server['self']['listen'], port=state.server['self']['port'], app=app)
		self.ctx = app.app_context()
		self.ctx.push()

	def _secho(self, text, file=None, nl=None, err=None, color=None, **styles): pass
	def _echo(self, text, file=None, nl=None, err=None, color=None, **styles): pass

	def run(self):
		log = logging.getLogger('werkzeug')
		log.disabled = True
		click.echo = self._echo
		click.secho = self._secho
		self.server.serve_forever()

	def shutdown(self):
		self.server.shutdown()


@app.route('/cache/playlist.m3u8')
def _serve():
	@after_this_request
	def shutdown(response):
		Thread(target=server.shutdown).start()
		return response

	return send_file(
		m3ufile,
		as_attachment=True,
		mimetype='Content-Type: application/mpegurl; charset=utf-8'
	)

def _request(s):
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

	server = Server(app, state)
	server.start()
	server.join()

	qout.put("\x00\0served")
	e.set()

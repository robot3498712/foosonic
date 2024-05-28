from threading import Thread

server = None

'''
https://tedboy.github.io/flask/_modules/werkzeug/serving.html
https://github.com/colour-science/flask-compress
https://stackoverflow.com/a/45017691
https://stackoverflow.com/questions/14888799/disable-console-messages-in-flask-server
'''
class Server(Thread):
	def __init__(self, state, e):
		Thread.__init__(self)
		import logging, click
		from flask import Flask, send_file, after_this_request
		from flask_compress import Compress
		from werkzeug.serving import make_server

		self.state, self.e = state, e
		self.after_this_request, self.send_file = after_this_request, send_file

		app = Flask(__name__)
		compress = Compress()

		app.route('/cache/playlist.m3u8')(self._serve)

		compress.init_app(app)
		app.config['COMPRESS_MIMETYPES'].append('application/mpegurl')
		self.server = make_server(host=state.server['remote']['listen'], port=state.server['remote']['port'], app=app)
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
			Thread(target=self.server.shutdown).start()
			return response

		return self.send_file(
			self.state.serve,
			as_attachment=True,
			mimetype='application/mpegurl; charset=utf-8'
		)

	def run(self):
		self.e.set()
		self.server.serve_forever()

	def shutdown(self): self.server.shutdown()
# end Server()

def _request(s, q, e):
	import requests
	from base64 import b64decode
	try:
		e.wait()    # wait for startup
		_ = q.get() # wait for playlist
	except:
		return
	try:
		requests.get(
			url = s['foo_httpcontrol']['url'],
			auth = requests.auth.HTTPBasicAuth(s['foo_httpcontrol']['user'], b64decode(s['foo_httpcontrol']['pswd']).decode("utf-8")),
			params = {
				'cmd': 'CmdLine',
				'param1': f"/add http://{s['remote']['ip']}:{s['remote']['port']}/cache/playlist.m3u8",
			},
			timeout = 3,
		)
	except: # shut down the server gracefully
		print("adding playlist failed")
		server.shutdown()

# define
def playlist(): pass

def run(qout, qin, evParent, evChild):
	global server
	try:
		evChild.wait()
	except KeyboardInterrupt:
		return

	_ = qin.get()
	state = qin.get()

	req = Thread(target=_request, args=[state.server, qin, evChild])
	req.daemon = True
	req.start()

	server = Server(state, evChild)
	server.start()
	server.join()

	qout.put("\x00")
	evParent.set()

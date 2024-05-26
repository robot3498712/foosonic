from threading import Thread
from foosonic import connection

state = None

class Server():
	def __init__(self, qout, qin, evParent):
		import json, logging, click
		from io import BytesIO 
		from flask import Flask, send_file, request, render_template
		from flask_compress import Compress

		self.qout, self.qin, self.evParent = qout, qin, evParent
		self.BytesIO = BytesIO
		self.json = json
		self.send_file = send_file
		self.request = request
		self.render_template = render_template

		app = Flask(__name__)
		Compress(app)

		app.route('/coverart/<id>')(self._coverart)
		app.route('/coverart/<size>/<id>')(self._coverart)
		app.route('/open/<id>')(self._open)
		app.route('/add/<client>/<mode>', methods=['POST'])(self._add)
		app.route('/')(self._index)

		log = logging.getLogger('werkzeug')
		log.disabled = True
		click.echo = self._echo
		click.secho = self._secho

		app.run(debug=False, port=state.server['web']['port'], host=state.server['web']['listen'])

	def _secho(text, file=None, nl=None, err=None, color=None, **styles): pass
	def _echo(text, file=None, nl=None, err=None, color=None, **styles): pass

	def _coverart(self, id, size=None):
		data = None
		try:
			r = state.connector.conn.getCoverArt(id, size=size)
			data = r.read()
		except: pass
		if data:
			return self.send_file(
				self.BytesIO(data),
				mimetype='image/png',
				download_name=f"{id}.png")
		return self.send_file(
			'./static/lazyload.png',
			mimetype='image/png',
			download_name='lazyload.png')

	def _open(self, id):
		self.qout.put(f"\x01\0{id}")
		self.evParent.set()
		return id

	def _add(self, client, mode):
		self.qout.put(f"\x20\0{client}\0{mode}\0{self.request.form['ids']}")
		self.evParent.set()
		try: _ = self.qin.get(timeout=10)
		except: pass
		return 'OK'

	def _index(self):
		d = {}
		for choice in state.choices:
			try:
				if not choice.value: raise ValueError
				d[choice.value] = choice.name
			except:
				pass
		return self.render_template('index.html', data=self.json.dumps(d))
# end Server()

def _update(qin, evChild):
	while True:
		evChild.wait()
		state.choices = qin.get()
		evChild.clear()

# define
def app(): pass

def run(qout, qin, evParent, evChild):
	global state
	try: 
		evChild.wait()
	except KeyboardInterrupt:
		return

	_ = qin.get()
	state = qin.get()
	state.connector = connection.LibSoniConn()

	evChild.clear()
	t = Thread(target=_update, args=[qin, evChild])
	t.daemon = True
	t.start()

	serve_forever = Server(qout, qin, evParent)

	qout.put("\x00")
	evParent.set()

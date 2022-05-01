import io, json, logging, click
from flask import Flask, render_template, send_file, request

app, state, _evParent, _qout, _qin = Flask(__name__), None, None, None, None

# logging overrides, https://stackoverflow.com/questions/14888799/disable-console-messages-in-flask-server
def _secho(text, file=None, nl=None, err=None, color=None, **styles): pass
def _echo(text, file=None, nl=None, err=None, color=None, **styles): pass


@app.route('/coverart/<id>')
@app.route('/coverart/<size>/<id>')
def _coverart(id, size=None):
	try:
		r = state.conn.getCoverArt(id, size=size)
		data = r.read()
	except:
		return send_file(
			'./static/lazyload.png',
			attachment_filename='lazyload.png')
	if data:
		return send_file(
			io.BytesIO(data),
			mimetype='image/png',
			attachment_filename='%s.png' % id)

@app.route('/open/<id>')
def _open(id):
	_qout.put("\x01\0%s" % (id,))
	_evParent.set()
	return id

@app.route('/add/<client>/<mode>/<id>')
def _add(client, mode, id):
	_qout.put("\x20\0%s\0%s\0%s" % (client, mode, id))
	_evParent.set()
	try: _ = _qin.get(timeout=10)
	except: pass
	return id

@app.route('/')
def _index():
	d = {}
	for choice in state.choices:
		try:
			if not choice.value: raise ValueError
			d[choice.value] = choice.name
		except:
			pass
	return render_template('index.html', data=json.dumps(d))


def _update(qin, evChild):
	global state
	while True:
		evChild.wait()
		state.choices = qin.get()
		evChild.clear()

def webapp(qin, qout, evParent, evChild):
	from threading import Thread

	global state, _evParent, _qout, _qin
	state = qin.get()
	evChild.clear()
	_evParent = evParent
	_qout = qout
	_qin = qin

	# don't print anything to console
	log = logging.getLogger('werkzeug')
	log.disabled = True
	click.echo = _echo
	click.secho = _secho

	t = Thread(target=_update, args=[qin, evChild])
	t.daemon = True
	t.start()

	app.run(debug=False, port=state.server['wsgi']['port'], host=state.server['wsgi']['listen'])

	qout.put("\x00")
	evParent.set()

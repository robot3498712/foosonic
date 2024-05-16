from http.server import BaseHTTPRequestHandler, HTTPServer

m3ufile = None

class Server(BaseHTTPRequestHandler):
	def do_GET(self):
		import os
		from shutil import copyfileobj
		with open(m3ufile, 'rb') as f:
			fs = os.fstat(f.fileno())
			self.send_response(200)
			self.send_header("Content-type", "application/mpegurl")
			self.send_header("Content-Disposition", 'attachment; filename="{}"'.format(os.path.basename(m3ufile)))
			self.send_header("Content-Length", str(fs.st_size))
			self.end_headers()
			copyfileobj(f, self.wfile)
		raise KeyboardInterrupt # serve one request

	def log_message(self, format, *args):
		return

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
		requests.get(f"http://{s['self']['ip']}:{s['self']['port']}/void/", timeout=1)

def playlist(qin, qout, e, _):
	from threading import Thread
	global m3ufile

	state = qin.get()
	m3ufile = state.serve

	httpd = HTTPServer((state.server['self']['listen'], state.server['self']['port']), Server)

	t = Thread(target=_request, args=[state.server])
	t.daemon = True
	t.start()

	try: httpd.serve_forever()
	except: pass
	finally: httpd.server_close()

	qout.put("\x00")
	e.set()

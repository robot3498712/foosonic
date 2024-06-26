import os
from threading import Thread
from foosonic import connection

tk, Image, ImageTk, BytesIO = (None,) * 4

def manual(qin, qout, e, _):
	state = qin.get()

	wnd = tk.Tk()
	wnd.geometry("600x300")
	wnd.title('Manual')

	scrollbar = tk.Scrollbar(wnd)
	text = tk.Text(wnd, height=25, width=200)
	scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
	text.pack(side=tk.LEFT, fill=tk.Y)
	scrollbar.config(command=text.yview)
	text.config(yscrollcommand=scrollbar.set)

	_text = """ctrl-space\t\tadd to foobar
alt-o\t\topen directory
alt-i\t\topen cover art
alt-w\t\topen web app
ctrl-r\t\tselect all albums
ctrl-s\t\tadd to session
ctrl-c\t\texit
delete\t\tremove (from) session
tab\t\tselect/move down
shift-tab\t\tselect/move up
arrow*\t\tmove | pager
pos1\t\tmove to top
end\t\tmove to end
alt-left\t\tback/reload
alt-g\t\tgenres
alt-s\t\tsessions
alt-r\t\tradio
	"""
	text.insert(tk.END, _text)

	t = Thread(target=_destroy, args=[qin, wnd])
	t.daemon = True
	t.start()

	_setIcon(wnd, state.sd)
	wnd.mainloop()

	qout.put("\x00")
	e.set()

def coverArt(qin, qout, e, _):
	state = qin.get()
	state.connector = connection.LibSoniConn()

	try:
		r = state.connector.conn.getCoverArt(state.alId)
	except:
		qout.put("\x00")
		return e.set()

	data = r.read()
	if not data:
		with open(os.path.join(state.sd, './foosonic/static/lazyload.png'), "rb") as fh:
			data = fh.read()
	if data:
		wnd = tk.Tk()
		wnd.title(state.alId)

		im = Image.open(BytesIO(data))
		w, h = im.size
		if w > 600 or h > 600:
			im.thumbnail((600, 600), Image.Resampling.LANCZOS)
		img = ImageTk.PhotoImage(im)

		_ = tk.Label(wnd, image=img).pack()
		_setIcon(wnd, state.sd)

		t = Thread(target=_destroy, args=[qin, wnd])
		t.daemon = True
		t.start()

		wnd.bind("<KeyRelease>", lambda _: (lambda: qin.put(None))())
		wnd.mainloop()

	qout.put("\x00")
	e.set()

def _setIcon(hwnd, sd):
	with Image.open(os.path.join(sd, './foosonic/static/favicon.ico')).convert("RGBA") as ico:
		hwnd.iconphoto(False, ImageTk.PhotoImage(ico))

def _destroy(qin, h):
	_ = qin.get()
	h.destroy()

def run(qout, qin, evParent, evChild, evTerm):
	global tk, Image, ImageTk, BytesIO
	import tkinter as tk
	from PIL import Image, ImageTk
	from io import BytesIO

	try:
		evChild.wait()
	except KeyboardInterrupt:
		return evTerm.set()

	fn = qin.get()
	fn(qin, qout, evParent, evChild)

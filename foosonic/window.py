def _destroy(qin, h):
	_ = qin.get()
	h.destroy()

def coverArt(qin, qout, e, _):
	import tkinter as tk
	from threading import Thread
	from PIL import Image, ImageTk
	from io import BytesIO

	state = qin.get()

	try:
		r = state.conn.getCoverArt(state.alId)
	except:
		qout.put("\x00")
		e.set()
		return

	data = r.read()
	if data:
		wnd = tk.Tk()
		wnd.title(state.alId)

		im = Image.open(BytesIO(data))
		w, h = im.size
		if w > 600 or h > 600:
			im.thumbnail((600, 600), Image.ANTIALIAS)
		img = ImageTk.PhotoImage(im)

		lbl = tk.Label(wnd, image=img).pack()

		t = Thread(target=_destroy, args=[qin, wnd])
		t.daemon = True
		t.start()

		wnd.mainloop()

	qout.put("\x00")
	e.set()

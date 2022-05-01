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
		img = ImageTk.PhotoImage(Image.open(BytesIO(data)))
		lbl = tk.Label(wnd, image=img).pack()

		t = Thread(target=_destroy, args=[qin, wnd])
		t.daemon = True
		t.start()

		wnd.mainloop()

	qout.put("\x00")
	e.set()

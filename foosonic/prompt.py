sig, inquirer, style = None, None, None

r'''
on topic of overrides see https://github.com/kazhala/InquirerPy/issues/42
for keys consult Python3\Lib\site-packages\prompt_toolkit\keys.py

inquirer style overrides
border=True : rendering bugged, and poor performance
'''
def run(qout, qin, evParent, evChild, evTerm, tty):
	global inquirer, style
	from InquirerPy import inquirer, get_style

	style = get_style({
		"question": "#ff9d00 bold",
		"marker": "#ff9d00 bold",
		"fuzzy_match": "green",
		"fuzzy_border": "#ff9d00",
		"fuzzy_info": "#ff9d00",
		"instruction": "#ff9d00",
		"long_instruction": "#ff9d00",
		"separator": "#ff9d00 bold"
	}, style_override=False)

	if tty:
		import sys
		sys.stdin = open('/dev/tty', 'r')
	try: # handle search abort
		evChild.wait()
	except KeyboardInterrupt:
		return evTerm.set()

	fn = qin.get()
	fn(qin, qout, evParent, evChild)

def confRmSession(qin, qout, e, _):
	state = qin.get()
	try:
		if inquirer.confirm(message="Confirm delete session", default=True,
			confirm_letter="y", reject_letter="n", style=style
		).execute():
			state.selChoice = True
		else:
			state.selChoice = False
	except KeyboardInterrupt:
		state.sig = KeyboardInterrupt
	qout.put(state)
	e.set()

def modeSession(qin, qout, e, _):
	state = qin.get()
	prompt = inquirer.select(message='Add to session', choices=['all', 'selected'],
		default=state.sessmode, show_cursor=False, style=style, height="100%")

	@prompt.register_kb("alt-left")
	def _handle_nav_back(event):
		global sig
		sig = "\x08"
		event.app.exit(result=None)

	try:
		state.selChoice = prompt.execute()
	except KeyboardInterrupt:
		state.sig = KeyboardInterrupt
	else:
		state.sig = sig
	qout.put(state)
	e.set()

def nameSession(qin, qout, e, _):
	state = qin.get()
	prompt = inquirer.text(message="Enter descriptive name for this session:",
		default=state.fuzzy['session'] if state.fuzzy['session'] else ''
	)

	@prompt.register_kb("alt-left")
	def _handle_nav_back(event):
		global sig
		sig = "\x08"
		event.app.exit(result=None)

	try:
		state.selChoice = prompt.execute()
	except KeyboardInterrupt:
		state.sig = KeyboardInterrupt
	else:
		state.sig = sig
	state.choices = []
	qout.put(state)
	e.set()

def listSessions(qin, qout, e, _):
	state = qin.get()
	prompt = inquirer.select(message="Select session", choices=state.sessions,
		long_instruction="new: c-a / rm: delete / ren: c-r",
		keybindings={"toggle": [], "toggle-all": [], "toggle-all-true": []},
		default=None, show_cursor=False, style=style, height="100%")

	@prompt.register_kb("alt-left")
	def _handle_nav_back(event):
		global sig
		sig = "\x08"
		event.app.exit(result=None)

	@prompt.register_kb("c-a")
	def _handle_make(event):
		global sig
		sig = "\x2B"
		event.app.exit(result=None)

	@prompt.register_kb("delete")
	def _handle_delete(event):
		global sig
		sig = "\x15"
		event.app.exit(result=prompt.content_control.selection["value"])

	@prompt.register_kb("c-r")
	def _handle_rename(event):
		global sig
		sig = "\x26"
		event.app.exit(result=prompt.content_control.selection["value"])

	@prompt.register_kb("alt-h")
	def _handle_manual(event):
		qout.put("\x42")
		e.set()

	try:
		state.selChoice = prompt.execute()
	except KeyboardInterrupt:
		state.sig = KeyboardInterrupt
	else:
		state.sig = sig

	state.sessions = []
	state.choices = []
	qout.put(state)
	e.set()

# tbd. decorator/refactor
def listArtists(qin, qout, e, _):
	listGenres(qin, qout, e, _)

def listGenres(qin, qout, e, _):
	state = qin.get()
	prompt = inquirer.fuzzy(message=f"Select {state.ltype}", long_instruction="toggle down: tab / up: s-tab / all: c-r / exact: c-t",
		choices=state.choices, match_exact=True, multiselect=True,
		keybindings={"answer": [], "toggle": [], "toggle-all": [{"key": "c-r"}], "toggle-all-true": [], "toggle-exact": [{"key": "c-t"}]},
		default=state.fuzzy['genre'], style=style, height="100%", transformer=lambda result: f"({len(result)})",
	)

	@prompt.register_kb("pagedown")
	@prompt.register_kb("right")
	def _handle_pagedown(event):
		prompt.content_control.selected_choice_index = prompt.content_control.selected_choice_index + prompt._dimmension_height - 1

	@prompt.register_kb("pageup")
	@prompt.register_kb("left")
	def _handle_pageup(event):
		prompt.content_control.selected_choice_index = prompt.content_control.selected_choice_index - (prompt._dimmension_height - 1)

	@prompt.register_kb("home")
	def _handle_home(event): prompt.content_control.selected_choice_index = 0

	@prompt.register_kb("end")
	def _handle_end(event): prompt.content_control.selected_choice_index = 999999

	@prompt.register_kb("c-m") # override {enter} to store input text
	def _handle_enter(event):
		state.fuzzy[state.ltype] = prompt._get_current_text().strip()
		prompt._handle_enter(event)

	@prompt.register_kb("alt-left")
	def _handle_nav_back(event):
		global sig
		sig = "\x08"
		event.app.exit(result=None)

	@prompt.register_kb("alt-r")
	def _handle_nav_radio(event):
		global sig
		sig = "\x1E"
		event.app.exit(result=None)

	@prompt.register_kb("alt-s")
	def _handle_nav_sessions(event):
		global sig
		sig = "\x1F"
		event.app.exit(result=None)

	@prompt.register_kb("alt-g")
	def _handle_nav_genre(event):
		global sig
		if state.ltype == "genre": return
		sig = "\x1D"
		event.app.exit(result=None)

	@prompt.register_kb("alt-a")
	def _handle_nav_artists(event):
		global sig
		if state.ltype == "artist": return
		sig = "\x2D"
		event.app.exit(result=None)

	@prompt.register_kb("alt-h")
	def _handle_manual(event):
		qout.put("\x42")
		e.set()

	try:
		state.selChoice = prompt.execute()
	except KeyboardInterrupt:
		state.sig = KeyboardInterrupt
	else:
		state.sig = sig

	state.choices = []
	qout.put(state)
	e.set()

def listAlbums(qin, qout, e, _):
	state = qin.get()

	prompt = inquirer.fuzzy(message=f"Select {'session/album' if state.type == 'session' else state.type}", choices=state.choices,
		long_instruction="+foo: c-space / open: a-o / cover: a-i / genres: a-g / artists: a-a / radio: a-r / web: a-w / sess: a-s / store: c-s",
		keybindings={"answer": [], "toggle": [], "toggle-all": [{"key": "c-r"}], "toggle-all-true": [], "toggle-exact": [{"key": "c-t"}]},
		match_exact=True, multiselect=True, default=state.fuzzy[state.type], style=style, height="100%",
		transformer=lambda result: f"({len(result)})"
	)
	prompt.content_control.selected_choice_index = state.selChoiceIdx if state.selChoiceIdx > -1 else 0

	@prompt.register_kb("pagedown")
	@prompt.register_kb("right")
	def _handle_pagedown(event):
		scrollTo = prompt.content_control.selected_choice_index + prompt._dimmension_height - 1
		if scrollTo > state.numRes - 1: scrollTo = state.numRes - 1
		prompt.content_control.selected_choice_index = scrollTo

	@prompt.register_kb("pageup")
	@prompt.register_kb("left")
	def _handle_pageup(event):
		scrollTo = prompt.content_control.selected_choice_index - (prompt._dimmension_height - 1)
		if scrollTo < 0: scrollTo = 0
		prompt.content_control.selected_choice_index = scrollTo

	@prompt.register_kb("home")
	def _handle_home(event): prompt.content_control.selected_choice_index = 0

	@prompt.register_kb("end")
	def _handle_end(event): prompt.content_control.selected_choice_index = state.numRes - 1

	@prompt.register_kb("c-m") # override {enter} to store selected index
	def _handle_enter(event):
		state.selChoiceIdx = prompt.content_control.selected_choice_index
		state.fuzzy[state.type] = prompt._get_current_text().strip()
		prompt._handle_enter(event)

	@prompt.register_kb("alt-g")
	def _handle_nav_genre(event):
		global sig
		sig = "\x1D"
		event.app.exit(result=None)

	@prompt.register_kb("alt-r")
	def _handle_nav_radio(event):
		global sig
		if state.ltype == "radio": return
		sig = "\x1E"
		event.app.exit(result=None)

	@prompt.register_kb("alt-s")
	def _handle_nav_sessions(event):
		global sig
		sig = "\x1F"
		event.app.exit(result=None)

	@prompt.register_kb("alt-a")
	def _handle_nav_artists(event):
		global sig
		sig = "\x2D"
		event.app.exit(result=None)

	@prompt.register_kb("c-space")
	def _handle_add(event):
		global sig
		sig = "\x06"
		state.selChoiceIdx = prompt.content_control.selected_choice_index
		prompt._handle_enter(event)

	@prompt.register_kb("alt-left")
	def _handle_nav_back(event):
		global sig
		sig = "\x08"
		state.selChoiceIdx = prompt.content_control.selected_choice_index
		event.app.exit(result=None)

	@prompt.register_kb("c-s")
	def _handle_sess(event):
		global sig
		sig = "\x14"
		state.selChoiceIdx = prompt.content_control.selected_choice_index
		prompt._handle_enter(event)

	@prompt.register_kb("alt-h")
	def _handle_manual(event):
		qout.put("\x42")
		e.set()

	if state.type == 'session':
		@prompt.register_kb("delete")
		def _handle_delete(event):
			global sig
			sig = "\x15"
			prompt._handle_enter(event)

	if state.type != "radio":
		@prompt.register_kb("alt-o")
		def _handle_open(event):
			qout.put(f"\x01\0{prompt.content_control.selection["value"]}")
			e.set()

		@prompt.register_kb("alt-i")
		def _handle_open_coverart(event):
			qout.put(f"\x07\0{prompt.content_control.selection["value"]}")
			e.set()

		@prompt.register_kb("alt-w")
		def _handle_open_webapp(event):
			qout.put("\x10")
			e.set()

	try:
		state.selChoice = prompt.execute()
	except KeyboardInterrupt:
		state.sig = KeyboardInterrupt
	else:
		state.sig = sig

	state.choices = []
	qout.put(state)
	e.set()

def getAlbumDetailsById(qin, qout, e, _):
	state = qin.get()
	prompt = inquirer.select(message='Album details', choices=state.alProp, keybindings={"toggle": []},
		long_instruction="+foo: c-space / open: a-o / cover: a-i",
		default=None, show_cursor=False, style=style, height="100%"
	)

	@prompt.register_kb("c-space")
	def _handle_add(event):
		global sig
		sig = "\x06"
		event.app.exit(result=None)

	@prompt.register_kb("alt-left")
	def _handle_nav_back(event):
		global sig
		sig = "\x08"
		event.app.exit(result=None)

	@prompt.register_kb("alt-o")
	def _handle_open(event):
		qout.put("\x01")
		e.set()

	@prompt.register_kb("alt-i")
	def _handle_open(event):
		qout.put("\x07")
		e.set()

	try:
		state.selChoice = prompt.execute()
	except KeyboardInterrupt:
		state.sig = KeyboardInterrupt
	else:
		state.sig = sig

	state.alProp = []
	qout.put(state)
	e.set()

def action(qin, qout, e, _):
	state = qin.get()
	prompt = inquirer.select(message='Select action', long_instruction="select mode: a-m", choices=['add to foobar', 'add to foobar (remote)', 'print details'],
		default=state.action, show_cursor=False, style=style, height="100%")

	@prompt.register_kb("alt-left")
	def _handle_nav_back(event):
		global sig
		sig = "\x08"
		event.app.exit(result=None)

	@prompt.register_kb("alt-m")
	def _handle_mode(event):
		global sig
		sig = "\x05"
		event.app.exit(result=None)

	try:
		state.selChoice = prompt.execute()
	except KeyboardInterrupt:
		state.sig = KeyboardInterrupt
	else:
		state.sig = sig
	qout.put(state)
	e.set()

def mode(qin, qout, e, _):
	state = qin.get()
	prompt = inquirer.select(message='Select mode', choices=['file system', 'stream'],
		default=state.mode, show_cursor=False, style=style, height="100%")

	@prompt.register_kb("alt-left")
	def _handle_nav_back(event):
		global sig
		sig = "\x08"
		event.app.exit(result=None)

	try:
		state.selChoice = prompt.execute()
	except KeyboardInterrupt:
		state.sig = KeyboardInterrupt
	else:
		state.sig = sig
	qout.put(state)
	e.set()

def backToList(qin, qout, e, _):
	state = qin.get()
	try:
		if inquirer.confirm(message="Back to list", default=True,
			confirm_letter="y", reject_letter="n", style=style
		).execute():
			state.selChoice = True
		else:
			state.selChoice = False
	except KeyboardInterrupt:
		state.sig = KeyboardInterrupt
	qout.put(state)
	e.set()

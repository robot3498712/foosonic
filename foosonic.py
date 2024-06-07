#!/usr/bin/env python3
'''
foosonic client by robot
	https://github.com/crustymonkey/py-sonic/blob/master/libsonic/connection.py
	https://github.com/kazhala/InquirerPy | https://inquirerpy.readthedocs.io/en/latest/index.html
'''

class _State:
	def __init__(self):
		self.call = deque([None])
		self.pool = deque(maxlen=2)
		self.procs = deque(maxlen=20)
		self.wndQs = deque()
		self.iter = tEvent()
		self.web = self.remote = (None,) * 5
		self.seen = set()
		self.choices = []
		self.sessions = []
		self.alProp = []

class State:
	def __init__(self):
		self.ltype = 'album'
		self.type = 'album'
		self.numRes = 0
		self.selChoiceIdx = -1
		self.selChoice = None
		self.fuzzy = {'genre': None, 'artist': None, 'session': None, 'radio': None, 'album': None}
		self.alId = None
		self.sess = None
		self.sig = None

class Page:
	def __init__(self, key, size, pbar=None):
		self._key = key
		self._size = size
		self._len = 0
		self.pbar = pbar

		with lock:
			if not self._key in _state._data:
				_state._data[self._key] = {}

	def fetch(self, fn, *args, **kwargs):
		_offset, _psize = 0, min(self._size, cfg.perf['pageSize'])
		'''
		don't use dict.update(), which introduces weird inconsistencies
		'''
		for i in itertools.count(start=1):
			if evTerm.is_set(): break
			match self._key:

				case 'albumList':
					_len, r = 0, fn(*args, **kwargs, size=_psize, offset=_offset)
					with lock:
						if not 'album' in _state._data[self._key]: _state._data[self._key]['album'] = []
						if 'album' in r[self._key]:
							_state._data[self._key]['album'].extend(r[self._key]['album'])
							_len = len(r[self._key]['album'])
					self._len += _len

				case 'searchResult2' | 'searchResult3':
					_len, r = 0, fn(*args, **kwargs, albumCount=_psize, albumOffset=_offset, songCount=_psize, songOffset=_offset, artistCount=_psize, artistOffset=_offset)
					with lock:
						for _key in ['album', 'artist', 'song']:
							if not _key in _state._data[self._key]: _state._data[self._key][_key] = []
							if _key in r[self._key]:
								_state._data[self._key][_key].extend(r[self._key][_key])
								_len = max(_len, len(r[self._key][_key]))
					self._len += _len

				case 'artist':
					r = fn(*args, **kwargs)
					with lock:
						if not 'album' in _state._data[self._key]: _state._data[self._key]['album'] = []
						_state._data[self._key]['album'].extend(r[self._key]['album'])
					break
				case _:
					break

			try: self.pbar.update(1)
			except: pass

			if (_len < _psize) or (self._len >= self._size): break
			_offset = _psize * i
		# end FOR
	# end fetch()

class Choice(dict):
	def __init__(self, value, name=None, enabled=False):
		super().__init__(value=value, name=name, enabled=enabled)
		if 'name' not in self or self['name'] is None:
			self['name'] = str(value)

	def __getattr__(self, attr): return self[attr]

class Separator(Choice):
	''' workaround: fuzzy prompts raise on built-in sep usage. compact ex. f"{'~'*50}" '''
	def __init__(self, name=f"{'\u00B7'*49}\U0001F47B"):
		super().__init__(value=None, name=name)


''' --------------- helpers ---------------  '''

def opendir(path):
	if not path: return
	if os.name == 'nt': return os.startfile(path)
	if os.name == 'posix': return Popen(["xdg-open", path])

def clean():
	for f in glob(sd + './cache/*.m3u*'): os.remove(f)

def clear():
	_ = call('clear' if os.name =='posix' else 'cls', shell=True)


''' --------------- windows ---------------  '''

def tWndCoverArt():
	t = Thread(target=show, args=[window.coverArt])
	t.daemon = True
	t.start()

def tWndManual():
	t = Thread(target=show, args=[window.manual])
	t.daemon = True
	t.start()


''' --------------- remotes ---------------  '''

def tRemote(m3ufile=None):
	if m3ufile:
		state.serve = m3ufile
		t = Thread(target=show, args=[remote.playlist])
		t.daemon = True
		return t.start()
	while not evTerm.is_set():
		(*_, qout, _, _) = _state.remote
		try: qout.put(None)
		except ValueError: sleep(0.05)
		except Exception as e: raise e
		else: break


''' --------------- webapps ---------------  '''

def tWeb():
	(p, *_) = _state.web
	if p: return
	t = Thread(target=show, args=[web.app])
	t.daemon = True
	t.start()


''' --------------- dialogs ---------------  '''

def dlgBackToList():
	show(prompt.backToList)
	# the call stack is somewhat of a mess
	if not state.selChoice:
		return _state.call.reverse() # quit via pop None
	fn = listStations if state.type == "radio" else listAlbums
	_state.call.append(lambda: fn())
	clear()

def dlgMode():
	show(prompt.mode)
	if state.sig == "\x08":
		clear()
		return _state.call.append(lambda: listAlbums())
	if state.selChoice in ["stream", "file system"]:
		args['mode'] = state.selChoice

def dlgAction(ids=[]):
	if not ids: ids = state.selChoice

	show(prompt.action)
	if state.sig == "\x08":
		clear()
		return _state.call.append(lambda: listAlbums())

	if state.sig == "\x05":
		clear()
		_state.call.append(lambda: dlgAction(ids))
		return _state.call.append(lambda: dlgMode())

	if state.selChoice == "print details":
		if state.type == 'radio': # just ignore it
			return _state.call.pop()
		args['action'] = state.selChoice
		_state.call.append(lambda: dlgBackToList())
		return _state.call.append(lambda: getAlbumDetailsById(ids[0]))

	if state.selChoice.startswith("add to foobar"):
		args['action'] = state.selChoice
		args['foo'] = state.selChoice
		_state.call.append(lambda: dlgBackToList())
		_state.call.append(lambda: add(ids))
		if not args['mode'] and state.type != 'radio':
			_state.call.append(lambda: dlgMode())


''' --------------- list views ---------------  '''

def listSessions():
	state.type = 'session'
	if not len(_state.sessions):
		for fname in sorted(glob(sd + './cache/sess.*'), key=os.path.getmtime, reverse=True):
			with open(fname, mode="rb") as f: sess = pickle.load(f)
			_state.sessions.append(Choice(fname,
				name=f"{sess['name'].ljust(70)}{strftime('%Y-%m-%d %H:%M:%S', localtime(int((fname.split('.'))[-2])))}"
			))
	if not len(_state.sessions):
		print("no sessions")
	else:
		show(prompt.listSessions)
		if state.sig == "\x08":
			if not len(_state.choices): return
			state.type = state.ltype
			clear()
			return _state.call.append(lambda: listAlbums())

		if state.sig == "\x2B":
			print("can't make empty list. use c-s to select and store")
			return _state.call.append(lambda: listSessions())

		if state.sig == "\x15":
			fp = state.selChoice
			show(prompt.confRmSession)
			if state.selChoice:
				_state.sessions = []
				os.remove(fp)
			clear()
			return _state.call.append(lambda: listSessions())

		if state.sig == "\x26":
			fp = state.selChoice
			_state.call.append(lambda: listSessions())
			with open(fp, mode="rb") as f: sess = pickle.load(f)
			state.fuzzy['session'] = sess['name']
			show(prompt.nameSession)
			if state.sig != "\x08":
				_state.sessions, state.fuzzy['session'] = [], None
				with open(fp, mode="wb") as f:
					pickle.dump({
						'name': state.selChoice,
						'choices': sess['choices']
					}, f)
			return clear()

		with open(state.selChoice, mode="rb") as f: sess = pickle.load(f)
		_state.choices = sess['choices']
		if numRes := len(_state.choices):
			state.numRes = numRes
			state.sess = state.selChoice
			_state.call.append(lambda: listAlbums())
			clear()

def listStations():
	state.type = state.ltype = 'radio'
	show(prompt.listAlbums)

	if state.sig == "\x06":
		urls = state.selChoice
		_state.call.append(lambda: listStations())
		_state.call.append(lambda: add(urls))
		if not args['foo']:
			return _state.call.append(lambda: dlgAction(urls))
		return

	if state.sig == "\x08":
		return clear()

	if state.sig == "\x1D":
		return _state.call.append(lambda: listGenres())

	if state.sig == "\x2D":
		return _state.call.append(lambda: listArtists())

	if state.sig == "\x1F":
		return _state.call.append(lambda: listSessions())

	_state.call.append(lambda: dlgAction())

def listAlbums():
	tWeb()
	show(prompt.listAlbums)

	if state.sig == "\x06":
		alIDs = state.selChoice
		_state.call.append(lambda: listAlbums())
		_state.call.append(lambda: add(alIDs))
		if not args['foo']:
			return _state.call.append(lambda: dlgAction(alIDs))
		if not args['mode']:
			return _state.call.append(lambda: dlgMode())
		return

	if state.sig == "\x08":
		clear()
		return _state.call.append(lambda: listAlbums())

	if state.sig == "\x1D":
		return _state.call.append(lambda: listGenres())

	if state.sig == "\x2D":
		return _state.call.append(lambda: listArtists())

	if state.sig == "\x1E":
		return _state.call.append(lambda: getStations())

	if state.sig == "\x1F":
		return _state.call.append(lambda: listSessions())

	if state.sig == "\x14":
		return _state.call.append(lambda: getSessions())

	if state.sig == "\x15":
		if trimSession():
			return _state.call.append(lambda: listAlbums())
		return _state.call.append(lambda: listSessions())

	_state.call.append(lambda: dlgAction())

def listGenres():
	state.type, state.ltype, _state.choices = 'album', 'genre', []
	genrescache = os.path.join(sd, './cache/genres.obj')
	if not os.path.isfile(genrescache) or (time() - os.path.getmtime(genrescache)) > 2592000:
		print("updating genres..")
		updateGenres()
	with open(genrescache, mode="rb") as f: _state.choices = pickle.load(f)
	if _len := len(_state.choices):
		state.numRes = _len
		clear()
		show(prompt.listGenres)

		if state.sig == "\x08":
			return _state.call.append(lambda: listGenres())

		if state.sig == "\x2D":
			return _state.call.append(lambda: listArtists())

		if state.sig == "\x1E":
			return _state.call.append(lambda: getStations())

		if state.sig == "\x1F":
			return _state.call.append(lambda: listSessions())

		_state.call.append(lambda: getAlbumsByGenres(state._size))

def listArtists():
	state.type, state.ltype, _state.choices = 'album', 'artist', []
	artistscache = os.path.join(sd, './cache/artists.obj')
	if not os.path.isfile(artistscache) or (time() - os.path.getmtime(artistscache)) > 2592000:
		print("updating artists..")
		updateArtists()
	with open(artistscache, mode="rb") as f: _state.choices = pickle.load(f)
	if _len := len(_state.choices):
		state.numRes = _len
		clear()
		show(prompt.listArtists)

		if state.sig == "\x08":
			return _state.call.append(lambda: listArtists())

		if state.sig == "\x1D":
			return _state.call.append(lambda: listGenres())

		if state.sig == "\x1E":
			return _state.call.append(lambda: getStations())

		if state.sig == "\x1F":
			return _state.call.append(lambda: listSessions())

		_state.call.append(lambda: getAlbumsByArtists(state._size))


''' --------------- search & fetch sets ---------------  '''

# @size unlimited
def getAlbums(ltype, _size):
	_state._data, _state.choices = {}, []
	with tqdm(desc=ltype.title()) as pbar:
		Page('albumList', _size, pbar=pbar).fetch(_state.connector.conn.getAlbumList, ltype)
	for album in _state._data['albumList']['album']:
		_state.choices.append(Choice(album['id'], name=f"{album['artist']}/{album['title']}"))
	del _state._data
	if numRes := len(_state.choices):
		state.numRes = numRes
		_state.call.append(lambda: listAlbums())
		clear()
	else: print("no result")

# @size unlimited
def getAlbumsByYear(query, _size):
	_state._data, alDict, _fromYear, _toYear, query = {}, {}, None, None, query.strip()
	if '-' in query and (_q := query.split('-')):
		_fromYear, _toYear = _q[0].strip(), _q[1].strip()
	else:
		_fromYear = _toYear = query
	with tqdm(desc='Year') as pbar:
		Page('albumList', _size, pbar=pbar).fetch(_state.connector.conn.getAlbumList, 'byYear', fromYear=_fromYear, toYear=_toYear)
	for album in _state._data['albumList']['album']:
		alDict[f"{album['artist']}/{album['title']}"] = album['id']
	del _state._data
	for key in sorted(alDict.keys()):
		_state.choices.append(Choice(alDict[key], name=key))
	if numRes := len(_state.choices):
		state.numRes = numRes
		_state.call.append(lambda: listAlbums())
		clear()
	else: print("no result")

# threadpool dispatch
def tGetAlbumsByGenre(genreQuery, _size):
	Page('albumList', _size).fetch(_state.connector.conn.getAlbumList, 'byGenre', genre=genreQuery)

def getAlbumsByGenres(_size):
	state.selChoiceIdx, _state.choices, _state.seen, alDict, _state._data = -1, [], set(), {}, {}
	tGetAlbumsByGenreP = partial(tGetAlbumsByGenre, _size=_size)
	shuffle(state.selChoice)
	with ThreadPoolExecutor(cfg.perf["searchThreads"]) as _state.tpe:
		list(tqdm(_state.tpe.map(tGetAlbumsByGenreP, state.selChoice), total=len(state.selChoice), desc='Genre'))
	for album in _state._data['albumList']['album']:
		if album['id'] in _state.seen: continue
		alDict[f"{album['artist']}/{album['title']}"] = album['id']
		_state.seen.add(album['id'])
	del _state._data
	for key in sorted(alDict.keys()):
		_state.choices.append(Choice(alDict[key], name=key))
	if numRes := len(_state.choices):
		state.numRes = numRes
		_state.call.append(lambda: listAlbums())
		clear()
	else:
		_state.call.append(lambda: listGenres())

def getAlbumsByArtists(_size):
	state.selChoiceIdx, _state.choices, _state.seen, alDict, _state._data = -1, [], set(), {}, {}

	tGetArtistP = partial(tGetArtist, _size=_size)
	with ThreadPoolExecutor(cfg.perf["searchThreads"]) as _state.tpe:
		list(tqdm(_state.tpe.map(tGetArtistP, state.selChoice), total=len(state.selChoice), desc='Artist'))

	# songDict concept not implemented (yet)
	for album in _state._data['artist']['album']:
		if album['id'] in _state.seen: continue
		title = [album['artist']]
		if 'year' in album and album['year']: title.append(f"{album['year']}")
		title.append(album['name'])
		alDict[' / '.join(title)] = album['id']
		_state.seen.add(album['id'])

	del _state._data
	for key in sorted(alDict.keys()):
		_state.choices.append(Choice(alDict[key], name=key))

	if numRes := len(_state.choices):
		state.numRes = numRes
		_state.call.append(lambda: listAlbums())
		clear()
	else: print("no result")

# @size unlimited
# @query exact genre needed, and no combinations
def getAlbumsByGenre(query, _size):
	genrescache = os.path.join(sd, './cache/genres.obj')
	if not os.path.isfile(genrescache):
		print("update the genre cache first: -ug")
		return
	# tbd: show warning if genre cache is outdated, say older than 1 month
	with open(genrescache, mode="rb") as f: choices = pickle.load(f)
	alDict, _state._data = {}, {}
	if choices:
		genreQueryList = []
		for choice in choices:
			if query.lower() in choice.name.lower():
				genreQueryList.append(choice.value)
		if _len := len(genreQueryList):
			tGetAlbumsByGenreP = partial(tGetAlbumsByGenre, _size=_size)
			shuffle(genreQueryList)
			with ThreadPoolExecutor(cfg.perf["searchThreads"]) as _state.tpe:
				list(tqdm(_state.tpe.map(tGetAlbumsByGenreP, genreQueryList), total=_len, desc='Genre'))
			for album in _state._data['albumList']['album']:
				if album['id'] in _state.seen: continue
				alDict[f"{album['artist']}/{album['title']}"] = album['id']
				_state.seen.add(album['id'])
	del _state._data
	for key in sorted(alDict.keys()):
		_state.choices.append(Choice(alDict[key], name=key))
	if numRes := len(_state.choices):
		state.numRes = numRes
		_state.call.append(lambda: listAlbums())
		clear()
	else: print("no result")

# threadpool dispatch
def tGetSearch(fn, _key, _query, _size, pbar=None):
	Page(_key, _size, pbar=pbar).fetch(fn, _query)

def tGetArtist(id, _size):
	Page('artist', _size).fetch(_state.connector.conn.getArtist, id)

def getSearch(query, _size, _all=False):
	_state._data, alDict, songDict, arIDs = {}, {}, {}, set()
	with tqdm(desc='Search') as pbar:
		with ThreadPoolExecutor(2) as _state.tpe:
			_state.tpe.submit(tGetSearch, _state.connector.conn.search2, 'searchResult2', query, _size, pbar)
			_state.tpe.submit(tGetSearch, _state.connector.conn.search3, 'searchResult3', query, _size, pbar)

	if 'album' in _state._data['searchResult2']:
		for album in _state._data['searchResult2']['album']:
			if album['id'] in _state.seen: continue
			alDict[album['title']] = album['id']
			_state.seen.add(album['id'])
	if 'song' in _state._data['searchResult2']:
		for song in _state._data['searchResult2']['song']:
			if song['parent'] in _state.seen: continue
			title = [song['album']]
			title.append(f"{song['artist'] if 'artist' in song else 'Unknown Artist'} - {song['title']}")
			title = ' / '.join(title)
			songDict[title] = song['parent']
			_state.seen.add(song['parent'])
	if 'artist' in _state._data['searchResult2']:
		for artist in _state._data['searchResult2']['artist']:
			if not artist['id'] in arIDs: arIDs.add(artist['id'])

	# tag lookup
	if 'album' in _state._data['searchResult3']:
		for album in _state._data['searchResult3']['album']:
			if album['id'] in _state.seen: continue
			title = [album['name']]
			if 'year' in album and album['year']: title.append(f"{album['year']}")
			if 'artist' in album and album['artist']: title.append(album['artist'])
			title = ' / '.join(title)
			alDict[title] = album['id']
			_state.seen.add(album['id'])
	if 'song' in _state._data['searchResult3']:
		for song in _state._data['searchResult3']['song']:
			if song['parent'] in _state.seen: continue
			title = [song['album']]
			if 'year' in song and song['year']: title.append(f"{song['year']}")
			title.append(f"{song['artist'] if 'artist' in song else 'Unknown Artist'} - {song['title']}")
			title = ' / '.join(title)
			songDict[title] = song['parent']
			_state.seen.add(song['parent'])
	if 'artist' in _state._data['searchResult3']:
		for artist in _state._data['searchResult3']['artist']:
			if not artist['id'] in arIDs: arIDs.add(artist['id'])

	if _all and (_len := len(arIDs)):
		tGetArtistP = partial(tGetArtist, _size=_size)
		with ThreadPoolExecutor(cfg.perf["searchThreads"]) as _state.tpe:
			list(tqdm(_state.tpe.map(tGetArtistP, arIDs), total=_len, desc='Artist'))

		for album in _state._data['artist']['album']:
			if album['id'] in _state.seen: continue
			title = []
			# WIP (transliterate)
			if query.lower() in album['artist'].lower():
				title.append(album['artist'])
				if 'year' in album and album['year']: title.append(f"{album['year']}")
				title.append(album['name'])
				alDict[' / '.join(title)] = album['id']
			else:
				title.append(album['name'])
				if 'year' in album and album['year']: title.append(f"{album['year']}")
				title.append(album['artist'])
				songDict[' / '.join(title)] = album['id']
			_state.seen.add(album['id'])

	del _state._data
	for key in sorted(alDict.keys()):
		_state.choices.append(Choice(alDict[key], name=key))
	if len(songDict):
		_state.choices.append(Separator())
	for key in sorted(songDict.keys()):
		_state.choices.append(Choice(songDict[key], name=key))

	if numRes := len(_state.choices):
		state.numRes = numRes if not len(songDict) else numRes-1
		_state.call.append(lambda: listAlbums())
		clear()
	else: print("no result")

def getAlbumPathById(id):
	r = _state.connector.conn.getAlbum(id)
	if 'songCount' in r['album'] and r['album']['songCount'] > 0:
		for song in r['album']['song']:
			p = song['path']
			path = None
			for k, v in cfg.pathmap.items():
				if p.startswith(k):
					path = f"{v}{p}"
					break
			if not path:
				path = f'{cfg.pathmap["\0"]}{p}'
			return os.path.dirname(os.path.abspath(path))
	return None

def getAlbumDetailsById(id):
	if not id: return _state.call.pop()
	r = _state.connector.conn.getAlbum(id)
	if not 'songCount' in r['album'] or not r['album']['songCount']:
		return print("invalid album or songcount is zero")

	prop, al, alArtist = [], None, None
	if r['album']['artist']:
		alArtist = r['album']['artist']
		prop.append(f"{'artist'.ljust(10)}: {r['album']['artist']}")
	if al := r['album']['album']: prop.append(f"{'album'.ljust(10)}: {r['album']['album']}")
	if al != r['album']['name']: prop.append(f"{'name'.ljust(10)}: {r['album']['name']}")
	if al != r['album']['title']: prop.append(f"{'title'.ljust(10)}: {r['album']['title']}")

	if 'year' in r['album'] and r['album']['year']: prop.append(f"{'year'.ljust(10)}: {r['album']['year']}")
	if 'genre' in r['album'] and r['album']['genre']: prop.append(f"{'genre'.ljust(10)}: {r['album']['genre']}")
	if r['album']['songCount']: prop.append(f"{'songCount'.ljust(10)}: {r['album']['songCount']}")

	prop.append(f"{'tracks'.ljust(10)}:")
	for song in r['album']['song']:
		if alArtist == song['artist']:
			prop.append(f"{(f"{song['track'] if 'track' in song else 0}").rjust(3)} - {song['title']}")
		else:
			prop.append(f"{(f"{song['track'] if 'track' in song else 0}").rjust(3)} - {song['artist']} - {song['title']}")

	prop.append('')
	if r['album']['duration']:
		prop.append(f"{'duration'.ljust(10)}: {r['album']['duration']} ({ceil(r['album']['duration'] / 60)}m)")
	if r['album']['created']: prop.append(f"{'created'.ljust(10)}: {r['album']['created']}")
	if r['album']['artistId']: prop.append(f"{'artistId'.ljust(10)}: {r['album']['artistId']}")
	if r['album']['id']: prop.append(f"{'albumId'.ljust(10)}: {r['album']['id']}")
	if 'coverArt' in r['album'] and r['album']['coverArt']: prop.append(f"{'coverArt'.ljust(10)}: {r['album']['coverArt']}")

	_state.alProp = prop
	state.alId = id
	clear()
	show(prompt.getAlbumDetailsById)

	if state.sig == "\x06":
		_state.call.append(lambda: getAlbumDetailsById(id))
		_state.call.append(lambda: add([id]))
		if not args['mode']:
			return _state.call.append(lambda: dlgMode())
		return clear()

	if state.sig == "\x08":
		_state.call.append(lambda: listAlbums())
		clear()


''' --------------- store & pipe ---------------  '''

def add(ids, silent=False):
	_state._data, fnx, tasks, step, header, m3ufile = {}, [], [], 50, False, os.path.join(sd, f"./cache/{int(time())}.m3u8")
	ids = deque([str(x) for x in ids if x is not None])
	if (args['foo'] and "remote" in args['foo']): tRemote(m3ufile)
	with open(m3ufile, mode="a", encoding="utf8") as fh:	
		for id in ids:
			if not "://" in id:
				if args['mode'] == "stream":
					fn = tAddAlbumByIdStream
					if not header: header = fh.write("#EXTM3U\n")
				else:
					fn = tAddAlbumById
			else:
				fn = tAddStation
				if not header: header = fh.write("#EXTM3U\n")
			fnx.append(partial(fn, id=id))
		# end FOR
		# preserving FIFO, flush to file on step
		with tqdm(total=len(ids), desc='Add', disable=silent) as pbar:
			with ThreadPoolExecutor(cfg.perf["addThreads"]) as _state.tpe:
				for fn in fnx: tasks.append(_state.tpe.submit(fn))
				for _ in as_completed(tasks):
					pbar.update(1)
					if not pbar.n % step:
						with lock:
							for i in itertools.count(start=0):
								try:
									if not ids[i] in _state._data: break
									try: fh.write(_state._data[ids[i]] + "\n")
									except:
										if not silent: print(f"failed to add {ids[i]}")
								except IndexError: # EODeque
									break
							for j in itertools.count(start=0):
								if j==i: break
								del _state._data[ids.popleft()]
			# end WITH_TPE
		# end WITH_TQDM
		for id in ids:
			try: fh.write(_state._data[id] + "\n")
			except:
				if not silent: print(f"failed to add {id}")
	# end WITH_OPEN
	del _state._data
	try:
		if os.stat(m3ufile).st_size < 12: raise ValueError
		if (args['foo'] and "remote" in args['foo']):
			tRemote()
		else:
			p = Popen([cfg.foo, '/add', m3ufile])
	except Exception as e:
		if not silent: print(f"error adding playlist: {e}")
	else:
		state._remote = True

# threadpool dispatch
def tAddAlbumById(id):
	if evTerm.is_set(): return
	paths, r = [], _state.connector.conn.getAlbum(id)
	if 'album' in r:
		if ('songCount' in r['album'] and r['album']['songCount'] > 0):
			for song in r['album']['song']:
				p = song['path']
				path = None
				for k, v in cfg.pathmap.items():
					if p.startswith(k):
						path = f"{v}{p}"
						break
				if not path:
					path = f'{cfg.pathmap["\0"]}{p}'
				paths.append(path)
			if len(paths):
				with lock: _state._data[id] = "\n".join(paths)
	return

def tAddAlbumByIdStream(id):
	if evTerm.is_set(): return
	urls, r = [], _state.connector.conn.getAlbum(id)
	if 'album' in r:
		if ('songCount' in r['album'] and r['album']['songCount'] > 0):
			af = lambda x: (x if len(x) <= 30 else x[:30].strip()) + " ~ "
			if r['album']: album = af(f"{r['album']['name']}")
			elif r['album']['title']: album = af(f"{r['album']['title']}")
			else: album = ''

			for song in r['album']['song']:
				url = _state.connector.conn.stream(song['id'], maxBitRate=192)
				urls.append(f"#EXTINF:{song['duration'] if song['duration'] else '-1'},{album}{song['artist']} - {song['title']}")
				urls.append(url)
			if len(urls):
				with lock: _state._data[id] = "\n".join(urls)
	return

def tAddStation(id):
	if evTerm.is_set(): return
	urls, label = [], None
	for k, v in cfg.radio.items():
		if v == id:
			label = k
			break
	urls.append(f"#EXTINF:-1,{label} - {id}")
	urls.append(id)
	with lock: _state._data[id] = "\n".join(urls)
	return


''' --------------- misc. tasks ---------------  '''

def scan(start=True, progr=False):
	r = _state.connector.conn.getScanStatus()
	sc = r['scanStatus']['count']
	if start:
		if not r['scanStatus']['scanning']: r = _state.connector.conn.startScan()
		if progr:
			fc = lambda r: f"{r['scanStatus']['count']} <- {r['scanStatus']['count']-sc}" if r['scanStatus']['count'] > sc else sc
			fs = lambda r: f"scanning: {r['scanStatus']['scanning']} | count: {fc(r)}"
			with tqdm(desc=fs(r), bar_format='{desc} [{elapsed}]', position=0) as pbar:
				while True:
					sleep(1)
					pbar.update(1)
					if not pbar.n % 30:
						r = _state.connector.conn.getScanStatus()
						if not r['scanStatus']['scanning']: return pbar.set_description_str(fs(r))
	from pprint import pprint
	pprint(r, indent=1, sort_dicts=False)

# tbd: streamline & remove duplicated session code (as well see listSessions())
def getSessions():
	state.type, _state.sessions, alIds = state.ltype, [], state.selChoice

	_state.call.append(lambda: listAlbums())
	show(prompt.modeSession)
	if state.sig == "\x08":
		return clear()
	selected = True if state.selChoice == 'selected' else False
	args['sessmode'] = state.selChoice

	for fname in sorted(glob(sd + './cache/sess.*'), key=os.path.getmtime, reverse=True):
		with open(fname, mode="rb") as f: sess = pickle.load(f)
		_state.sessions.append(Choice(fname,
			name=f"{sess['name'].ljust(70)}{strftime('%Y-%m-%d %H:%M:%S', localtime(int((fname.split('.'))[-2])))}"
		))
	if not len(_state.sessions):
		show(prompt.nameSession)
		if state.sig == "\x08":
			return clear()
		makeSession(selected, alIds)
	else:
		show(prompt.listSessions)
		if state.sig == "\x2B":
			show(prompt.nameSession)
			if state.sig == "\x08":
				return clear()
			makeSession(selected, alIds)
		elif state.sig == "\x08":
			clear()
		else:
			expandSession(selected, alIds)

def trimSession():
	with open(state.sess, mode="rb") as f: sess = pickle.load(f)
	alDict, songDict, sep = {}, {}, False
	for choice in sess['choices']:
		if sep:
			if choice.value not in state.selChoice:
				songDict[choice.name] = choice.value
			continue
		try:
			if not choice.value: raise ValueError
			if choice.value not in state.selChoice:
				alDict[choice.name] = choice.value
		except:
			sep = True

	if not len(alDict) and not len(songDict):
		_state.sessions = []
		os.remove(state.sess)
		return False

	_state.choices = []
	for key in sorted(alDict.keys()):
		_state.choices.append(Choice(alDict[key], name=key))
	if len(songDict):
		_state.choices.append(Separator())
	for key in sorted(songDict.keys()):
		_state.choices.append(Choice(songDict[key], name=key))

	with open(state.sess, mode="wb") as f:
		pickle.dump({
			'name': sess['name'],
			'choices': _state.choices
		}, f)
	return True

def expandSession(selected=False, alIds=[]):
	with open(state.selChoice, mode="rb") as f: sess = pickle.load(f)
	alDict, songDict, sep = {}, {}, False
	for choice in sess['choices']:
		if sep:
			songDict[choice.name] = choice.value
			continue
		try:
			if not choice.value: raise ValueError
			alDict[choice.name] = choice.value
		except:
			sep = True

	with open(state.selChoice, mode="wb") as f:
		pickle.dump({
			'name': sess['name'],
			'choices': getSessionChoices(alDict, songDict, selected, alIds)
		}, f)

def getSessionChoices(alDict={}, songDict={}, selected=False, alIds=[]):
	sep, i = False, -1
	for choice in _state.choices:
		i += 1
		if sep:
			if not choice.name in songDict:
				if not selected or choice.value in alIds:
					songDict[choice.name] = choice.value
		try:
			if not choice.value: raise ValueError
			if not choice.name in alDict:
				if not selected or choice.value in alIds:
					alDict[choice.name] = choice.value
		except:
			sep = True

	choices = []
	for key in sorted(alDict.keys()):
		choices.append(Choice(alDict[key], name=key))
	if len(songDict):
		choices.append(Separator())
	for key in sorted(songDict.keys()):
		choices.append(Choice(songDict[key], name=key))
	return choices

def makeSession(selected=False, alIds=[]):
	fname = os.path.join(sd, f"./cache/sess.{int(time())}.obj")
	_state.sessions.insert(0, Choice(fname,
		name=f"{state.selChoice.ljust(70)}{strftime('%Y-%m-%d %H:%M:%S', localtime(int((fname.split('.'))[-2])))}"
	))
	with open(fname, mode="wb") as f:
		pickle.dump({
			'name': state.selChoice,
			'choices': _state.choices if not selected else getSessionChoices({}, {}, selected, alIds)
		}, f)

def getStations():
	_state.choices = []
	for k, v in cfg.radio.items():
		_state.choices.append(Choice(v, name=k))
	state.type = 'radio'
	state.numRes = len(cfg.radio)
	_state.call.append(lambda: listStations())
	clear()

def updateGenres():
	r = _state.connector.conn.getGenres()
	if 'genre' in r['genres']:
		_r = []
		for itm in r['genres']['genre']:
			if not 'albumCount' in itm: itm['albumCount'] = 0
			_r.append(itm)
		for itm in sorted(_r, key=lambda d: d['albumCount'], reverse=True):
			_state.choices.append(Choice(itm['value'], name=f"{itm['value']} ({itm['albumCount']})"))	
		with open(os.path.join(sd, './cache/genres.obj'), mode="wb") as f:
			pickle.dump(_state.choices, f)

def updateArtists():
	r = _state.connector.conn.getArtists()
	for index in r['artists']['index']:
		for artist in index['artist']:
			_state.choices.append(Choice(artist['id'], name=f"{artist['name']}"))
	with open(os.path.join(sd, './cache/artists.obj'), mode="wb") as f:
		pickle.dump(_state.choices, f)


''' --------------- processing ---------------
prompt_toolkit is leaking memory, so we create a new process for each prompt
- pool used to minimize latency
	1) event loop using threading: dispatch()->pman()->show()
	2) child process pool (size=2), waiting for prompt tasks '''

def wndPopper():
	while True: 
		try: q = _state.wndQs.pop()
		except IndexError: break
		else:
			try: q.put(None)
			except: pass

def qCloser(qin, qout):
	qin.close()
	qout.close()
	qin.cancel_join_thread()
	qout.cancel_join_thread()

def show(fn):
	shareState = copy(state)
	if fn in {prompt.listAlbums, prompt.listArtists, prompt.listGenres}:
		shareState.choices = _state.choices
	elif fn in {prompt.listSessions}:
		shareState.sessions = _state.sessions
	elif fn in {prompt.getAlbumDetailsById}:
		shareState.alProp = _state.alProp
	elif fn in {web.app, remote.playlist}:
		shareState.server = cfg.server
	else:
		shareState.mode = args['mode']
		shareState.action = args['action'] if 'action' in args else None
		shareState.sessmode = args['sessmode'] if 'sessmode' in args else None

	# threaded modules spin up on demand
	match fn:
		case remote.playlist:
			_state.remote = p = tmake(remote.run)
			p[0].start()

		case web.app:
			_state.web = p = tmake(web.run)
			p[0].start()

		case window.coverArt | window.manual:
			p = pmake(window.run)
			p[0].start()
			_state.wndQs.append(p[2])
			shareState.sd = sd

		case _:
			p = _state.pool.popleft()
			_state.iter.set()

	(_, qin, qout, evParent, evChild) = p
	qout.put(fn)
	qout.put(shareState)
	evChild.set()
	del shareState

	while not evTerm.is_set():
		try:
			evParent.wait()
			r = qin.get()
		except Exception:
			return qCloser(qin, qout)

		# on state object (i.e. prompt returning)
		if isinstance(r, State):
			wndPopper()
			break

		# instructions not requiring a new prompt
		if r == "\x00":
			if hasattr(state, '_remote'): del state._remote
			if len(_state.wndQs): wndPopper()
			return qCloser(qin, qout)
		elif r.startswith("\x01"):
			try:
				alId = (r.split("\0"))[1]
				opendir(getAlbumPathById(alId))
			except:
				opendir(getAlbumPathById(state.alId))
		elif r.startswith("\x07"):
			try:
				alId = (r.split("\0"))[1]
				if len(_state.wndQs) and alId == state.alId:
					wndPopper()
				else:
					state.alId = alId
					tWndCoverArt()
			except:
				if len(_state.wndQs): wndPopper()
				else: tWndCoverArt()
		elif r == "\x10":
			import webbrowser
			webbrowser.open(f"http://{cfg.server['web']['ip']}:{cfg.server['web']['port']}", new=2, autoraise=True)
		elif r.startswith("\x20\0"):
			(_, args['foo'], args['mode'], idsStr) = r.split("\0")
			add(idsStr.split(","), silent=True)
			# resolve a request promise; typically takes couple more seconds to complete the playlist transfer
			# a more sophisticated approach will yield bool result
			qout.put(None)
		elif r == "\x30":
			qout.put(_state.choices)
		elif r == "\x42":
			tWndManual()

	qCloser(qin, qout)
	if r.sig == KeyboardInterrupt: raise KeyboardInterrupt

	state.selChoice, state.selChoiceIdx = r.selChoice, r.selChoiceIdx
	state.sig, state.fuzzy = r.sig, r.fuzzy
# end show()

def pmake(target, tty=None):
	qe = (mpQueue(), mpQueue(), mpEvent(), mpEvent())
	if tty is not None:
		return (Process(target=target, daemon=True, args=(*qe, evTerm, tty)), *qe)
	return (Process(target=target, daemon=True, args=(*qe, evTerm)), *qe)

def tmake(target):
	qe = (mpQueue(), mpQueue(), mpEvent(), mpEvent())
	return (Thread(target=target, daemon=True, args=(*qe,)), *qe)

def pman():
	tty = True if os.name == 'posix' else False
	while not evTerm.is_set():
		p = pmake(prompt.run, tty)
		_state.pool.append([*p])
		_state.procs.append(p[0])
		p[0].start()
		_state.iter.wait()
		_state.iter.clear()

	try: _state.tpe.shutdown(wait=True, cancel_futures=True)
	except: pass

	for p in _state.procs:
		p.terminate()
		p.join()

def dispatch(man=True, exit=True):
	if man:
		t = Thread(target=pman)
		t.start()
	try:
		while True:
			try:
				_call = _state.call.pop()
				if not _call: raise IndexError
			except IndexError: break
			_call()
		if (args['foo'] and "remote" in args['foo']):
			while hasattr(state, '_remote'): sleep(0.05)
	except KeyboardInterrupt: pass
	except Exception as e: raise e
	finally:
		if man:
			evTerm.set()
			_state.iter.set()
			t.join()
	if exit: sys.exit(0)


def main():
	global args, _state, state, lock, evTerm
	clean()

	parser = ArgumentParser(description='foosonic client')
	parser.add_argument('-v', '--version', action='version', version='0.2.7')
	parser.add_argument('-a', '--add', help='add to foobar, such as <id1>[,<id2>]', required=False)
	parser.add_argument('-f', '--foo', help='set foo: local | remote', required=False)
	parser.add_argument('-l', '--size', help='specify list size, such as 50', required=False)
	parser.add_argument('-s', '--search', help='issue search query', required=False)
	parser.add_argument('-sa', '--searchall', help='issue search query with artist lookup', required=False)
	parser.add_argument('-y', '--year', help='list albums by year/range, such as 2020-2021', required=False)
	parser.add_argument('-g', '--genre', help='list albums by *genre*', required=False)
	parser.add_argument('-i', '--details', help='print details via id', required=False)
	parser.add_argument('-m', '--mode', help='set mode: stream | fs', required=False)
	parser.add_argument('-r', '--radio', help='select radio station', action='store_true', required=False)
	parser.add_argument('-ug', '--updategenres', help='update genre cache', action='store_true', required=False)
	parser.add_argument('-ua', '--updateartists', help='update artist cache', action='store_true', required=False)
	parser.add_argument('-gg', '--genres', help='list genres', action='store_true', required=False)
	parser.add_argument('-aa', '--artists', help='list artists', action='store_true', required=False)
	parser.add_argument('-ss', '--sessions', help='list sessions', action='store_true', required=False)
	parser.add_argument('-rand', '--random', help='list random albums', action='store_true', required=False)
	parser.add_argument('--scan', help='initiate rescan. --scan <argv> to check done', nargs='?', const=True, default=False)
	parser.add_argument('--status', help='print status', action='store_true', required=False)
	args = vars(parser.parse_args())
	# end argparse

	_state, state, _state.connector = _State(), State(), connection.LibSoniConn()
	lock, evTerm = Lock(), mpEvent()

	try:
		args['size'] = _size = int(args['size'])
		if args['size'] <= 0: raise ValueError
	except:
		args['size'] = 25
		_size = sys.maxsize
	finally:
		state.size = args['size']
		state._size = _size

	if args['searchall']:
		args['search'] = args['searchall']
		searchall = True
	else:
		searchall = False

	if args['mode']:
		if (args['mode'] == 'stream' or args['mode'] == 'fs'): pass
		else: args['mode'] = 'fs'

	if args['radio']:
		_state.call.append(lambda: getStations())
		dispatch()

	if args['year']:
		_state.call.append(lambda: getAlbumsByYear(args['year'], state._size))
		dispatch()

	if args['genre']:
		_state.call.append(lambda: getAlbumsByGenre(args['genre'], state._size))
		dispatch()

	if args['genres']:
		_state.call.append(lambda: listGenres())
		dispatch()

	if args['artists']:
		_state.call.append(lambda: listArtists())
		dispatch()

	if args['sessions']:
		_state.call.append(lambda: listSessions())
		dispatch()

	if args['search']:
		_state.call.append(lambda: getSearch(args['search'], state._size, _all=searchall))
		dispatch()

	if args['scan'] or args['status']:
		_state.call.append(lambda: scan(start=args['scan'], progr=(args['scan'] is not True)))
		dispatch(man=False)

	if args['add']:
		_state.call.append(lambda: add(args['add'].split(',')))
		dispatch(man=False, exit=True)

	if args['updategenres']:
		print("updating genres..")
		_state.call.append(lambda: updateGenres())
		dispatch(man=False, exit=False)
		print("done")
		sys.exit(0)

	if args['updateartists']:
		print("updating artists..")
		_state.call.append(lambda: updateArtists())
		dispatch(man=False, exit=False)
		print("done")
		sys.exit(0)

	if args['details']:
		if not "://" in args['details']:
			_state.call.append(lambda: getAlbumDetailsById(args['details']))
			dispatch()

	if args['random']:
		_state.call.append(lambda: getAlbums('random', state.size))
		dispatch()

	# default mode
	_state.call.append(lambda: getAlbums('newest', state.size))
	dispatch()

# end main()

if __name__ == "__main__":
	import sys, os, pickle, itertools
	from multiprocessing import (Event as mpEvent, Queue as mpQueue, Process)
	from threading import (Event as tEvent, Thread, Lock)
	from concurrent.futures import ThreadPoolExecutor, as_completed
	from functools import partial
	from glob import glob
	from subprocess import call, Popen
	from argparse import ArgumentParser
	from copy import copy
	from collections import deque
	from time import time, strftime, localtime, sleep
	from random import shuffle
	from math import ceil
	from tqdm import tqdm
	from foosonic import prompt, window, remote, web, connection
	from _config import cfg

	sd = os.path.dirname(os.path.realpath(__file__))
	args, _state, state, lock, evTerm = (None,) * 5

	main()
	sys.exit(0)

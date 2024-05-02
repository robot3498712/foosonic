#!/usr/bin/env python3
'''
foosonic client by robot
	https://github.com/crustymonkey/py-sonic/blob/master/libsonic/connection.py
	https://github.com/kazhala/InquirerPy | https://inquirerpy.readthedocs.io/en/latest/index.html
'''

class State:
	def __init__(self):
		self.connector = None
		self.type = 'album'
		self.numRes = 0
		self.choices = []
		self.selectedChoice = None
		self.selectedChoiceIndex = -1
		self.seen = set()
		self.sessions = []
		self.fuzzyText = {'genre': None, 'session': None, 'radio': None, 'album': None}
		self.alProp = []
		self.alId = None
		self.sess = None
		self.sig = None
		self.call = deque([lambda: None])
		self.serve = u""
		self.fh = None
		self._data = {}


''' --------------- helpers ---------------  '''

def opendir(path):
	if not path: return
	if os.name == 'nt': return os.startfile(path)
	if os.name == 'posix': return Popen(["xdg-open", path])

def clean():
	for f in glob(sd + './cache/*.m3u*'): os.remove(f)

def clear():
	_ = call('clear' if os.name =='posix' else 'cls', shell=True)

# mainly useful for cli ops like --add
def waitProcs():
	while True:
		_pool, _continue = [p for p, *_ in pool], False
		for proc in procs:
			if not proc in _pool:
				if proc.is_alive():
					_continue = True
					break
		if _continue:
			sleep(0.2)
			continue
		break


''' --------------- windows ---------------  '''

def wndCoverArt():
	t = Thread(target=show, args=[window.coverArt])
	t.daemon = True
	t.start()

def wndManual():
	t = Thread(target=show, args=[window.manual])
	t.daemon = True
	t.start()


''' --------------- remotes ---------------  '''

def remotePlaylist(m3ufile):
	global state
	state.serve = m3ufile
	t = Thread(target=show, args=[remote.playlist])
	t.daemon = True
	t.start()


''' --------------- webapps ---------------  '''

def webapp():
	(p, _, qout, _, evChild) = webProc
	if p:
		qout.put(state.choices)
		evChild.set()
	else:
		t = Thread(target=show, args=[wsgi.webapp])
		t.daemon = True
		t.start()


''' --------------- dialogs ---------------  '''

def dlgBackToList():
	show(prompt.backToList)
	if state.selectedChoice:
		fn = listStations if state.type == "radio" else listAlbums
		state.call.append(lambda: fn())
		clear()

def dlgMode():
	show(prompt.mode)
	if state.sig == "\x08":
		clear()
		return state.call.append(lambda: listAlbums())
	if state.selectedChoice in ["stream", "file system"]:
		args['mode'] = state.selectedChoice

def dlgAction(ids=[]):
	if not ids: ids = state.selectedChoice

	show(prompt.action)
	if state.sig == "\x08":
		clear()
		return state.call.append(lambda: listAlbums())

	if state.sig == "\x05":
		clear()
		state.call.append(lambda: dlgAction(ids))
		return state.call.append(lambda: dlgMode())

	if state.selectedChoice == "print details":
		if state.type == 'radio': # just ignore it
			return state.call.pop()
		args['action'] = state.selectedChoice
		state.call.append(lambda: dlgBackToList())
		return state.call.append(lambda: getAlbumDetailsById(ids[0]))

	if state.selectedChoice.startswith("add to foobar"):
		args['action'] = state.selectedChoice
		args['foo'] = state.selectedChoice
		state.call.append(lambda: dlgBackToList())
		state.call.append(lambda: add(ids))
		if not args['mode'] and state.type != 'radio':
			state.call.append(lambda: dlgMode())


''' --------------- list views ---------------  '''

def listSessions():
	global state
	state.type = 'session'
	if not len(state.sessions):
		for fname in sorted(glob(sd + './cache/sess.*'), key=os.path.getmtime, reverse=True):
			with open(fname, mode="rb") as f: sess = pickle.load(f)
			state.sessions.append(Choice(fname,
				name=u"%s%s" % (sess['name'].ljust(70), "%s" % strftime('%Y-%m-%d %H:%M:%S', localtime(int((fname.split('.'))[-2]))))
			))
	if not len(state.sessions):
		print("no sessions")
	else:
		show(prompt.listSessions)
		if state.sig == "\x08":
			if not len(state.choices): return
			clear()
			return state.call.append(lambda: listAlbums())

		if state.sig == "\x2B":
			print("can't make empty list. use c-s to select and store")
			return state.call.append(lambda: listSessions())

		if state.sig == "\x15":
			fp = state.selectedChoice
			show(prompt.confRmSession)
			if state.selectedChoice:
				state.sessions = []
				os.remove(fp)
			clear()
			return state.call.append(lambda: listSessions())

		if state.sig == "\x26":
			fp = state.selectedChoice
			state.call.append(lambda: listSessions())
			with open(fp, mode="rb") as f: sess = pickle.load(f)
			self.fuzzyText['session'] = sess['name']
			show(prompt.nameSession)
			if state.selectedChoice != "\x08":
				state.sessions = []
				with open(fp, mode="wb") as f:
					pickle.dump({
						'name': state.selectedChoice,
						'choices': sess['choices']
					}, f)
			return clear()

		with open(state.selectedChoice, mode="rb") as f: sess = pickle.load(f)
		state.choices = sess['choices']
		if numRes := len(state.choices):
			state.numRes = numRes
			state.sess = state.selectedChoice
			state.call.append(lambda: listAlbums())
			clear()

def listStations():
	show(prompt.listAlbums)

	if state.sig == "\x06":
		urls = state.selectedChoice
		state.call.append(lambda: listStations())
		state.call.append(lambda: add(urls))
		if not args['foo']:
			return state.call.append(lambda: dlgAction(urls))
		return

	if state.sig == "\x08":
		return clear()

	if state.sig == "\x1D":
		return state.call.append(lambda: listGenres())

	if state.sig == "\x1F":
		return state.call.append(lambda: listSessions())

	state.call.append(lambda: dlgAction())

def listAlbums():
	webapp()
	show(prompt.listAlbums)

	if state.sig == "\x06":
		alIDs = state.selectedChoice
		state.call.append(lambda: listAlbums())
		state.call.append(lambda: add(alIDs))
		if not args['foo']:
			return state.call.append(lambda: dlgAction(alIDs))
		if not args['mode']:
			return state.call.append(lambda: dlgMode())
		return

	if state.sig == "\x08":
		clear()
		return state.call.append(lambda: listAlbums())

	if state.sig == "\x1D":
		return state.call.append(lambda: listGenres())

	if state.sig == "\x1E":
		return state.call.append(lambda: getStations())

	if state.sig == "\x1F":
		return state.call.append(lambda: listSessions())

	if state.sig == "\x14":
		return state.call.append(lambda: getSessions())

	if state.sig == "\x15":
		if trimSession():
			return state.call.append(lambda: listAlbums())
		return state.call.append(lambda: listSessions())

	state.call.append(lambda: dlgAction())

def listGenres():
	global state
	state.type = 'album'
	genrescache = os.path.join(sd, './cache/genres.obj')
	if not os.path.isfile(genrescache):
		print("update the genre cache first: -ug")
		return
	# tbd: show warning if genre cache is outdated, say older than 1 month
	with open(genrescache, mode="rb") as f: genres = pickle.load(f)
	if genres:
		genreList = []
		for genre in genres:
			genreList.append(Choice(genre['value'], name=u"%s (%s)" % (genre['value'], genre['albumCount'])))

		state.choices = genreList
		clear()
		show(prompt.listGenres)

		if state.sig == "\x08":
			return state.call.append(lambda: listGenres())

		if state.sig == "\x1E":
			return state.call.append(lambda: getStations())

		if state.sig == "\x1F":
			return state.call.append(lambda: listSessions())

		state.call.append(lambda: getAlbumsByGenres(state._size))


''' --------------- search & fetch sets ---------------  '''

# @size unlimited
def getAlbums(ltype, _size):
	global state
	r = state.connector.conn.getAlbumList(ltype, size=_size)
	state.choices = []
	for album in r['albumList']['album']:
		state.choices.append(Choice(album['id'], name=u"%s/%s" % (album['artist'], album['title'])))
	if numRes := len(state.choices):
		state.numRes = numRes
		state.call.append(lambda: listAlbums())
		clear()
	else: print("no result")

# @size unlimited
def getAlbumsByYear(query, _size):
	global state
	_fromYear = _toYear = None
	query = query.strip()
	if '-' in query and (_q := query.split('-')):
		_fromYear = _q[0].strip()
		_toYear = _q[1].strip()
	else:
		_fromYear = _toYear = query
	r = state.connector.conn.getAlbumList('byYear', size=_size, fromYear=_fromYear, toYear=_toYear)
	alDict = {}

	for album in r['albumList']['album']:
		alDict[u"%s/%s" % (album['artist'], album['title'])] = album['id']
	for key in sorted(alDict.keys()):
		state.choices.append(Choice(alDict[key], name=key))
	if numRes := len(state.choices):
		state.numRes = numRes
		state.call.append(lambda: listAlbums())
		clear()
	else: print("no result")

# threadpool dispatch
def tGetAlbumsByGenre(genreQuery, _len, _size):
	global state
	if evTerm.is_set(): return
	state.numRes += 1
	print(u"%s of %i".ljust(70) % (("%s" % (state.numRes)).rjust(2), _len), end='\r')
	return state.connector.conn.getAlbumList('byGenre', size=_size, genre=genreQuery)

def getAlbumsByGenres(_size):
	global state
	state.selectedChoiceIndex, state.choices, state.seen, alDict = -1, [], set(), {}

	tGetAlbumsByGenreP = partial(tGetAlbumsByGenre, _len=len(state.selectedChoice), _size=_size)
	state.numRes = 0 # reused as counter
	with ThreadPoolExecutor(cfg.perf["searchThreads"]) as exe:
		for r in exe.map(tGetAlbumsByGenreP, state.selectedChoice):
			for album in r['albumList']['album']:
				if album['id'] in state.seen: continue
				alDict[u"%s/%s" % (album['artist'], album['title'])] = album['id']
				state.seen.add(album['id'])

	for key in sorted(alDict.keys()):
		state.choices.append(Choice(alDict[key], name=key))
	if numRes := len(state.choices):
		state.numRes = numRes
		state.call.append(lambda: listAlbums())
		clear()
	else:
		state.call.append(lambda: listGenres())

# @size unlimited
# @query exact genre needed, and no combinations
def getAlbumsByGenre(query, _size):
	global state
	genrescache = os.path.join(sd, './cache/genres.obj')
	if not os.path.isfile(genrescache):
		print("update the genre cache first: -ug")
		return
	# tbd: show warning if genre cache is outdated, say older than 1 month
	with open(genrescache, mode="rb") as f: genres = pickle.load(f)
	alDict = {}
	if genres:
		genreQueryList = []
		for genre in genres:
			if query.lower() in genre['value'].lower():
				genreQueryList.append(genre['value'])
		if _len := len(genreQueryList):
			tGetAlbumsByGenreP = partial(tGetAlbumsByGenre, _len=_len, _size=_size)
			state.numRes = 0 # reused as counter
			with ThreadPoolExecutor(cfg.perf["searchThreads"]) as exe:
				for r in exe.map(tGetAlbumsByGenreP, genreQueryList):
					for album in r['albumList']['album']:
						if album['id'] in state.seen: continue
						alDict[u"%s/%s" % (album['artist'], album['title'])] = album['id']
						state.seen.add(album['id'])

	for key in sorted(alDict.keys()):
		state.choices.append(Choice(alDict[key], name=key))
	if numRes := len(state.choices):
		state.numRes = numRes
		state.call.append(lambda: listAlbums())
		clear()
	else: print("no result")

# threadpool dispatch
def tGetSearch(fn, _key, _query, _size):
	global state
	state._data[_key] = fn(_query, albumCount=_size, songCount=_size, artistCount=_size)

def tGetArtist(id, _len):
	global state
	if evTerm.is_set(): return
	state.numRes += 1
	print(u"%s of %i".ljust(70) % (("%s" % (state.numRes)).rjust(2), _len), end='\r')
	return state.connector.conn.getArtist(id)

def getSearch(query, _size, _all=False):
	global state
	fnx, alDict, songDict, arIDs = [], {}, {}, set()
	fnx.append(partial(tGetSearch, fn=state.connector.conn.search2, _key='s2', _query=query, _size=_size))
	fnx.append(partial(tGetSearch, fn=state.connector.conn.search3, _key='s3', _query=query, _size=_size))

	with ThreadPoolExecutor(2) as exe:
		for fn in fnx: exe.submit(fn)

	if 'album' in state._data['s2']['searchResult2']:
		for album in state._data['s2']['searchResult2']['album']:
			if album['id'] in state.seen: continue
			alDict[album['title']] = album['id']
			state.seen.add(album['id'])
	if 'song' in state._data['s2']['searchResult2']:
		for song in state._data['s2']['searchResult2']['song']:
			if song['parent'] in state.seen: continue
			title = []
			title.append(song['album'])
			title.append(u"%s - %s" % (song['artist'] if 'artist' in song else 'Unknown Artist', song['title']))
			title = ' / '.join(title)
			songDict[title] = song['parent']
			state.seen.add(song['parent'])
	if 'artist' in state._data['s2']['searchResult2']:
		for artist in state._data['s2']['searchResult2']['artist']:
			if not artist['id'] in arIDs: arIDs.add(artist['id'])

	# tag lookup
	if 'album' in state._data['s3']['searchResult3']:
		for album in state._data['s3']['searchResult3']['album']:
			if album['id'] in state.seen: continue
			title = []
			title.append(album['name'])
			if 'year' in album and album['year']: title.append(u"%s" % (album['year'],))
			if 'artist' in album and album['artist']: title.append(album['artist'])
			title = ' / '.join(title)
			alDict[title] = album['id']
			state.seen.add(album['id'])
	if 'song' in state._data['s3']['searchResult3']:
		for song in state._data['s3']['searchResult3']['song']:
			if song['parent'] in state.seen: continue
			title = []
			title.append(song['album'])
			if 'year' in song and song['year']: title.append(u"%s" % (song['year'],))
			title.append(u"%s - %s" % (song['artist'] if 'artist' in song else 'Unknown Artist', song['title']))
			title = ' / '.join(title)
			songDict[title] = song['parent']
			state.seen.add(song['parent'])
	if 'artist' in state._data['s3']['searchResult3']:
		for artist in state._data['s3']['searchResult3']['artist']:
			if not artist['id'] in arIDs: arIDs.add(artist['id'])

	state._data = {}

	if _all and (_len := len(arIDs)):
		tGetArtistP = partial(tGetArtist, _len=_len)
		with ThreadPoolExecutor(cfg.perf["searchThreads"]) as exe:
			for r in exe.map(tGetArtistP, arIDs):
				for album in r['artist']['album']:
					if album['id'] in state.seen: continue
					title = []
					# WIP (transliterate)
					if query.lower() in album['artist'].lower():
						title.append(album['artist'])
						if 'year' in album and album['year']: title.append(u"%s" % (album['year'],))
						title.append(album['name'])
						alDict[' / '.join(title)] = album['id']
					else:
						title.append(album['name'])
						if 'year' in album and album['year']: title.append(u"%s" % (album['year'],))
						title.append(album['artist'])
						songDict[' / '.join(title)] = album['id']
					state.seen.add(album['id'])

	for key in sorted(alDict.keys()):
		state.choices.append(Choice(alDict[key], name=key))
	if len(songDict):
		state.choices.append(Choice(0, name="%s" % ('~' * 50)))
	for key in sorted(songDict.keys()):
		state.choices.append(Choice(songDict[key], name=key))

	if numRes := len(state.choices):
		state.numRes = numRes if not len(songDict) else numRes-1
		state.call.append(lambda: listAlbums())
		clear()
	else: print("no result")

def getAlbumPathById(id):
	r = state.connector.conn.getAlbum(id)
	if 'songCount' in r['album'] and r['album']['songCount'] > 0:
		for song in r['album']['song']:
			p = song['path']
			path = None
			for k, v in cfg.pathmap.items():
				if p.startswith(k):
					path = u"%s%s" % (v, p)
					break
			if not path:
				path = u"%s%s" % (cfg.pathmap["\0"], p)
			return os.path.dirname(os.path.abspath(path))
	return None

def getAlbumDetailsById(id):
	global state
	if not id: return state.call.pop()
	r = state.connector.conn.getAlbum(id)
	if 'songCount' in r['album'] and r['album']['songCount'] > 0:
		prop = []
		alArtist = None
		if r['album']['artist']:
			alArtist = r['album']['artist']
			prop.append(u"%s: %s" % ("artist".ljust(10), r['album']['artist'],))
		if r['album']['name']: prop.append(u"%s: %s" % ("name".ljust(10), r['album']['name'],))
		if r['album']['title']: prop.append(u"%s: %s" % ("title".ljust(10), r['album']['title'],))
		if 'year' in r['album'] and r['album']['year']: prop.append(u"%s: %s" % ("year".ljust(10), r['album']['year'],))
		if 'genre' in r['album'] and r['album']['genre']: prop.append(u"%s: %s" % ("genre".ljust(10), r['album']['genre'],))
		if r['album']['songCount']: prop.append(u"%s: %s" % ("songCount".ljust(10), r['album']['songCount'],))
		if r['album']['duration']:
			prop.append(u"%s: %s (%im)" % ("duration".ljust(10), r['album']['duration'], ceil(r['album']['duration'] / 60)))
		if r['album']['created']: prop.append(u"%s: %s" % ("created".ljust(10), r['album']['created'],))
		if r['album']['artistId']: prop.append(u"%s: %s" % ("artistId".ljust(10), r['album']['artistId'],))
		if r['album']['album']: prop.append(u"%s: %s" % ("album".ljust(10), r['album']['album'],))
		if r['album']['id']: prop.append(u"%s: %s" % ("albumId".ljust(10), r['album']['id'],))
		if 'coverArt' in r['album'] and r['album']['coverArt']: prop.append(u"%s: %s" % ("coverArt".ljust(10), r['album']['coverArt'],))

		prop.append(u"%s:" % ("Tracks".ljust(10),))
		for song in r['album']['song']:
			if alArtist == song['artist']:
				prop.append(u"%s - %s" % (("%s" % (song['track'] if 'track' in song else 0,)).rjust(3), song['title']))
			else:
				prop.append(u"%s - %s - %s" % (("%s" % (song['track'] if 'track' in song else 0,)).rjust(3), song['artist'], song['title']))

		state.alProp = prop
		state.alId = id
		clear()
		show(prompt.getAlbumDetailsById)

		if state.sig == "\x06":
			state.call.append(lambda: getAlbumDetailsById(id))
			state.call.append(lambda: add([id]))
			if not args['mode']:
				return state.call.append(lambda: dlgMode())
			return clear()

		if state.sig == "\x08":
			state.call.append(lambda: listAlbums())
			clear()
	else:
		print("invalid album or songcount is zero")


''' --------------- store & pipe ---------------  '''

def add(alIds, silent=False):
	global state
	fnx, m3ufile = [], os.path.join(sd, u"./cache/%s.%s" % (int(time()), 'm3u8'))
	header = False
	with open(m3ufile, mode="a", encoding="utf8") as state.fh:
		for alId in alIds:
			if not alId: next
			if not "://" in alId:
				if args['mode'] == "stream":
					fn = tAddAlbumByIdStream
					if not header: header = state.fh.write("#EXTM3U\n")
				else:
					fn = tAddAlbumById
			else:
				fn = tAddStation
				if not header: header = state.fh.write("#EXTM3U\n")
			fnx.append(partial(fn, id=alId, silent=silent))
		# end FOR
		with ThreadPoolExecutor(cfg.perf["addThreads"]) as exe:
			for fn in fnx: exe.submit(fn)
	# end WITH_OPEN
	state.fh = None
	try:
		if os.stat(m3ufile).st_size < 12: raise ValueError
		if (args['foo'] and "remote" in args['foo']):
			remotePlaylist(m3ufile)
		else:
			p = Popen([cfg.foo, '/add', m3ufile])
	except:
		if not silent: print("unknown error adding playlist")

# threadpool dispatch
def tAddAlbumById(id, silent=False):
	paths, r = [], state.connector.conn.getAlbum(id)
	if 'album' in r:
		if ('songCount' in r['album'] and r['album']['songCount'] > 0):
			for song in r['album']['song']:
				p = song['path']
				path = None
				for k, v in cfg.pathmap.items():
					if p.startswith(k):
						path = u"%s%s" % (v, p)
						break
				if not path:
					path = u"%s%s" % (cfg.pathmap["\0"], p)
				paths.append(path)
			if len(paths):
				state.fh.write("\n".join(paths) + "\n")
				if not silent: print(u"adding playlist: %s" % (r['album']['name'],))
		else:
			if not silent: print("failed to add invalid album")

def tAddAlbumByIdStream(id, silent=False):
	urls, r = [], state.connector.conn.getAlbum(id)
	if 'album' in r:
		if ('songCount' in r['album'] and r['album']['songCount'] > 0):
			af = lambda x: (x if len(x) <= 30 else strip(x[:30])) + " ~ "
			if r['album']['name']: album = af(u"%s" % (r['album']['name'],))
			elif r['album']['title']: album = af(u"%s" % (r['album']['title'],))
			else: album = u""
			for song in r['album']['song']:
				url = state.connector.conn.stream(song['id'], maxBitRate=192)
				urls.append(u"#EXTINF:%s,%s%s - %s" % (
					song['duration'] if song['duration'] else "-1",
					album,
					song['artist'],
					song['title']
				))
				urls.append(url)
			if len(urls):
				state.fh.write("\n".join(urls) + "\n")
				if not silent: print(u"adding playlist: %s" % (r['album']['name'],))
		else:
			if not silent: print("failed to add invalid album")

def tAddStation(id, silent=False):
	urls, label = [], None
	for k, v in cfg.radio.items():
		if v == id:
			label = k
			break
	urls.append(u"#EXTINF:-1,%s - %s" % (label, id))
	urls.append(id)
	state.fh.write("\n".join(urls) + "\n")
	if not silent: print(u"adding station: %s" % (label,))


''' --------------- misc. tasks ---------------  '''

def scan():
	r = state.connector.conn.getScanStatus()
	if r['scanStatus']['scanning']:
		print('already scanning')
		return
	r = state.connector.conn.startScan()
	print(r)

# tbd: streamline & remove duplicated session code (as well see listSessions())
def getSessions():
	global state
	state.type = 'session'
	state.sessions = []

	alIds = state.selectedChoice

	state.call.append(lambda: listAlbums())
	show(prompt.modeSession)
	if state.sig == "\x08":
		return clear()
	selected = True if state.selectedChoice == 'selected' else False
	args['sessmode'] = state.selectedChoice

	for fname in sorted(glob(sd + './cache/sess.*'), key=os.path.getmtime, reverse=True):
		with open(fname, mode="rb") as f: sess = pickle.load(f)
		state.sessions.append(Choice(fname,
			name=u"%s%s" % (sess['name'].ljust(70), "%s" % strftime('%Y-%m-%d %H:%M:%S', localtime(int((fname.split('.'))[-2]))))
		))
	if not len(state.sessions):
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
	global state
	with open(state.sess, mode="rb") as f: sess = pickle.load(f)
	alDict = {}
	songDict = {}

	sep = False
	for choice in sess['choices']:
		if sep:
			if choice.value not in state.selectedChoice:
				songDict[choice.name] = choice.value
			continue
		try:
			if not choice.value: raise ValueError
			if choice.value not in state.selectedChoice:
				alDict[choice.name] = choice.value
		except:
			sep = True

	if not len(alDict) and not len(songDict):
		state.sessions = []
		os.remove(state.sess)
		return False

	state.choices = []
	for key in sorted(alDict.keys()):
		state.choices.append(Choice(alDict[key], name=key))
	if len(songDict):
		state.choices.append(Choice(None, name="%s" % ('~' * 50)))
	for key in sorted(songDict.keys()):
		state.choices.append(Choice(songDict[key], name=key))

	with open(state.sess, mode="wb") as f:
		pickle.dump({
			'name': sess['name'],
			'choices': state.choices
		}, f)
	return True

def expandSession(selected=False, alIds=[]):
	with open(state.selectedChoice, mode="rb") as f: sess = pickle.load(f)
	alDict = {}
	songDict = {}

	sep = False
	for choice in sess['choices']:
		if sep:
			songDict[choice.name] = choice.value
			continue
		try:
			if not choice.value: raise ValueError
			alDict[choice.name] = choice.value
		except:
			sep = True

	with open(state.selectedChoice, mode="wb") as f:
		pickle.dump({
			'name': sess['name'],
			'choices': getSessionChoices(alDict, songDict, selected, alIds)
		}, f)

def getSessionChoices(alDict={}, songDict={}, selected=False, alIds=[]):
	sep = False
	i = -1
	for choice in state.choices:
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
		choices.append(Choice(None, name="%s" % ('~' * 50)))
	for key in sorted(songDict.keys()):
		choices.append(Choice(songDict[key], name=key))
	return choices

def makeSession(selected=False, alIds=[]):
	global state
	fname = os.path.join(sd, "./cache/sess.%i.obj" % (int(time()),))
	state.sessions.insert(0, Choice(fname,
		name=u"%s%s" % (state.selectedChoice.ljust(70), "%s" % strftime('%Y-%m-%d %H:%M:%S', localtime(int((fname.split('.'))[-2]))))
	))
	with open(fname, mode="wb") as f:
		pickle.dump({
			'name': state.selectedChoice,
			'choices': state.choices if not selected else getSessionChoices({}, {}, selected, alIds)
		}, f)

def getStations():
	global state
	state.choices = []
	for k, v in cfg.radio.items():
		state.choices.append(Choice(v, name=k))
	state.type = 'radio'
	state.numRes = len(cfg.radio)
	state.call.append(lambda: listStations())
	clear()

def updateGenres():
	r = state.connector.conn.getGenres()
	if 'genre' in r['genres']:
		_r = [] # fix here to speed up lookup later
		for itm in r['genres']['genre']:
			if not 'albumCount' in itm: itm['albumCount'] = 0
			_r.append(itm)
		with open(os.path.join(sd, './cache/genres.obj'), mode="wb") as f:
			pickle.dump(sorted(_r, key=lambda d: d['albumCount'], reverse=True), f)


''' --------------- processing ---------------
prompt_toolkit is leaking memory, so we create a new process for each prompt
- pool used to minimize latency
	1) event loop using threading. see dispatch()->procMan()
	2) child process pool (size=2), waiting for tasks
	3) on job task child_1, and add a child process to the pool
- show() reused for tk GUIs, remotes, web apps '''

def wndPopper():
	global wndQs
	while True: 
		try: _q = wndQs.pop()
		except IndexError: break
		else:
			try: _q.put('')
			except: pass

def queueCloser(qin, qout):
	qin.close()
	qin.join_thread()
	qout.close()
	qout.join_thread()

def show(fn):
	global state, pool, evTerm, wndQs, webProc

	while True: # wait for procMan
		try: p, qin, qout, evParent, evChild = pool.popleft()
		except IndexError: sleep(0.1)
		else: break

	sharedState = copy(state)
	sharedState.connector = None
	if fn in [prompt.action, prompt.mode, prompt.backToList, prompt.nameSession, prompt.listSessions, prompt.modeSession, prompt.confRmSession, window.coverArt, window.manual, remote.playlist]:
		sharedState.choices = None
		sharedState.alProp = None
		sharedState.mode = args['mode']
		sharedState.action = args['action'] if 'action' in args else None
		sharedState.sessmode = args['sessmode'] if 'sessmode' in args else None
	if fn in [window.coverArt, window.manual]:
		wndQs.append(qout)
	elif fn in [wsgi.webapp]:
		webProc = (p, qin, qout, evParent, evChild)
	if fn in [remote.playlist, wsgi.webapp]:
		sharedState.server = cfg.server
	sharedState.seen = None
	sharedState.call = None

	qout.put(fn)
	qout.put(sharedState)
	evChild.set()

	while True:
		evParent.wait()
		r = qin.get()

		# on state object (i.e. prompt returning)
		if isinstance(r, State):
			wndPopper()
			break

		# instructions not requiring a new prompt
		if r == "\x00":
			return queueCloser(qin, qout)
		elif r == "\x01":
			opendir(getAlbumPathById(state.alId))
		elif r.startswith("\x01\0"):
			alId = (r.split("\0"))[1]
			opendir(getAlbumPathById(alId))
		elif r == "\x07":
			if len(wndQs): wndPopper()
			else: wndCoverArt()
		elif r.startswith("\x07\0"):
			alId = (r.split("\0"))[1]
			if len(wndQs) and alId == state.alId:
				wndPopper()
			else:
				state.alId = alId
				wndCoverArt()
		elif r == "\x10":
			import webbrowser
			webbrowser.open("http://%s:%s" % (cfg.server['wsgi']['ip'], cfg.server['wsgi']['port']), new=2, autoraise=True)
		elif r.startswith("\x20\0"):
			(_, args['foo'], args['mode'], alIdsStr) = r.split("\0")
			add(alIdsStr.split(","), silent=True)
			# resolve a request promise; typically takes couple more seconds to complete the playlist transfer
			# a more sophisticated approach will yield bool result
			qout.put('')
		elif r == "\x42":
			wndManual()

	state.selectedChoice = r.selectedChoice
	state.selectedChoiceIndex = r.selectedChoiceIndex
	state.fuzzyText = r.fuzzyText
	state.sig = r.sig

	queueCloser(qin, qout)
	if state.sig == KeyboardInterrupt:
		evTerm.set()
		raise KeyboardInterrupt

def procMan():
	global pool, procs, evTerm
	tty = True if os.name == 'posix' else False
	while not evTerm.is_set():
		if not len(pool):
			evChild, evParent = mpEvent(), mpEvent()
			qin, qout = mpQueue(), mpQueue()
			p = Process(target=prompt.proc, args=(qin, qout, evParent, evChild, evTerm, tty))
			pool.append([p, qin, qout, evParent, evChild])
			procs.append(p)
			p.start()
		sleep(0.1)
	for p in procs:
		p.terminate()
		p.join()
	(p, _, _, _, _) = webProc
	if p:
		p.terminate()
		p.join()

def dispatch(exit=True, mp=True):
	global state, evTerm
	evTerm = mpEvent()
	if mp:
		t = Thread(target=procMan)
		t.start()
	while True:
		try:
			_call = state.call.pop()
			if not _call: raise IndexError
		except IndexError: break
		_call()
	evTerm.set()
	if exit: sys.exit(0)


def main():
	global args, state
	clean()

	parser = ArgumentParser(description='foosonic client')
	parser.add_argument('-v', '--version', action='version', version='0.1.5')
	parser.add_argument('-a', '--add', help='add to foobar, such as <album-id>', required=False)
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
	parser.add_argument('-gg', '--genres', help='list genres', action='store_true', required=False)
	parser.add_argument('-ss', '--sessions', help='list sessions', action='store_true', required=False)
	parser.add_argument('-rand', '--random', help='list random albums', action='store_true', required=False)
	parser.add_argument('--scan', help='initiate rescan of the media libraries', action='store_true', required=False)
	args = vars(parser.parse_args())
	# end argparse

	state = State()
	state.connector = connection.LibSoniConn()

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
		state.call.append(lambda: getStations())
		dispatch()

	if args['updategenres']:
		print("updating genres..")
		state.call.append(lambda: updateGenres())
		dispatch(exit=False, mp=False)
		print("done")
		sys.exit(0)

	if args['scan']:
		state.call.append(lambda: scan())
		dispatch(mp=False)

	if args['year']:
		state.call.append(lambda: getAlbumsByYear(args['year'], state._size))
		dispatch()

	if args['genre']:
		state.call.append(lambda: getAlbumsByGenre(args['genre'], state._size))
		dispatch()

	if args['genres']:
		state.call.append(lambda: listGenres())
		dispatch()

	if args['sessions']:
		state.call.append(lambda: listSessions())
		dispatch()

	if args['search']:
		state.call.append(lambda: getSearch(args['search'], state._size, _all=searchall))
		dispatch()

	if args['add']:
		state.call.append(lambda: waitProcs())
		state.call.append(lambda: add([args['add']]))
		dispatch()

	if args['details']:
		if not "://" in args['details']:
			state.call.append(lambda: getAlbumDetailsById(args['details']))
			dispatch()

	if args['random']:
		state.call.append(lambda: getAlbums('random', state.size))
		dispatch()

	# default mode
	state.call.append(lambda: getAlbums('newest', state.size))
	dispatch()

# end main()

if __name__ == "__main__":
	import sys, os, pickle
	from multiprocessing import (Event as mpEvent, Queue as mpQueue, Process)
	from threading import Thread
	from concurrent.futures import ThreadPoolExecutor
	from functools import partial
	from glob import glob
	from subprocess import call, Popen
	from argparse import ArgumentParser
	from copy import copy
	from collections import deque
	from time import time, strftime, localtime, sleep
	from math import ceil
	from InquirerPy.base.control import Choice
	from foosonic import prompt, window, remote, wsgi, connection
	from _config import cfg

	sd, args, state = os.path.dirname(os.path.realpath(__file__)), None, None
	pool, procs, wndQs, evTerm, webProc = deque(maxlen=2), deque(maxlen=20), deque(), None, (None, None, None, None, None)

	try:
		main()
	except KeyboardInterrupt:
		pass
	sys.exit(0)

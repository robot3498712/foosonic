/**
 * foosonic webapp
 */

var onpage = 0,
	lastpage,
	lazyloadImages,
	lazyloadThrottleTimeout,
	albumIds = []
;

var lightbox = {
	src: null,
	init: function(image, size, src) {
		lightbox.src = (typeof src !== 'undefined') ? src : image.src.replace('/250/', '/');
		if (image.naturalWidth === undefined) {
			var tmp = document.createElement('img');
			tmp.style.visibility = 'hidden';
			tmp.src = lightbox.src;
			image.naturalWidth = tmp.width;
			image.naturalHeight = tmp.height;
			delete tmp;
		}
		if (image.naturalWidth > size || image.naturalHeight > size) {
			$('#lightbox').show().click(lightbox.unbox).html(
				'<p size="7" style="color: gray; font-size: 50px; padding-top: 25px;">Loading...</p>'
			);
			$('#curtain').show().click(lightbox.unbox);
			image = new Image();
			image.src = lightbox.src.replace('/250/', '/');
			image.onload = function () {
				lightbox.box_async(image);
			};
			image.onerror = lightbox.unbox;
		}
	},
	box: function(image) {
		var parentIsA = (image.parentNode != null && image.parentNode.tagName.toUpperCase() == 'A') ? true : false;
		if (!parentIsA) {
			$('#lightbox').show().click(lightbox.unbox).html('<img src="' + lightbox.src + '" alt="" />');
			$('#curtain').show().click(lightbox.unbox);
		}
	},
	box_async: function(image) {
		var parentIsA = (image.parentNode != null && image.parentNode.tagName.toUpperCase() == 'A') ? true : false;
		if (!parentIsA) {
			$('#lightbox').html('<img src="' + lightbox.src + '" alt="" />');
		}
	},
	unbox: function(data) {
		$('#curtain').hide();
		$('#lightbox').hide().html('');
	}
};

function onNavigate(act) {
	switch(true) {
		case act == 'f':
			if (onpage == 0) return;
			$(`div#page-${onpage}`).hide();
			onpage = 0;
			break;
		case act == 'p':
			if (onpage == 0) return;
			$(`div#page-${onpage}`).hide();
			onpage--;
			break;
		case act == 'n':
			if (++onpage > lastpage) {
				onpage = lastpage;
				return;
			}
			$(`div#page-${onpage-1}`).hide();
			break;
		case act == 'l':
			if (onpage == lastpage) return;
			$(`div#page-${onpage}`).hide();
			onpage = lastpage;
			break;
		default: // selected
			$(`div#page-${onpage}`).hide();
			onpage = parseInt(act);
	}
	$('#ctrl-select').val(onpage);
	$('div.ctrl span.label').html(`page&nbsp;${onpage+1}&nbsp;of&nbsp;${lastpage+1}`);
	window.scrollTo(0, 0);
	$(`div#page-${onpage}`).show();
	listen();
	lazyload();
}

function listen() {
	document.addEventListener("scroll", lazyload);
	window.addEventListener("resize", lazyload);
	window.addEventListener("orientationChange", lazyload);
}

function lazyload() {
	lazyloadImages = document.querySelectorAll(`div#page-${onpage} img.lazy`);

	if (lazyloadThrottleTimeout) {
		clearTimeout(lazyloadThrottleTimeout);
	}
	lazyloadThrottleTimeout = setTimeout(function() {
		let scrollTop = window.pageYOffset;
		lazyloadImages.forEach(function(img) {
			if (img.offsetTop < (window.innerHeight + scrollTop)) {
				let preloadImage = new Image();
				preloadImage.src = img.dataset.src;
				preloadImage.onload = function() {
					img.src = preloadImage.src;
					img.classList.remove('lazy');
					$(img).click(function() {
						lightbox.init(this, 100); // px guess
					});
				};
			}
		});
		if (lazyloadImages.length == 0) {
			document.removeEventListener("scroll", lazyload);
			window.removeEventListener("resize", lazyload);
			window.removeEventListener("orientationChange", lazyload);
		}
	}, 20);
}

function onCloseFoo() {
	$('.highlight').each(function() {
		$(this).removeClass('highlight');
	})
	$('.foo-container').hide();
	if (!lastpage) $('.ctrl-container').hide();
	$('#foo-open').show();
	albumIds = [];
}

function showWait(hide=false) {
	if (hide) {
		$('#curtain').hide();
		$('#lightbox').hide();
		return;
	}
	$('#lightbox').show().html('<p size="7" style="color: gray; font-size: 50px; padding-top: 25px;">Loading...</p>');
	$('#curtain').show();
}

function onClickAlbum(ev) {
	let albumId = $(ev.target).closest('a').attr('data-src'),
		div = $(ev.target).closest('div'),
		selected = $(div).hasClass('highlight') ? true : false
	;
	if (selected) { // remove
		if (albumIds.includes(albumId)) {
			albumIds = albumIds.filter(item => item !== albumId);
		}
		$(div).removeClass('highlight');
	} else { // add
		if (!albumIds.includes(albumId)) {
			albumIds.push(albumId);
		}
		$(div).addClass('highlight');
	}
	if (albumIds.length) {
		if (!lastpage) $('.ctrl-container').show();
		$('.foo-container').show();
	} else {
		onCloseFoo();
	}
	if (albumIds.length >= 2) {
		$('#foo-open').hide();
	} else {
		$('#foo-open').show();
	}
}

document.addEventListener("DOMContentLoaded", function(event) {
	if (localStorage.theme == "dark") {
		document.body.classList.add("dark");
	} else {
		document.body.classList.remove("dark");
	}

	const data = JSON.parse((document.getElementById("data")).value);
	let container = document.getElementById("container"),
		perRow = parseInt(window.innerWidth / 200),
		perPage = perRow * 12,
		overshoot = Object.keys(data).length % perRow,
		i = -1,
		j = -1,
		pagedata = []
	;

	for (d in data) {
		if (++i % perPage == 0) {
			pagedata[++j] = [];
		}
		pagedata[j][d] = data[d];
	}
	delete data;

	if (j) {
		lastpage = j;
		$('.ctrlf').click(function() { onNavigate('f'); });
		$('.ctrlp').click(function() { onNavigate('p'); });
		$('.ctrln').click(function() { onNavigate('n'); });
		$('.ctrll').click(function() { onNavigate('l'); });
		$('div.ctrl span.label').html(`page&nbsp;${onpage+1}&nbsp;of&nbsp;${lastpage+1}`);
		$('div.spacer').show();
		$('div.ctrl-container').show();
		$('.foo-container').hide();
	} else {
		$('.ctrl').html('');
	}

	$('#dark-mode').click(function() {
		let result = document.body.classList.toggle("dark");
		localStorage.theme = result ? "dark" : "light";
	});

	$('#foo-open').click(function() {
		$.get(`open/${albumIds[0]}`);
	});

	$('#foo-close').click(onCloseFoo);

	$('.foo-ctrl').click(function(ev) {
		let client = $(ev.target).attr('data-client'),
			mode = $(ev.target).attr('data-mode')
		;
		(async function() {
			showWait();
			const controller = new AbortController();
			const _ = setTimeout(() => controller.abort(), 5000);
			let fd = new FormData();
			fd.append('ids', albumIds.join(','));
			await fetch(`add/${client}/${mode}`, {
					method: 'POST', body: fd, signal: controller.signal
				}).catch(error => { alert("request error or timeout"); })
			;
			onCloseFoo();
			showWait(true);
		})();
	});

	let sel = $('#ctrl-select');
	$(sel).change(function(ev) {
		onNavigate(this.value);
	});

	// point of this is establishing the scaffold in firefox
	let preloadLazyImage = new Image();
	preloadLazyImage.src = "/static/lazyload.png";
	preloadLazyImage.onload = function() {
		i = -1;
		for (let page=0; page<=j; page++) {
			let opt = document.createElement("option");
			opt.value = page;
			opt.innerHTML = Object.values(pagedata[page])[0].split(' ', 3).join(' ');
			sel.append(opt);

			let cp = document.createElement("div");
			cp.id = `page-${page}`;
			if (page) cp.setAttribute("class", "hidden");
			container.appendChild(cp);

			let row;
			for (d in pagedata[page]) {
				if (++i % perRow == 0) {
					row = document.createElement("div");
					row.setAttribute("class", "grid-container");
					cp.appendChild(row);
				}
				let col = document.createElement("div");
				col.setAttribute("class", "grid-element");
				row.appendChild(col);

				let img = document.createElement("img");
				img.setAttribute("class", "lazy");
				img.setAttribute("src", preloadLazyImage.src);
				img.setAttribute("data-src", `/coverart/250/${d}`);
				col.appendChild(img);

				let a = document.createElement("a");
				a.setAttribute("href", "javascript:void(0)");
				a.setAttribute("data-src", d);
				$(a).click(function(ev) {
					onClickAlbum(ev);
				});
				col.appendChild(a);

				let p = document.createElement("p");
				let span = document.createElement("span");
				$(span).html(pagedata[page][d]);
				p.appendChild(span);
				a.appendChild(p);
			}
			if (page==j && overshoot) { // style fix
				let fill = perRow - overshoot;
				for (let i=0; i<fill; i++) {
					let col = document.createElement("div");
					col.setAttribute("class", "grid-element");
					row.appendChild(col);
				}
			}
		}

		listen();
		lazyload();
	};
});
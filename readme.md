# foosonic

## [0.2.7] (2024-06-07)


### Dependencies & preconditions

* Subsonic server
    * [gonic](https://github.com/sentriz/gonic) is very much recommended
    * ampache_subsonic: works in general, although some changes may be needed; not recommended for being too slow

* [Foobar2000](https://www.foobar2000.org/)

* Python >= 3.10 | see requirements.txt
    * py3.12 supported
    * developed on and for Windows, although should work fine on other OS with a few tweaks


### Motivation & core features

While modern desktop apps such as Sonixd look nice and work well enough, there are couple **issues**:
* Search is convoluted and laborious at best, partially malfunctional and incomplete.
* Playback via html5, and cannot be delegated easily to a native player like foobar.
* Electron and dubious framework decisions result in poor performance.

**foosonic** on the contrary provides
* Interactive cli based on prompts listing choices, i.e. albums.
* Search and lookup options including year and genre.
* Add to foobar, or remote foobar via foo_httpcontrol extension.
* Stream albums, or add playlists based on filesystem paths.
* Session management (playlists, in other words).
* Web app with a subset of features, displaying cover art.

[wiki](https://github.com/robot3498712/foosonic/wiki/foosonic-wiki) with sample images.

Edit _config.py to get started. alt-h to display manual.


### Technical notes

* Focus on multiprocessing and speed / responsiveness. Memory footprint thus is rather high, but there won't be major problems with memory leaks.
* Some exceptions may result in hanging processes (should be less of an issue as of version 0.2.6). In such case, kill the process via task manager, and fix the issue.
* prompt_toolkit/InquirerPy isn't perfect. As for console host on windows, default cmd (https://math.berkeley.edu/~serganov/ilyaz.org/software/fonts/) / Windows Terminal (Consolas) work best, while conemu performed very poorly in my tests. You may try turning off fuzzy prompts and simplifying in general.
* [Special keys](https://python-prompt-toolkit.readthedocs.io/en/master/pages/advanced_topics/key_bindings.html#list-of-special-keys)


### Future plans, pending features & issues

* Feature: Augment webapp
    * search / filter
    * style tweaks

* Feature: Search refinements
	* such as combinations, for example: query AND year_range AND genre

* Feature: Dynamic sessions
    * Store originating queries and implement automatic updates.

* Feature: History (a-left)
    * Similar to history in webbrowser; possibly requires caching implementation.

* Bugs / Known issues
    * Minimal exception handling (py-sonic errors not dealt with yet)


### Acknowledgements

* A modified version of [py-sonic](https://github.com/crustymonkey/py-sonic) is included.
* [InquirerPy](https://github.com/kazhala/InquirerPy)


### License

foosonic is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
foosonic is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with foosonic. If not, see <http://www.gnu.org/licenses/>

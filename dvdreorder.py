import re
from os import listdir, rename
from os.path import expanduser, join
from sys import argv

import fetch

from urlgrab import Cache

cdir = join(expanduser("~"), ".cache/renamer")
cache = Cache(debug=False, cache=cdir)

(_, path, series, season) = argv[:4]
season = int(season)


def epguides(name):
    inf = {"cache": cache, "core": (lambda i, eps: eps)}
    eps = {}
    for ep in fetch.tvdb().run(inf, name):
        extra = ep["extra"]
        if extra is None:
            continue
        dvdnum = extra.get("dvdEpisodeNumber")
        eps[(ep["season"], dvdnum)] = ep["epnum"]
    return eps


eppattern = re.compile(r"(\d+)x(\d+)")
eps = epguides(series)

for fname in listdir(path):
    naming = eppattern.search(fname)
    if naming is None:
        print(f"Can't find in '{fname}'")
        continue
    original = naming.group()
    season, episode = [int(x) for x in naming.groups()]
    key = (season, episode)
    if key not in eps:
        print(f"No {key} in episodes")
        continue
    dvdnum = eps[key]
    newname = fname.replace(original, f"{season}x{dvdnum:02d}")
    print(fname, newname)
    if len(argv) > 4 and argv[4] == "-r":
        rename(fname, newname)

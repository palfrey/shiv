import re
from os import listdir
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
        epnum = ep["epnum"]
        extra = ep["extra"]
        if extra is not None:
            dvdnum = extra.get("dvdEpisodeNumber")
        else:
            dvdnum = None
        eps[(ep["season"], epnum)] = dvdnum
    return eps


eppattern = re.compile(r"(\d+)x(\d+)")
eps = epguides(series)

for fname in listdir(path):
    naming = eppattern.search(fname)
    if naming is None:
        print(f"Can't find in '{fname}'")
        continue
    original = naming.span()
    key = (season, episode) = [int(x) for x in naming.groups()]
    if key not in eps:
        print(f"No {key} in episodes")
        continue
    dvdnum = eps[key]
    newname = fname.replace(original, f"{season}x{dvdnum:02d}")
    print(fname, newname)

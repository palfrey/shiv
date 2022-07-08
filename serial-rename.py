from sys import argv
from os import listdir, rename
from os.path import splitext, join, expanduser, getmtime
from urlgrab import Cache
import fetch
import re

cdir = join(expanduser("~"),".cache/renamer")
cache = Cache(debug=False,cache=cdir)

(_, path, prefix, series, season) = argv[:5]
season = int(season)

def epguides(name):
    inf = {"cache":cache,"core":(lambda i,eps:eps)}
    eps = {}
    for (season, epnum, date,title) in fetch.tvdb().run(inf,name):
        eps[(int(season),int(epnum))] = title
    return eps

eps = epguides(series)

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    main, ext = splitext(text)
    nums = [x for x in re.split('(\d+)', main) if x != '']
    ret = nums[:-1] + [atoi(nums[-1])]
    #print text, nums, ret
    return ret

def date_key(text):
    fullpath = join(path, text)
    return getmtime(fullpath)

key = natural_keys
key = date_key

extra = 1
for i,x in enumerate(sorted([x for x in listdir(path) if x.find(".mp4")!=-1], key=key)):
    ep = i + 1
    origpath = join(path, x)
    ext = splitext(x)[1]
    pair = (season, ep)
    #pair = "foo"
    if pair in eps:
        name = eps[(season, ep)].strip()
        to = "%s %dx%02d - %s%s"%(prefix, season, ep, name, ext)
    else:
        to = "%s Season %d Extra %02d%s"%(prefix, season, extra, ext)
        extra +=1
    fullpath = join(path, to)
    if origpath != fullpath:
        print(origpath, fullpath)
        if len(argv)>5 and argv[5] == "-r":
            rename(origpath, fullpath)



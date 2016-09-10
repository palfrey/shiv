from os.path import exists
import subprocess
from xml.dom.minidom import parseString
from sys import argv
from json import dumps, loads
from os import listdir

def read_lsdvd(root, fname):
	cmd = ["lsdvd", "-Ox", "-x", root]
	print cmd
	print fname
	data = subprocess.check_output(cmd)
	if len(data) == 0:
		raise Exception
	data = unicode(data, errors="ignore")
	data = data.replace("&", "&amp;")
	open(fname, "wb").write(data)
	return data

def parse_lsdvd(data):
	xml = parseString(data)

	tracks = {}

	for track in xml.getElementsByTagName("track"):
		id = None
		#print [x.nodeName for x in track.childNodes]
		for child in track.childNodes:
			if child.nodeName == u"ix":
				assert id == None,id
				id = int(child.firstChild.data)
			elif child.nodeName == u"length":
				assert id != None
				length = float(child.firstChild.data)
				tracks[id] = {"length": length/60.0}
			elif child.nodeName == "subp":
				assert tracks.has_key(id)
				element = child.getElementsByTagName("langcode")[0]
				if element.firstChild != None:
					if "subp" not in tracks[id]:
						tracks[id]["subp"] = {}
					if element.firstChild.data == "xx":
						#open(fname, "wb").write("")
						continue
						raise Exception, (id, tracks[id], child.toxml())
					tracks[id]["subp"][element.firstChild.data] = child.getElementsByTagName("ix")[0].firstChild.data
			elif child.nodeName == "audio":
				assert tracks.has_key(id)
				if "audio" not in tracks[id]:
					tracks[id]["audio"] = {}
				element = langcode = child.getElementsByTagName("langcode")[0]
				#print element.toxml()
				if element.firstChild != None:
					langcode = element.firstChild.data
					if langcode not in tracks[id]["audio"]:
						audioId = child.getElementsByTagName("ix")[0].firstChild.data
						tracks[id]["audio"][langcode] = audioId
			elif child.nodeName == "chapter":
				if "chapters" not in tracks[id]:
					tracks[id]["chapters"] = {}
				ix = int(child.getElementsByTagName("ix")[0].firstChild.data)
				length = child.getElementsByTagName("length")[0].firstChild.data
				tracks[id]["chapters"][ix] = float(length) / 60.0

			else:
				#print "node", child.nodeName
				pass

	return tracks, sorted(tracks.keys())

def decide_files(fname):
	tracks,order = parse_lsdvd(open(fname).read())

	#print tracks
	if tracks == {}:
		raise Exception, "empty tracks"

	episodeValues = dict((k,v) for (k,v) in tracks.iteritems() if v["length"] > 30 and v["length"] < 84)
	episodes = len(episodeValues)
	movieValues = dict((k,v) for (k,v) in tracks.iteritems() if v["length"] > 65 and k < 200)
	movies = len(movieValues)
	base = fname
	print "e,m", episodes, movies, [(k,v["length"]) for (k,v) in tracks.iteritems()]

	if episodes == 4 and movies == 2: # stargate hack
	    for k in order:
		    if k not in [5,6,7]:
			    continue
		    fname = "%s-%d.mkv"%(base, k)
		    yield (k, fname, tracks[k])

	elif episodes > movies:
		print "TV series", episodeValues
		episodeValues = episodeValues.keys()

		for k in order:
			if k not in episodeValues:
				continue
			fname = "%s-%d.mkv"%(base, k)
			yield (k, fname, tracks[k])
	elif movies == 1:
		print "Movie", movieValues
		fname = "%s.mkv"%base
		k = movieValues.keys()[0]
		yield (k, fname, tracks[k])
	else:
		print "Something else!", movies, episodes
		for k in sorted(movieValues):
			#print k, tracks[k]
			fname = "%s-%d.mkv"%(base, k)
			yield (k, fname, tracks[k])

def get_idname(root):
	data = subprocess.check_output(["./dvdid", root])
	return data.replace("|", "_").strip()

def read_disk(root):
	idname = get_idname(root)
	read_idname(idname)

def read_idname(idname):
	fname = "tracks/" + idname

	if not exists(fname):
		data = read_lsdvd(root, fname)
	else:
		data = open(fname).read()

	tracks = decide_files(fname)
	tracks = list(tracks)
	print tracks
	open(fname + ".tracks", "w").write(dumps(list([x[:2] for x in tracks])))

def check_disks():
	ret = True
	for fname in listdir("tracks"):
		if fname.startswith("."):
			continue
		if fname.endswith(".tracks"):
			wanted_tracks = loads(open("tracks/" + fname).read())
			gotten_tracks = [list(x[:2]) for x in decide_files("tracks/" + fname.replace(".tracks", ""))]
			if wanted_tracks == gotten_tracks:
				print fname, "is ok", wanted_tracks
			else:
				print fname, "is bad: "
				print wanted_tracks
				print gotten_tracks
				ret = False
				raise Exception
		elif not exists("tracks/%s.tracks" % fname):
			print "Making %s.tracks" % fname
			read_idname(fname)
	return ret

if __name__ == "__main__":
	if len(argv)>1:
		read_disk(argv[1])
	else:
		ret = check_disks()
		if not ret:
		    exit(-1)

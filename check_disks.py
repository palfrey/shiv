from os.path import exists
import subprocess
from xml.dom.minidom import parseString
from sys import argv
from json import dumps, loads
from os import listdir
import json

def read_lsdvd(root, fname):
	print "lsdvd data:", fname
	if exists(fname):
		data = open(fname).read()
	else:
		cmd = ["lsdvd", "-Ox", "-x", root]
		print cmd
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
				tracks[id] = {"length": length/60.0, "id": id}
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

	if tracks == {}:
		raise Exception, "empty tracks"

	base = fname

	if exists(fname + ".trackmap"):
		trackmap = json.loads(open(fname + ".trackmap").read())
		print trackmap
		for k, entry in enumerate(trackmap):
			fname = "%s-%d-t%d-s%d-e%d.mkv"%(base, k, entry["track"], entry["startChapter"], entry["endChapter"])
			yield {"number":k, "fname":fname, "track": tracks[entry["track"]], "startChapter":entry["startChapter"], "endChapter":entry["endChapter"]}
		return

	if len(tracks) == 99:
		print "Protected with RipGuard, need a .trackmap"
		raise Exception

	episodeValues = dict((k,v) for (k,v) in tracks.iteritems() if v["length"] > 30 and v["length"] < 84)
	episodes = len(episodeValues)
	movieValues = dict((k,v) for (k,v) in tracks.iteritems() if v["length"] > 65 and v["length"] < 180)
	movies = len(movieValues)
	print "e,m", episodes, movies, [(k,v["length"]) for (k,v) in tracks.iteritems()]

	if episodes > 20: # too many!
		print "Too many!", movies, episodes
		print tracks
		raise Exception

	if episodes > movies:
		print "TV series", episodeValues
		episodeValues = episodeValues.keys()

		for k in order:
			if k not in episodeValues:
				continue
			fname = "%s-%d.mkv"%(base, k)
			yield {"number":k, "fname":fname, "track":tracks[k]}

	elif movies == 1:
		print "Movie", movieValues
		fname = "%s.mkv"%base
		k = movieValues.keys()[0]
		yield {"number":k, "fname":fname, "track":tracks[k]}

	else:
		print "Something else!", movies, episodes
		print tracks
		raise Exception

def get_idname(root):
	data = subprocess.check_output(["./dvdid", root])
	return data.replace("|", "_").strip()

def read_disk(root):
	idname = get_idname(root)
	read_idname(idname)

def strip_entry(m):
	m["track"] = m["track"]["id"]
	del m["fname"]
	del m["number"]
	return m

def read_idname(idname):
	fname = "tracks/" + idname

	if not exists(fname):
		data = read_lsdvd(root, fname)
	else:
		data = open(fname).read()

	tracks = decide_files(fname)
	tracks = list(tracks)
	print tracks
	open(fname + ".tracks", "w").write(dumps(list([strip_entry(x) for x in tracks])))

def check_disks():
	ret = True
	for fname in listdir("tracks"):
		if fname.startswith("."):
			continue
		if fname.endswith(".trackmap"):
			continue
		if fname.endswith(".tracks"):
			wanted_tracks = loads(open("tracks/" + fname).read())
			gotten_tracks = [strip_entry(x) for x in decide_files("tracks/" + fname.replace(".tracks", ""))]
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

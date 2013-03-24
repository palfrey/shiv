from os import walk, system, popen
from os.path import exists, isdir, basename
from xml.dom.minidom import parseString
from stats import *
from subprocess import Popen, PIPE
from optparse import OptionParser

parser = OptionParser()
parser.add_option("--chapter", dest="byChapter", default=False, action="store_true")
(opts, folders) = parser.parse_args()

def reencode(root):
	cmd = "lsdvd -Ox -x '%s'"%root
	p = Popen(cmd, shell=True, stdout = PIPE)
	data = p.stdout.read()
	if len(data) == 0:
		return
	data = unicode(data, errors="ignore")
	data = data.replace("&", "&amp;")
	open("dump", "wb").write(data)
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

	print root
	#print tracks
	if tracks == {}:
		return

	if opts.byChapter:
		for k in sorted(tracks.keys()):
			for c in sorted(tracks[k]["chapters"].keys()):
				fname = "%s-%d-%d.mp4"%(root, k, c)
				if tracks[k]["chapters"][c] > 15:
					encode(root, k, fname, tracks[k], c)

	else:
		episodeValues = dict((k,v) for (k,v) in tracks.iteritems() if v["length"] > 15 and v["length"] < 65)
		episodes = len(episodeValues)
		movieValues = dict((k,v) for (k,v) in tracks.iteritems() if v["length"] > 65)
		movies = len(movieValues)
		if episodes > movies:
			print "TV series", episodeValues
			length = -1
			base = root
			if isdir(root):
				base = basename(root)
				cmd = "./dvdid '%s'"%root
				print cmd
				p = Popen(cmd, shell=True, stdout = PIPE)
				data = p.stdout.read()
				base += "-" + data.replace("|", "_")

			for k in sorted(episodeValues):
				fname = "%s-%d.mp4"%(base, k)
				if length != tracks[k]["length"]:
					encode(root, k, fname, tracks[k])
					length = tracks[k]["length"]
		elif movies == 1: 
			print "Movie", movieValues
			if isdir(root):
				base = basename(root)
			else:
				base = root
			fname = "%s.mp4"%base
			k = movieValues.keys()[0]
			encode(root, k, fname, tracks[k])
		else:
			print "Something else!"
			for k in sorted(movieValues):
				fname = "%s-%d.mp4"%(root, k)
				encode(root, k, fname, tracks[k])

def encode(root, k, fname, info, chapter = None):
	cmd = "HandBrakeCLI -e x264 -q 21 -a 1 -E lame -B 128 -6 dpl2 -R Auto -D 0.0 -f mp4 -X 640 --loose-anamorphic -i \"%s\" --denoise weak --decomb -t %d -o \"%s\""%(root, k, fname)
	if "subp" in info and "audio" in info and "ja" in info["audio"]:
		print "anime"
		cmd += " -a %s -s %s"%(info["audio"]["ja"], info["subp"]["en"])
	if chapter!=None:
		cmd += " -c %d"%chapter
	print cmd
	if not exists(fname):
		system(cmd)
		pass
	mplayer = popen("mplayer -vo null -frames 0 -identify '%s' 2>&1"%fname).readlines()
	values = {}
	for l in mplayer:
		if l.find("=")!=-1 and l.find(" ")==-1 and l.find("==")==-1:
			key,value = l.split("=",1)
			values[key] = value.strip()
	length = float(values["ID_LENGTH"])
	diff = abs((length/60.0)-info["length"])
	if diff > 1:
		print info["length"]
		print length, length/60.0
		raise Exception, diff

if len(folders) == 0:
	for root, dirs, files in walk(".", topdown=False):
		dirs = sorted(dirs)
		if "VIDEO_TS" in dirs:
			reencode(root)
else:
	for a in folders:
		reencode(a)

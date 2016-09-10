from os import walk, system, popen
from os.path import exists, isdir, basename
from xml.dom.minidom import parseString
from stats import *
from subprocess import Popen, PIPE
from optparse import OptionParser
import re
from check_disks import read_lsdvd, decide_files, get_idname

parser = OptionParser()
parser.add_option("--chapter", dest="byChapter", default=False, action="store_true")
(opts, folders) = parser.parse_args()

def handbrakeList(root, fname):
	titlePattern = re.compile("\+ title (\d+):")
	durationPattern = re.compile("\+ duration: (\d+):(\d+):(\d+)")
	chapterPattern = re.compile("\+ (\d+): cells \d+->\d+, \d+ blocks, duration (\d+):(\d+):(\d+)")

	tracks = {}
	order = []
	for line in open(fname).readlines():
		value = int(line)
		order.append(value)
		cmd = "HandBrakeCLI --scan -i '%s' --title %d"%(root, value)
		p = Popen(cmd, shell=True, stdout = PIPE, stderr = PIPE)
		data = p.stderr.read()
		data = unicode(data, errors="ignore")
		open("dump", "wb").write(data)
		title = titlePattern.search(data)
		if title == None:
			raise Exception
		if int(title.groups()[0]) != value:
			raise Exception, (title.groups(), value)
		duration = durationPattern.search(data)
		duration = [int(x) for x in duration.groups()]
		duration = (duration[0]*60)+duration[1]+(duration[2]/60.0)
		tracks[value] = {"length": duration}
		chapters = {}
		for chapter in chapterPattern.findall(data):
			chapter = [int(x) for x in chapter]
			chapters[int(chapter[0])] = (chapter[1]*60)+chapter[2]+(chapter[3]/60.0)
		tracks[value]["chapters"] = chapters

	return tracks, order
	
def reencode(root):
	idname = get_idname(root)
	fname = "tracks/" + idname
	read_lsdvd(root, fname)
	items = list(decide_files(fname))
	print items

	for k, fname, tracks in items:
		encode(root, k, fname, tracks)

def encode(root, k, fname, info, chapter = None):
	fname = fname.replace("/","")
	cmd = "HandBrakeCLI -e x264 -q 19 -a 1 -E lame -B 128 -6 dpl2 -R Auto -D 0.0 -X 720 --loose-anamorphic -i \"%s\" --denoise weak --decomb -t %d -o \"%s\" --no-dvdnav"%(root, k, fname)
	if "subp" in info and "audio" in info and "ja" in info["audio"]:
		print "anime"
		cmd += " -a %s -s %s"%(info["audio"]["ja"], info["subp"]["en"])
	#elif "subp" in info and "en" in info["subp"]:
	#	print "subtitles (foreign only)"
	#	cmd += " --subtitle scan --subtitle-forced %s"%(info["subp"]["en"])
	if chapter!=None:
		cmd += " -c %d"%chapter
	print cmd
	if not exists(fname):
		#raise Exception, cmd
		system(cmd)
	cmd = "mplayer -vo null -frames 0 -identify '%s' 2>&1" % fname
	print cmd
	mplayer = popen(cmd).readlines()
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
			print "root", root
			reencode(root)
else:
	for a in folders:
		reencode(a)

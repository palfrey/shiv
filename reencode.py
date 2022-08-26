from os import walk, system, popen
from os.path import exists, isdir, basename
import os
from xml.dom.minidom import parseString
from stats import *
from subprocess import Popen, PIPE, check_output
from optparse import OptionParser
import re
from check_disks import read_lsdvd, decide_files, get_idname, is_bluray, read_makemkv
import shellescape

parser = OptionParser()
parser.add_option("--chapter", dest="byChapter", default=False, action="store_true")
parser.add_option("--uuid", dest="uuid", default=None)
(opts, folders) = parser.parse_args()


def handbrakeList(root, fname):
    titlePattern = re.compile("\+ title (\d+):")
    durationPattern = re.compile("\+ duration: (\d+):(\d+):(\d+)")
    chapterPattern = re.compile(
        "\+ (\d+): cells \d+->\d+, \d+ blocks, duration (\d+):(\d+):(\d+)"
    )

    tracks = {}
    order = []
    for line in open(fname).readlines():
        value = int(line)
        order.append(value)
        cmd = "HandBrakeCLI --scan -i '%s' --title %d" % (root, value)
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        data = p.stderr.read()
        data = str(data, errors="ignore")
        open("dump", "wb").write(data)
        title = titlePattern.search(data)
        if title == None:
            raise Exception
        if int(title.groups()[0]) != value:
            raise Exception(title.groups(), value)
        duration = durationPattern.search(data)
        duration = [int(x) for x in duration.groups()]
        duration = (duration[0] * 60) + duration[1] + (duration[2] / 60.0)
        tracks[value] = {"length": duration}
        chapters = {}
        for chapter in chapterPattern.findall(data):
            chapter = [int(x) for x in chapter]
            chapters[int(chapter[0])] = (
                (chapter[1] * 60) + chapter[2] + (chapter[3] / 60.0)
            )
        tracks[value]["chapters"] = chapters

    return tracks, order


def check_file(fname, expected_length):
    cmd = ["mplayer", "-vo", "null", "-frames", "0", "-identify", fname]
    print(cmd)
    mplayer = check_output(cmd, encoding="utf-8")
    values = {}
    for l in mplayer.split("\n"):
        if l.find("=") != -1 and l.find(" ") == -1 and l.find("==") == -1:
            key, value = l.split("=", 1)
            values[key] = value.strip()
    try:
        length = float(values["ID_LENGTH"])
    except KeyError:
        print(mplayer)
        print(values)
        raise
    diff = abs((length / 60.0) - expected_length)
    percent = 100.0 * (diff / expected_length)
    if diff > 1 and percent > 1.5:
        raise Exception(
            "Missing %f minutes. Expected %f and got %f which is %f%%"
            % (diff, expected_length, length / 60.0, percent)
        )


def reencode(root):
    if opts.uuid == None:
        idname = get_idname(root)
    else:
        idname = opts.uuid
    fname = "tracks/" + idname
    if is_bluray(root):
        read_makemkv(root, fname)
    else:
        read_lsdvd(root, fname)
    items = list(decide_files(fname))
    print("items", items)

    for data in items:
        print("data", data)
        fname = "output/" + (
            data["fname"].replace("/", "").replace("'", "\\'").replace(":", " -")
        )
        if not exists(fname):
            data["fname"] = fname
            if is_bluray(root):
                bluray_encode(root, data)
            else:
                dvd_encode(root, data)
        check_file(fname, data["track"]["length"])


def dvd_encode(root, data):
    cmd = (
        "HandBrakeCLI -e x264 -q 19 -a 1 -E lame -B 128 -6 dpl2 -R Auto -D 0.0 -X 720 --loose-anamorphic -i %s --denoise weak --decomb --title %d -o %s --no-dvdnav"
        % (root, data["track"]["id"], data["fname"])
    )
    info = data["track"]
    if "subp" in info and "audio" in info and "ja" in info["audio"]:
        print("anime")
        cmd += " --audio %s --subtitle %s" % (
            ",".join(info["audio"]["ja"]),
            ",".join(info["subp"]["en"]),
        )
    elif "subp" in info and "en" in info["subp"]:
        if "audio" in info and "en" in info["audio"]:
            print("subtitles (en only)")
            cmd += " --subtitle %s" % (info["subp"]["en"])
        else:
            print("subtitles (foreign only)")
            cmd += " --subtitle scan --subtitle-forced %s" % (info["subp"]["en"])
    if "startChapter" in data:
        cmd += " -c %d-%d" % (data["startChapter"], data["endChapter"])
    print(cmd)
    cmd = cmd.split(" ")
    check_output(cmd)


def bluray_encode(root, data):
    track_id = int(data["track"]["id"])
    makemkv_folder = "mkv_temp/%s/%d" % (opts.uuid, track_id)
    if not exists(makemkv_folder):
        os.makedirs(makemkv_folder)
    track_path = os.path.join(makemkv_folder, data["track"]["track_path"])
    if not exists(track_path):
        cmd = "makemkvcon -r --decrypt mkv disc:0 %d %s" % (track_id, makemkv_folder)
        print(cmd)
        result = system(cmd)
        if result != 0:
            raise Exception
    track_path = shellescape.quote(track_path)
    info = data["track"]
    cmd = (
        'HandBrakeCLI -e x264 --two-pass --quality 23 --audio %s -E lame -B 192 -R Auto -X 1920 --loose-anamorphic -i %s --denoise weak --decomb -o "%s" --subtitle-lang-list eng --all-subtitles'
        % (",".join([str(x) for x in info["audio"]["eng"]]), track_path, data["fname"])
    )
    if "subp" in info and "audio" in info and "ja" in info["audio"]:
        print("anime")
        cmd += " -a %s -s %s" % (info["audio"]["ja"], info["subp"]["eng"])
        raise Exception
    print(cmd)
    # raise Exception
    result = system(cmd)
    if result != 0:
        raise Exception


if len(folders) == 0:
    for root, dirs, files in walk(".", topdown=False):
        dirs = sorted(dirs)
        if "VIDEO_TS" in dirs:
            print("root", root)
            reencode(root)
else:
    for a in folders:
        reencode(a)
print("done")

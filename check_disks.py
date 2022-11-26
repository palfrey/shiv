from os.path import exists, join
import subprocess
from xml.dom.minidom import parseString
from sys import argv
from json import dumps, loads
import os
import json
import stat
import csv


def read_lsdvd(root, fname):
    print("lsdvd data:", fname)
    if exists(fname):
        data = open(fname).read()
    else:
        cmd = ["lsdvd", "-Ox", "-x", root]
        print(cmd)
        data = subprocess.check_output(cmd)
        if len(data) == 0:
            raise Exception
        data = str(data, errors="ignore")
        data = data.replace("&", "&amp;")
        open(fname, "w").write(data)
    return data


def read_makemkv(root, fname):
    print("makemkv data:", fname, root)
    if exists(fname):
        data = open(fname).read()
    else:
        cmd = [
            "makemkvcon",
            "-r",
            "info",
            "disc:0",
        ]  # FIXME: Ignores root and I can't seem to make it not...
        print(" ".join(cmd))
        try:
            data = subprocess.check_output(cmd, encoding="utf-8")
        except subprocess.CalledProcessError as e:
            print(e.output)
            raise
        if len(data) == 0:
            raise Exception
        open(fname, "w").write(data)
    return data


def parse_lsdvd(data):
    xml = parseString(data)

    tracks = {}

    for track in xml.getElementsByTagName("track"):
        id = None
        # print [x.nodeName for x in track.childNodes]
        for child in track.childNodes:
            if child.nodeName == "ix":
                assert id == None, id
                id = int(child.firstChild.data)
            elif child.nodeName == "length":
                assert id != None
                length = float(child.firstChild.data)
                tracks[id] = {"length": length / 60.0, "id": id}
            elif child.nodeName == "subp":
                assert id in tracks
                element = child.getElementsByTagName("langcode")[0]
                if element.firstChild != None:
                    if "subp" not in tracks[id]:
                        tracks[id]["subp"] = {}
                    lang = element.firstChild.data
                    if lang == "xx":
                        # open(fname, "wb").write("")
                        continue
                        raise Exception(id, tracks[id], child.toxml())
                    if lang not in tracks[id]["subp"]:
                        tracks[id]["subp"][lang] = []
                    tracks[id]["subp"][lang].append(
                        child.getElementsByTagName("ix")[0].firstChild.data
                    )
            elif child.nodeName == "audio":
                assert id in tracks
                if "audio" not in tracks[id]:
                    tracks[id]["audio"] = {}
                element = langcode = child.getElementsByTagName("langcode")[0]
                # print element.toxml()
                if element.firstChild != None:
                    langcode = element.firstChild.data
                    if langcode not in tracks[id]["audio"]:
                        tracks[id]["audio"][langcode] = []
                    audioId = child.getElementsByTagName("ix")[0].firstChild.data
                    tracks[id]["audio"][langcode].append(audioId)
            elif child.nodeName == "chapter":
                if "chapters" not in tracks[id]:
                    tracks[id]["chapters"] = {}
                ix = int(child.getElementsByTagName("ix")[0].firstChild.data)
                length = child.getElementsByTagName("length")[0].firstChild.data
                tracks[id]["chapters"][ix] = float(length) / 60.0

            else:
                # print "node", child.nodeName
                pass

    return tracks, sorted(tracks.keys())


def parse_makemkv(data):
    tracks = {}
    subkind = None
    for line in data.split("\n"):
        if len(line.strip()) == 0:
            continue
        try:
            code, rest = line.split(":", 1)
        except ValueError:
            raise Exception("'%s'" % line)
        if code in ["MSG", "DRV", "TCOUNT", "CINFO"]:
            continue
        items = list(csv.reader([rest]))[0]
        if code == "TINFO":
            id = int(items[0])
            if id not in tracks:
                tracks[id] = {"id": id, "subp": {}, "audio": {}}
            kind = int(items[1])
            data = items[3]
            if kind == 9:
                (h, m, s) = [int(x) for x in data.split(":")]
                length = (h * 60) + m
                tracks[id]["length"] = length
            elif kind == 27:
                tracks[id]["track_path"] = data
            elif kind == 2:
                tracks[id]["name"] = data
            elif kind in [8, 10, 11, 15, 16, 25, 26, 28, 29, 30, 31, 33, 49]:
                pass
            else:
                print(items)
                raise Exception(kind)
        elif code in ["SINFO"]:
            kind = int(items[2])
            if kind == 1:
                subkind = int(items[3])
                if subkind in [6201, 6202, 6203]:  # Video, Audio, Subtitles
                    pass
                else:
                    print(items)
                    raise Exception(subkind)
            elif kind in [5, 6, 7, 19, 20, 21, 22, 29, 30, 21, 33, 38]:
                pass
            elif kind == 3:  # identifier
                lang = items[4]
                if subkind == 6201:  # video
                    pass
                elif subkind == 6202:  # audio
                    lang = items[4]
                    if lang not in tracks[id]["audio"]:
                        tracks[id]["audio"][lang] = []
                    tracks[id]["audio"][lang].append(int(items[1]))
                elif subkind == 6203:  # subtitles
                    if lang not in tracks[id]["subp"]:
                        tracks[id]["subp"][lang] = []
                    tracks[id]["subp"][lang].append(int(items[1]))
                else:
                    print(items)
                    raise Exception(kind, subkind)
        else:
            raise Exception((code, items))
    return tracks, sorted(tracks.keys())


def decide_files(fname):
    data = open(fname).read()
    if data.startswith("<?xml"):
        tracks, order = parse_lsdvd(data)
    else:
        tracks, order = parse_makemkv(data)

    if tracks == {}:
        raise Exception("empty tracks")

    base = fname

    if exists(fname + ".trackmap"):
        trackmap = json.loads(open(fname + ".trackmap").read())
        print("trackmap", trackmap)
        for k, entry in enumerate(trackmap):
            fname = "%s-%d-t%d-s%d-e%d.mkv" % (
                base,
                k,
                entry["track"],
                entry["startChapter"],
                entry["endChapter"],
            )
            yield {
                "number": k,
                "fname": fname,
                "track": tracks[entry["track"]],
                "startChapter": entry["startChapter"],
                "endChapter": entry["endChapter"],
            }
        return

    if len(tracks) == 99:
        print("Protected with RipGuard, need a .trackmap")
        raise Exception

    tracks = dict((k, v) for (k, v) in tracks.items() if v["length"] > 5)

    episodeValues = dict((k, v) for (k, v) in tracks.items() if v["length"] < 87)
    episodes = len(episodeValues)
    movieValues = dict(
        (k, v) for (k, v) in tracks.items() if v["length"] > 85 and v["length"] < 200
    )
    movies = len(movieValues)
    print("e,m", episodes, movies, [(k, v["length"]) for (k, v) in tracks.items()])

    if episodes > 30:  # too many!
        print("Too many!", movies, episodes)
        print(tracks)
        raise Exception

    totalEpisodeLength = sum([x["length"] for x in list(episodeValues.values())])
    movieLength = sum([m["length"] for m in movieValues.values()])
    print(
        "Total lengths",
        totalEpisodeLength,
        movieLength,
        (movieLength - totalEpisodeLength),
    )

    if movies == 0 or (
        movies == 1
        and episodes > movies
        and (movieLength - totalEpisodeLength) < 1
        and (episodes < 10 or movieLength > 120)
    ):
        print(
            "TV series",
            len(episodeValues),
            [(k, v["length"]) for (k, v) in episodeValues.items()],
        )
        episodeValues = list(episodeValues.keys())

        for k in order:
            if k not in episodeValues:
                continue
            fname = "%s-%d.mkv" % (base, k)
            yield {"number": k, "fname": fname, "track": tracks[k]}

    elif movies == 1:
        print("Movie", movieValues)
        k = list(movieValues.keys())[0]
        if "name" in tracks[k]:
            fname = "%s.mkv" % tracks[k]["name"]
        else:
            fname = "%s.mkv" % base
        yield {"number": k, "fname": fname, "track": tracks[k]}

    else:
        print("Something else!", movies, episodes)
        print(movieValues, episodeValues)

        for k in order:
            if k not in tracks:
                continue
            fname = "%s-%d.mkv" % (base, k)
            yield {"number": k, "fname": fname, "track": tracks[k]}


def is_bluray(root):
    st = os.stat(root)
    return stat.S_ISBLK(st.st_mode)


def get_idname(root):
    if exists(join(root, "VIDEO_TS")):
        data = subprocess.check_output(["./dvdid", root], encoding="utf-8")
        return data.replace("|", "_").strip()
    elif is_bluray(root):
        raise Exception("blu ray")
    else:
        raise Exception(os.listdir(root))


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
        raise Exception(fname)

    tracks = list(decide_files(fname))
    print(tracks)
    open(fname + ".tracks", "w").write(dumps(list([strip_entry(x) for x in tracks])))


def check_disks():
    ret = True
    for fname in os.listdir("tracks"):
        if fname.startswith("."):
            continue
        if fname.endswith(".trackmap"):
            continue
        if fname.endswith(".tracks"):
            wanted_tracks = loads(open("tracks/" + fname).read())
            gotten_tracks = [
                strip_entry(x)
                for x in decide_files("tracks/" + fname.replace(".tracks", ""))
            ]
            if wanted_tracks == gotten_tracks:
                print(fname, "is ok", wanted_tracks)
            else:
                print(fname, "is bad: ")
                print(wanted_tracks)
                print(gotten_tracks)
                ret = False
                raise Exception
        elif not exists("tracks/%s.tracks" % fname):
            print("Making %s.tracks" % fname)
            read_idname(fname)
    return ret


if __name__ == "__main__":
    if len(argv) > 1:
        read_disk(argv[1])
    else:
        ret = check_disks()
        if not ret:
            exit(-1)

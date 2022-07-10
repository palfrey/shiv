import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gobject
from os.path import basename
from os import system

loop = gobject.MainLoop()
DBusGMainLoop(set_as_default=True)

bus = dbus.SystemBus()
ud_manager_obj = bus.get_object("org.freedesktop.UDisks", "/org/freedesktop/UDisks")
ud_manager = dbus.Interface(ud_manager_obj, "org.freedesktop.UDisks")


def handler(*args, **kwargs):
    print("handler", kwargs, args)
    obj = bus.get_object("org.freedesktop.UDisks", kwargs["path"])
    device_props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
    handle_mount(device_props)


def eject(device_props):
    cmd = "eject '%s'" % device_props.Get("org.freedesktop.UDisks.Device", "DeviceFile")
    print(cmd)
    # raise Exception
    system(cmd)


def handle_mount(device_props):
    media = device_props.Get("org.freedesktop.UDisks.Device", "DriveMedia")
    if media in ["optical_cd", "optical_cd_r"]:
        deviceFile = device_props.Get(
            "org.freedesktop.UDisks.Device", "DeviceFileById"
        )[0]
        cmd = "abcde -d %s" % deviceFile
        print(cmd)
        result = system(cmd)
        print(result)
    elif media == "optical_bd":
        deviceFile = device_props.Get(
            "org.freedesktop.UDisks.Device", "DeviceFileById"
        )[0]
        uuid = device_props.Get("org.freedesktop.UDisks.Device", "IdUuid")
        cmd = "python reencode.py %s --uuid %s" % (deviceFile, uuid)
        print(cmd)
        result = system(cmd)
        if result != 0:
            raise Exception(result)
        eject(device_props)
    elif media in ["optical_dvd", "optical_dvd_r"]:
        print("media type", media)
        mount = device_props.Get("org.freedesktop.UDisks.Device", "DeviceMountPaths")
        print("mount", mount)
        if len(mount) == 0:
            media = device_props.Get(
                "org.freedesktop.UDisks.Device", "DeviceIsMediaAvailable"
            )
            if media:
                deviceFile = device_props.Get(
                    "org.freedesktop.UDisks.Device", "DeviceFileById"
                )[0]
                cmd = "pmount %s" % deviceFile
                print(cmd)
                system(cmd)
                mount = device_props.Get(
                    "org.freedesktop.UDisks.Device", "DeviceMountPaths"
                )
            else:
                return
        for m in mount:
            name = basename(m)
            print(name)
            # if not exists(name):
            # cmd = "vobcopy -m -i '%s' -t '%s'"%(m, name)
            cmd = "python reencode.py %s" % m
            print(cmd)
            result = system(cmd)
            if result != 0:
                raise Exception(result)
            eject(device_props)
    else:
        print("Unrecognised media: '%s'" % media)


for dev in ud_manager.EnumerateDevices():
    device_obj = bus.get_object("org.freedesktop.UDisks", dev)
    device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)

    drive = device_props.Get("org.freedesktop.UDisks.Device", "DriveMediaCompatibility")
    # print "drive", device_obj, drive
    if "optical_dvd" in drive:
        handle_mount(device_props)
        device_obj.connect_to_signal(
            None,
            handler,
            sender_keyword="sender",
            destination_keyword="dest",
            interface_keyword="intf",
            member_keyword="member",
            path_keyword="path",
        )
        loop.run()

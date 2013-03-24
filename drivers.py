import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gobject
from os.path import basename, exists
from os import system, popen
from glob import glob

loop = gobject.MainLoop()
DBusGMainLoop(set_as_default=True)

bus = dbus.SystemBus()
ud_manager_obj = bus.get_object("org.freedesktop.UDisks", "/org/freedesktop/UDisks")
ud_manager = dbus.Interface(ud_manager_obj, 'org.freedesktop.UDisks')

def handler(*args, **kwargs):
	print "handler", kwargs, args
	obj = bus.get_object("org.freedesktop.UDisks", kwargs["path"])
	device_props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
	handle_mount(device_props)
	
def handle_mount(device_props):
	mount = device_props.Get('org.freedesktop.UDisks.Device', "DeviceMountPaths")
	#print device_props.GetAll('org.freedesktop.UDisks.Device')
	print "mount", mount
	for m in mount:
		name = basename(m)
		print name
		#if not exists(name):
		#cmd = "vobcopy -m -i '%s' -t '%s'"%(m, name)
		cmd = "python reencode.py %s"%m
		print cmd
		result = system(cmd)
		if result!=0:
			raise Exception, result

		cmd = "eject '%s'"%device_props.Get('org.freedesktop.UDisks.Device', "DeviceFile")
		print cmd
		system(cmd)

for dev in ud_manager.EnumerateDevices():
	device_obj = bus.get_object("org.freedesktop.UDisks", dev)
	device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)

	drive = device_props.Get('org.freedesktop.UDisks.Device', "DriveMediaCompatibility")
	#print "drive", device_obj, drive
	if "optical_dvd" in drive:
		handle_mount(device_props)
		device_obj.connect_to_signal(None, handler, sender_keyword='sender', destination_keyword="dest", interface_keyword="intf", member_keyword="member", path_keyword="path")
		loop.run()


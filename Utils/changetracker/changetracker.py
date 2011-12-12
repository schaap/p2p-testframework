import os, mimetypes, sys, getopt
from BitTorrent.bencode import bencode, bdecode

helpMessage = """USAGE:
-h/--help: to print this message

-f/--folder (REQUIRED): specify the folder in which to read the torrents to be modified

-w/--write (REQUIRED): specify the folder in which to write the modified torrents

-o/--old-tracker (OPTIONAL): if specified, will only modify those torrents whose announce urls CONTAIN this string (probably does not work with multitracker torrents).	If not specified, will change all torrents. Be sure to not underspecify this string, or you will get more matches than you want.

-n/--new-tracker (REQUIRED): set new tracker to specified url. 

-d/--delete (OPTIONAL): will offer an option to delete the torrents after the edited ones are listed (only those torrents that were changed should be deleted)

-z/--force-delete (OPTIONAL): will delete the edited torrents without prompting the user

Depending on how your shell deals with some characters, it is probably a good idea to quote your option arguments.
No guarantees that this won't burn your computer, kill your mother, or steal your dog. Use carefully.
Does not check for valid options (e.g. valid directory names).

If you know how multitracker torrents are stored as python objects once bdecoded, you can edit the top of this file to set oldTrackG/newTrackG to the desired setting and run the program without passing -o/-n. Can also set set dirToListG/writeDirG that way. If everything is set that way, pass -p to run with just the internal defaults you set if you don't pass -d/-z. If you set them, and provide cli arguments as well, the cli arguments will override. Specify None to -o to set to all torrents when you have oldTrackG set to something"""

##dirToListG = """/home/user/torrentdir"""
##writeDirG = """/home/user/torrentdir2"""
##oldTrackG = ""
##oldTrackG = """http://sometracker.com/announce.php"""
##newTrackG = """http://someothertracker.com/announce.php"""

def getFileList(dirToList):
	"takes a directory, returns a list of torrent files (including directory name!) in the directory, non-recursive"
	files = os.listdir(dirToList)
	retFiles = []
	for i in files:
		if  not os.path.isfile(os.path.join(dirToList, i)): continue
		if mimetypes.guess_type(i) == ('application/x-bittorrent', None): 		
			retFiles.append( i )
	return retFiles

def bDecode(torrent, dir):
	fd = open(os.path.join(dir, torrent), 'rb')
	fdT = bdecode(fd.read())
	fd.close()
	return fdT

def trimTrackUrl(torrent, dir, trackerUrl):
	"""takes a torrent filename/fullpath and tracker url, returns a bdecoded torrent if there is a match, returns False otherwise.
	If trackerUrl is boolean False (so None, [], (), 0, False, ''....) will just bdecode the torrent file and return it."""
	fdT = bDecode(torrent, dir)
	if trackerUrl and trackerUrl not in fdT['announce']: return False
	return fdT
	
def changeTracker(fdT, torrent, directory, trackerUrl):
	"takes a bdecoded torrent, changed tracker url, writes new torrent in directory, returns nothing"
	fdT['announce'] = trackerUrl
	fd = open(os.path.join(directory, torrent), 'wb')
	fd.write(bencode(fdT))
	fd.close()

def processArgs(argp):
	"""takes a getopt sequence of tuples of argument, options. returns a tuple of (dirToList, writeDir, oldTrack, newTrack, postaction)"""
	dirToList, writeDir, oldTrack, newTrack, postaction = (None, None, None, None, None)
	for argum, option in argp:
		if argum == '-f' or argum == '--folder':
			dirToList = option
		elif argum == '-w' or argum == '--write':
			writeDir = option
		elif argum == '-o' or argum =='--old-tracker':
			if option.lower() == 'none': oldTrack = None
			else: oldTrack = option
		elif argum == '-n' or argum == '--new-tracker':
			newTrack =option
		elif argum == '-d' or argum == '--delete':
			postaction = 'delete'
		elif argum == '-z' or argum == '--force-delete':
			postaction = 'forceDelete'
		elif argum == '-h' or argum == '--help':
			print helpMessage
			sys.exit()
	return dirToList, writeDir, oldTrack, newTrack, postaction
	
def postProcessArgs(argTup):
	global dirToListG, writeDirG, oldTrackG, newTrackG
	if argTup[0]: dirToList = argTup[0]
	else:
		try: 
			dirToList = dirToListG
		except: 
			sys.stderr.write('Must specify a directory to list%s' % os.linesep )
			sys.exit(1)
	if argTup[1]: writeDir = argTup[1]
	else:
		try:
			writeDir = writeDirG
		except: 
			sys.stderr.write('Must specify a write directory%s' % os.linesep)
			sys.exit(1)
	if argTup[2]: oldTrack = argTup[2]
	else:
		try:
			oldTrack = oldTrackG
		except: oldTrack = argTup[2]
	if argTup[3]: newTrack = argTup[3]
	else:
		try:
			newTrack = newTrackG
		except: 
			sys.stderr.write('Must specify a new tracker to set%s' % os.linesep)
			sys.exit(1)
	postaction = argTup[4]
	return dirToList, writeDir, oldTrack, newTrack, postaction

try:
	(argp, rest) = getopt.gnu_getopt(sys.argv[1:], 'f:w:o:n:dzhp', longopts=['folder=', 'write=', 'old-tracker=', 'new-tracker=', 'delete', 'force-delete', 'help'])
	if len(argp) == 0: 
		print helpMessage
		sys.exit()
except getopt.GetoptError:
	sys.stderr.write(helpMessage + os.linesep)
	sys.exit(1)

argTup = processArgs(argp)
dirToList, writeDir, oldTrack, newTrack, postaction = postProcessArgs(argTup)
fileList = getFileList(dirToList)
changeList = []
for theTorrent in fileList:
	bdTor = trimTrackUrl(theTorrent, dirToList, oldTrack)
	if not bdTor: continue
	changeTracker(bdTor, theTorrent, writeDir, newTrack)
	changeList.append( theTorrent )

for i in changeList: print i
if postaction:
	if postaction == 'delete': confirm = raw_input("Are you sure you want to delete the above files? (y/N)")
	elif postaction == 'forceDelete': confirm = 'y'
	if not confirm.lower().startswith('y'): sys.exit()
	for delFile in changeList:
		os.unlink( os.path.join(dirToList, delFile))

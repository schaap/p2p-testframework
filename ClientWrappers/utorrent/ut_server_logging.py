#!/usr/bin/python

import sys
import os
import shutil
import socket
import ntpath
import tempfile
import subprocess
import time
import signal
import httplib
import Cookie
import base64
import json
import errno
import random
import traceback

# Client wrapper for uTorrent windows version
# USAGE:
# $0 clientDir workingDir stopWhenSeeding metaDirCount [metaDir [metaDir ...]] dataDirCount [dataDir [dataDir ...]]
#
# clientDir will contain the lock files for sockets, this should be a shared directory for all clients on the same machine
# workingDir will be cleaned out (rm -rf *), webui.zip and utorrent.exe will be copied in
# stopWhenSeeding is 0 or 1; if 1 the client will be killed when the torrent has reached "Seeding" state
# metaDirCount is the number of metaDir arguments passed
# metaDir is a directory containing .torrent files to be seeded or downloaded (pass exactly metaDirCount of these)
# dataDirCount is the number of dataDir arguments passed
# dataDir is a directory containing data for the .torrent files (pass exactly dataDirCount of these)

# subprocess.Popen object for utorrent client
utorrent_process = None

# Windows client specifics:
# subprocess.Popen object for Xvfb
xvfb_process = None
# flag whether xauth has been loaded for sn
authLoaded = False
# the screen number loaded in xauth (and hence used for Xvfb) 
sn = None

going = True

def which(name):
    result = []
    exts = [ex for ex in os.environ.get('PATHEXT', '').split(os.pathsep) if ex]
    path = os.environ.get('PATH', None)
    if path is None:
        return []
    for p in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, os.X_OK):
            result.append(p)
        for ex in exts:
            pext = p + ex
            if os.access(pext, os.X_OK):
                result.append(pext)
    return result

def posixToNT( path ):
    split = os.path.split( path )
    res = None
    while split[0] is not None and split[0] != '' and split[0] != '/':
        if res is None:
            res = split[1]
        else:
            res = ntpath.join( split[1], res )
        split = os.path.split( split[0] )
    return ntpath.join( 'z:\\', split[1], res )

def is_list_type( obj ):
    return hasattr( obj, "__iter__" ) and not isinstance( obj, ( str, bytes ) )

def bdecode( data, str_encoding = "utf8" ):
    if not hasattr( data, "__next__" ):
        data = iter( data )
    out = None
    t = next( data )
    if t == "e": # end of list/dict
        return None
    elif t == "i": # integer
        out = ""
        c = next( data )
        while c != "e":
            out += c
            c = next( data )
        out = int( out )
    elif t == "l": # list
        out = []
        while True:
            e_ = bdecode( data )
            if e_ == None:
                break
            out.append( e_ )
    elif t == "d": # dictionary
        out = {}
        while True:
            k = bdecode( data )
            if k == None:
                break
            out[k] = bdecode( data )
    elif t.isdigit(): # string
        out = ""
        l = t
        c = next( data )
        while c != ":":
            l += c
            c = next( data )
        bout = bytearray()
        for _ in range( int( l ) ):
            bout.append( next( data ) )
        try:
            out = bout.decode( str_encoding )
        except UnicodeDecodeError:
            out = bout
    return out

def bencode( obj, str_encoding = "utf8" ):
    out = bytearray()
    t = type( obj )
    if t == int:
        out.extend( "i{0}e".format( obj ).encode( str_encoding ) )
    elif t == dict:
        out.extend( b"d" )
        for k in sorted( obj.keys() ):
            out.extend( bencode( k ) )
            out.extend( bencode( obj[k] ) )
        out.extend( b"e" )
    elif t in ( bytes, bytearray ):
        out.extend( str( len( obj ) ).encode( str_encoding ) )
        out.extend( b":" )
        out.extend( obj )
    elif is_list_type( obj ):
        out.extend( b"l" )
        for e_ in [bencode(p) for p in obj]:
            out.extend( e_ )
        out.extend( b"e" )
    else:
        obj = str( obj ).encode( str_encoding )
        out.extend( str( len( obj ) ).encode( str_encoding ) )
        out.extend( b":" )
        out.extend( obj )
    return bytes( out )

def checkPortOpen(port):
    if len(which('netstat')) == 0:
        print >> sys.stderr, "Warning: Can't verify availability of ports. Missing netstat. Assuming available."
        return True
    proc = subprocess.Popen( ["bash"], stdin=subprocess.PIPE, stdout=subprocess.PIPE )
    (out, _) = proc.communicate( 'netstat -tan | grep -E "^[^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+[^[:space:]]+:{0}[[:space:]]"'.format( port ) )
    # pylint: disable-msg=E1103
    # PyLint doesn't understand the return type of communicate() and will complain .strip() doesn't exist for a list (it's actually a string)
    return out.strip() == ''
    # pylint: enable-msg=E1103

def check_output(args, shell = False, stderr = None ):
    proc = subprocess.Popen(args, shell=shell, stderr=stderr, stdout=subprocess.PIPE)
    (out, _) = proc.communicate()
    if proc.returncode != 0:
        raise Exception( "Called process '{0}' exited with returncode {1}. Output: {2}".format( " ".join(args), proc.returncode, out ) )
    return out

def check_call(args, shell = False):
    check_output( args, shell = shell )

class uTorrentConnection( httplib.HTTPConnection ):
    _cookies = Cookie.SimpleCookie()
    _resp = None
    def __init__(self, port):
        httplib.HTTPConnection.__init__(self, 'localhost', port, timeout=1)
    
    def request(self, url, body = None, headers = None, method = 'GET'):
        headers_ = {}
        if headers:
            for h in headers:
                headers_[h] = headers[h]
        headers_['Cookie'] = self._cookies.output(None, '', '\n')
        headers_['Authorization'] = 'Basic {0}'.format( base64.b64encode( 'admin:' ) )
        httplib.HTTPConnection.request(self, method, url, body, headers_)
        self._resp = httplib.HTTPConnection.getresponse(self)
        headers = self._resp.getheaders()
        for h in headers:
            if h[0].lower == 'set-cookie':
                self._cookies.load(h[1])
    
    def getresponse(self, buffering = False):
        return self._resp
    
    def doRequest(self, url, reportErrors = True, method = 'GET', headers = None, data = None):
        try:
            self.request( url, method = method, headers = headers, body = data )
            page = self._resp.read()
            self.close()
            if self._resp.status != 200 and reportErrors:
                print >> sys.stderr, "Unexpected status: {0}".format( self._resp.status )
                print >> sys.stderr, "Server says: {0}".format( self._resp.reason )
                print >> sys.stderr, "Page: {0}".format( page )
                print >> sys.stderr, "End of unexpected status"
            return page
        except httplib.NotConnected:
            if reportErrors:
                print >> sys.stderr, time.time()
                print >> sys.stderr, "Client could not be connected while earlier contact was succesfull."
            return None
        except httplib.ImproperConnectionState:
            if reportErrors:
                print >> sys.stderr, time.time()
                print >> sys.stderr, "Client could was not connected properly while earlier contact was succesfull."
            return None
        except httplib.BadStatusLine:
            if reportErrors:
                print >> sys.stderr, time.time()
                print >> sys.stderr, "Client reacted with strange status after ealier succesfull contact, assuming crash."
            return None
        except socket.timeout:
            if reportErrors:
                print >> sys.stderr, time.time()
                print >> sys.stderr, "Client did not respond in 5 seconds after earlier succesfull contact, assuming crash."
            return None
        except socket.error as e:
            if e.errno == errno.ECONNREFUSED:
                if reportErrors:
                    print >> sys.stderr, time.time()
                    print >> sys.stderr, "Client did not accept connection after earlier succesfull contact, assuming crash."
                return None
            raise

def randomstring(l):
    res = ''
    for i in range(l):
        random.randint(0,255)
        res += chr(i)
    return base64.b64encode(res)
        
def handler(_a,_b):
    # pylint: disable-msg=W0603
    # Yes, that's global
    global going
    # pylint: enable-msg=W0603
    going = False

def interact(webport, metadirs, stopWhenSeeding):
    # pylint: disable-msg=W0603,W0602
    # Yes, that's global
    # And yes, it's not being assigned to. Yet.
    global going, utorrent_process
    # pylint: enable-msg=W0603,W0602
    torrentLoaded = False
    seedStopping = 0
    torrentCounter = 0
    while going:
        time.sleep(1)
        # Request status
        conn = uTorrentConnection( webport )
        page = conn.doRequest('/gui/?list=1', reportErrors = torrentLoaded)
        if page is None:
            if torrentLoaded:
                break
            continue
        #print >> sys.stderr, "DEBUG LIST:\n{0}".format( page )
        # Check if client still exists
        if utorrent_process.poll() is not None:
            # Client died
            try:
                utorrent_process.communicate()
            except Exception:
                pass
            print >> sys.stderr, time.time()
            print >> sys.stderr, "Client disappeared. Crashed? This is normal if the client was stopped when seeding."
            break
        # Load torrents if this is the first contact
        if not torrentLoaded:
            conn = uTorrentConnection( webport )
            for d in metadirs:
                for torrentFile in [os.path.join(d, f) for f in os.listdir(d) if f[-8:] == '.torrent' and os.path.isfile(os.path.join(d,f))]:
                    fObj = open(torrentFile, 'rb')
                    torrData = fObj.read()
                    fObj.close()
                    data = '\r\n'.join( (
                                    '--{{BOUNDARY}}',
                                    'Content-Disposition: form-data; name="torrent_file"; filename="t{0}.torrent"'.format(torrentCounter),
                                    'Content-Type: application/x-bittorrent',
                                    '',
                                    torrData,
                                    '--{{BOUNDARY}}--',
                                    ''
                                    ) )
                    torrentCounter += 1
                    bndlen = 20
                    bnd = ''
                    while True:
                        bnd = randomstring(bndlen)
                        if bnd not in data:
                            break
                        bndlen += 1
                    data = data.replace('{{BOUNDARY}}', bnd)
                    headers = {}
                    headers['Content-Type'] = 'multipart/form-data; boundary=' + bnd
                    page2 = conn.doRequest('/gui/?action=add-file', data = data, method='POST', headers = headers)
                    #print >> sys.stderr, "DEBUG ADD:\n{0}".format( page2 )
            print >> sys.stderr, time.time()
            print >> sys.stderr, "Loaded {0} files".format(torrentCounter)
            torrentLoaded = True
        # Decode status
        try:
            status = json.loads( page )
        except ValueError:
            if torrentLoaded:
                print >> sys.stderr, time.time()
                print >> sys.stderr, "Client reacted with invalid json string while earlier contact was succesfull."
                break
            continue
        stillBusy = torrentCounter
        uploadDone = 0
        downloadDone = 0
        percentDone = 0
        for t in status['torrents']:
            percentDone += t[4]
            if t[4] >= 1000:
                stillBusy -= 1
            downloadDone += t[5]
            uploadDone += t[6]
        print time.time()
        if len(status['torrents']) == 0:
            print "0 0 0"
        else:
            print "{0} {1} {2}".format( percentDone / (len(status['torrents']) * 10.0), downloadDone, uploadDone )
        if stillBusy == 0 and stopWhenSeeding:
            if seedStopping == 0:
                print >> sys.stderr, time.time()
                print >> sys.stderr, "Stopped when seeding"
                seedStopping = 1
                # Stop the process
                utorrent_process.terminate()
            elif seedStopping <= 5:
                # Give it some time (at least 1 sec per seedStopping increment, so at least 5 secs)
                seedStopping += 1
            elif seedStopping == 6:
                # Not listening? Die, then.
                utorrent_process.kill()
                seedStopping += 1
            elif seedStopping <= 10:
                # Give it some time again
                seedStopping += 1
            else:
                # OK, we're outta here
                print >> sys.stderr, time.time()
                print >> sys.stderr, "Client did not die after 5 secs, giving up on it, anyway"
                break

def patchLinuxConfig(port, webport, workingDir, _): # _ == clientDir
    print >> sys.stderr, "WARNING: The settings of the Linux client are not up to date. They are especially not equal to the Windows settings."
    f = open( os.path.join( workingDir, 'utserver.conf' ) )
    f.write( "token_auth_enable: 0\n" )
    f.write( "dir_active: {0}/\n".format( os.path.join(workingDir, 'download_data') ) )
    f.write( "dir_autoload: {0}/torrents/\n".format( workingDir ) )
    f.write( "auto_bandwidth_management: 0\n" )
    f.write( "bind_port: {0}\n".format( port ) )
    f.write( "ut_webui_port: {0}\n".format( webport ) )
    f.close()

def runLinuxClient(workingDir, _): # _ == clientDir
    # pylint: disable-msg=W0603
    # Yes, that's global
    global utorrent_process
    # pylint: enable-msg=W0603
    utorrent_process = subprocess.Popen(["./utserver", "-configfile", "{0}/utserver.conf".format(workingDir), "-settingspath", workingDir, "-pidfile", "{0}/utserver.pid".format( workingDir ), "-logfile", "{0}/utserver.log".format( workingDir )])

def patchWindowsConfig(port, webport, workingDir, clientDir):
    f = open( os.path.join( clientDir, 'settings.dat' ), 'r' )
    settings = bdecode( f.read() )
    f.close()
    settings['bind_port'] = port
    settings['ut_webui_port'] = webport
    settings['webui.port'] = webport
    settings['dir_active_download'] = posixToNT( os.path.abspath( os.path.join( workingDir, 'download_data' ) ) )
    settings['dir_autoload'] = posixToNT( os.path.abspath(os.path.join(workingDir, 'torrents')) )
    f = open( os.path.join( workingDir, 'settings.dat' ), 'w' )
    f.write( bencode( settings ) )
    f.close()

def runWindowsClient(workingDir, clientDir):
    # pylint: disable-msg=W0603
    # Yes, they're global
    global xvfb_process, utorrent_process, authLoaded, sn
    # pylint: enable-msg=W0603
    # Ensure clean wine dir
    if os.path.exists(os.path.join( workingDir, '.wine' )):
        shutil.rmtree(os.path.join( workingDir, '.wine' ))
    os.makedirs(os.path.join( workingDir, '.wine' ) )
    
    # Copy program files
    shutil.copy( 'webui.zip', workingDir )
    shutil.copy( 'utorrent.exe', workingDir )
    
    # Setup execution environment
    os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.path.join( os.path.expanduser('~'), 'bin' )
    
    # Check availability of Xvfb
    if len(which('xauth')) == 0 or len(which('Xvfb')) == 0:
        raise Exception( 'Could not find xauth or Xvfb, both of which are required to run the windows version of uTorrent under wine' )
    
    # Temporary files for Xvfb
    xvfb_tmpdir = tempfile.mkdtemp('', 'utorrent-xvfb', clientDir)
    (f, authfile) = tempfile.mkstemp('', 'Xauthority', xvfb_tmpdir)
    os.close(f)
    (f_err, errorfile) = tempfile.mkstemp('', 'Xerr.log', xvfb_tmpdir)
    
    # Figure out an available screen number for Xvfb and start Xvfb
    sn = 220
    while xvfb_process is None:
        while os.path.exists( os.path.join( '/tmp', '.X{0}-lock'.format( sn ) ) ):
            sn += 1
            if sn > 1000:
                raise Exception( "Tried all screen numbers from 100 to 1000; no free screen numbers" )
        # pylint: disable-msg=E1103
        # PyLint thinks the return type of check_output is list, but it's actually string
        # It will complain .strip() doesn't exist for lists
        xvfb_mcookie = check_output(["mcookie"], shell=True, stderr=f_err).strip()
        # pylint: enable-msg=E1103
        os.environ['XAUTHORITY'] = authfile
        authLoaded = True
        #check_call(["xauth", "add", ":{0}".format( sn ), ".", xvfb_mcookie], shell=True)
        xauth_proc = subprocess.Popen(["xauth", "source", "-"], shell=True, stdin=subprocess.PIPE)
        xauth_proc.communicate("add :{0} . {1}\n".format( sn, xvfb_mcookie ))
        xvfb_process = subprocess.Popen(["Xvfb", ":{0}".format(sn), "-screen", "0", "640x480x8", "-nolisten", "tcp"], stderr=f_err)
        time.sleep(3)
        f = open(errorfile)
        s = f.read()
        f.close()
        if '_XSERVTransMakeAllCOTSServerListeners: server already running' in s:
            xvfb_process.kill()
            xvfb_process.communicate()
            xvfb_process = None
            os.close(f_err)
            f_err = os.open(errorfile, os.O_WRONLY | os.O_TRUNC)
            check_call(["xauth", "remove", ":{0}".format( sn )], shell=True)
            authLoaded = False
            sn += 1
    
    # Add wine and X variables to execution environment and run uTorrent windows client
    os.environ['WINEPREFIX'] = os.path.join( os.path.abspath(workingDir), '.wine' )
    os.environ['DISPLAY'] = ":{0}".format( sn )
    utorrent_process = subprocess.Popen(["wine", "utorrent", "/noinstall", "/logfile", posixToNT( os.path.abspath(workingDir) )], cwd = os.path.abspath(workingDir))

def mainFunction():
    # pylint: disable-msg=W0603,W0602
    # Yes, that's global
    # And yes, it's not being assigned to. Yet.
    global going, xvfb_process, utorrent_process, authLoaded, sn
    # pylint: enable-msg=W0603,W0602
    
    # Read command line args
    if len(sys.argv) < 6:
        raise Exception( "Not enough arguments" )

    clientDir = sys.argv[1]
    workingDir = sys.argv[2]
    stopWhenSeeding_ = sys.argv[3]
    metaDirCount = int(sys.argv[4])
    if len(sys.argv) < 6 + metaDirCount:
        raise Exception( "Expected {0} meta file dirs, but only {1} arguments given".format( metaDirCount, len(sys.argv) ) )
    dataDirCount = int(sys.argv[5 + metaDirCount])
    if len(sys.argv) < 6 + metaDirCount + dataDirCount:
        raise Exception( "Expected {0} meta file dirs and {1} data dirs, but only {2} arguments given".format( metaDirCount, dataDirCount, len(sys.argv) ) )
    metadirs = []
    datadirs = []
    for i in range(5, 5+metaDirCount):
        metadirs.append( sys.argv[i] )
    for i in range(6+metaDirCount, 6+metaDirCount+dataDirCount):
        datadirs.append( sys.argv[i] )
    
    # Setup signal handling
    signal.signal( signal.SIGINT, handler )
    signal.signal( signal.SIGTERM, handler )
    
    # Check command line args
    if not os.path.isdir( clientDir ):
        raise Exception( "Not a client dir: {0}".format( clientDir ) )
    if not os.path.isdir( workingDir ):
        raise Exception( "Not a working dir: {0}".format( workingDir ) )
    for d in metadirs:
        if not os.path.isdir( d ):
            raise Exception( "Not a meta dir: {0}".format( d ) )
    for d in datadirs:
        if not os.path.isdir( d ):
            raise Exception( "Not a data dir: {0}".format( d ) )
    if stopWhenSeeding_ != '0' and stopWhenSeeding_ != '1':
        raise Exception( "stopWhenSeeding must be 0 or 1, not {0}".format( stopWhenSeeding_ ) )
    stopWhenSeeding = 1
    if stopWhenSeeding_ == '0':
        stopWhenSeeding = 0
    
    # Clean and initialize working dir
    for f in [os.path.join( workingDir, n ) for n in os.listdir(workingDir) if os.path.isfile( os.path.join( workingDir, n ) )]:
        os.remove( f )
    if not os.path.exists( os.path.join( workingDir, 'download_data' ) ):
        os.makedirs(os.path.join( workingDir, 'download_data' ) )
    for f in [os.path.join( workingDir, 'download_data', n ) for n in os.listdir(os.path.join(workingDir, 'download_data'))]:
        if os.path.isfile(f):
            os.remove( f )
        else:
            shutil.rmtree(f)
    if not os.path.exists( os.path.join( workingDir, 'torrents' ) ):
        os.makedirs(os.path.join( workingDir, 'torrents' ) )
    for f in [os.path.join( workingDir, 'torrents', n ) for n in os.listdir(os.path.join(workingDir, 'torrents')) if os.path.isfile( os.path.join( workingDir, 'torrents', n ) )]:
        os.remove( f )
    
    # Copy datafiles if given
    for d in datadirs:
        for f in [f for f in os.listdir(d)]:
            p = os.path.join(d, f)
            if os.path.isdir(p):
                shutil.copytree(p, os.path.join(workingDir, 'download_data', f))
            else:
                shutil.copy(p, os.path.join(workingDir, 'download_data'))
    
    # Figure out which port to use
    port=6881
    webport=8090
    while port < 7000:
        try:
            f = os.open( os.path.join( clientDir, 'port_{0}'.format( port ) ), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 600 )
            os.close(f)
        except OSError as e:
            if e.args[0] == 17: # File exists, exclusive port lock attempt failed
                port += 1
                webport += 1
                continue
            raise
        if not ( checkPortOpen(port) and checkPortOpen(webport) ):
            port += 1
            webport += 1
            continue
        break
    if port >= 7000:
        raise Exception( "No port found" )
    
    # Check what type of client we're running
    haveWindows = False
    haveLinux = False
    if os.path.exists( 'utorrent.exe' ):
        haveWindows = True
    if os.path.exists( 'utserver' ):
        haveLinux = True
    if haveWindows and haveLinux:
        print >> sys.stderr, "\n\n\n\nWARNING!!!\nWARNING!!!\nWARNING!!!\nCan't decide which client to use. Using Windows client.\nWARNING!!!\nWARNING!!!\nWARNING!!!\n\n\n"
        haveLinux = False
    if not (haveWindows or haveLinux):
        raise Exception( "ERROR: No client found." ) 
    
    # [Read,] change and save config file
    if haveWindows:
        patchWindowsConfig(port, webport, workingDir, clientDir)
    else:
        patchLinuxConfig(port, webport, workingDir, clientDir)
    
    xvfb_process = None
    utorrent_process = None
    authLoaded = False
    try:
        # Run the client
        if haveWindows:
            runWindowsClient(workingDir, clientDir)
        else:
            runLinuxClient(workingDir, clientDir)
    
        # Log starting time    
        print time.time()
        print >> sys.stderr, time.time()
        print >> sys.stderr, "Client started"
        
        # Start interaction with the client
        interact(webport, metadirs, stopWhenSeeding)
    except Exception as e:
        print >> sys.stderr, e.__str__()
        print >> sys.stderr, traceback.format_exc()
        raise
    finally:
        needSleep = False 
        if utorrent_process:
            try:
                if utorrent_process.poll() is None:
                    utorrent_process.kill()
                    needSleep = True
                else:
                    utorrent_process.communicate()
            except Exception as e:
                print >> sys.stderr, e.__str__()
                print >> sys.stderr, traceback.format_exc()
        if xvfb_process:
            try:
                if xvfb_process.poll() is None:
                    xvfb_process.kill()
                    needSleep = True
                else:
                    xvfb_process.communicate()
            except Exception as e:
                print >> sys.stderr, e.__str__()
                print >> sys.stderr, traceback.format_exc()
        if authLoaded:
            try:
                check_call(["xauth", "remove", ":{0}".format( sn )], shell=True)
            except Exception as e:
                print >> sys.stderr, e.__str__()
                print >> sys.stderr, traceback.format_exc()
        if needSleep:
            time.sleep(1)
            if utorrent_process:
                try:
                    if utorrent_process.poll() is not None:
                        utorrent_process.communicate()
                except Exception as e:
                    print >> sys.stderr, e.__str__()
                    print >> sys.stderr, traceback.format_exc()
            if xvfb_process:
                try:
                    if xvfb_process.poll() is not None:
                        xvfb_process.communicate()
                except Exception as e:
                    print >> sys.stderr, e.__str__()
                    print >> sys.stderr, traceback.format_exc()

if __name__ == '__main__':
    mainFunction()

import sys
import select
import struct
import paramiko
import traceback
import socket
import fcntl
import types

# DEBUG
# SET THE FOLLOWING TO TRUE TO HAVE DEBUG WRITTEN TO YOUR HOMEDIR ON THE MACHINE THE DEMUX IS RUNNING ON:

DODEBUG = False

# /DEBUG

import os
import time

if __name__ != "__main__":
    raise Exception( "Do not import python_ssh_demux. It is a program meant to run on its own." )

if DODEBUG:
    logfile = open( 'demux_log_{0}'.format( os.getpid() ), 'a' )
    zerotime = time.time()

readlist = [sys.stdin]

class Conn:
    io = None
    hostname = None
    client = None
    number = None
    packedNumber = None
    channel = None
    isClosed = False
    
    def __init__(self, io_, hostname_, client_, number_, chan_):
        self.io = io_
        self.hostname = hostname_
        self.client = client_
        self.number = number_
        self.packedNumber = struct.pack( '!I', number_ )
        self.channel = chan_
        self.isClosed = False

connections = {}

def buildReadList():
    # pylint: disable-msg=W0603
    global readlist
    # pylint: enable-msg=W0603
    readlist = [connections[c].channel for c in connections if not connections[c].isClosed] + [sys.stdin]

def log( msg_ ):
    if DODEBUG:
        logfile.write( "{0}: {1}\n".format( (time.time() - zerotime), msg_ ) )
        logfile.flush()

fl_block = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
fl_nonblock = fl_block | os.O_NONBLOCK

preknownopcode = ''

running = True

try:
    while running:
        nodata = True
        s__ = time.time()
        ready = []
        (ready, _, _) = select.select( readlist, [], [], 600 )
        while ready == []:
            # No input found on any channel for 60 seconds; we're dead?
            if time.time() - s__ < 600:
                log( "timeout without timeout? Only {0} seconds passed".format( time.time() - s__ ) )
                (ready, _, _) = select.select( readlist, [], [], 600 )
                continue
            preknownopcode = ''
            fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, fl_nonblock)
            try:
                preknownopcode = sys.stdin.read(1)
            except IOError as e: # Catch resource not available : it's expected, although it shouldn't be thrown by spec /sigh
                if (not type(e.args) == types.TupleType) or e.args[0] != 11:
                    raise
                preknownopcode = ''
            fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, fl_block)
            if preknownopcode != '':
                log( "Timeout, but data available, anyway? Ugh...")
                break
            log( "EXCEPTION: No input, closing" )
            raise Exception( 'No input for 600 seconds, assuming something crashed.' )
        firstGo = True
        while running:
            # try and read data from the mux channel
            opcode = ''
            if preknownopcode != '':
                opcode = preknownopcode
                preknownopcode = ''
            else:
                fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, fl_nonblock)
                try:
                    opcode = sys.stdin.read(1)
                except IOError as e: # Catch resource not available : it's expected, although it shouldn't be thrown by spec /sigh
                    if (not type(e.args) == types.TupleType) or e.args[0] != 11:
                        raise
                    opcode = ''
                fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, fl_block)
            if opcode != '':
                nodata = False
                log( "STDIN: RECV opcode {0}".format( opcode ) )
                if opcode == '':
                    log( "EXCEPTION: EOF?" )
                    raise Exception( 'Empty opcode. EOF?' )
                elif opcode == '\n':
                    # NOP
                    log( "STDIN: NOP \\n" )
                elif opcode == 'N':
                    # NOP
                    log( "STDIN: NOP N")
                elif opcode == '\r':
                    # NOP
                    log( "STDIN: NOP \\r" )
                elif opcode == '+':
                    buf = sys.stdin.read(12)
                    if len(buf) != 12:
                        log( "EXCEPTION: Expected 12 bytes of info on '+', but got {0} bytes".format( len(buf) ) )
                        raise Exception( 'Unexpected EOF on mux channel; expected 12 bytes of connection number and message lengths, received {0} bytes'.format( len(buf) ) )
                    connNumber = struct.unpack( '!I', buf[:4] )[0]
                    hostnameLen = struct.unpack( '!I', buf[4:8] )[0]
                    commandLen = struct.unpack( '!I', buf[8:] )[0]
                    log( "STDIN: RECV decodec connection number {0}, hostname length {1} and command length {2}".format( connNumber, hostnameLen, commandLen ) )
                    hostname = sys.stdin.read(hostnameLen)
                    if len(hostname) != hostnameLen:
                        log( "EXCEPTION: Expected {0} bytes of hostname, but got only {1} bytes: '{2}'".format( hostnameLen, len(hostname), hostname ) )
                        raise Exception( "Unexpected EOF on mux channel; expected {0} bytes of hostname, received {1} bytes: '{2}'".format( hostnameLen, len(hostname), hostname ) )
                    log( "STDIN: RECV hostname {0}".format( hostname ) )
                    command = sys.stdin.read(commandLen)
                    if len(command) != commandLen:
                        log( "EXCEPTION: Expected {0} bytes of command, but got only {1} bytes: '{2}'".format( commandLen, len(command), command ) )
                        raise Exception( "Unexpected EOF on mux channel; expected {0} bytes of command, received {1} bytes: '{2}'".format( commandLen, len(command), command ) )
                    log( "STDIN: RECV command {0}".format( command ) )
                    if connNumber in connections:
                        problem = 'Connection number already used'
                        log( "STDOUT: SEND +-{0}{1}".format( struct.pack( '!I', len(problem) ), problem ) )
                        sys.stdout.write( '+-{0}{1}'.format( struct.pack( '!I', len(problem) ), problem ) )
                        sys.stdout.flush()
                    else:
                        try:
                            client = paramiko.SSHClient()
                            client.load_system_host_keys()
                            try:
                                client.connect( hostname )
                            except paramiko.BadHostKeyException:
                                raise Exception( "Bad host key for node {0}. Please make sure the host key is already known to the DAS4 headnode system. The easiest way is usually to just manually use ssh to connect to the remote host once and save the host key.".format( hostname ) )
                            except paramiko.AuthenticationException:
                                raise Exception( "Could not authenticate to node {0}. This is strange, please see if you can SSH from the DAS4 headnode to other nodes without interaction.".format( hostname ) )
                            trans = client.get_transport()
                            chan = trans.open_session()
                            chan.set_combine_stderr( True )
                            chan.exec_command( command )
                            chan.setblocking(False)
                            io = (chan.makefile( 'wb', -1 ), chan.makefile( 'rb', -1 ), chan)
                            obj = Conn(io, hostname, client, connNumber, chan)
                            connections[connNumber] = obj
                            buildReadList()
                            log( "STDOUT: SEND ++" )
                            sys.stdout.write( '++' )
                            sys.stdout.flush()
                        except Exception as e:
                            problem = e.__str__() + '\n' + traceback.format_exc()
                            log( "STDOUT: SEND +-{0}{1}".format( struct.pack( '!I', len(problem) ), problem ) )
                            sys.stdout.write( '+-{0}{1}'.format( len(problem), problem ) )
                            sys.stdout.flush()
                elif opcode == '-':
                    buf = sys.stdin.read(4)
                    if len(buf) != 4:
                        log( "EXCEPTION: Expected 4 bytes of connection number, got only {0} bytes".format( len(buf) ) )
                        raise Exception( 'Unexpected EOF on mux channel; expected 4 bytes of connection number, received {0} bytes'.format( len(buf) ) )
                    connNumber = struct.unpack( '!I', buf )[0]
                    log( "STDIN: RECV decoded connection number {0}".format( connNumber ) )
                    if connNumber in connections:
                        try:
                            del connections[connNumber].io
                            connections[connNumber].client.close()
                            del connections[connNumber].client
                            del connections[connNumber]
                        except Exception:
                            pass
                    buildReadList()
                    log( "STDOUT: SEND -{0}".format( buf ) )
                    sys.stdout.write( '-{0}'.format( buf ) )
                    sys.stdout.flush()
                elif opcode == '0' or opcode == '1':
                    buf = sys.stdin.read(4)
                    if len(buf) != 4:
                        log( "EXCEPTION: Expected 4 bytes of connection number, got only {0} bytes".format( len(buf) ) )
                        raise Exception( 'Unexpected EOF on mux channel; expected 4 bytes of connection number, received {0} bytes'.format( len(buf) ) )
                    connNumber = struct.unpack( '!I', buf )[0]
                    log( "STDIN: RECV decoded connection number {0}".format( connNumber ) )
                    if opcode == '0':
                        buf = sys.stdin.readline()
                        if buf == '' or buf[-1] != '\n':
                            log( "EXCEPTION: Excepted a single line, received '{0}'".format( buf ) )
                            raise Exception( "Unexpected EOF on mux channel; expected a single line, received '{0}'".format( buf ) )
                        log( "STDIN: RECV data '{0}'".format( buf ) )
                    else:
                        buf = sys.stdin.read(4)
                        if len(buf) != 4:
                            log( "EXCEPTION: Expected 4 bytes data length, got only {0} bytes".format( len(buf) ) )
                            raise Exception( 'Unexpected EOF on mux channel; expected 4 bytes of data length, received {0} bytes'.format( len(buf) ) )
                        datalen = struct.unpack( '!I', buf )[0]
                        log( "STDIN: RECV decoded data length {0}".format( datalen ) )
                        buf = sys.stdin.read(datalen)
                        if len(buf) != datalen:
                            log( "EXCEPTION: Expected {0} bytes of data, got only {1}: '{2}'".format( datalen, len(buf), buf ) )
                            raise Exception( "Unexpected EOF on mux channel; expected {0} bytes of data, received {1} bytes: '{2}'".format( datalen, len(buf), buf ) )
                        log( "STDIN: RECV data '{0}'".format( buf ) )
                    if connNumber in connections:
                        connections[connNumber].channel.setblocking(True)
                        log( "CONN {0}: SEND {1}".format( connNumber, buf ) )
                        try:
                            #connections[connNumber].io[0].write( buf )
                            #connections[connNumber].io[0].flush()
                            connections[connNumber].io[2].sendall( buf )
                            connections[connNumber].channel.setblocking(False)
                        except Exception as e:
                            log( "CONN {0}: EXCEPT {1}".format( connNumber, e.__str__() + '\n' + traceback.format_exc() ))
                            packedNumber = connections[connNumber].packedNumber
                            try:
                                del connections[connNumber].io
                                connections[connNumber].client.close()
                                del connections[connNumber].client
                                del connections[connNumber]
                            except Exception:
                                pass
                            buildReadList()
                            log( "STDOUT: SEND -{0}".format( packedNumber ) )
                            sys.stdout.write( '-{0}'.format( packedNumber ) )
                            sys.stdout.flush()
                    else:
                        log( "EXCEPTION: Unknown connection {0}".format( connNumber ) )
                        raise Exception( "Received data for unknown connection {0}: '{1}'".format( connNumber, buf ))
                elif opcode == 'X':
                    log( "STDIN: QUIT" )
                    running = False
                    break
                else:
                    log( "EXCEPTION: Unknown opcode {0}".format( opcode ) )
                    raise Exception( "Unknown opcode {0} on mux channel".format( opcode ) )
            elif not firstGo:
                break
            for connN in connections:
                conn = connections[connN]
                if conn.channel.recv_ready():
                    nodata = False
                    buf = ''
                    closed = False
                    while True:
                        try:
                            buf2 = conn.channel.recv(1024)
                        except socket.timeout:
                            break
                        log( "CONN {0}: RECV '{1}'".format( connN, buf2 ) )
                        if buf2 == '':
                            closed = True
                        buf += buf2
                        if len(buf2) < 1024:
                            break
                    if buf.find('\n') == len(buf) - 1:
                        log( "STDOUT: SEND {1}".format( connN, '0{0}{1}'.format( conn.packedNumber, buf ) ) )
                        sys.stdout.write( '0{0}{1}'.format( conn.packedNumber, buf ) )
                    else:
                        log( "STDOUT: SEND {1}".format( connN, '1{0}{1}{2}'.format( conn.packedNumber, struct.pack( '!I', len(buf) ), buf ) ) )
                        sys.stdout.write( '1{0}{1}{2}'.format( conn.packedNumber, struct.pack( '!I', len(buf) ), buf ) )
                    if closed:
                        log( "STDOUT: SEND -{0}".format( conn.packedNumber ) )
                        sys.stdout.write( '-{0}'.format( conn.packedNumber ) )
                        conn.isClosed = True
                        buildReadList()
                    sys.stdout.flush()
            firstGo = False
        if nodata:
            log( "EXCEPTION: No data received, while ready signalled?" )
            raise Exception( "No data was received, while ready was signalled. Assuming failure or end of life. Breaking down for safety." )
            
except Exception as e:
    msg = e.__str__() + '\n' + traceback.format_exc()
    log( "STDOUT: SEND X{0}{1}".format( struct.pack( '!I', len(msg) ), msg ) )
    sys.stdout.write( 'X{0}{1}'.format( struct.pack( '!I', len(msg) ), msg ) )
    sys.stdout.flush()

if DODEBUG:
    logfile.close()

dellist = [connNumber for connNumber in connections]
for connNumber in dellist:
    try:
        del connections[connNumber].io
        connections[connNumber].client.close()
        del connections[connNumber].client
        del connections[connNumber]
    except Exception:
        pass
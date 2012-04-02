from core.parsing import containsSpace, isPositiveInt
from core.campaign import Campaign
from core.host import host, countedConnectionObject

import getpass
import threading
import errno
import os
import stat
from subprocess import Popen, STDOUT, PIPE
import subprocess
from binascii import hexlify
import time
import sys

paramiko = None
try:
    paramiko = __import__('paramiko', globals(), locals() )
except ImportError:
    Campaign.logger.log( "Warning! You are using host:ssh without the paramiko packages installed. This is supported, but definitely not ideal. Please install the paramiko packages to have a much more effective host:ssh." )
    print "Warning! You are using host:ssh without the paramiko packages installed. This is supported, but definitely not ideal. Please install the paramiko packages to have a much more effective host:ssh."
    paramiko = None
    
def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for host object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class sshFallbackConnectionObject(countedConnectionObject):
    """
    SSH connection object for fallback connections (no paramiko available)
    """
    
    # @static
    sshProgram = None
    # @static
    scpProgram = None
    
    proc = None             # The remote bash process (Popen object)
    
    def __init__(self, proc):
        countedConnectionObject.__init__(self)
        self.proc = proc
        
    def close(self):
        countedConnectionObject.close(self)
        self.proc.stdin.close()
        self.proc.stdout.close()
        del self.proc
        self.proc = None
    
    def write(self, msg):
        self.proc.stdin.write( msg )
        self.proc.stdin.flush()
    
    def readline(self):
        line = self.proc.stdout.readline()
        return line
    
    @staticmethod
    def getSSHProgram():
        if not sshFallbackConnectionObject.sshProgram:
            if os.path.exists( '/bin/ssh' ):
                sshFallbackConnectionObject.sshProgram = '/bin/ssh'
            elif os.path.exists( '/usr/bin/ssh' ):
                sshFallbackConnectionObject.sshProgram = '/usr/bin/ssh'
            else:
                out, _ = Popen( 'which ssh', stdout = PIPE, shell = True ).communicate()
                if out is None or out == '' or not os.path.exists( 'out' ):
                    raise Exception( "host:ssh requires either the paramiko modules (preferred) or ssh command line utility to be present" )
                sshFallbackConnectionObject.sshProgram = out
        return sshFallbackConnectionObject.sshProgram
    
    @staticmethod
    def getSCPProgram():
        if not sshFallbackConnectionObject.scpProgram:
            if os.path.exists( '/bin/scp' ):
                sshFallbackConnectionObject.scpProgram = '/bin/scp'
            elif os.path.exists( '/usr/bin/scp' ):
                sshFallbackConnectionObject.scpProgram = '/usr/bin/scp'
            else:
                out, _ = Popen( 'which scp', stdout = PIPE, shell = True ).communicate()
                if out is None or out == '' or not os.path.exists( 'out' ):
                    raise Exception( "host:ssh requires either the paramiko modules (preferred) or scp command line utility to be present" )
                sshFallbackConnectionObject.scpProgram = out
        return sshFallbackConnectionObject.scpProgram
    
    @staticmethod
    def existsRemote(useHost, connection, remotePath):
        res = useHost.sendCommand('[ -e "{0}" ] && echo "Y" || echo "N"'.format( remotePath ), connection)
        if len(res) == 0:
            raise Exception( "No reply from host {0} when querying existence of file {1}".format( useHost.name, remotePath ) )
        return res[0] == 'Y'

    @staticmethod
    def isRemoteDir(useHost, connection, remotePath):
        res = useHost.sendCommand('[ -d "{0}" ] && echo "Y" || echo "N"'.format( remotePath ), connection)
        if len(res) == 0:
            raise Exception( "No reply from host {0} when querying whether this is a directory: {1}".format( useHost.name, remotePath ) )
        return res[0] == 'Y'

class sshParamikoConnectionObject(countedConnectionObject):
    """
    SSH connection object for paramiko connections
    """
    
    client = None
    io = None
    
    sftpChannel = None
    sftp__lock = None
    
    def __init__(self, client, io ):
        countedConnectionObject.__init__(self)
        self.client = client
        self.sftp__lock = threading.Lock()
        self.io = io
    
    def close(self):
        countedConnectionObject.close(self)
        try:
            self.sftp__lock.acquire()
            if self.sftpChannel:
                self.sftpChannel.close()
                Campaign.debuglogger.log( self.getIdentification(), 'SFTP CHANNEL REMOVED DURING CLOSE' )
                del self.sftpChannel
                self.sftpChannel = None
        finally:
            self.sftp__lock.release()
            self.client.close()
            del self.client
            self.client = None
            Campaign.debuglogger.closeChannel( self.getIdentification() )
    
    def write(self, msg):
        self.io[0].write( msg )
        self.io[0].flush()
    
    def readline(self):
        line = self.io[1].readline()
        return line
    
    def createSFTPChannel(self):
        if self.isClosed():
            raise Exception( "Can't create an SFTP channel for a closed SSH connection on connection {0}".format( self.getIdentification( ) ) )
        try:
            self.sftp__lock.acquire()
            if self.sftpChannel:
                return True
            self.sftpChannel = self.client.open_sftp()
            Campaign.debuglogger.log( self.getIdentification(), 'SFTP CHANNEL CREATED' )
        finally:
            self.sftp__lock.release()
        return False
    
    def removeSFTPChannel(self):
        if self.isClosed():
            return
        try:
            self.sftp__lock.acquire()
            if not self.sftpChannel:
                return
            self.sftpChannel.close()
            del self.sftpChannel
            self.sftpChannel = None
            Campaign.debuglogger.log( self.getIdentification(), 'SFTP CHANNEL REMOVED' )
        finally:
            self.sftp__lock.release()
    
    @staticmethod
    def existsRemote(sftp, remotePath):
        found = True
        try:
            sftp.stat( remotePath )
        except IOError as e:
            found = False
            if not e.errno == errno.ENOENT:
                raise e
        return found

    @staticmethod
    def isRemoteDir(sftp, remotePath):
        attribs = sftp.stat(remotePath)
        return stat.S_ISDIR( attribs.st_mode )

class sshWarnHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    allowedKeys = {}
    disallowing = False
    
    def __init__(self):
        paramiko.MissingHostKeyPolicy.__init__(self)
    
    def missing_host_key(self, client, hostname, key):
        if sshWarnHostKeyPolicy.disallowing:
            raise Exception( "Key {0} for host {1} disallowed: Not allowing any new keys after one was disallowed.".format( hexlify( key.get_fingerprint() ), hostname ) )
        if hostname in sshWarnHostKeyPolicy.allowedKeys:
            if sshWarnHostKeyPolicy.allowedKeys[hostname] != key.get_fingerprint():
                print "!!! ERROR !!! ERROR !!!"
                print "Host {0} was allowed with key {1} earlier during this session, but now it suddenly has key {2}. Disallowing.".format( hostname, hexlify(sshWarnHostKeyPolicy.allowedKeys[hostname]), hexlify(key.get_fingerprint()) )
                print "This means something is seriously wrong."
                print "!!! ERROR !!! ERROR !!!"
                Campaign.logger.log( "ERROR! paramiko: Disallowing unknown SSH key {2} for hostname {0}, since it already had key {1} before. This means something is seriously wrong.".format( hostname, hexlify(sshWarnHostKeyPolicy.allowedKeys[hostname]), hexlify(key.get_fingerprint()) ) )
            else:
                return
        try:
            print "!!! WARNING !!! WARNING !!!"
            print "paramiko could not verify the following host key using the loaded system host keys: "
            print "host: {0}".format(hostname)
            print "key:  {0}".format(hexlify(key.get_fingerprint()))
            print "The key will be added and allowed for the current session in 10 seconds."
            print "Press Ctrl+C to abort."
            print "!!! WARNING !!! WARNING !!!"
            print "5",
            sys.stdout.flush()
            time.sleep(1)
            print "4",
            sys.stdout.flush()
            time.sleep(1)
            print "3",
            sys.stdout.flush()
            time.sleep(1)
            print "2",
            sys.stdout.flush()
            time.sleep(1)
            print "1",
            sys.stdout.flush()
            time.sleep(1)
            print "Allowing"
            client.get_host_keys().add( hostname, key.get_name(), key )
            Campaign.logger.log( "WARNING! paramiko: Allowing unknown SSH key {0} for hostname {1}".format( hexlify(key.get_fingerprint()), hostname ) )
            sshWarnHostKeyPolicy.allowedKeys[hostname] = key.get_fingerprint()
        except KeyboardInterrupt as e:
            print "Rejecting"
            sshWarnHostKeyPolicy.disallowing = True
            raise e

class ssh(host):
    """
    The SSH implementation of the host object.
    
    Extra parameters:
    - hostname      The hostname of the host to be used over SSH. Hostnames and IP addresses are accepted.
    - port          The port on which the SSH daemon listens on the host; optional, defaults to 22.
    - user          The user name to be used for logging in over SSH.
    """

    hostname = None     # The hostname to connect to
    port = None         # The port to use
    user = None         # The username to use

    def __init__(self, scenario):
        """
        Initialization of a generic host object.
        
        @param  scenario        The ScenarioRunner object this host object is part of.
        """
        host.__init__(self, scenario)

    def parseSetting(self, key, value):
        """
        Parse a single setting for this object.

        Settings are written in text files in a key=value fashion.
        For each such setting that belongs to this object this method will be called.

        After all settings have been given, the method checkSettings will be called.

        If a setting does not parse correctly, this method raises an Exception with a descriptive message.

        Subclassers should first parse their own settings and then call this implementation to have the
        generic settings parsed and to have any unknown settings raise an Exception.
        
        @param  key     The name of the parameter, i.e. the key from the key=value pair.
        @param  value   The value of the parameter, i.e. the value from the key=value pair.
        """
        if key == 'hostname':
            if self.hostname:
                parseError( "The hostname was already set: {0}".format( self.hostname ) )
            if containsSpace( value ):
                parseError( "A hostname must not contain spaces" )
            self.hostname = value
        elif key == 'port':
            if self.port:
                parseError( "The port was already set: {0}".format( self.port ) )
            if not isPositiveInt( value, True ):
                parseError( "The port must be a positive, non-zero integer" )
            self.port = value
        elif key == 'user':
            if self.user:
                parseError( "The user was already set: {0}".format( self.user ) )
            self.user = value
        else:
            host.parseSetting(self, key, value)            

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        host.checkSettings(self)
        if not self.hostname:
            raise Exception( "The hostname parameter to an SSH connection is required" )
        if not self.port:
            self.port = 22
        if not paramiko and not self.user:
            self.user = getpass.getuser()

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        host.resolveNames(self)

    def setupNewConnection(self):
        """
        Create a new connection to the host.

        The returned object has no specific type, but should be usable as a connection object either by uniquely identifying it or 
        simply by containing the needed information for it.

        Connections created using this function can be closed with closeConnection(...). When cleanup(...) is called all created
        connections will automatically closed and, hence, any calls using those connections will then fail.

        @return The connection object for a new connection. This should be an instance of a subclass of core.host.connectionObject.
        """
        if self.isInCleanup():
            return
        if paramiko:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(sshWarnHostKeyPolicy())
            client.load_system_host_keys()
            try:
                client.connect( self.hostname, port = self.port, username = self.user )
            except paramiko.BadHostKeyException:
                raise Exception( "Bad host key for host {0}. Please make sure the host key is already known to the system. The easiest way is usually to just manually use ssh to connect to the remote host once and save the host key.".format( self.name ) )
            except paramiko.AuthenticationException:
                raise Exception( "Could not authenticate to host {0}. Please make sure that authentication can proceed without user interaction, e.g. by loading an SSH agent or using unencrypted keys.".format( self.name ) )
            trans = client.get_transport()
            chan2 = trans.open_session()
            chan2.set_combine_stderr( True )
            chan2.exec_command( 'bash -l' )
            io = (chan2.makefile( 'wb', -1 ), chan2.makefile( 'rb', -1 ) )
            obj = sshParamikoConnectionObject( client, io )
            Campaign.debuglogger.log( obj.getIdentification(), 'CREATED in scenario {2} for SSH host {0} to node {1} type paramiko'.format( self.name, self.hostname, self.scenario.name ) )
        else:
            args = ['{0}'.format(sshFallbackConnectionObject.getSSHProgram()), '-l', self.user]
            if self.port:
                args.append( '-p' )
                args.append( '{0}'.format( self.port ) )
            args.append( self.hostname )
            proc = Popen(args, bufsize=8192, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
            if self.isInCleanup():
                try:
                    proc.communicate( 'exit' )
                except OSError as e:
                    if not e.errno == errno.EPIPE: # This one is expected
                        raise e
                return
            obj = sshFallbackConnectionObject( proc )
            Campaign.debuglogger.log( obj.getIdentification(), 'CREATED in scenario {2} for SSH host {0} to node {1} type fallback'.format( self.name, self.hostname, self.scenario.name ) )
        try:
            self.connections__lock.acquire()
            if self.isInCleanup():
                obj.close()
                return
            self.connections.append( obj )
        finally:
            try:
                self.connections__lock.release()
            except RuntimeError:
                pass
        # The 'cd' below is absolutely necessary to make sure that automounts and stuff work correctly
        res = self.sendCommand('cd; echo "READY"', obj )
        if not res[-5:] == "READY":
            raise Exception( "Connection to host {0} seems not to be ready after it has been made. Reponse: {1}".format( self.name, res ) )
        return obj

    def closeConnection(self, connection):
        """
        Close a previously created connection to the host.

        Any calls afterwards to methods of this host with the close connection will fail.
        
        The default implementation will close the connection if it wasn't already closed
        and remove it from self.connections.

        @param  The connection to be closed.
        """
        Campaign.debuglogger.closeChannel(connection.getIdentification())
        host.closeConnection(self, connection)

    def sendCommand(self, command, reuseConnection = True):
        """
        Sends a bash command to the remote host.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     True for commands that are shortlived or are expected not to be parallel with other commands.
                                    False to build a new connection for this command and use that.
                                    A specific connection object as obtained through setupNewConnection(...) to reuse that connection.

        @return The result from the command. The result is stripped of leading and trailing whitespace before being returned.
        """
        connection = None
        try:
            connection = self.getConnection(reuseConnection)
            # Send command
            self.sendCommandAsyncStart(command, connection)
            # Read output of command
            return self.sendCommandAsyncEnd(connection)
        finally:
            self.releaseConnection(reuseConnection, connection)
    
    def sendCommandAsyncStart(self, command, reuseConnection):
        """
        Sends a bash command to the remote host without waiting for the answer.
        
        Note that it is imperative that you call sendCommandAsyncEnd(...) after this call, or you will screw up your connection!

        Be sure to call connection.setInAsync() as well.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
                                    Contrary to other methods True of False are explicitly not accepted.
        """
        connection = None
        try:
            connection = self.getConnection(reuseConnection)
            if connection.isInAsync():
                Campaign.logger.log( "WARNING! Connection {0} of host {1} started an async command, but an async command was still running.".format( connection.getIdentification(), self.name ), True )
                Campaign.logger.localTraceback( True )
                res = self.sendCommandAsyncEnd(connection)
                Campaign.logger.log( "WARNING! Output of ending the connection: {0}".format( res ), True )
                connection.outOfOrderResult = res
            connection.write( command+'\n# `\n# \'\n# "\necho "\nblabladibla__156987349253457979__noonesGonnaUseThis__right__p2ptestframework"\n' )
            connection.setInAsync()
            Campaign.debuglogger.log( connection.getIdentification(), 'SEND {0}'.format( command ) )
        finally:
            self.releaseConnection(reuseConnection, connection)

    def sendCommandAsyncEnd(self, reuseConnection):
        """
        Retrieves the response to a bash command to the remote host that was sent earlier on.
        
        Note that this must not be called other than directly after sendCommandAsyncStart(...).
        Do not call on just any connection or you will screw it up!

        Be sure to call connection.clearInAsync() as well.

        @param  reuseConnection     A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
                                    Contrary to other methods True of False are explicitly not accepted.
        
        @return The result from the command. The result is stripped of leading and trailing whitespace before being returned.
        """
        connection = None
        try:
            connection = self.getConnection(reuseConnection)
            if not connection.isInAsync():
                Campaign.logger.log( "WARNING! Connection {0} of host {1} ended an async command, but none was running. Returning ''.".format( connection.getIdentification(), self.name ), True )
                Campaign.logger.localTraceback(True)
                res = connection.outOfOrderResult
                connection.outOfOrderResult = ''
                return res
            res = ''
            line = connection.readline()
            while line != '' and line.strip() != 'blabladibla__156987349253457979__noonesGonnaUseThis__right__p2ptestframework':
                Campaign.debuglogger.log( connection.getIdentification(), 'RECV {0}'.format( line ) )
                res += line
                line = connection.readline()
            connection.clearInAsync()
            # Return output (ditch the last trailing \n)
            return res.strip()
        finally:
            self.releaseConnection(reuseConnection, connection)
            
    def sendFile(self, localSourcePath, remoteDestinationPath, overwrite = False, reuseConnection = True):
        """
        Sends a file to the remote host.

        Regarding reuseConnection it is possible the value may be ignored: a new connection may be needed for file transfer, anyway.

        @param  localSourcePath         Path to the local file that is to be sent.
        @param  remoteDestinationPath   Path to the destination file on the remote host.
        @param  overwrite               Set to True to not raise an Exception if the destination already exists.
        @param  reuseConnection         True to try and reuse the default connection for sending the file.
                                        False to build a new connection for sending this file and use that.
                                        A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
        """
        if paramiko:
            connection = None
            try:
                connection = self.getConnection(reuseConnection)
                newConnection = connection.createSFTPChannel()
                try:
                    sftp = connection.sftpChannel
                    if sshParamikoConnectionObject.existsRemote(sftp, remoteDestinationPath):
                        if not overwrite: 
                            raise Exception( "Sending file {0} to {1} on host {2} without allowing overwrite, but the destination already exists".format( localSourcePath, remoteDestinationPath, self.name ) )
                        elif sshParamikoConnectionObject.isRemoteDir(sftp, remoteDestinationPath):
                            raise Exception( "Sending file {0} to {1} on host {2} with overwrite, but the destination already exsits and is a directory".format( localSourcePath, remoteDestinationPath, self.name ) )
                    if self.isInCleanup():
                        return
                    Campaign.debuglogger.log( connection.getIdentification(), 'SFTP SEND FILE {0} TO {1}'.format( localSourcePath, remoteDestinationPath ) )
                    sftp.put( localSourcePath, remoteDestinationPath )
                    sftp.chmod( remoteDestinationPath, os.stat(localSourcePath).st_mode )
                finally:
                    if newConnection:
                        connection.removeSFTPChannel()
            finally:
                self.releaseConnection(reuseConnection, connection)
        else:
            connection = reuseConnection
            if connection == False:
                connection = self.setupNewConnection()
            try:
                if sshFallbackConnectionObject.existsRemote(self, connection, remoteDestinationPath):
                    if not overwrite:
                        raise Exception( "Sending file {0} to {1} on host {2} without allowing overwrite, but the destination already exists".format( localSourcePath, remoteDestinationPath, self.name ) )
                    elif sshFallbackConnectionObject.isRemoteDir(self, connection, remoteDestinationPath):
                        raise Exception( "Sending file {0} to {1} on host {2} with overwrite, but the destination already exsits and is a directory".format( localSourcePath, remoteDestinationPath, self.name ) )
                if self.isInCleanup():
                    return
                args = ['{0}'.format(sshFallbackConnectionObject.getSCPProgram())]
                if self.port:
                    args.append( '-P' )
                    args.append( '{0}'.format( self.port ) )
                args.append( localSourcePath )
                args.append( '{0}@{1}:{2}'.format( self.user, self.hostname, remoteDestinationPath ) )
                try:
                    Campaign.debuglogger.log( connection.getIdentification(), 'SCP SEND FILE {0} TO {1}'.format( localSourcePath, remoteDestinationPath ) )
                    subprocess.check_output( args, bufsize=8192 )
                except subprocess.CalledProcessError as e:
                    Campaign.logger.log( "Sending file {1} to {2} on host {0} failed: {3}".format( self.name, localSourcePath, remoteDestinationPath, e.output ) )
                    raise e
                localMode = os.stat(localSourcePath).st_mode
                # The three localMode expressions extract the octal values for the user, group and other parts of the mode
                self.sendCommand( 'chmod {0}{1}{2} "{3}"'.format( (localMode & 0x1C0) / 0x40, (localMode & 0x38) / 0x8, localMode & 0x7, remoteDestinationPath ), connection )
            finally:
                if reuseConnection == False:
                    self.closeConnection(connection)
    
    def sendFiles(self, localSourcePath, remoteDestinationPath, reuseConnection = True):
        """
        Sends a directory to the remote host.

        This will recursively send the local directory and all its contents to the remote host.

        Example:    sendFiles( '/home/me/myLocalDir', '/tmp/myTmpDir/newRemoteDir' )
        If newRemoteDir does not already exist then it will be created. A file /home/me/myLocalDir/x will end up
        on the remote host as /tmp/myTmpDir/newRemoteDir/x .

        This method will always overwrite existing files.

        Regarding reuseConnection it is possible the value may be ignored: a new connection may be needed for file transfer, anyway.

        The default implementation will recursively call sendFile or sendFiles on the contents of the
        local directory.

        @param  localSourcePath         Path to the local directory that is to be sent.
        @param  remoteDestinationPath   Path to the destination directory on the remote host.
        @param  reuseConnection         True to try and reuse the default connection for sending the file.
                                        False to build a new connection for sending this file and use that.
                                        A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
        """
        if paramiko:
            connection = None
            try:
                connection = self.getConnection(reuseConnection)
                newConnection = connection.createSFTPChannel()
                try:
                    sftp = connection.sftpChannel
                    paths = [(localSourcePath, remoteDestinationPath)]
                    while len(paths) > 0:
                        localPath, remotePath = paths.pop()
                        if self.isInCleanup():
                            return
                        if os.path.isdir( localPath ):
                            if not sshParamikoConnectionObject.existsRemote(sftp, remotePath):
                                Campaign.debuglogger.log( connection.getIdentification(), 'SFTP CREATE REMOTE DIR {0}'.format( remotePath ) )
                                sftp.mkdir( remotePath )
                                sftp.chmod( remotePath, os.stat(localPath).st_mode )
                            paths += [(os.path.join( localPath, path ), '{0}/{1}'.format( remotePath, path )) for path in os.listdir( localPath )]
                        else:
                            if sshParamikoConnectionObject.existsRemote(sftp, remotePath) and sshParamikoConnectionObject.isRemoteDir(sftp, remotePath):
                                raise Exception( "Sending file {0} to {1} on host {2} with overwrite, but the destination already exsits and is a directory".format( localPath, remotePath, self.name ) )
                            Campaign.debuglogger.log( connection.getIdentification(), 'SFTP SEND FILE {0} TO {1}'.format( localPath, remotePath ) )
                            sftp.put( localPath, remotePath )
                            sftp.chmod( remotePath, os.stat(localPath).st_mode )
                finally:
                    if newConnection:
                        connection.removeSFTPChannel()
            finally:
                self.releaseConnection(reuseConnection, connection)
        else:
            if reuseConnection == False:
                connection = self.setupNewConnection()
                try:
                    host.sendFiles(self, localSourcePath, remoteDestinationPath, connection)
                finally:
                    self.closeConnection(connection)
            else:
                host.sendFiles(self, localSourcePath, remoteDestinationPath, reuseConnection)

    def getFile(self, remoteSourcePath, localDestinationPath, overwrite = False, reuseConnection = True):
        """
        Retrieves a file from the remote host.

        Regarding reuseConnection it is possible the value may be ignored: a new connection may be needed for file transfer, anyway.

        @param  remoteSourcePath        Path to the file to be retrieved on the remote host.
        @param  localDestinationPath    Path to the local destination file.
        @param  overwrite               Set to True to not raise an Exception if the destination already exists.
        @param  reuseConnection         True to try and reuse the default connection for sending the file.
                                        False to build a new connection for sending this file and use that.
                                        A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
        """
        if os.path.exists( localDestinationPath ):
            if not overwrite:
                raise Exception( "Getting file {0} to {1} from host {2} without allowing overwrite, but the destination already exists".format( remoteSourcePath, localDestinationPath, self.name ) )
            elif os.path.isdir( localDestinationPath ):
                raise Exception( "Getting file {0} to {1} from host {2} with overwrite, but the destination already exists and is a directory".format( remoteSourcePath, localDestinationPath, self.name ) )
        if self.isInCleanup():
            return
        if paramiko:
            connection = None
            try:
                connection = self.getConnection(reuseConnection)
                newConnection = connection.createSFTPChannel()
                try:
                    sftp = connection.sftpChannel
                    if self.isInCleanup():
                        return
                    Campaign.debuglogger.log( connection.getIdentification(), 'SFTP RETRIEVE FILE {0} TO {1}'.format( remoteSourcePath, localDestinationPath ) )
                    sftp.get( remoteSourcePath, localDestinationPath )
                finally:
                    if newConnection:
                        connection.removeSFTPChannel()
            finally:
                self.releaseConnection(reuseConnection, connection)
        else:
            args = ['{0}'.format(sshFallbackConnectionObject.getSCPProgram())]
            if self.port:
                args.append( '-P' )
                args.append( '{0}'.format( self.port ) )
            args.append( '{0}@{1}:{2}'.format( self.user, self.hostname, remoteSourcePath ) )
            args.append( localDestinationPath )
            try:
                Campaign.debuglogger.log( connection.getIdentification(), 'SCP RETRIEVE FILE {0} TO {1}'.format( remoteSourcePath, localDestinationPath ) )
                subprocess.check_output( args, bufsize=8192 )
            except subprocess.CalledProcessError as e:
                Campaign.logger.log( "Retrieving file {1} to {2} from host {0} failed: {3}".format( self.name, remoteSourcePath, localDestinationPath, e.output ) )
                raise e

    def prepare(self):
        """
        Execute commands on the remote host needed for host specific preparation.

        The default implementation simply ensures the existence of a remote directory.
        """
        host.prepare(self)

    def cleanup(self, reuseConnection = None):
        """
        Executes commands to do host specific cleanup.
        
        The default implementation removes the remote temporary directory, if one was created.

        Subclassers are advised to first call this implementation and then proceed with their own steps.
        
        @param  reuseConnection If not None, force the use of this connection object for commands to the host.
        """
        host.cleanup(self, reuseConnection)

    def getSubNet(self):
        """
        Return the subnet of the external addresses of the host.

        @return The subnet of the host(s).
        """
        return self.hostname

    def getAddress(self):
        """
        Return the single address (IP or hostname) of the remote host, if any.

        An obvious example of this method returning '' would be a host implementation that actually uses a number
        of remote hosts in one host object: one couldn't possibly return exactly one address for that and be
        correct about it in the process.

        Default implementation just returns ''.

        @return The address of the remote host, or '' if no such address can be given.
        """
        return self.hostname

    @staticmethod
    def APIVersion():
        return "2.2.0"

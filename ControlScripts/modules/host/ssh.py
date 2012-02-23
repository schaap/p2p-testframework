from core.parsing import containsSpace, isPositiveInt
from core.campaign import Campaign
from core.host import host, countedConnectionObject

import getpass
import threading
import errno
import os
import stat
from subprocess import Popen, STDOUT, PIPE

paramiko = None
try:
    paramiko = __import__('paramiko', globals(), locals() )
except ImportError:
    paramiko = None
    
def design():
    """
    This function is just here for easier comment writing.
    
Given paramiko:
- reading a key for connecting to the host given an SSH agent is a matter of:
    try:
        agent = paramiko.Agent()
        key = agent.get_keys()
        agent.close()
    except SSHException: # incompatible protocol
        keys = []
- reading a key for connecting to the host is a matter of:
    try:
        key = paramiko.DSSKey.from_private_key_file( filename )
    except paramiko.SSHException:
        try:
            key = paramiko.RSAKey.from_private_key_file( filename )
        except paramiko.SSHException:
            raise Exception( "Key in {0} is not a valid DSS or RSA key.".format( filename ) )
        except paramiko.PasswordRequiredException:
            raise Exception( "Encrypted keys are not supported." )
    except paramiko.PasswordRequiredException:
        raise Exception( "Encrypted keys are not supported." )
- reading the known_hosts into paramiko is a matter of:
    try:
        hostkeys = paramiko.HostKeys( filename )
    except IOError:
        hostkeys = paramiko.HostKeys()
- using saved configuration is a matter of:
    sshConfig = paramiko.SSHConfig()
    sshConfig.parse( filename )
    configurationDict = sshConfig.lookup( hostname )
    
    """
    pass

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
    
    def __init__(self):
        countedConnectionObject.__init__(self)
    
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

class sshParamikoConnectionObject(countedConnectionObject):
    """
    SSH connection object for paramiko connections
    """
    
    client = None
    interactiveChannel = None
    io = None
    
    sftpChannel = None
    sftp__lock = None
    
    def __init__(self, client, interactiveChannel, io ):
        countedConnectionObject.__init__(self)
        self.client = client
        self.interactiveChannel = interactiveChannel
        self.sftp__lock = threading.Lock()
        self.io = io
    
    def close(self):
        try:
            countedConnectionObject.close(self)
        finally:
            try:
                self.sftp__lock.acquire()
                if self.sftpChannel:
                    self.sftpChannel.close()
                    del self.sftpChannel
                    self.sftpChannel = None
            finally:
                self.sftp__lock.release()
                try:
                    self.interactiveChannel.shutdown( 2 )
                    self.interactiveChannel.close()
                    del self.interactiveChannel
                    self.interactiveChannel = None
                except Exception:
                    self.client.close()
                    del self.client
                    self.client = None
    
    def write(self, msg):
        #self.interactiveChannel.sendall( msg )
        print "DEBUG: CONN {0} SEND:\n{1}".format( self.getIdentification(), msg )
        self.io[0].write( msg )
        self.io[0].flush()
    
    def readline(self):
        #res = ''
        #while True:
        #    read = self.interactiveChannel.recv(1)
        #    res += read
        #    if read == '\n':
        #        return res
        line = self.io[1].readline()
        print "DEBUG: CONN {0} READLINE:\n{1}".format( self.getIdentification(), line )
        return line
    
    def createSFTPChannel(self):
        if self.isClosed():
            raise Exception( "Can't create an SFTP channel for a closed SSH connection on connection {0}".format( self.getIdentification( ) ) )
        try:
            self.sftp__lock.acquire()
            if self.sftpChannel:
                return True
            self.sftpChannel = self.client.open_sftp()
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
            client.load_system_host_keys()
            try:
                client.connect( self.hostname, port = self.port, username = self.user )
            except paramiko.BadHostKeyException:
                raise Exception( "Bad host key for host {0}. Please make sure the host key is already known to the system. The easiest way is usually to just manually use ssh to connect to the remote host once and save the host key.".format( self.name ) )
            except paramiko.AuthenticationException:
                raise Exception( "Could not authenticate to host {0}. Please make sure that authentication can proceed without user interaction, e.g. by loading an SSH agent or using unencrypted keys.".format( self.name ) )
            chan = client.invoke_shell()
            chan.set_combine_stderr( True )
            trans = client.get_transport()
            chan2 = trans.open_session()
            chan2.set_combine_stderr( True )
            chan2.exec_command( 'bash -l' )
            io = (chan2.makefile( 'wb', -1 ), chan2.makefile( 'rb', -1 ) )
            obj = sshParamikoConnectionObject( client, chan, io )
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
            self.sendCommand('cd; echo "READY"', obj )
            return obj
        else:
            # FIXME: Adapt
            args = ['{0}'.format(sshFallbackConnectionObject.getSSHProgram()), '-l', self.user]
            if self.port:
                args.append( ' -p {0}'.format( self.port ) )
            args.append( self.hostname )
            proc = Popen(args, bufsize=8192, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
            try:
                self.connections__lock.acquire()
                if self.isInCleanup():
                    try:
                        proc.communicate( 'exit' )
                    except OSError as e:
                        if not e.errno == errno.EPIPE: # This one is expected
                            raise e
                    return
                obj = sshFallbackConnectionObject( proc )
                self.connections.append( obj )
                if self.isInCleanup():
                    self.connections.pop()
                    try:
                        proc.communicate( 'exit' )
                    except OSError as e:
                        if not e.errno == errno.EPIPE: # This one is expected
                            raise e
                    return
            finally:
                try:
                    self.connections__lock.release()
                except RuntimeError:
                    pass
            self.sendCommand('echo "READY"', obj )
            return obj

    def closeConnection(self, connection):
        """
        Close a previously created connection to the host.

        Any calls afterwards to methods of this host with the close connection will fail.
        
        The default implementation will close the connection if it wasn't already closed
        and remove it from self.connections.

        @param  The connection to be closed.
        """
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
            connection.write( command+'\necho "\nblabladibla__156987349253457979__noonesGonnaUseThis__right__p2ptestframework"\n' )
            # Read output of command
            res = ''
            line = connection.readline()
            while line != '' and line.strip() != 'blabladibla__156987349253457979__noonesGonnaUseThis__right__p2ptestframework':
                res += line
                line = connection.readline()
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
        connection = None
        try:
            connection = self.getConnection(reuseConnection)
            if paramiko:
                newConnection = connection.createSFTPChannel()
                try:
                    sftp = connection.sftpChannel
                    if sshParamikoConnectionObject.existsRemote(sftp, remoteDestinationPath):
                        if not overwrite: 
                            raise Exception( "Sending file {0} to {1} on host {2} without allowing overwrite, but the destination already exists".format( localSourcePath, remoteDestinationPath, self.name ) )
                        else:
                            attribs = sftp.stat(remoteDestinationPath)
                            if stat.S_ISDIR( attribs.st_mode ):
                                raise Exception( "Sending file {0} to {1} on host {2} with overwrite, but the destination already exsits and is a directory".format( localSourcePath, remoteDestinationPath, self.name ) )
                    if self.isInCleanup():
                        return
                    sftp.put( localSourcePath, remoteDestinationPath )
                finally:
                    if newConnection:
                        connection.removeSFTPChannel()
            else:
                pass
                # FIXME: IMPLEMENT
        finally:
            self.releaseConnection(reuseConnection, connection)
    
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
        connection = None
        try:
            connection = self.getConnection(reuseConnection)
            if paramiko:
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
                                sftp.mkdir( remotePath )
                            paths += [(os.path.join( localPath, path ), '{0}/{1}'.format( remotePath, path )) for path in os.listdir( localPath )]
                        else:
                            sftp.put( localPath, remotePath )
                finally:
                    if newConnection:
                        connection.removeSFTPChannel()
            else:
                pass
                # FIXME: IMPLEMENT
        finally:
            self.releaseConnection(reuseConnection, connection)

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
        connection = None
        try:
            connection = self.getConnection(reuseConnection)
            if paramiko:
                newConnection = connection.createSFTP()
                try:
                    sftp = connection.sftpChannel
                    if os.path.exists( localDestinationPath ):
                        if not overwrite:
                            raise Exception( "Getting file {0} to {1} from host {2} without allowing overwrite, but the destination already exists".format( remoteSourcePath, localDestinationPath, self.name ) )
                        elif os.path.isdir( localDestinationPath ):
                            raise Exception( "Getting file {0} to {1} from host {2} with overwrite, but the destination already exists and is a directory".format( remoteSourcePath, localDestinationPath, self.name ) )
                    if self.isInCleanup():
                        return
                    sftp.get( remoteSourcePath, localDestinationPath )
                finally:
                    if newConnection:
                        connection.removeSFTP()
            else:
                pass
                # FIXME: IMPLEMENT
        finally:
            self.releaseConnection(reuseConnection, connection)

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
        return "2.0.0"

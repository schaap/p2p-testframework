from core.parsing import *
from core.campaign import Campaign
from core.host import host, countedConnectionObject

import getpass

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
    
    def __init__(self):
        countedConnectionObject.__init__(self)

class sshParamikoConnectionObject(countedConnectionObject):
    """
    SSH connection object for paramiko connections
    """
    
    client = None
    
    def __init__(self, client):
        countedConnectionObject.__init__(self)
        self.client = client
    
    def close(self):
        try:
            countedConnectionObject.close(self)
        finally:
            self.client.close()
            del self.client
            self.client = None

class ssh(host):
    """
    The SSH implementation of the host object.
    
    Extra parameters:
    - hostname      The hostname of the host to be used over SSH. Hostnames and IP addresses are accepted.
    - port          The port on which the SSH daemon listens on the host; optional, defaults to 22.
    - user          The user name to be used for logging in over SSH.
    """

    # TODO: For almost all the methods in this class it goes that, whenever you're about to do something that takes
    # significant time or that will introduce something that would need to be cleaned up, check self.isInCleanup()
    # and bail out if that returns True.
    
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
        # TODO: Implement this! Example:
        #
        #   FIXME: WRITE EXAMPLE
        #
        # Be sure to include the new connection in the self.connections list after acquiring self.connections__lock
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
            client.exec_command( 'bash' )   # FIXME: This might work, but returns a tuple of three files. It is imperative to make sure reading output does not block.
            obj = sshParamikoConnectionObject( client )
        else:
            pass
            # FIXME: IMPLEMENT
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

    # TODO: If you really must you can override getConnection. This is needed in case your connection object
    # is not a subclass of core.host.connectionObject. There is no real need for that, though.

    def sendCommand(self, command, reuseConnection = True):
        """
        Sends a bash command to the remote host.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     True for commands that are shortlived or are expected not to be parallel with other commands.
                                    False to build a new connection for this command and use that.
                                    A specific connection object as obtained through setupNewConnection(...) to reuse that connection.

        @return The result from the command. The result is stripped of leading and trailing whitespace before being returned.
        """
        # TODO: Implement this! Example:
        #
        #   connection = None
        #   try:
        #       connection = self.getConnection( reuseConnection )
        #   FIXME: WRITE MORE EXAMPLE
        #   finally:
        #       self.releaseConnection( reuseConnection, connection )
        #
        connection = None
        try:
            connection = self.getConnection(reuseConnection)
            return connection.sendCommand( command )
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
        # TODO: Implement this! Example:
        #
        #   FIXME: WRITE EXAMPLE
        #
        raise Exception( "Not implemented" )
    
    # TODO: If you have a more effective way of sending multiple files at once, override sendFiles as well.

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
        # TODO: Implement this! Example:
        #
        #   FIXME: WRITE EXAMPLE
        #
        raise Exception( "Not implemented" )

    def prepare(self):
        """
        Execute commands on the remote host needed for host specific preparation.

        The default implementation simply ensures the existence of a remote directory.
        """
        # TODO: Prepare anything you may need before being able to set up a connection, first.
        #
        # Then do this call, and definitely do this call unless you know what you're doing:
        host.prepare(self)
        # After that you can do any other less-important host-specific preparation
        #
        # Usually this one call will be enough if you just need to set up the connection.

    def cleanup(self, reuseConnection = None):
        """
        Executes commands to do host specific cleanup.
        
        The default implementation removes the remote temporary directory, if one was created.

        Subclassers are advised to first call this implementation and then proceed with their own steps.
        
        @param  reuseConnection If not None, force the use of this connection object for commands to the host.
        """
        # Be symmetrical with prepare(), clean up the less-important host-specific stuff here
        # Then do this call, and definitely do this call unless you know what you're doing:
        host.cleanup(self, reuseConnection)
        # TODO: Cleanup all of the host, be sure to check what has and what has not been done and needs cleanup.
        # Don't just assume you're at the end of everything. Example:
        #
        #   FIXME: WRITE EXAMPLE
        #

    # TODO: If you need a separate location to store data to ensure that data survives until the end of the test,
    # override getPersistentTestDir() and make sure to initialize correctly to have both the test dir and the
    # persistent test dir set up on the remote host

    def getSubNet(self):
        """
        Return the subnet of the external addresses of the host.

        @return The subnet of the host(s).
        """
        # TODO: Implement this! Example:
        #
        #   return self.hostname
        #
        raise Exception( "Not implemented" )

    def getAddress(self):
        """
        Return the single address (IP or hostname) of the remote host, if any.

        An obvious example of this method returning '' would be a host implementation that actually uses a number
        of remote hosts in one host object: one couldn't possibly return exactly one address for that and be
        correct about it in the process.

        Default implementation just returns ''.

        @return The address of the remote host, or '' if no such address can be given.
        """
        # TODO: Implement this, if possible. Example:
        #
        #   return self.hostname
        #
        return ''

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version.
        return "2.0.0"

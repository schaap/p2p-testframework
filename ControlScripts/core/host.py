import os
import threading

from core.parsing import isPositiveInt
from core.parsing import isPositiveFloat
from core.parsing import isValidName
from core.campaign import Campaign
from core.coreObject import coreObject

def parseError( msg ):
    raise Exception( "Parse error for host object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

def checkSpeedValue( value, speedName ):
    origValue = value
    intValue = value
    if value[-4:] == 'mbit':
        intValue = value[:-4]
    elif value[-4:] == 'kbit':
        intValue = value[:-4]
    else:
        value = value + 'mbit'
    if not isPositiveInt( intValue ):
        parseError( '{1} should be a positive integer, possibly postfixed by kbit or mbit (default: mbit), found "{0}"'.format( origValue, speedName ) )
    return value

class host(coreObject):
    """
    The parent class for all hosts.

    This object contains all the default implementations for every host.
    When subclassing host be sure to use the skeleton class as a basis: it saves you a lot of time.
    Also please note that any attribute starting with tc is reserved for traffic control settings.
    """

    remoteDirectory = None      # String with the path on the remote host to a directory where test data can be stored
    tempDirectory = None        # String with the path on the remote host to a temporary directory; this should be removed during cleanup

    tc = ''                     # String with the name of the traffic control (TC) module to use, or '' for no TC
    tcInterface = None          # String with the name of the interface on which TC is to be applied
    tcDown = 0                  # Integer, maximum download speed enforced by TC, 0 for unlimited
    tcDownBurst = 0             # Integer, maximum download burst enforced by TC, 0 for unlimited
    tcUp = 0                    # Integer, maximum upload speed enforced by TC, 0 for unlimited
    tcUpBurst = 0               # Integer, maximum upload burst enforced by TC, 0 for unlimited
    tcLoss = 0.0                # Float, percentage chance of incoming packet loss by TC
    tcCorruption = 0.0          # Float, percentage chance of corruption in an incoming packet by TC
    tcDuplication = 0.0         # Float, percentage chance of an incoming packet being duplicated by TC
    tcDelay = 0                 # Integer, delay in ms added to each outgoing packet by TC
    tcJitter = 0                # Integer, maximum deviation in ms to tcDelay
    tcParamsSet = False         # True iff any of the tc attributes have been set by settings

    tcObj = None                # The instance of the requested TC module; will be loaded by the ScenarioRunner
    tcInboundPortList = None    # The list of incoming ports that will be restricted using TC; [] for no restrictions, -1 for all ports
    tcOutboundPortList = None   # The list of outgoing ports that will be restricted using TC; [] for no restrictions, -1 for all ports
    tcProtocol = ''             # The name of the protocol on which port-based restrictions will be placed, '' for multi-protocol (tcInboundPortList or tcOutboundPortList will be -1 in this case)

    connections = None          # The list of connections created for this host. self.connections[0] should always be the default connection. Do not access this list from outside a host class.
    connections__lock = None    # The threading.RLock() guarding access to the connections list.
    
    clients = None              # List of clients that are to be run on this host. Will be filled when all executions are known.
    files = None                # List of files that are to be used on this host. Will be filled when all executions are known.
    seedingFiles = None         # List of files that are to be seeded from this host. Will be filled when all executions are known.

    def __init__(self, scenario):
        """
        Initialization of a generic module object.

        @param  scenario            The ScenarioRunner object this module object is part of.
        """
        coreObject.__init__(self, scenario)
        self.connections__lock = threading.RLock()
        self.tcInboundPortList = []
        self.tcOutboundPortList = []
        self.connections = []
        self.clients = []
        self.files = []
        self.seedingFiles = []

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
        if key == 'name':
            if self.name != '':
                parseError( 'Name already set: {0}'.format( self.name ) )
            if not isValidName( value ):
                parseError( '"{0}" is not a valid name'.format( value ) )
            if value in self.scenario.getObjectsDict('host'):
                parseError( 'Host object called {0} already exists'.format( value ) )
            self.name = value
        elif key == 'preparation':
            parseError( 'The preparation parameter was badly supported under version 1 and has been deprecated. If you need this parameter, please contact the developers of the framework to discuss support.' )
        elif key == 'cleanup':
            parseError( 'The cleanup parameter was badly supported under version 1 and has been deprecated. If you need this parameter, please contact the developers of the framework to discuss support.' )
        elif key == 'remoteFolder' or key == 'remoteDirectory':
            if self.remoteDirectory:
                parseError( 'Remote directory already set' )
            if value != '':
                self.remoteDirectory = value
        elif key == 'tc_iface' or key == 'tcInterface':
            if self.tcInterface:
                parseError( 'Only one interface for TC allowed' )
            if value == '':
                parseError( 'Empty interface for TC found, but an interface is required' )
            self.tcInterface = value
            self.tcParamsSet = True
        elif key == 'tc_down' or key == 'tcMaxDownSpeed':
            if self.tcDown != 0:
                parseError( 'Maximum download speed for TC already set' )
            self.tcDown = checkSpeedValue( value, 'Maximum download speed' )
            self.tcParamsSet = True
        elif key == 'tc_down_burst' or key == 'tcMaxDownBurst':
            if self.tcDownBurst != 0:
                parseError( 'Maximum download burst for TC already set' )
            self.tcDownBurst = checkSpeedValue( value, 'Maximum download burst' )
            self.tcParamsSet = True
        elif key == 'tc_up' or key == 'tcMaxUpSpeed':
            if self.tcUp != 0:
                parseError( 'Maximum upload speed for TC already set' )
            self.tcUp = checkSpeedValue( value, 'Maximum upload speed' )
            self.tcParamsSet = True
        elif key == 'tc_up_burst' or key == 'tcMaxUpBurst':
            if self.tcUpBurst != 0:
                parseError( 'Maximum upload burst for TC already set' )
            self.tcUpBurst = checkSpeedValue( value, 'Maximum upload burst' )
            self.tcParamsSet = True
        elif key == 'tc':
            if self.tc != '':
                parseError( 'TC module already set' )
            if value == '':
                return
            if not isValidName( value ):
                parseError( 'Name given as name of TC module is not a valid name: {0}'.format( value ) )
            __import__( 'modules.tc.'+value, globals(), locals(), value )    # Just checks availability
            self.tc = value
        elif key == 'tc_loss' or key == 'tcLossChance':
            if self.tcLoss != 0:
                parseError( 'Loss chance for TC already set' )
            if (not isPositiveFloat( value )) or float(value) > 100:
                parseError( 'Loss chance for TC should be a floating point number >= 0.0 and <= 100.0, unlike {0}'.format( value ) )
            self.tcLoss = float(value)
        elif key == 'tc_corruption' or key == 'tcCorruptionChance':
            if self.tcCorruption != 0:
                parseError( 'Corruption chance for TC already set' )
            if (not isPositiveFloat( value )) or float(value) > 100:
                parseError( 'Corruption chance for TC should be a floating point number >= 0.0 and <= 100.0, unlike {0}'.format( value ) )
            self.tcCorruption = float(value)
        elif key == 'tc_duplication' or key == 'tcDuplicationChance':
            if self.tcDuplication != 0:
                parseError( 'Duplication chance for TC already set' )
            if (not isPositiveFloat( value )) or float(value) > 100:
                parseError( 'Duplication chance for TC should be a floating point number >= 0.0 and <= 100.0, unlike {0}'.format( value ) )
            self.tcDuplication = float(value)
        elif key == 'tc_delay' or key == 'tcDelay':
            if self.tcDelay != 0:
                parseError( 'Delay for TC already set' )
            if not isPositiveInt( value ):
                parseError( 'Delay for TC should be a positive integer denoting the delay in ms, unlike {0}'.format( value ) )
            self.tcDelay = int(value)
        elif key == 'tc_jitter' or key == 'tcJitter':
            if self.tcJitter != 0:
                parseError( 'Jitter in the delay for TC already set' )
            if not isPositiveInt( value ):
                parseError( 'Jitter in the delay for TC should be a positive integer denoting the maximum deviation in the delay for TC in ms, unlike {0}'.format( value ) )
            self.tcJitter = int(value)
        else:
            parseError( 'Unknown parameter name: {0}'.format( key ) )

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        if self.name == '':
            raise Exception( "Host object declared at line {0} was not given a name".format( self.declarationLine ) )
        if self.tc == '':
            if self.tcParamsSet:
                raise Exception( "Some parameters were set for TC in host {0}, but TC itself was not enabled.".format( self.name ) )
        else:
            if not self.tcParamsSet:
                raise Exception( "TC was enabled for host {0}, but no actual parameters were given, rendering effectively no TC at all.".format( self.name ) )
            if not self.tcInterface:
                self.tcInterface = 'eth0'
            if self.tcDownBurst != 0:
                if self.tcDown == 0:
                    raise Exception( "A maximum download burst was provided for host {0}, but no maximum download speed.".format( self.name ) )
                else:
                    if self.tcDownBurst[-4:] == 'mbit':
                        burst = int(self.tcDownBurst[:-4]) * 1024 * 1024
                    elif self.tcDownBurst[-4:] == 'kbit':
                        burst = int(self.tcDownBurst[:-4]) * 1024
                    else:
                        burst = int(self.tcDownBurst)
                    if self.tcDown[-4:] == 'mbit':
                        rate = int(self.tcDown[:-4]) * 1024 * 1024
                    elif self.tcDown[-4:] == 'kbit':
                        rate = int(self.tcDown[:-4]) * 1024
                    else:
                        rate = int(self.tcDown)
                    # minimum burst:
                    # max down / 800
                    # http://lartc.org/howto/lartc.qdisc.classless.html#AEN691
                    # http://mailman.ds9a.nl/pipermail/lartc/2001q4/001972.html
                    if burst * 800 < rate:
                        Campaign.logger.log( "Warning! The advised minimum for maximum download burst is the maximum download / 8 * 10ms. This would be {0} for host {1}, which is larger than the given burst {2}. Ignoring at your risk.".format( rate / 800, self.name, self.tcDownBurst ) )
            if self.tcUpBurst != 0:
                if self.tcUp == 0:
                    raise Exception( "A maximum upload burst was provided for host {0}, but no maximum upload speed.".format( self.name ) )
                else:
                    if self.tcUpBurst[-4:] == 'mbit':
                        burst = int(self.tcUpBurst[:-4]) * 1024 * 1024
                    elif self.tcUpBurst[-4:] == 'kbit':
                        burst = int(self.tcUpBurst[:-4]) * 1024
                    else:
                        burst = int(self.tcUpBurst)
                    if self.tcUp[-4:] == 'mbit':
                        rate = int(self.tcUp[:-4]) * 1024 * 1024
                    elif self.tcUp[-4:] == 'kbit':
                        rate = int(self.tcUp[:-4]) * 1024
                    else:
                        rate = int(self.tcUp)
                    if burst * 800 < rate:
                        Campaign.logger.log( "Warning! The advised minimum for maximum upload burst is the maximum upload / 8 * 10ms. This would be {0} for host {1}, which is larger than the given burst {2}. Ignoring at your risk.".format( rate / 800, self.name, self.tcUpBurst ) )
            if self.tcJitter != 0:
                if self.tcJitter > self.tcDelay:
                    raise Exception( "Host {0} was given a jitter ({1}) and delay ({2}) for TC, but the jitter can't be larger tan the delay.".format( self.name, self.tcJitter, self.tcDelay ) )

    def setupNewConnection(self):
        """
        Create a new connection to the host.

        The returned object has no specific type, but should be usable as a connection object either by uniquely identifying it or 
        simply by containing the needed information for it.

        Connections created using this function can be closed with closeConnection(...). When cleanup(...) is called all created
        connections will automatically closed and, hence, any calls using those connections will then fail.

        @return The connection object for a new connection.
        """
        raise Exception( "Not implemented" )

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
    def closeConnection(self, connection):
        """
        Close a previously created connection to the host.

        Any calls afterwards to methods of this host with the close connection will fail.

        @param  The connection to be closed.
        """
        raise Exception( "Not implemented" )
    # pylint: enable-msg=W0613

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
    def sendCommand(self, command, reuseConnection = True):
        """
        Sends a bash command to the remote host.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     True for commands that are shortlived or are expected not to be parallel with other commands.
                                    False to build a new connection for this command and use that.
                                    A specific connection object as obtained through setupNewConnection(...) to reuse that connection.

        @return The result from the command. The result is stripped of leading and trailing whitespace before being returned.
        """
        raise Exception( "Not implemented" )
    # pylint: enable-msg=W0613

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
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
        raise Exception( "Not implemented" )
    # pylint: enable-msg=W0613
    
    def sendFiles(self, localSourcePath, remoteDestinationPath, reuseConnection = True):
        """
        Sends a directory to the remote host.

        This will recursively send the local directory and all its contents to the remote host.

        Example:    sendFile( '/home/me/myLocalDir', '/tmp/myTmpDir/newRemoteDir' )
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
        if not os.path.isdir( localSourcePath ):
            raise Exception( "localSourcePath must point to a local directory, found: {0}".format( localSourcePath ) )
        if self.sendCommand( "[ -f {0} ] && echo 'E'".format( remoteDestinationPath ) )[0] == 'E':
            raise Exception( "remoteDistinationPath {0} already exists on the remote host, but points to a file".format( remoteDestinationPath ) )
        for path in os.listdir( localSourcePath ):
            fullLocalPath = os.path.join( localSourcePath, path )
            fullRemotePath = '{0}/{1}'.format( remoteDestinationPath, path )
            if os.path.isdir( fullLocalPath ):
                self.sendFiles( fullLocalPath, fullRemotePath, reuseConnection = reuseConnection )
            else:
                self.sendFile( fullLocalPath, fullRemotePath, True, reuseConnection = reuseConnection )

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
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
        raise Exception( "Not implemented" )
    # pylint: enable-msg=W0613

    def prepare(self):
        """
        Execute commands on the remote host needed for host specific preparation.

        The default implementation creates self.connections[0] (the default connection) and ensures the
        existence of a remote directory.
        """
        if self.isInCleanup():
            return
        try:
            self.connections__lock.acquire()
            if len(self.connections) > 0:
                raise Exception( "While running prepare(...) for host {0} self.connections[0] was already filled?".format( self.name ) )
            self.connections[0] = self.setupNewConnection()
            if len(self.connections) == 0 or not self.connections[0]:
                if not self.isInCleanup():
                    raise Exception( "Could not create default connection" )
                if len(self.connections) > 0:
                    del self.connections[0]
            if self.isInCleanup():
                return
        finally:
            try:
                self.connections__lock.release()
            except RuntimeError:
                pass
        if not self.remoteDirectory:
            self.tempDirectory = self.sendCommand( 'mktemp -d' )
            if self.tempDirectory == '' or self.sendCommand( '[ -d {0} ] || echo "E"'.format( self.tempDirectory ) ) == 'E':
                res = self.tempDirectory
                self.tempDirectory = None
                raise Exception( "Could not correctly create a remote temporary directory on host {1}. Response: {0}".format( res, self.name ) )

    def cleanup(self):
        """
        Executes commands to do host specific cleanup.
        
        The default implementation removes the remote temporary directory, if one was created, and closes all
        created connections.

        Subclassers are advised to first call this implementation and then proceed with their own steps.
        Whatever is done, however, it is important to call coreObject.cleanup(self) as soon as possible; this
        implementation starts with that call (which may be made multiple times without harm).
        """
        coreObject.cleanup(self)
        self.connections__lock.acquire()
        try:
            if self.tempDirectory:
                if len(self.connections) < 1:
                    Campaign.logger.log( "Warning: no connections open for host {0}, but tempDirectory is set. Temporary directory {1} is most likely not removed from the host.".format( self.name, self.tempDirectory ) )
                    return
                conn = self.connections[0]
                if not conn:
                    Campaign.logger.log( "Warning: default connection for host {0} seems unavailable, but tempDirectory is set. Temporary directory {1} is most likely not removed from the host.".format( self.name, self.tempDirectory ) )
                    return
                self.sendCommand( 'rm -rf {0}'.format( self.tempDirectory ), conn )
                res = self.sendCommand( '[ -d {0} ] && echo "N" || echo "E"'.format( self.tempDirectory ), conn )
                if res[0] != 'E':
                    Campaign.logger.log( "Warning: Could not remove temporary directory {0} from host {1} during cleanup.".format( self.tempDirectory, self.name ) )
                self.tempDirectory = None
            closeConns = []     # Copy self.connections first: it will be modified while iterating over all connections to close them
            for conn in self.connections:
                closeConns.append( conn )
            for conn in closeConns:
                try:
                    self.closeConnection( conn )
                except Exception:
                    Campaign.logger.log( "An exception occurred while closing a connection of host {0} during cleanup; ignoring".format( host.name ) )
                    Campaign.logger.exceptionTraceback()
        finally:
            self.connections__lock.release()

    def getTestDir(self):
        """
        Returns the path to the directory on the remote host where (temporary) files are stored for the testing
        environment.

        Files placed in this directory are not guaranteed to remain available for later downloading.
        This is the perfect location for files such as data to be downloaded by clients, which can be forgotten
        the moment the client finishes.
        For logfiles and other files that are needed after the execution of the client, use
        getPersistentTestDir().

        The default implementation uses self.remoteDirectory if it exists, or otherwise self.tempDirectory.

        @return The test directory on the remote host.
        """
        if self.remoteDirectory:
            return self.remoteDirectory
        return self.tempDirectory

    def getPersistentTestDir(self):
        """
        Returns the path to the directory on the remote host where (temporary) files are stored for the testing
        environment, which will remain available until the host is cleaned.

        Note that persistence in this case is limited to the complete test as opposed to data being thrown away
        at any possible moment in between commands.

        The default implementation just uses self.getTestDir() and is hence under the assumption that the
        normal test dir is persistent enough.

        @return The persisten test directory on the remote host.
        """
        return self.getTestDir()

    def getSubNet(self):
        """
        Return the subnet of the external addresses of the host.

        @return The subnet of the host(s).
        """
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
        return ''

    def getModuleType(self):
        """
        Return the moduleType string.
        
        @return    The module type.
        """
        return 'host'
    
    def getName(self):
        """
        Return the name of the object.
        
        @return    The name.
        """
        return self.name

    @staticmethod
    def APIVersion():
        return "2.0.0-core"

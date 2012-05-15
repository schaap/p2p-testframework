import os
import threading
import time

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

class connectionObject():
    """
    The parent class for all connection objects.
    
    Unless subclassers override about every method in host it is highly advised to subclass this
    class for specific connection objects.
    """
    
    closeFlag = True        # True iff this connection was closed
    closeFlag__lock = None  # Lock to protect closeFlag. DO NOT USE! Use isClosed(), close() and closeIfNotClosed() instead.
    
    use__lock = None        # Lock for usage. DO NOT USE! Use lockForUse() and unlockForUse() instead.
    
    badFlag = False         # Internal flag to DEBUG locking. DO NOT USE!
    badFlag__lock = None    # Internal flag to DEBUG locking. DO NOT USE!
    badSince = -1           # Time since when the badFlag has been set. For DEBUG locking. DO NOT USE!
    
    async = False           # Flag for asynchronous processing. DO NOT USE! Use setInAsync(), clearInAsync() and isInAsync() instead.
    async__lock = None      # Lock to protect async
    
    def __init__(self):
        """
        Initialization of the core connectionObject.
        
        Be sure to call this when subclassing the connection object!
        """
        self.closeFlag__lock = threading.RLock()
        self.closeFlag = False
        self.use__lock = threading.RLock()
        self.badFlag__lock = threading.Lock()
        self.async__lock = threading.Lock()
    
    def getIdentification(self):
        """
        Returns a unique identification for this connection object.
        
        This may be a number of a string, or anything really. As long as
        it can be compared with == it's fine.
        
        @return The unique identification of this connection object.
        """
        raise Exception( "Not implemented" )
    
    def isClosed(self):
        """
        Returns whether this connection object was closed.
        
        @return True iff this connection object was closed.
        """
        res = True
        try:
            self.closeFlag__lock.acquire()
            res = self.closeFlag
        finally:
            self.closeFlag__lock.release()
        return res
    
    def close(self):
        """
        Close this connection object.
        """
        try:
            self.closeFlag__lock.acquire()
            self.closeFlag = True
        finally:
            self.closeFlag__lock.release()
    
    def closeIfNotClosed(self):
        """
        Closes the object if it wasn't closed already and returns whether it was closed already.
        
        @return True iff the object was already closed.
        """
        res = True
        try:
            self.closeFlag__lock.acquire()
            if not self.closeFlag:
                res = False
                self.close()
        finally:
            self.closeFlag__lock.release()
        return res
    
    def lockForUse(self):
        """
        Locks this connection object for use.
        
        This method will return whether object was locked. Be sure to check!
        This method will always fail if the object is closed.
        
        Advised usage:
            try:
                while not connection.lockForUse():
                    Campaign.logger.log( "Warning! Can't lock connection {0} for use.".format( connection.getIdentification() ) )
                    if self.isInCleanup():
                        return
                    time.sleep( 5 )
                # Use your connection here
            finally:
                connection.tryUnlockForUse()

        @return True iff the object was locked.
        """
        if self.closeFlag:
            return False
        self.badFlag__lock.acquire()
        badFlag = self.badFlag
        self.badFlag = True
        res = self.use__lock.acquire(False)
        if not badFlag:
            if res:
                self.badFlag = False
            else:
                self.badSince = time.time()
        self.badFlag__lock.release()
        return res
    
    def unlockForUse(self):
        """
        Unlocks this connection object for later use.
        
        This method will raise a RuntimeError if a lock has not been acquired using lockForUse earlier on.
        """
        self.badFlag__lock.acquire()
        if self.badFlag:
            Campaign.logger.log( "DEBUG: Previous use preventing connection {0} from locking was unlocked.".format( self.getIdentification( ) ) )
            #Campaign.logger.log( "Previous use preventing connection {0} from locking was unlocked, traceback follows.".format( self.getIdentification( ) ) )
            #Campaign.logger.localTraceback()
            self.badFlag = False
        self.badFlag__lock.release()
        self.use__lock.release()
    
    def tryUnlockForUse(self):
        """
        If this connection object was locked for use, unlock it.
        
        This method is equal to unlockForUse, but will not throw a RuntimeError if a lock was not acquired.
        """
        try:
            self.unlockForUse()
        except RuntimeError:
            pass
    
    def setInAsync(self):
        """
        Marks the connection as having sent an asynchronous command.
        """
        try:
            self.async__lock.acquire()
            self.async = True
        finally:
            self.async__lock.release()
    
    def clearInAsync(self):
        """
        Marks the connection as having ended an asynchronous command.
        """
        try:
            self.async__lock.acquire()
            self.async = False
        finally:
            self.async__lock.release()
    
    def isInAsync(self):
        """
        Returns whether the connectino is marked as having sent an asynchronous command.
        
        @return    True iff an asynchronous command should be ended, first.
        """
        try:
            self.async__lock.acquire()
            return self.async
        finally:
            self.async__lock.release()

class countedConnectionObject(connectionObject):
    """
    A small extension to connectionObject that fills in the identification part with a simple counter.
    """
    
    # @static
    staticCounter = 0                       # Static counter for all countedConnectionObject instances DO NOT TOUCH!
    # @static
    staticCounter__lock = threading.Lock()  # Lock for the static counter. DO NOT USE!
    
    counter = 0                             # The specific counter of this countedConnectionObject. This identifies the object.
    
    def __init__(self):
        """
        Initialization of the core connectionObject.
        
        This also initializes self.counter, the identifying counter.
        
        Be sure to call this when subclassing the connection object!
        """
        connectionObject.__init__(self)
        countedConnectionObject.staticCounter__lock.acquire()
        countedConnectionObject.staticCounter += 1
        self.counter = countedConnectionObject.staticCounter
        countedConnectionObject.staticCounter__lock.release()
        self.staticCounter__lock = None
    
    def getIdentification(self):
        """
        Returns a unique identification for this connection object.
        
        This may be a number of a string, or anything really. As long as
        it can be compared with == it's fine.
        
        This specific implementation uses self.counter.
        
        @return The unique identification of this connection object.
        """
        return self.counter

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
    
    def copyhost(self, other):
        """
        Creates a copy of the other host in this host.
        
        Copies should not include host object specific information, such as cached objects or references. 

        DO NOT rely on this function for generic use. It is just here to support subclasses that wish to
        implement it. In general it can be assumed it is not fully implemented by subclasses and hence
        broken to call it. 
        
        The tempDirectory parameter will be None. 
        The tcObj parameter will be loaded by creating a new object of the same class.
        The connections list will be empty.
        The client, files and seedingFiles connections will be empty.
        """
        self.remoteDirectory = other.remoteDirectory
        self.tc = other.tc
        self.tcInterface = other.tcInterface
        self.tcDown = other.tcDown
        self.tcDownBurst = other.tcDownBurst
        self.tcUp = other.tcUp
        self.tcUpBurst = other.tcUpBurst
        self.tcLoss = other.tcLoss
        self.tcCorruption = other.tcCorruption
        self.tcDuplication = other.tcDuplication
        self.tcDelay = other.tcDelay
        self.tcJitter = other.tcJitter
        self.tcParamsSet = other.tcParamsSet
        if other.tcObj:
            self.tcObj = other.tcObj.__class__()
        if isinstance( other.tcInboundPortList, list ):
            self.tcInboundPortList = list(other.tcInboundPortList)
        else:
            self.tcInboundPortList = other.tcInboundPortList
        if isinstance( other.tcOutboundPortList, list ):
            self.tcOutboundPortList = list(other.tcOutboundPortList)
        else:
            self.tcOutboundPortList = other.tcOutboundPortList
        self.tcProtocol = other.tcProtocol

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

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        pass

    def getByArguments(self, argumentString):
        """
        Selects a hsot object by specific arguments.
        
        The arguments can be used to return a different host object than the one this is called on.
        
        This is called for the execution's host parameter's selection syntax:
            host=name@args
        Invariant: self.scenario.getObjectsDict('host')[name] == self and argumentString == args
        
        The primary use of selection by arguments is to select a single host object from a host object that multiplies itself.
        
        The default implementation returns self for no arguments and raises an exception for any other argument.
        
        @param     argumentString    The arguments passed in the selection
        
        @return    A single, specific host object.
        """
        if argumentString != '':
            raise Exception( 'Host {0} does not support object selection by argument'.format( self.getName() ) )
        return self
    
    def setupNewConnection(self):
        """
        Create a new connection to the host.

        The returned object has no specific type, but should be usable as a connection object either by uniquely identifying it or 
        simply by containing the needed information for it.

        Connections created using this function can be closed with closeConnection(...). When cleanup(...) is called all created
        connections will automatically closed and, hence, any calls using those connections will then fail.

        @return The connection object for a new connection. This should be an instance of a subclass of core.host.connectionObject.
        """
        raise Exception( "Not implemented" )

    def setupNewCleanupConnection(self):
        """
        Create a new connection to the host.
        
        This connection may not be dependent on the state of previous connections. In other words: this function should always work,
        even if things have really blown up.

        The returned object has no specific type, but should be usable as a connection object either by uniquely identifying it or 
        simply by containing the needed information for it.

        Connections created using this function can be closed with closeConnection(...). When cleanup(...) is called all created
        connections will automatically closed and, hence, any calls using those connections will then fail.

        @return The connection object for a new connection. This should be an instance of a subclass of core.host.connectionObject.
        """
        return self.setupNewConnection()

    def closeConnection(self, connection):
        """
        Close a previously created connection to the host.

        Any calls afterwards to methods of this host with the close connection will fail.
        
        The default implementation will close the connection if it wasn't already closed
        and remove it from self.connections.

        @param  The connection to be closed.
        """
        if not connection:
            return
        
        connection.closeIfNotClosed()
        
        index = 0
        try:
            self.connections__lock.acquire()
            ident = connection.getIdentification()
            maxlen = len(self.connections)
            while index < maxlen:
                if self.connections[index].getIdentification() == ident:
                    self.connections.pop(index)
                    break
                index += 1
        finally:
            self.connections__lock.release()
    
    def getConnection(self, reuseConnection):
        """
        Internal method for acquiring the right connection to use.
        
        This method will decide what connection to use depending on the value of reuseConnection
        (as passed on through e.g. sendCommand(...)). This includes creating a new connection
        when reuseConnection is False. In the latter case the connection will NOT be destroyed
        automatically, so that is one step that still needs to be done by the caller.
        
        This method will also try and lock the connection object to prevent multiple threads from
        using the same connection at the same time. Warnings will be emitted when the lock can't
        be acquired.
        
        Advised usage:
        
            connection = None
            try:
                connection = self.getConnection( reuseConnection )
                # Use the connection
            finally:
                self.releaseConnection( reuseConnection, connection )

        @param  reuseConnection     True for commands that are shortlived or are expected not to be parallel with other commands.
                                    False to build a new connection for this command and use that.
                                    A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
        
        @return A usable connection. Be sure to close it iff reuseConnection was False.
        """
        connection = None
        if reuseConnection == False:
            connection = self.setupNewConnection()
            if connection.isClosed():
                raise Exception( "A new connection is already closed." )
        elif reuseConnection == True:
            try:
                self.connections__lock.acquire()
                if len(self.connections) < 1:
                    raise Exception( "Reuse of the default connection was requested, but no default connection exists." )
                connection = self.connections[0]
            finally:
                self.connections__lock.release()
            if connection.isClosed():
                raise Exception( "The default connection is already closed." )
        else:
            if not isinstance(reuseConnection, connectionObject):
                raise Exception( "Trying to reuse a connection that is not a connection." )
            connection = reuseConnection
            if connection.isClosed():
                raise Exception( "Trying to reuse already closed connection {0}".format( connection.getIdentification() ) )
        while not connection.lockForUse():
            Campaign.logger.log( "DEBUG: Trying to lock connection {0}, but it seems to be locked already. Been locked for {1} seconds. Sleeping.".format( connection.getIdentification(), time.time() - connection.badSince ) )
            #Campaign.logger.log( "Trying to lock connection {0}, but it seems to be locked already. Traceback follows. Been locked for {1} seconds. Sleeping.".format( connection.getIdentification(), time.time() - connection.badSince ) )
            #Campaign.logger.localTraceback()
            if connection.isClosed():
                raise Exception( "Could not lock connection {0}, which now turns out to be closed.".format( connection.getIdentification() ) )
            time.sleep( 1 )
        return connection
    
    def releaseConnection(self, reuseConnection, connection):
        """
        Release a connection retrieved through getConnection().
        
        This method provides symmetry to self.getConnection() without the need for much boilerplate code.
        
        Do not attempt to use the connection after calling this method!
        
        @param  reuseConnection     True for commands that are shortlived or are expected not to be parallel with other commands.
                                    False to build a new connection for this command and use that.
                                    A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
        @param  connection          The connection as returned by self.getConnnection().
        """
        if connection:
            connection.tryUnlockForUse()
            if reuseConnection == False:
                self.closeConnection(connection)

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
    
    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
    def sendCommandAsyncStart(self, command, reuseConnection):
        """
        Sends a bash command to the remote host without waiting for the answer.
        
        Note that it is imperative that you call sendCommandAsyncEnd(...) after this call, or you will screw up your connection!
        
        Be sure to call connection.setInAsync() as well.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
                                    Contrary to other methods True of False are explicitly not accepted.
        """
        raise Exception( "Not implemented" )
    # pylint: enable-msg=W0613

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
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
        if not os.path.isdir( localSourcePath ):
            raise Exception( "localSourcePath must point to a local directory, found: {0}".format( localSourcePath ) )
        res = self.sendCommand( "[ -f {0} ] && echo 'E'".format( remoteDestinationPath ), reuseConnection ) 
        if len(res) > 0 and res[0] == 'E':
            raise Exception( "remoteDistinationPath {0} already exists on the remote host, but points to a file".format( remoteDestinationPath ) )
        res = self.sendCommand( "[ ! -e {0} ] && echo 'E'".format( remoteDestinationPath ), reuseConnection ) 
        if len(res) > 0 and res[0] == 'E':
            self.sendCommand( 'mkdir -p "{0}"'.format( remoteDestinationPath ), reuseConnection)
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
            self.connections.append( self.setupNewConnection() )
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
            if self.tempDirectory != '':
                testres = self.sendCommand( '[ -d "{0}" ] && [ `ls -a "{0}" | wc -l` -eq 2 ] && echo "OK"'.format( self.tempDirectory ) )
            if self.tempDirectory == '' or testres.strip() != "OK":
                res = self.tempDirectory
                self.tempDirectory = None
                raise Exception( "Could not correctly create a remote temporary directory on host {1} or could not verify it. Response: {0}\nResponse to the verification: {2}".format( res, self.name, testres ) )

    # Indeed, PyLint, host.cleanup() has more arguments than coreObject.cleanup(). This is actually CORRECT in normal OO.
    # pylint: disable-msg=W0221
    def cleanup(self, reuseConnection = None):
        """
        Executes commands to do host specific cleanup.
        
        The default implementation removes the remote temporary directory, if one was created, and closes all
        created connections.

        Subclassers are advised to first call this implementation and then proceed with their own steps.
        Whatever is done, however, it is important to call coreObject.cleanup(self) as soon as possible; this
        implementation starts with that call (which may be made multiple times without harm).
        
        @param  reuseConnection If not None, force the use of this connection object for commands to the host.
        """
        coreObject.cleanup(self)
        self.connections__lock.acquire()
        try:
            try:
                if self.tempDirectory:
                    conn = reuseConnection
                    if not conn:
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
            finally:
                closeConns = []     # Copy self.connections first: it will be modified while iterating over all connections to close them
                for conn in self.connections:
                    closeConns.append( conn )
                for conn in closeConns:
                    try:
                        self.closeConnection( conn )
                    except Exception as exc:
                        Campaign.logger.log( "An exception occurred while closing a connection of host {0} during cleanup; ignoring: ".format( self.name, exc.__str__() ) )
                        Campaign.logger.exceptionTraceback()
        finally:
            self.connections__lock.release()
    # pylint: enable-msg=W0221

    def getTestDir(self):
        """
        Returns the path to the directory on the remote host where (temporary) files are stored for the testing
        environment.

        Files placed in this directory are not guaranteed to remain available for later downloading.
        This is the perfect location for files such as data to be downloaded by clients, which can be forgotten
        the moment the client finishes.
        For logfiles and other files that are needed after the execution of the client, use
        getPersistentTestDir().

        During cleanup this may return None! 

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

        During cleanup this may return None! 

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
        return "2.2.0-core"

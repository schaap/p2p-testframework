from core.parsing import *
from core.campaign import Campaign

def parseError( msg ):
    raise Exception( "Parse error for host object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

    # FIXME: Go over all the cleanup stuff to see which are really needed. It's a bit of a mess, now.

class client:
    """
    The parent class for all clients.

    This object contains all the default implementations for every host.
    When subclassing client be sure to use the skeleton class as a basis: it saves you a lot of time.
    """

    scenario = None             # The ScenarioRunner this object is part of
    name = ''                   # String containing the name of this object; unique among all hosts
    declarationLine = -1        # Line number of the declaration of this host object, read during __init__

    extraParameters = ''        # String with extra parameters to be passed on to the client
    defaultParser = None        # String with the name of the parser object to be used with this client if no other parser is given in the execution; defaults to None which will use the default parser for the client (which is the parser module named the same as the client, with the default settings of that module)

    source = None               # String with the name of the source module to use to retrieve the client; defaults to directory which is just an on-disk accessible directory
    isRemote = False            # True iff the client source is on the remote host; this means either having the source available there or retrieving it from there
    location = None             # String with the path to the location of the client; meaning depends on the way the client is to be found
    builder = None              # String with the name of the builder module to use to build the source; None for precompiled binaries

    builderObj = None           # The instance of the builder module requested
    sourceObj = None            # The instance of the source module requested

    # For more clarity: the way source, isRemote, location and builder work together is as follows.
    #
    # If isRemote is set, we first go to the remote host and work there.
    # If isRemote is not set, we work on the local host and copy the needed binaries to the remote host afterwards.
    #
    # We ask the source module to retrieve the client for use; the source module uses the location to know where
    # to get the client from. An svn source module, for example, would retrieve the client from the svn repository
    # given in the location (e.g. https://svn.tribler.org/abc/...); the directory source module interprets the
    # location argument as a path to a directory. Note that the interpretation of the location argument is already
    # in the context of isRemote: when isRemote is set the location for a directory source module is the path to a
    # directory on the remote host, whereas it's a path to a directory on the local host if isRemote is not set.
    #
    # After that we ask the builder module to build the sources for us, the result of which will always be that we
    # have binaries available in a directory on the local (!isRemote)/remote (isRemote) host.

    def __init__(self, scenario):
        """
        Initialization of a generic client object.

        @param  scenario        The ScenarioRunner object this client object is part of.
        """
        self.scenario = scenario
        self.declarationLine = Campaign.currentLineNumber

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
            if value in self.scenario.getObjectsDict('client'):
                parseError( 'Host object called {0} already exists'.format( value ) )
            self.name = value
        elif key == 'params' or key == 'extraParameters':
            if self.extraParameters != '':
                parseError( 'Extra parameters already set: {0}'.format( self.extraParameters ) )
            self.extraParameters = value
        elif key == 'location':
            if self.location:
                parseError( 'Location already set: {0}'.format( self.location ) )
            self.location = value
        elif key == 'parser':
            if self.defaultParser:
                parseError( 'Parser already set for client: {0}'.format( self.defaultParser ) )
            if not isValidName( value ):
                parseError( 'Parser name given is not a valid name: {0}'.format( value ) )
            self.parser = value
        elif key == 'builder':
            if self.builder:
                parseError( 'Builder already set for client: {0}'.format( self.builder ) )
            if not isValidName( value ):
                parseError( 'Builder name given is not a valid name: {0}'.format( value ) )
            __import__( 'module.builder.'+value, globals(), locals(), value )
            self.builder = value
        elif key == 'source':
            if self.source:
                parseError( 'Source already set for client: {0}'.format( self.source ) )
            if not isValidName( value ):
                parseError( 'Source name given is not a valid name: {0}'.format( value ) )
            __import__( 'module.source.'+value, globals(), locals(), value )
            self.source = value
        elif key == 'remoteClient':
            self.isRemote = ( value != '' )
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
            raise Exception( "Client object declared at line {0} was not given a name".format( self.declarationLine ) )
        if self.defaultParser:
            if self.defaultParser not in self.scenario.getObjectsDict( 'parser' ):
                raise Exception( "Client {0} refers to parser named {1}, but that is not declared".format( self.name, self.defaultParser ) )
        else:
            try:
                __import__( 'module.parser.'+self.__class__.__name__, globals(), locals(), self.__class__.__name__ )
            except ImportError:
                raise Exception( "Client {0} has no parser specified, but falling back to default parser module parser:{0} is not possible since that module does not exist.".format( self.name, self.__class__.__name__ ) )
        if not self.builder:
            self.builder = 'none'
            try:
                __import__( 'module.builder.none', globals(), locals(), 'none' )
            except ImportError:
                raise Exception( "The default builder module builder:none can't be imported. This means your installation is broken." )
        self.builderObj = Campaign.loadModule( 'builder', self.builder )()
        if not self.builderObj:
            raise Exception( "Could not instantiate builder module builder:{0} for client {1}".format( self.builder, self.name ) )
        if not self.source:
            self.source = 'directory'
            try:
                __import__( 'module.source.directory', globals(), locals(), 'directory' )
            except ImportError:
                raise Exception( "The default source module source:directory can't be imported. This means your installation is broken." )
        self.sourceObj = Campaign.loadModule( 'souce', self.source )()
        if not self.sourceObj:
            raise Exception( "Could not instantiate source module source:{0} for client {1}".format( self.source, self.name ) )

    def prepare(self):
        """
        Generic preparations for the client, irrespective of executions or hosts.
        """
        pass

    def prepareHost(self, host):
        """
        Client specific preparations on a host, irrespective of execution.

        This usually includes send files to the host, such as binaries.

        Note that the sendToHost and sendToSeedingHost methods of the file objects have not been called, yet.
        This means that any data files are not available.

        @param  host            The host on which to prepare the client.
        """
        pass

    def prepareExecution(self, execution):
        """
        Client specific preparations for a specific execution.

        If any scripts for running the client on the host are needed, this is the place to build them.
        Be sure to take self.extraParameters into account, in that case.

        @param  execution       The execution to prepare this client for.
        """
        pass

    def start(self, execution):
        """
        Run the client for the provided execution.

        All necessary files are already available on the host at this point.
        Be sure to take self.extraParameters into account, here.

        @param  execution       The execution this client is to be run for.
        """
        pass

    def isRunning(self, execution):
        """
        Return whether the client is running for the provided execution.

        @param  execution       The execution for which to check if the client is running.

        @return True iff the client is running.
        """
        pass

    def kill(self, execution):
        """
        End the execution of the client for the provided execution.

        @param  execution       The execution for which to kill the client.
        """
        pass

    def retrieveLogs(self, execution, localLogDestination):
        """
        Retrieve client specific logs for the given execution.
        
        The logs are to be stored in the directory pointed to by localLogDestination.

        @param  execution               The execution for which to retrieve logs.
        @param  localLogDestination     A string that is the path to a local directory in which the logs are to be stored.
        """
        pass

    def cleanupExection(self, execution):
        """
        Client specific cleanup for a specific execution.

        @param  execution       The execution for which to clean up.
        """
        pass

    def cleanupHost(self, host):
        """
        Client specific cleanup for a host, irrespective of execution.

        Should also remove the client from the host as far as it wasn't already there.

        @param  host            The host on which to clean up the client.
        """
        pass

    def loadDefaultParser(self, execution):
        """
        Loads the default parser for the given execution.

        The order in which parsers are determined is this (first hit goes):
        - The parser given in the execution object
        - The parser given in the client object
        - The parser with the same name as the client
        The second and third are to be loaded by this method.
        
        @param  execution       The execution for which to load a parser.

        @return The parser instance.
        """
        pass

    def cleanup(self):
        """
        Client specific cleanup, irrespective of host or execution.
        """
        pass

    def trafficProtocol(self):
        """
        Returns the protocol on which the client will communicate.

        This value is used for setting up restricted traffic control (TC), if requested.
        Typical values are "TCP", "UDP", etc.

        When a TC module finds a protocol it can't handle explicitly, or '' as a protocol, it will fall back to
        full traffic control, i.e. all traffic between involved hosts.

        If possible, specify this correctly, otherwise leave it ''.

        @return The protocol the client uses for communication.
        """
        pass

    def trafficInboundPorts(self):
        """
        Returns a list of inbound ports on which all incoming traffic can be controlled.
        
        This list is used to set up traffic control, if requested.

        The list should only be given if it is definite: if dynamic ports can be assigned to the clients it is best
        to just return [] to force full traffic control. This also goes if the list can't be given for other reasons.

        The exact notation of ports depends on the value returned by self.trafficProtocol().

        @return A list of all ports on which incoming traffic can come, or [] if no such list can be given.
        """
        pass

    def trafficOutboundPorts(self):
        """
        Returns a list of outbound ports on which all outgoing traffic can be controlled.

        This list is used to set up traffic control, if requested.

        The list should only be given if it is definite: if dynamic ports can be assigned to the clients it is best
        to just return [] to force full traffic control. This also goes if the list can't be given for other reasons.

        The exact notation of ports depends on the value returned by self.trafficProtocol().

        @return A list of all ports from which outgoing traffic can come, or [] if no such list can be given.
        """
        pass

    @staticmethod
    def APIVersion():
        return "2.0.0-core"

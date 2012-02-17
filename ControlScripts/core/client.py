import tempfile
import os
import stat
import threading
import re
import time

from core.parsing import isValidName
from core.campaign import Campaign
from core.coreObject import coreObject

def parseError( msg ):
    raise Exception( "Parse error for client object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class client(coreObject):
    """
    The parent class for all clients.

    This object contains all the default implementations for every client.
    When subclassing client be sure to use the skeleton class as a basis: it saves you a lot of time.
    """

    extraParameters = ''        # String with extra parameters to be passed on to the client

    source = None               # String with the name of the source module to use to retrieve the client; defaults to directory which is just an on-disk accessible directory
    isRemote = False            # True iff the client source is on the remote host; this means either having the source available there or retrieving it from there
    location = None             # String with the path to the location of the client; meaning depends on the way the client is to be found
    builder = None              # String with the name of the builder module to use to build the source; None for precompiled binaries
    
    parser = None               # String with the name of the parser object to use

    builderObj = None           # The instance of the builder module requested
    sourceObj = None            # The instance of the source module requested

    pids = {}                   # The process IDs of the running clients (dictionary execution-number->PID)
    pid__lock = None            # Lock object to guard the pids dictionary

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
        coreObject.__init__(self, scenario)
        self.pid__lock = threading.Lock()
        self.pids = {}

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
                parseError( 'Client object called {0} already exists'.format( value ) )
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
            if self.parser:
                parseError( 'Parser already set for client: {0}'.format( self.parser ) )
            if not isValidName( value ):
                parseError( 'Parser name given is not a valid name: {0}'.format( value ) )
            self.parser = value
        elif key == 'builder':
            if self.builder:
                parseError( 'Builder already set for client: {0}'.format( self.builder ) )
            if not isValidName( value ):
                parseError( 'Builder name given is not a valid name: {0}'.format( value ) )
            __import__( 'modules.builder.'+value, globals(), locals(), value )
            self.builder = value
        elif key == 'source':
            if self.source:
                parseError( 'Source already set for client: {0}'.format( self.source ) )
            if not isValidName( value ):
                parseError( 'Source name given is not a valid name: {0}'.format( value ) )
            __import__( 'modules.source.'+value, globals(), locals(), value )
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
            if self.__class__.__name__ in self.scenario.getObjectsDict( 'client' ):
                raise Exception( "Client object declared at line {0} was not given a name and default name {1} was already taken".format( self.declarationLine, self.__class__.__name__ ) )
            else:
                self.name = self.__class__.__name__
        if self.parser:
            if self.parser not in self.scenario.getObjectsDict( 'parser' ):
                raise Exception( "Client {0} refers to parser named {1}, but that is not declared".format( self.name, self.parser ) )
        else:
            try:
                __import__( 'modules.parser.'+self.__class__.__name__, globals(), locals(), self.__class__.__name__ )
                Campaign.loadModule( 'parser', self.__class__.__name__ )
            except ImportError:
                raise Exception( "Client {0} has no parser specified, but falling back to default parser module parser:{1} is not possible since that module does not exist or is outdated.".format( self.name, self.__class__.__name__ ) )
        if not self.builder:
            self.builder = 'none'
            try:
                __import__( 'modules.builder.none', globals(), locals(), 'none' )
            except ImportError:
                raise Exception( "The default builder module builder:none can't be imported. This means your installation is broken." )
        builderClass = Campaign.loadModule( 'builder', self.builder )
        # PyLint really doesn't understand dynamic loading ('too many positional arguments')
        # pylint: disable-msg=E1121
        self.builderObj = builderClass(self.scenario)
        # pylint: enable-msg=E1121
        if not self.builderObj:
            raise Exception( "Could not instantiate builder module builder:{0} for client {1}".format( self.builder, self.name ) )
        if not self.source:
            self.source = 'directory'
            try:
                __import__( 'modules.source.directory', globals(), locals(), 'directory' )
            except ImportError:
                raise Exception( "The default source module source:directory can't be imported. This means your installation is broken." )
        sourceClass = Campaign.loadModule( 'source', self.source )
        # PyLint really doesn't understand dynamic loading ('too many positional arguments')
        # pylint: disable-msg=E1121
        self.sourceObj = sourceClass(self.scenario)
        # pylint: enable-msg=E1121
        if not self.sourceObj:
            raise Exception( "Could not instantiate source module source:{0} for client {1}".format( self.source, self.name ) )

    def prepare(self):
        """
        Generic preparations for the client, irrespective of executions or hosts.

        This implementation takes care of local compilation of the client, if needed.
        """
        # Build the client if it is to be built locally
        if self.isInCleanup():
            return
        if not self.isRemote:
            if self.builder:
                # Only say we're compiling if a builder was given
                print "Locally compiling client {0}".format( self.name )
            if not self.sourceObj.prepareLocal( self ):
                if self.isInCleanup():
                    return
                raise Exception( "The source of client {0} could not be prepared locally".format( self.name ) )
            if self.isInCleanup():
                return
            if not self.builderObj.buildLocal( self ):
                if self.isInCleanup():
                    return
                raise Exception( "A local build of client {0} failed".format( self.name ) )

    def prepareHost(self, host):
        """
        Client specific preparations on a host, irrespective of execution.

        This usually includes send files to the host, such as binaries.

        Note that the sendToHost and sendToSeedingHost methods of the file objects have not been called, yet.
        This means that any data files are not available.

        This implementation takes care of creating client specific directories on the host, as well as compilation
        of the client, if needed.

        @param  host            The host on which to prepare the client.
        """
        if self.isInCleanup():
            return
        # Create client specific directories
        host.sendCommand( 'mkdir -p "{0}/clients/{2}"; mkdir -p "{0}/logs/{2}"; mkdir -p "{1}/clients/{2}"; mkdir -p "{1}/logs/{2}"'.format( host.getTestDir(), host.getPersistentTestDir(), self.name ) )
        # Build the client if it is to be built remotely
        if self.isRemote:
            if self.isInCleanup():
                return
            if self.builder:
                # Only say we're compiling if a builder was given
                print "Remotely compiling client {0}".format( self.name )
            if not self.sourceObj.prepareRemote( self, host ):
                if self.isInCleanup():
                    return
                raise Exception( "The source of client {0} could not be prepared remotely on host {1}".format( self.name, host.name ) )
            if self.isInCleanup():
                return
            if not self.builderObj.buildRemote( self, host ):
                if self.isInCleanup():
                    return
                raise Exception( "A remote build of client {0} failed on host {1}".format( self.name, host.name ) )

    def getClientDir(self, host, persistent = False):
        """
        Convenience function that constructs the path to the test directory of the client on the remote host.

        This is the directory where client-specific temporary data, irrespective of execution, should be stored.

        @param  host            The remote host for to construct the path.
        @param  persistent      Set to True to get the persistent test directory (default: False).

        @return The path to the client test directory on the remote host.
        """
        if persistent:
            return "{0}/clients/{1}".format( host.getPersistentTestDir(), self.name )
        else:
            return "{0}/clients/{1}".format( host.getTestDir(), self.name )

    def getLogDir(self, host, persistent = True):
        """
        Convenience function that constructs the path to the log directory of the client on the remote host.

        This is the directory where client-specific logs, irrespective of execution, should be stored.

        @param  host            The remote host for to construct the path.
        @param  persistent      Set to True to get the persistent log directory (default: True).

        @return The path to the log directory on the remote host.
        """
        if persistent:
            return "{0}/logs/{1}".format( host.getPersistentTestDir(), self.name )
        else:
            return "{0}/logs/{1}".format( host.getTestDir(), self.name )

    def getExecutionClientDir(self, execution, persistent = False):
        """
        Convenience function that constructs the path to the test directory of the execution on the remote host.

        This is the directory where client/execution-specific temporary data should be stored.

        @param  execution       The execution for which to construct the path.
        @param  persistent      Set to True to get the persistent test directory (default: False).

        @return The path to the execution test directory on the remote host.
        """
        if persistent:
            return "{0}/clients/{1}/exec_{2}".format( execution.host.getPersistentTestDir(), self.name, execution.getNumber() )
        else:
            return "{0}/clients/{1}/exec_{2}".format( execution.host.getTestDir(), self.name, execution.getNumber() )

    def getExecutionLogDir(self, execution, persistent = True):
        """
        Convenience function that constructs the path to the log directory of the execution on the remote host.

        This is the directory where client/execution-specific logs should be stored.

        @param  execution       The execution for which to construct the path.
        @param  persistent      Set to True to get the persistent test directory (default: True).

        @return The path to the execution log directory on the remote host.
        """
        if persistent:
            return "{0}/logs/{1}/exec_{2}".format( execution.host.getPersistentTestDir(), self.name, execution.getNumber() )
        else:
            return "{0}/logs/{1}/exec_{2}".format( execution.host.getTestDir(), self.name, execution.getNumber() )

    def prepareExecution(self, execution, simpleCommandLine = None, complexCommandLine = None):
        """
        Client specific preparations for a specific execution.

        If any scripts for running the client on the host are needed, this is the place to build them.
        Be sure to take self.extraParameters into account, in that case.

        This implementation will create the client/execution specific directories.

        If one wishes, a client runner script can also be created for use with start() later on.
        To use this, fill in either the simpleCommandLine or complexCommandLine parameters. Not both!
        A client runner script will always start with changing directory to the directory where the client will
        reside on the remote host. Note that this directory is not necessarily the same directory where results
        or data should be stored. Those directories can be found via getClientDir(...), getLogDir(...),
        getExecutionClientDir(...) and getExecutionLogDir(...). The client runner script will be placed on the
        remote host as "{0}/clientRunnerScript".format( self.getExecutionClientDir( execution ) ) )
        
        The simpleCommandLine should be a single command that will be running for the duration of your client, e.g.:
            ./myClientBinary
        This can be prefixed with simple command that have a short duration, such as:
            mkdir dataDir; touch dataDir/fileToBeDownloaded; ./myClientBinary
        The simple command will be postfixed with an & to push the last command in the simpleCommandLine parameter
        to the background of the shell (in both examples myClientBinary would be running in the background, the
        mkdir and touch commands would be running in the foreground which is why they should be quick).

        If you need for more complex operations to be performed before your final client launch, or your client
        is made up of multiple phases of execution, then use the complexCommandLine parameter. An example:
            ./myClientBinaryLeechPart; ./myClientBinarySeedPart
        This example would be for an imaginary client that is first started to leech, and finishes as soon as it's
        done leeching (but leeching *does* take quite some time). Then the client is started again to start seeding.
        For the complexCommandLine the whole will be run in a subshell. Take into account that it's possible that
        only part of your command line is actually executed; as an example the framework could decide to stop all
        executions while the imaginary client is still leeching. The subshell is stopped, which in turn will stop
        the leeching client. The seeding client will never be run.

        @param  execution           The execution to prepare this client for.
        @param  simpleCommandLine   Fill in to have a client runner script ready with a simple command.
        @param  complexCommandLine  Fill in to have a client runner script ready with a complex command.
        """
        if self.isInCleanup():
            return
        # Create client/execution specific directories
        execution.host.sendCommand( 'mkdir -p "{0}/clients/{2}/exec_{3}"; mkdir -p "{0}/logs/{2}/exec_{3}"; mkdir -p "{1}/clients/{2}/exec_{3}"; mkdir -p "{1}/logs/{2}/exec_{3}"'.format( execution.host.getTestDir(), execution.host.getPersistentTestDir(), self.name, execution.getNumber() ) )

        # Build runner script, if requested
        if simpleCommandLine or complexCommandLine:
            if self.isInCleanup():
                return
            if simpleCommandLine and complexCommandLine:
                raise Exception( "The documentation explicitly states: do NOT use both simpleCommandLine and complexCommandLine together." )
            crf, clientRunner = tempfile.mkstemp()
            fileObj = os.fdopen( crf, 'w' )
            remoteClientDir = self.getClientDir( execution.host )
            if self.isRemote:
                remoteClientDir = self.sourceObj.getRemoteLocation()
            fileObj.write( 'cd "{0}"\n'.format( remoteClientDir ) )
            if simpleCommandLine:
                fileObj.write( '{0} &\n'.format( simpleCommandLine ) )
            else:
                fileObj.write( '( {0} ) &\n'.format( complexCommandLine ) )
            fileObj.write( 'echo $!\n' )
            fileObj.close()
            os.chmod( clientRunner, os.stat( clientRunner ).st_mode | stat.S_IXUSR )
            if self.isInCleanup():
                os.remove( clientRunner )
                return
            execution.host.sendFile( clientRunner, "{0}/clientRunnerScript".format( self.getExecutionClientDir( execution ) ) )
            os.remove( clientRunner )

    def start(self, execution):
        """
        Run the client for the provided execution.

        All necessary files are already available on the host at this point.
        Be sure to take self.extraParameters into account, here.

        This implementation simply tries and run the client runner script. If you didn't give a command line to
        prepareExecution(...) or didn't provide a script in the location indicated by the documentation of
        prepareExecution(...), be sure to provide your own implementation.

        The PID of the running client will be saved in the dictionary self.pids, which is guarded by
        self.pid__lock

        @param  execution       The execution this client is to be run for.
        """
        self.pid__lock.acquire()
        try:
            if self.isInCleanup():
                return
            if execution.getNumber() in self.pids:
                raise Exception( "Execution number {0} already present in list PIDs".format( execution.getNumber() ) )
            result = execution.host.sendCommand( '{0}/clientRunner'.format( self.getClientDir( execution.host ) ) )
            m = re.match( '^([0-9][0-9]*)', result )
            if not m:
                raise Exception( "Could not retrieve PID for execution {0} of client {1} on host {2} from result:\n{3}".format( execution.getNumber(), execution.client.name, execution.host.name, result ) )
            self.pids[execution.getNumber()] = m.group( 1 )
        finally:
            self.pid__lock.release()

    def isRunning(self, execution):
        """
        Return whether the client is running for the provided execution.

        This implementation will check the remote host to see if the process with PID
        self.pids[execution.getNumber()] is still running.

        @param  execution       The execution for which to check if the client is running.

        @return True iff the client is running.
        """
        res = False
        self.pid__lock.acquire()
        try:
            if execution.getNumber() not in self.pids:
                raise Exception( "Execution {0} of client {1} on host {2} is not known by PID".format( execution.getNumber(), execution.client.name, execution.host.name ) )
            print "DEBUG: Checking for PID {0}".format( self.pids[execution.getNumber()] )
            result = execution.host.sendCommand( 'kill -0 {0} && echo "Y" || echo "N"'.format( self.pids[execution.getNumber()] ) )
            res = re.match( '^Y', result ) is not None
        finally:
            self.pid__lock.release()
        return res

    def kill(self, execution):
        """
        End the execution of the client for the provided execution.

        This implementation will check the remote host to see if the process with PID
        self.pids[execution.getNumber()] is still running and while it is send signals to have it stop.

        @param  execution       The execution for which to kill the client.
        """
        # Important note: it is NOT doable to get a trace on all forks of subprocesses. One MAY be able to trace the
        # direct child, but that is inefficient (ptrace creates actual traps, not just simple notifications,
        # potentially many traps that really slow things down) and then the child's children still aren't traced. It
        # stinks, basically. In other words: it is not possible to track all children recursively of this process, so
        # we're not going to try. Child processes started by this method MUST behave correctly when sent the signals
        # to stop. This means that wrapper scripts need to trap on signals and pass them on to their detected children.
        self.pid__lock.acquire()
        try:
            if execution.getNumber() not in self.pids:
                # An execution for which no PID has been found is assumed dead and hence kill 'succeeded'
                return
            theProgramPID = self.pids[execution.getNumber()]
        finally:
            self.pid__lock.release()
        isRunning = True
        # Signal sent by kill to the process to try and stop it (0 for no signal)
        killActions = ('TERM', 0, 0, 0, 0, 0, 0, 0, 'INT', 'INT', 'KILL')
        # Time to wait after sending the signal before checking whether the process died
        killDelays =  (1,      1, 1, 2, 5, 5, 5, 5, 5,     5,     5)
        # The counter with which to walk the above arrays
        killCounter = 0
        # E.g. for killCounter = 8 the following will be done:
        # - kill -INT $pid
        # - sleep 5
        # - kill -0 $pid
        # The first line tries and kill the process using signal INT (killActions[8]).
        # The second line gives the process 5 second time (killDelays[8]).
        # The third line checks whether the process died.
        while isRunning and killCounter < len(killActions):
            if killActions[killCounter] == 0:
                execution.host.sendCommand( 'kill -{0} {1}'.format( killActions[killCounter], theProgramPID ) )
            time.sleep( killDelays[killCounter] )
            killCounter += 1
            result = execution.host.sendCommand( 'kill -0 {0} && echo "Y" || echo "N"'.format( theProgramPID ) )
            if re.match( '^Y', result ) is not None:
                self.pid__lock.acquire()
                try:
                    del self.pids[execution.getNumber()]
                finally:
                    self.pid__lock.release()
                break

    def retrieveLogs(self, execution, localLogDestination):
        """
        Retrieve client specific logs for the given execution.
        
        The logs are to be stored in the directory pointed to by localLogDestination.
        
        By default this doesn't do anything.

        @param  execution               The execution for which to retrieve logs.
        @param  localLogDestination     A string that is the path to a local directory in which the logs are to be stored.
        """
        pass

    def cleanupHost(self, host):
        """
        Client specific cleanup for a host, irrespective of execution.

        Should also remove the client from the host as far as it wasn't already there.

        @param  host            The host on which to clean up the client.
        """
        host.sendCommand( 'rm -rf "{0}/clients/{2}" "{0}/logs/{2}" "{1}/clients/{2}" "{1}/logs/{2}"'.format( host.getTestDir(), host.getPersistentTestDir(), self.name ) )

    # This method has unused argument execution; that's fine
    # pylint: disable-msg=W0613
    def loadDefaultParser(self, execution):
        """
        Loads the default parser for the given execution.

        The order in which parsers are determined is this (first hit goes):
        - The parser given in the execution object
        - The parser given in the client object
        - The parser object with the same name as the client
        - The parser with the same name as the client
        The second, third and fourth are to be loaded by this method.
        
        @param  execution       The execution for which to load a parser.

        @return The parser instance.
        """
        if self.parser:
            return self.scenario.getObjectsDict( 'parser' )[self.parser]
        elif self.__class__.__name__ in self.scenario.getObjectsDict( 'parser' ):
            return self.scenario.getObjectsDict( 'parser' )[self.__class__.__name__]
        else:
            modclass = Campaign.loadModule( 'parser', self.__class__.__name__ )
            obj = modclass()
            obj.checkSettings()
            return obj
        # pylint: enable-msg=W0613

    def cleanup(self):
        """
        Client specific cleanup, irrespective of host or execution.

        The default calls any required cleanup on the sources.
        """
        self.sourceObj.cleanup()

    def trafficProtocol(self):
        """
        Returns the protocol on which the client will communicate.

        This value is used for setting up restricted traffic control (TC), if requested.
        Typical values are "TCP", "UDP", etc.

        When a TC module finds a protocol it can't handle explicitly, or '' as a protocol, it will fall back to
        full traffic control, i.e. all traffic between involved hosts.

        If possible, specify this correctly, otherwise leave it '' (default).

        @return The protocol the client uses for communication.
        """
        return ''

    def trafficInboundPorts(self):
        """
        Returns a list of inbound ports on which all incoming traffic can be controlled.
        
        This list is used to set up traffic control, if requested.

        The list should only be given if it is definite: if dynamic ports can be assigned to the clients it is best
        to just return () to force full traffic control. This also goes if the list can't be given for other reasons.

        The exact notation of ports depends on the value returned by self.trafficProtocol().

        The default implementation just returns [].

        @return A list of all ports on which incoming traffic can come, or [] if no such list can be given.
        """
        return []

    def trafficOutboundPorts(self):
        """
        Returns a list of outbound ports on which all outgoing traffic can be controlled.

        This list is used to set up traffic control, if requested.

        The list should only be given if it is definite: if dynamic ports can be assigned to the clients it is best
        to just return () to force full traffic control. This also goes if the list can't be given for other reasons.

        The exact notation of ports depends on the value returned by self.trafficProtocol().

        The default implementation just returns [].

        @return A list of all ports from which outgoing traffic can come, or [] if no such list can be given.
        """
        return []

    def getModuleType(self):
        """
        Return the moduleType string.
        
        @return    The module type.
        """
        return 'client'
    
    def getName(self):
        """
        Return the name of the object.
        
        @return    The name.
        """
        return self.name

    @staticmethod
    def APIVersion():
        return "2.0.0-core"

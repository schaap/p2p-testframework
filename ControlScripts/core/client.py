import tempfile
import os
import stat
import threading
import re
import time
import posixpath

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
    
    parsers = None              # List of strings with the names of the parser objects to use

    builderObj = None           # The instance of the builder module requested
    sourceObj = None            # The instance of the source module requested

    pids = {}                   # The process IDs of the running clients (dictionary execution-number->PID)
    pid__lock = None            # Lock object to guard the pids dictionary
    
    profile = False             # Flag to include external profiling code
    logStart = False            # Flag to include logging of the starting time of the client on the remote host

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
            if not isValidName( value ):
                parseError( 'Parser name given is not a valid name: {0}'.format( value ) )
            if not self.parsers:
                self.parsers = []
            self.parsers.append( value )
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
        elif key == 'profile':
            self.profile = ( value != '' )
        elif key == 'logStart':
            self.logStart = ( value != '' )
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
        if not self.builder:
            try:
                __import__( 'modules.builder.none', globals(), locals(), 'none' )
            except ImportError:
                raise Exception( "The default builder module builder:none can't be imported. This means your installation is broken." )
            builderClass = Campaign.loadModule( 'builder', 'none' )
        else:
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

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        if self.parsers:
            for parser in self.parsers:
                if parser not in self.scenario.getObjectsDict( 'parser' ):
                    try:
                        Campaign.loadModule( 'parser', parser )
                    except ImportError:
                        raise Exception( "Client {0} refers to parser named {1}, but that is not declared nor the name of parser module".format( self.name, parser ) )
        else:
            try:
                __import__( 'modules.parser.'+self.__class__.__name__, globals(), locals(), self.__class__.__name__ )
                Campaign.loadModule( 'parser', self.__class__.__name__ )
            except ImportError:
                raise Exception( "Client {0} has no parser specified, but falling back to default parser module parser:{1} is not possible since that module does not exist or is outdated.".format( self.name, self.__class__.__name__ ) )

    def getByArguments(self, argumentString):
        """
        Selects a client object by specific arguments.
        
        The arguments can be used to return a different client object than the one this is called on.
        
        This is called for the execution's client parameter's selection syntax:
            client=name@args
        Invariant: self.scenario.getObjectsDict('client')[name] == self and argumentString == args
        
        The primary use of selection by arguments is to select a single client object from a client object that multiplies itself.
        
        The default implementation returns self for no arguments and raises an exception for any other argument.
        
        @param     argumentString    The arguments passed in the selection
        
        @return    A single, specific client object.
        """
        if argumentString != '':
            raise Exception( 'Client {0} does not support object selection by argument'.format( self.getName() ) )
        return self
    
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
        if self.isInCleanup():
            return
        # Check sanity of getBinaryLayout() and getSourceLayout(), as well as create directories remotely
        if self.getBinaryLayout():
            if self.isInCleanup():
                return
            if self.builder and self.getSourceLayout():
                binariesInSources = [entry[1] for entry in self.getSourceLayout()]
                dirCount = 0
                for entry in self.getBinaryLayout():
                    if entry[-1:] == '/':
                        dirCount += 1
                    elif not entry in binariesInSources:
                        raise Exception( "Client module {0} has both getBinaryLayout() and getSourceLayout(), but entry {1} in the binaries is not present in the sources. That's wrong.".format( self.__class__.__name__, entry ) )
                if len(binariesInSources) + dirCount != len(self.getSourceLayout()):
                    raise Exception( "Client module {0} has both getBinaryLayout() and getSourceLayout(), but not every entry in the sources corresponds to an entry in the binaries. That's wrong.".format( self.__class__.__name__ ) )
            for entry in self.getBinaryLayout():
                if entry[:-1] == '/':
                    if self.isInCleanup():
                        return
                    host.sendCommand( 'mkdir -p "{0}/{1}"'.format( self.getClientDir(host), entry ) )
        # Make sure client is uploaded/present
        if self.isRemote:
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
            # Check and shuffle files
            if self.getBinaryLayout():
                if self.isInCleanup():
                    return
                if self.builder and self.getSourceLayout():
                    for entry in self.getSourceLayout():
                        if self.isInCleanup():
                            return
                        if self.sourceObj.remoteLocation( self, host ) == self.getClientDir(host) and entry[0] == entry[1]:
                            res = host.sendCommand( '[ -f "{0}/{1}" ] && echo "OK"'.format( self.sourceObj.remoteLocation( self, host ), entry[0] ) )
                        else:
                            res = host.sendCommand( '[ -f "{0}/{1}" ] && cp "{0}/{1}" "{2}/{3}" && echo "OK"'.format( self.sourceObj.remoteLocation( self, host ), entry[0], self.getClientDir(host), entry[1] ) )
                        if res != "OK":
                            raise Exception( "Client {0} failed to prepare host {1}: checking for existence of file {2} after building and copying it to {3} (if needed) failed. Response: {4}.".format( self.name, host.name, entry[0], entry[1], res ) )
                elif not self.builder:
                    for entry in self.getBinaryLayout():
                        if entry[-1:] == '/':
                            continue
                        if self.isInCleanup():
                            return
                        res = host.sendCommand( '[ -f "{0}/{1}" ] && echo "OK"'.format( self.sourceObj.remoteLocation( self, host ), entry ) )
                        if res != "OK":
                            raise Exception( "Client {0} failed to prepare host {1}: checking for existence of file {2} after preparing remotely failed. Response: {3}.".format( self.name, host.name, entry, res ) )
        else:
            if self.getBinaryLayout():
                if self.builder:
                    # Upload from source locations
                    for entry in self.getSourceLayout():
                        if self.isInCleanup():
                            return
                        if not os.path.exists( os.path.join( self.sourceObj.localLocation( self ), entry[0] ) ):
                            raise Exception( "Client {0} failed to prepare host {1}: local compilation misses file {2}".format( self.name, host.name, entry[0] ) )
                        host.sendFile( os.path.join( self.sourceObj.localLocation( self ), entry[0] ), '{0}/{1}'.format( self.getClientDir(host), entry[1] ), True )
                else:
                    # Upload from binary locations
                    for entry in self.getBinaryLayout():
                        if self.isInCleanup():
                            return
                        if not os.path.exists( os.path.join( self.sourceObj.localLocation( self ), entry ) ):
                            raise Exception( "Client {0} failed to prepare host {1}: local binary location misses file {2}".format( self.name, host.name, entry ) )
                        host.sendFile( os.path.join( self.sourceObj.localLocation( self ), entry ), '{0}/{1}'.format( self.getClientDir(host), entry ), True )
        # Upload extra files
        if self.getExtraUploadLayout():
            for entry in self.getExtraUploadLayout():
                if entry[0] == '':
                    if entry[1][-1:] != '/':
                        raise Exception( "Client module {0} has an entry in the extra upload layout which has no local location, but is not a remote directory. This is wrong.".format( self.__class__.__name__ ) )
                    host.sendCommand( 'mkdir -p "{0}/{1}"'.format( self.getClientDir(host), entry[1] ) )
            for entry in self.getExtraUploadLayout():
                if entry[0] != '':
                    if not os.path.exists( entry[0] ):
                        raise Exception( "Client module {0} has an entry to upload file {1}, but that doesn't exist locally.".format( self.__class__.__name__, entry[0] ) )
                    host.sendFile( entry[0], "{0}/{1}".format( self.getClientDir(host), entry[1] ), True )
        # Check availability of /proc if profiling is requested
        if self.profile:
            res = host.sendCommand( 'cat /proc/$$/stat && echo "OK" || echo "NO"' )
            if res.splitlines()[-1] == 'OK':
                pass
            elif res.splitlines()[-1] == 'NO':
                raise Exception( "Client {0} has requested profiling, but a usable /proc seems not to be available on host {1}.".format( self.name, host.name ) )
            else:
                raise Exception( "Client {0} has requested profiling, but a strange response was received when testing availability of /proc on host {1}: {2}".format( self.name, host.name, res ) )

    def getClientDir(self, host, persistent = False):
        """
        Convenience function that constructs the path to the test directory of the client on the remote host.

        This is the directory where client-specific temporary data, irrespective of execution, should be stored.

        During cleanup this may return None! 

        @param  host            The remote host for to construct the path.
        @param  persistent      Set to True to get the persistent test directory (default: False).

        @return The path to the client test directory on the remote host.
        """
        if persistent:
            if host.getPersistentTestDir():
                return "{0}/clients/{1}".format( host.getPersistentTestDir(), self.name )
        else:
            if host.getTestDir():
                return "{0}/clients/{1}".format( host.getTestDir(), self.name )
        return None

    def getLogDir(self, host, persistent = True):
        """
        Convenience function that constructs the path to the log directory of the client on the remote host.

        This is the directory where client-specific logs, irrespective of execution, should be stored.

        During cleanup this may return None! 

        @param  host            The remote host for to construct the path.
        @param  persistent      Set to True to get the persistent log directory (default: True).

        @return The path to the log directory on the remote host.
        """
        if persistent:
            if host.getPersistentTestDir():
                return "{0}/logs/{1}".format( host.getPersistentTestDir(), self.name )
        else:
            if host.getTestDir():
                return "{0}/logs/{1}".format( host.getTestDir(), self.name )
        return None

    def getExecutionClientDir(self, execution, persistent = False):
        """
        Convenience function that constructs the path to the test directory of the execution on the remote host.

        This is the directory where client/execution-specific temporary data should be stored.

        During cleanup this may return None! 

        @param  execution       The execution for which to construct the path.
        @param  persistent      Set to True to get the persistent test directory (default: False).

        @return The path to the execution test directory on the remote host.
        """
        if persistent:
            if execution.host.getPersistentTestDir():
                return "{0}/clients/{1}/exec_{2}".format( execution.host.getPersistentTestDir(), self.name, execution.getNumber() )
        else:
            if execution.host.getTestDir():
                return "{0}/clients/{1}/exec_{2}".format( execution.host.getTestDir(), self.name, execution.getNumber() )
        return None

    def getExecutionLogDir(self, execution, persistent = True):
        """
        Convenience function that constructs the path to the log directory of the execution on the remote host.

        This is the directory where client/execution-specific logs should be stored.

        During cleanup this may return None! 

        @param  execution       The execution for which to construct the path.
        @param  persistent      Set to True to get the persistent test directory (default: True).

        @return The path to the execution log directory on the remote host.
        """
        if persistent:
            if execution.host.getPersistentTestDir():
                return "{0}/logs/{1}/exec_{2}".format( execution.host.getPersistentTestDir(), self.name, execution.getNumber() )
        else:
            if execution.host.getTestDir():
                return "{0}/logs/{1}/exec_{2}".format( execution.host.getTestDir(), self.name, execution.getNumber() )
        return None

    def prepareExecution(self, execution, simpleCommandLine = None, complexCommandLine = None, linkDataIn = None):
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
        
        For seeders it's very common to have their data linked for the specific execution. Setting linkDataIn to
        the path to a remote directory will add commands before your simple or complex command line to copy the
        directory structure of all the files to be seeded and to link all the files into that directory structure.
        The data directory will be created if needed. Setting linkDataIn does nothing if the execution is not a
        seeder and will raise an Exception is neither simpleCommandLine nor complexCommandLine is set.

        @param  execution           The execution to prepare this client for.
        @param  simpleCommandLine   Fill in to have a client runner script ready with a simple command.
        @param  complexCommandLine  Fill in to have a client runner script ready with a complex command.
        @param  linkDataIn          Set this to the remote path where all data for the client is to be linked.
        """
        if self.isInCleanup():
            return
        # Create client/execution specific directories
        execution.host.sendCommand( 'mkdir -p "{0}/clients/{2}/exec_{3}"; mkdir -p "{0}/logs/{2}/exec_{3}"; mkdir -p "{1}/clients/{2}/exec_{3}"; mkdir -p "{1}/logs/{2}/exec_{3}"'.format( execution.host.getTestDir(), execution.host.getPersistentTestDir(), self.name, execution.getNumber() ) )

        prependCommands = ''
        if linkDataIn is not None:
            if simpleCommandLine is None and complexCommandLine is None:
                raise Exception( "linkDataIn is set, but neither simpleCommandLine not complexCommandLine is set: error in calling code" )
            if execution.isSeeder():
                res = execution.host.sendCommand( '([ -e "{0}" ] && (([ -d "{0}" ] && echo "D") || echo "E")) || (mkdir -p "{0}" && echo "D")'.format( linkDataIn ) )
                isDir = res.splitlines()[-1]
                if isDir != 'D':
                    if isDir == 'F':
                        raise Exception( 'linkDataIn for execution {2} client {1} is set to {0} but that already exists and is not a directory'.format( linkDataIn, self.name, execution.getNumber() ) )
                    else:
                        raise Exception( "Checking linkDataIn directory {0} for existence and creating if needed in execution {2} of client {3}; got unexpected response {1}".format( linkDataIn, res, execution.getNumber(), self.name ) )
                prependCommands = " ".join( ['mkdir -p "{0}";'.format(posixpath.join(linkDataIn, *d[1])) for d in execution.getDataDirTree()])
                prependCommands += " ".join( ['ln "{0}" "{1}";'.format( posixpath.join(*d[0]), posixpath.join(linkDataIn, *d[1])) for d in execution.getDataFileTree()])
                prependCommands += "\n"

        # Build runner script, if requested
        if simpleCommandLine or complexCommandLine:
            if self.isInCleanup():
                return
            if simpleCommandLine and complexCommandLine:
                raise Exception( "The documentation explicitly states: do NOT use both simpleCommandLine and complexCommandLine together." )
            crf = None
            clientRunner = None
            fileObj = None
            try:
                crf, clientRunner = tempfile.mkstemp()
                fileObj = os.fdopen( crf, 'w' )
                crf = None
                remoteClientDir = self.getClientDir( execution.host )
                if self.isRemote:
                    remoteClientDir = self.sourceObj.remoteLocation(self, execution.host)
                fileObj.write( 'cd "{0}"\n'.format( remoteClientDir ) )
                if self.logStart:
                    fileObj.write( 'date > {0}/starttime.log\n'.format( self.getExecutionLogDir(execution) ) )
                if len(prependCommands) > 0:
                    fileObj.write( prependCommands )
                if simpleCommandLine:
                    if execution.host.getAddress() != '':
                        if execution.isSeeder:
                            print "DEBUG: Preparing execution {0} of seeder client:{4} {1} on host {2} ({5}) with simple command line:\n{3}".format( execution.getNumber(), self.name, execution.host.name, simpleCommandLine, self.__class__.__name__, execution.host.getAddress() )
                        else:
                            print "DEBUG: Preparing execution {0} of leecher client:{4} {1} on host {2} ({5}) with simple command line:\n{3}".format( execution.getNumber(), self.name, execution.host.name, simpleCommandLine, self.__class__.__name__, execution.host.getAddress() )
                    else:
                        if execution.isSeeder:
                            print "DEBUG: Preparing execution {0} of seeder client:{4} {1} on host {2} with simple command line:\n{3}".format( execution.getNumber(), self.name, execution.host.name, simpleCommandLine, self.__class__.__name__ )
                        else:
                            print "DEBUG: Preparing execution {0} of leecher client:{4} {1} on host {2} with simple command line:\n{3}".format( execution.getNumber(), self.name, execution.host.name, simpleCommandLine, self.__class__.__name__ )
                    fileObj.write( '{0} &\n'.format( simpleCommandLine ) )
                else:
                    if execution.host.getAddress() != '':
                        if execution.isSeeder:
                            print "DEBUG: Preparing execution {0} of seeder client:{4} {1} on host {2} ({5}) with complex command line:\n{3}".format( execution.getNumber(), self.name, execution.host.name, complexCommandLine, self.__class__.__name__, execution.host.getAddress() )
                        else:
                            print "DEBUG: Preparing execution {0} of leecher client:{4} {1} on host {2} ({5}) with complex command line:\n{3}".format( execution.getNumber(), self.name, execution.host.name, complexCommandLine, self.__class__.__name__, execution.host.getAddress() )
                    else:
                        if execution.isSeeder:
                            print "DEBUG: Preparing execution {0} of seeder client:{4} {1} on host {2} with complex command line:\n{3}".format( execution.getNumber(), self.name, execution.host.name, complexCommandLine, self.__class__.__name__ )
                        else:
                            print "DEBUG: Preparing execution {0} of leecher client:{4} {1} on host {2} with complex command line:\n{3}".format( execution.getNumber(), self.name, execution.host.name, complexCommandLine, self.__class__.__name__ )
                    fileObj.write( '( {0} ) &\n'.format( complexCommandLine ) )
                print ""
                if self.profile:
                    fileObj.write( 'myPid=$!\n' )
                    fileObj.write( 'echo $myPid\n' )
                    # FIXME: CLK_TCK is deprecated, but the linux kernel uses it for stats??? - needs sysconf(), really
                    fileObj.write( '(getconf CLK_TCK 2>/dev/null || echo 100) >> {0}/cpu.log\n'.format( self.getExecutionLogDir(execution) ) )
                    fileObj.write( '(while kill -0 $myPid > /dev/null 2> /dev/null; do ' )
                    fileObj.write( 'date "+%y-%m-%d %H:%M:%S.%N" >> {0}/cpu.log; '.format( self.getExecutionLogDir(execution) ) )
                    fileObj.write( 'cat /proc/$myPid/stat 2>&1 >> {0}/cpu.log; '.format( self.getExecutionLogDir(execution) ) )
                    fileObj.write( 'ps -p $myPid -o vsz= -o rss= 2>&1 >> {0}/cpu.log; '.format( self.getExecutionLogDir(execution) ) )
                    fileObj.write( 'sleep 1;  done) &\n' )
                else:
                    fileObj.write( 'echo $!\n' )
                fileObj.close()
                fileObj = None

                os.chmod( clientRunner, os.stat( clientRunner ).st_mode | stat.S_IXUSR )
                if self.isInCleanup():
                    return
                execution.host.sendFile( clientRunner, "{0}/clientRunnerScript".format( self.getExecutionClientDir( execution ) ) )
            finally:
                if fileObj:
                    fileObj.close()
                elif crf is not None:
                    os.close(crf)
                if clientRunner:
                    os.remove( clientRunner )

    def start(self, execution):
        """
        Run the client for the provided execution.
        
        It is NOT advised to overwrite this method, nor should it be necessary.

        All necessary files are already available on the host at this point.
        Be sure to take self.extraParameters into account, here.

        This implementation simply tries and run the client runner script. If you didn't give a command line to
        prepareExecution(...) or didn't provide a script in the location indicated by the documentation of
        prepareExecution(...), be sure to provide your own implementation.

        The PID of the running client will be saved in the dictionary self.pids, which is guarded by
        self.pid__lock
        
        PLEASE NOTE: This method *must* be a generator method that calls yield exactly twice: once after sending
        the command and once at the end.

        @param  execution       The execution this client is to be run for.
        """
        try:
            self.pid__lock.acquire() 
            if self.isInCleanup():
                try:
                    self.pid__lock.release()
                except RuntimeError:
                    pass
                yield
                yield
                return
            if execution.getNumber() in self.pids:
                raise Exception( "Execution number {0} already present in list PIDs".format( execution.getNumber() ) )
        finally:
            try:
                self.pid__lock.release()
            except RuntimeError:
                pass
        execution.host.sendCommandAsyncStart( '{0}/clientRunnerScript'.format( self.getExecutionClientDir( execution ) ), execution.getExecutionConnection() )
        yield
        result = execution.host.sendCommandAsyncEnd( execution.getExecutionConnection() )
        #result = execution.host.sendCommand( '{0}/clientRunnerScript'.format( self.getExecutionClientDir( execution ) ), execution.getRunnerConnection() )
        m = re.match( '^([0-9][0-9]*)', result )
        if not m:
            raise Exception( "Could not retrieve PID for execution {0} of client {1} on host {2} from result:\n{3}".format( execution.getNumber(), execution.client.name, execution.host.name, result ) )
        try:
            self.pid__lock.acquire() 
            self.pids[execution.getNumber()] = m.group( 1 )
        finally:
            try:
                self.pid__lock.release()
            except RuntimeError:
                pass
        yield
    
    def hasStarted(self, execution):
        """
        Returns whether the client has actually been started.
        
        If this method returns True, then no problems should arise when calling isRunning.
        
        @return True iff the client has been started in the past.
        """
        try:
            self.pid__lock.acquire()
            return execution.getNumber() in self.pids
        finally:
            try:
                self.pid__lock.release()
            except RuntimeError:
                pass

    def isRunning(self, execution, reuseConnection = None ):
        """
        Return whether the client is running for the provided execution.

        This implementation will check the remote host to see if the process with PID
        self.pids[execution.getNumber()] is still running.

        @param  execution       The execution for which to check if the client is running.
        @param  reuseConnection If not None, force use of the specified connection object.

        @return True iff the client is running.
        """
        pid = ''
        try:
            self.pid__lock.acquire()
            if execution.getNumber() not in self.pids:
                Campaign.logger.log( "Execution {0} of client {1} on host {2} is not known by PID when checking for isRunning. Ignoring.".format( execution.getNumber(), execution.client.name, execution.host.name ) )
                return False
            pid = self.pids[execution.getNumber()]
        finally:
            try:
                self.pid__lock.release()
            except RuntimeError:
                pass
        connection = reuseConnection
        if not connection:
            connection = execution.getRunnerConnection()
        result = execution.host.sendCommand( 'kill -0 {0} && echo "Y" || echo "N"'.format( pid ), connection )
        return re.match( '^Y', result ) is not None

    def kill(self, execution, reuseConnection = None ):
        """
        End the execution of the client for the provided execution.

        This implementation will check the remote host to see if the process with PID
        self.pids[execution.getNumber()] is still running and while it is send signals to have it stop.

        @param  execution       The execution for which to kill the client.
        @param  reuseConnection If not None, force use of the specified connection object.
        """
        # Important note: it is NOT doable to get a trace on all forks of subprocesses. One MAY be able to trace the
        # direct child, but that is inefficient (ptrace creates actual traps, not just simple notifications,
        # potentially many traps that really slow things down) and then the child's children still aren't traced. It
        # stinks, basically. In other words: it is not possible to track all children recursively of this process, so
        # we're not going to try. Child processes started by this method MUST behave correctly when sent the signals
        # to stop. This means that wrapper scripts need to trap on signals and pass them on to their detected children.
        try:
            self.pid__lock.acquire()
            if execution.getNumber() not in self.pids:
                # An execution for which no PID has been found is assumed dead and hence kill 'succeeded'
                return
            theProgramPID = self.pids[execution.getNumber()]
        finally:
            try:
                self.pid__lock.release()
            except RuntimeError:
                pass
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
        try:
            connection = reuseConnection
            if not connection:
                connection = execution.getRunnerConnection()
            for killCounter in range( 0, len(killActions) ):
                if killActions[killCounter] != 0:
                    execution.host.sendCommand( 'kill -{0} {1}'.format( killActions[killCounter], theProgramPID ), connection )
                time.sleep( killDelays[killCounter] )
                result = execution.host.sendCommand( 'kill -0 {0} 2>/dev/null && echo "Y" || echo "N"'.format( theProgramPID ), connection )
                if re.match( '^Y', result ) is None:
                    try:
                        self.pid__lock.acquire()
                        del self.pids[execution.getNumber()]
                    finally:
                        try:
                            self.pid__lock.release()
                        except RuntimeError:
                            pass
                    break
            else:
                Campaign.logger.log( "Warning! Execution {0} of client {1} on host {2} (PID {3}) is probably still running.".format( execution.getNumber(), self.name, execution.host.name, theProgramPID ) )
                print "Warning! Execution {0} of client {1} on host {2} (PID {3}) is probably still running.".format( execution.getNumber(), self.name, execution.host.name, theProgramPID )
        except Exception as exc:
            Campaign.logger.log( "Warning! Execution {0} of client {1} on host {2} (PID {3}) is probably still running.".format( execution.getNumber(), self.name, execution.host.name, theProgramPID ) )
            print "Warning! Execution {0} of client {1} on host {2} (PID {3}) is probably still running.".format( execution.getNumber(), self.name, execution.host.name, theProgramPID )
            raise exc

    def retrieveLogs(self, execution, localLogDestination):
        """
        Retrieve client specific logs for the given execution.
        
        The logs are to be stored in the directory pointed to by localLogDestination.
        
        By default this doesn't do anything.

        @param  execution               The execution for which to retrieve logs.
        @param  localLogDestination     A string that is the path to a local directory in which the logs are to be stored.
        """
        if self.getExecutionLogDir(execution):
            if self.profile:
                execution.host.getFile( '{0}/cpu.log'.format( self.getExecutionLogDir(execution) ), os.path.join( localLogDestination, 'cpu.log' ) )
            if self.logStart:
                execution.host.getFile( '{0}/starttime.log'.format( self.getExecutionLogDir(execution) ), os.path.join( localLogDestination, 'starttime.log' ) )

    def cleanupHost(self, host, reuseConnection = None):
        """
        Client specific cleanup for a host, irrespective of execution.

        Should also remove the client from the host as far as it wasn't already there.

        @param  host            The host on which to clean up the client.
        @param  reuseConnection If not None, force the use of this connection for command to the host.
        """
        connection = True
        if reuseConnection:
            connection = reuseConnection
        if host.getTestDir() and host.getPersistentTestDir():
            host.sendCommand( 'rm -rf "{0}/clients/{2}" "{0}/logs/{2}" "{1}/clients/{2}" "{1}/logs/{2}"'.format( host.getTestDir(), host.getPersistentTestDir(), self.name ), connection )
        elif host.getTestDir():
            host.sendCommand( 'rm -rf "{0}/clients/{1}" "{0}/logs/{1}"'.format( host.getTestDir(), self.name ), connection )
        elif host.getPersistentTestDir():
            host.sendCommand( 'rm -rf "{0}/clients/{1}" "{0}/logs/{1}"'.format( host.getPersistentTestDir(), self.name ), connection )

    # This method has unused argument execution; that's fine
    # pylint: disable-msg=W0613
    def loadDefaultParsers(self, execution):
        """
        Loads the default parsers for the given execution.

        The order in which parsers are determined is this (first hit goes):
        - The parsers given in the execution object
        - The parsers given in the client object
        - The parser object with the same name as the client
        - The parser with the same name as the client
        The second, third and fourth are to be loaded by this method.
        
        @param  execution       The execution for which to load a parser.

        @return The list of parser instances.
        """
        if self.parsers:
            plist = []
            pdict = self.scenario.getObjectsDict( 'parser' )
            for parser in self.parsers:
                if parser in pdict:
                    plist.append( pdict[parser] )
                else:
                    modclass = Campaign.loadModule( 'parser', parser )
                    # *Sigh*. PyLint. Dynamic loading!
                    # pylint: disable-msg=E1121
                    obj = modclass( self.scenario )
                    # pylint: enable-msg=E1121
                    obj.checkSettings()
                    plist.append( obj )
            return plist
        elif self.__class__.__name__ in self.scenario.getObjectsDict( 'parser' ):
            return [self.scenario.getObjectsDict( 'parser' )[self.__class__.__name__]]
        else:
            modclass = Campaign.loadModule( 'parser', self.__class__.__name__ )
            # *Sigh*. PyLint. Dynamic loading!
            # pylint: disable-msg=E1121
            obj = modclass( self.scenario )
            # pylint: enable-msg=E1121
            obj.checkSettings()
            return [obj]
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
    
    def getBinaryLayout(self):
        """
        Return a list of binaries that need to be present on the server.
        
        Add directories to be created as well, have them end with a /.
        
        Return None to handle the uploading or moving yourself.
        
        @return    List of binaries.
        """
        return None
    
    def getSourceLayout(self):
        """
        Return a list of tuples that describe the layout of the source.
        
        Each tuple in the list corresponds to (sourcelocation, binarylocation),
        where the binarylocation is one of the entries returned by getBinaryLayout().
        
        Each entry in getBinaryLayout() that is not directory needs to be present.
        
        Return None to handle the uploading or moving yourself.
        
        @return    The layout of the source.
        """
        return None
    
    def getExtraUploadLayout(self):
        """
        Returns a list of local files that are always uploaded to the remote host.
        
        Each tuple in the list corresponds to (locallocation, remotelocation),
        where the first is the location of the local file and the second is the
        relative location of the file on the remote host (relative to the location
        of the client's directory).
        
        Add directories to be created as well, have their locallocation be '' and 
        have their remotelocation end with a /.
        
        This method is especially useful for wrappers and the like.
        
        Return None to handle the uploading yourself.
        
        @return    The files that are always to be uploaded.
        """
        return None
    
    def isSideService(self):
        """
        Returns whether this client is an extra service needed for scenarios,
        rather than an actual client iself.
        
        Side services are clients such as torrent trackers or HTTP servers that only
        provide files to actually running clients.
        
        If a client is a side service it will be ignored for several purposes, such
        as when determining if all clients have finished yet and when retrieving and
        processing logs.
        
        @return     True iff this client is a side serice.
        """
        return False

    @staticmethod
    def APIVersion():
        return "2.4.0-core"

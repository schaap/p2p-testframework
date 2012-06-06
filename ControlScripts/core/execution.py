from core.parsing import isValidName, isPositiveFloat, isPositiveInt
from core.campaign import Campaign
from core.coreObject import coreObject

def parseError( msg ):
    raise Exception( "Parse error for execution object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

def _getDataTree(host, number, _type, files):
    """
    Internal implementation method for getDataDirTree() (type == 'd') and getDataFileTree() (type == 'f').
    """
    l = []
    for f in host.seedingFiles:
        if f not in files:
            continue
        # Get the data's structure. If empty, don't bother with the rest
        if _type == 'd':
            t = f.getDataDirTree()
        else:
            t = f.getDataFileTree()
        if len(t) == 0:
            continue
        # First get the actual data directory in which the data for f reside, and convert it to list notation
        basedir_s = f.getDataDir(host)
        basedir = []
        if basedir_s is not None:
            p = 0
            if basedir_s[0] == '/':
                basedir.append( '/' )
                p = 1
            while p < len(basedir_s):
                np = basedir_s.find('/', p)
                if np == -1:
                    basedir.append( basedir_s[p:] )
                    break
                basedir.append( basedir_s[p:np] )
                p = np + 1
        # Check the unicity of each element in t and build the results 
        for d in t:
            for ed in l:
                if ed[1] == d:
                    if _type == 'd':
                        raise Exception( "Duplicate relative data directory found in files for execution {0}.".format( number ) )
                    else:
                        raise Exception( "Duplicate relative data file found in files for execution {0}.".format( number ) )
            l.append( (basedir + d, d) )
    return l
    
class execution(coreObject):
    """
    An execution object.

    Executions are the combination of host, client and files. Their meaning is that the client is executed once on
    the host to transfer the files.

    Subclasses of execution do not exist.
    """

    hostName = None             # The name of the host object
    clientName = None           # The name of the client object
    fileNames = None            # The names of the file objects
    parserNames = None          # The list of names of the parser objects

    host = None                 # The host object
    client = None               # The client object
    # Yes, that's a warning below. That's OK, though.
    files = None                # The files array, consist of multiple file objects
    parsers = None              # The list of parser objects

    seeder = False              # True iff this execution is a seeder

    number = None               # The number of this execution
    
    runnerConnection = None     # A specific connection to use for querying a client in parallel
    executionConnection = None  # A specific connection to use for execution a client
    
    timeout = None              # A number of seconds to wait before starting the client (float)
    
    keepSeeding = False         # Set to True to have this execution keep on seeding when all leechers are done

    multiply = None             # The number of copies of this execution to be created (None for 1)

    # @static
    executionCount = 0          # The total number of executions

    def __init__(self, scenario):
        """
        Initialization of an execution object.

        @param  scenario        The ScenarioRunner object this execution object is part of.
        """
        coreObject.__init__(self, scenario)
        self.number = execution.executionCount
        execution.executionCount += 1
    
    def copyExecution(self, other):
        """
        Copies all values of the other execution object into this execution object.
        
        This method can be used as the basis for duplicating executions on-the-fly.
        Be sure to register the new execution correctly with the scenario and to call
        .checkSettings() and possible .resolveNames() after changing values.
        
        You may also want to cross-reference the objects to make sure all objects in
        the execution are up to date, although if you need to do this you should rather
        be rethinking where you're duplicating the execution: you're probably too late
        in the flow of the scenario.
        
        Variables not copied:
        - number
        - runnerConnection
        - executionConnection
        - parent variables
        
        @param  other          The execution object from which the values are to be copied.
        """
        self.hostName = other.hostName
        self.clientName = other.clientName
        if other.fileNames:
            self.fileNames = list(other.fileNames)
        else:
            self.fileNames = None
        if other.parserNames:
            self.parserNames = list(other.parserNames)
        else:
            self.parserNames = None
        self.host = other.host
        self.client = other.client
        if other.files:
            self.files = list(other.files)
        else:
            self.files = None
        if other.parsers:
            self.parsers = list(other.parsers)
        else:
            self.parsers = None
        self.timeout = other.timeout
        self.keepSeeding = other.keepSeeding
        self.seeder = other.seeder

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
        if key == 'host':
            if self.hostName:
                parseError( "A host was already given: {0}".format( self.hostName ) )
            if not isValidName( value ):
                if not isValidName( value[:value.find('@')]):
                    parseError( "{0} is not a valid host object name".format( value ) )
            self.hostName = value
        elif key == 'client':
            if self.clientName:
                parseError( "A client was already given: {0}".format( self.clientName ) )
            if not isValidName( value ):
                if not isValidName( value[:value.find('@')]):
                    parseError( "{0} is not a valid client object name".format( value ) )
            self.clientName = value
        elif key == 'file':
            if not isValidName( value ):
                if not isValidName( value[:value.find('@')]):
                    parseError( "{0} is not a valid file object name".format( value ) )
            if not self.fileNames:
                self.fileNames = [value]
            elif value not in self.fileNames:
                self.fileNames.append(value)
            else:
                Campaign.logger.log( "Warning for execution object on line {0}: file object {1} already added".format( Campaign.currentLineNumber, value ) )
        elif key == 'parser':
            if not isValidName( value ):
                parseError( "{0} is not a valif parser object name".format( value ) )
            if not self.parserNames:
                self.parserNames = []
            self.parserNames.append( value )
        elif key == 'seeder':
            if value != '':
                self.seeder = True
        elif key == 'timeout':
            if self.timeout != None:
                parseError( "The timeout was already set: {0}".format( self.timeout ) )
            if not isPositiveFloat( value ):
                parseError( "The timeout must be a non-negative floating point number." )
            self.timeout = float(value)
        elif key == 'keepSeeding':
            if value != '':
                self.keepSeeding = False
        elif key == 'multiply':
            if self.multiply is not None:
                parseError( "Multiply already set: {0}".format( self.multiply ) )
            if not isPositiveInt(value, True):
                parseError( "The multiply parameter must be a non-zero positive integer." )
            self.multiply = int(value)
        else:
            parseError( 'Unknown parameter name: {0}'.format( key ) )

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        if not self.hostName:
            raise Exception( "Execution defined at line {0} must have a host.".format( self.declarationLine ) )
        if not self.clientName:
            raise Exception( "Execution defined at line {0} must have a client.".format( self.declarationLine ) )
        if self.timeout == None:
            self.timeout = 0
        if not self.isSeeder() and self.keepSeeding:
            Campaign.logger.log( "Warning: Execution define at line {0} is declared to keep seeding, but it's not a seeder.".format( self.declarationLine ))
        if self.multiply is not None and self.multiply > 1:
            m = self.multiply
            self.multiply = None
            for _ in range( 1, m ):
                e = execution( self.scenario )
                e.copyExecution( self )
                self.scenario.addObject( e )

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        pdict = self.scenario.getObjectsDict('parser')
        if self.parserNames:
            for parser in self.parserNames:
                if parser not in pdict:
                    try:
                        Campaign.loadModule( 'parser', parser )
                    except ImportError:
                        raise Exception( "Execution defined at line {0} refers to parser {1} which is never declared".format( self.declarationLine, parser ) )
        self.host = self.scenario.resolveObjectName( 'host', self.hostName )
        self.client = self.scenario.resolveObjectName( 'client', self.clientName )
        self.files = []
        if self.fileNames:
            for fileName in self.fileNames:
                self.files.append( self.scenario.resolveObjectName( 'file', fileName ) )
        if self.parserNames:
            self.parsers = []
            for parser in self.parserNames:
                if parser in pdict:
                    self.parsers.append( pdict[parser] )
                else:
                    modclass = Campaign.loadModule( 'parser', parser )
                    # *Sigh*. PyLint. Dynamic loading!
                    # pylint: disable-msg=E1121
                    obj = modclass( self.scenario )
                    # pylint: enable-msg=E1121
                    obj.checkSettings()
                    self.parsers.append( obj )

    def isSeeder(self):
        """
        Returns whether this execution is a seeder.

        @return True iff this execution is a seeder.
        """
        return self.seeder
    
    def getNumber(self):
        """
        Returns the number of this execution.

        @return The execution's number.
        """
        return self.number

    @staticmethod
    def getExecutionCount():
        """
        Returns the total number of executions.

        This should be equal to len(self.scenario.getObjectsDict('execution'))

        @return The number of execution objects.
        """
        return execution.executionCount

    def runParsers(self, logDir, outputDir):
        """
        Runs all the parsers for this execution.

        This method will choose the right parser and pass on the arguments.

        @param  logDir      The path to the directory on the local machine where the logs reside.
        @param  outputDir   The path to the directory on the local machine where the parsed logs are to be stored.
        """
        # The parser loading has already been done
        if self.parsers:
            for parser in self.parsers:
                parser.parseLogs( self, logDir, outputDir )
        else:
            p = self.client.loadDefaultParsers(self)
            for parser in p:
                parser.parseLogs(self, logDir, outputDir)

    def getModuleType(self):
        """
        Return the moduleType string.
        
        @return    The module type.
        """
        return 'execution'
    
    def getName(self):
        """
        Return the name of the object.
        
        @return    The name.
        """
        return self.number

    def createRunnerConnections(self):
        """
        Creates two new connections on the included host that can be used to do parallel queries to the client and to execute the client.
        
        The connections will be held internally and requested for use through getRunnerConnection() and getExecutionConnection().
        """
        self.runnerConnection = self.host.setupNewConnection()
        self.executionConnection = self.host.setupNewConnection()

    def getRunnerConnection(self):
        """
        Returns a separate connection to be used to query a client in parallel.
        
        Creates a new connection if needed.
        """
        if not self.runnerConnection:
            self.createRunnerConnections()
        return self.runnerConnection

    def getExecutionConnection(self):
        """
        Returns a separate connection to be used to execute a client.
        
        Creates a new connection if needed.
        """
        if not self.executionConnection:
            self.createRunnerConnections()
        return self.executionConnection
    
    def getDataDirList(self):
        """
        Returns the list of data directories of seeding files for this execution.
        
        This is basically just a loop over all seeding file objects in the host which request their data dir and appends it to the list.
        Each element is guaranteed to be unique.
        
        Please note that this list is usually the wrong one to use. Consider a combination of getDataDirTree() and getDataFiles(), instead.
        Those allow you to copy the directory structure and link all the files you need, and more specifically *only* the files you need, in
        that copied directory structure.
        """
        l = []
        for f in self.host.seedingFiles:
            d = f.getDataDir(self.host)
            if d is not None:
                if d not in l:
                    l.append(d)
        return l
    
    def getDataDirTree(self):
        """
        Returns a list of directories in the data directories of seeding files for this execution.
        
        This is a loop that will go over all those files and call getDataDirTree() on them. The resulting lists will be transformed and
        concatenated and the relativeDir part (see below) of each item is checked for unicity. If duplicates are found an Exception is
        raised.
        
        Please note that the resulting list of this method is different from file's getDataDirTree(). This method will return a list of
        pairs of lists instead of just a list of lists. The pairs are (remoteSourceDir, destinationDir) where remoteSourceDir is the
        absolute path to the existing directory on this execution's remote host and destinationDir is the relative directory as returned
        in the list of file's getDataDirTree(). In pseudocode:
            for relativeDir in file.getDataDirTree():
                result.append( (file.getDataDir() + relativeDir, relativeDir) )
        
        @return    The list of tuples of all files' directory structures giving (original, relative), in list notation.
        """
        return _getDataTree(self.host, self.getNumber(), 'd', self.files)
    
    def getDataFileTree(self):
        """
        Returns a list of files in the data of seeding files for this execution.
        
        This is a loop that will go over all those files and call getDataFileTree() on them. The resulting list will be transformed and
        concatenated and the relativePath (see below) of each item is checked for unicity. If duplicates are found an Exception is
        raised.
        
        Plase note that the resulting list of this method is different from file's getDataFileTree(). This method will return a list of
        pairs of lists instead of just a list of lists. The pairs are (remoteSourceFile, destinationFile) where remoteSourceFile is the
        absolute path to the existing file on this execution's remote host and destinationFile is the relative destination as returned
        in the list of file's getDataFileTree(). In pseudocode:
            for relativePath in file.getDataFileTree():
                result.append( (file.getDataDir() + relativePath, relativePath) )
                
        @return    The list of tuples of all files' files giving (original, relative), in list notation.
        """
        return _getDataTree(self.host, self.getNumber(), 'f', self.files)

    def getMetaFileDirList(self):
        """
        Returns the list of metafile directories of files for this execution.
        
        This is basically just a loop over all file objects in the host which request their metafile dir and appends it to the list.
        Each element is guaranteed to be unique.
        
        WARNING! DEPRECATED!
        This method gives treacherous results: you might be reading much more meta files than just the ones you want.
        Please use getMetaFileList() instead, possible combined with linking to an execution specific directory.
        """
        Campaign.logger.log("WARNING! execution.getMetaFileDirList() was used, but is treacherous and hence deprecated. Backtrace follows.")
        Campaign.logger.localTraceback()
        l = []
        for f in self.host.files:
            if f not in self.files:
                continue
            d = f.getMetaFileDir(self.host)
            if d is not None:
                if d not in l:
                    l.append(d)
        return l
    
    def getMetaFileList(self, required = False):
        """
        Returns the list of all metafiles of files for this execution.
        
        This is basically just a loop over all file objects in the host which requests their metafile and appends it to the list.
        Each element is guaranteed to be unique.
        
        @param    required    Set to True to have an Exception raised if any of the files does not have a metafile associated.
        """
        l = []
        for f in self.host.files:
            if f not in self.files:
                continue
            mf = f.getMetaFile(self.host)
            if mf is not None:
                if mf not in l:
                    l.append(mf)
            elif required:
                raise Exception( "File {0} has no metafile associated, but is required to have one by our caller.".format( f.getName() ) )
        return l

    @staticmethod
    def APIVersion():
        return "2.4.0-core"

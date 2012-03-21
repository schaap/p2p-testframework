from core.parsing import isValidName, isPositiveFloat
from core.campaign import Campaign
from core.coreObject import coreObject

def parseError( msg ):
    raise Exception( "Parse error for execution object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class execution(coreObject):
    """
    An execution object.

    Executions are the combination of host, client and file. Their meaning is that the client is executed once on
    the host to transfer the file.

    Subclasses of execution do not exist.
    """

    hostName = None             # The name of the host object
    clientName = None           # The name of the client object
    fileName = None             # The name of the file object
    parserNames = None          # The list of names of the parser objects

    host = None                 # The host object
    client = None               # The client object
    # Yes, that's a warning below. That's OK, though.
    file = None                 # The file object
    parsers = None              # The list of parser objects

    seeder = False              # True iff this execution is a seeder

    number = None               # The number of this execution
    
    runnerConnection = None     # A specific connection to use for querying a client in parallel
    executionConnection = None  # A specific connection to use for execution a client
    
    timeout = None              # A number of seconds to wait before starting the client (float)
    
    keepSeeding = False         # Set to True to have this execution keep on seeding when all leechers are done

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
                parseError( "{0} is not a valid host object name".format( value ) )
            self.hostName = value
        elif key == 'client':
            if self.clientName:
                parseError( "A client was already given: {0}".format( self.clientName ) )
            if not isValidName( value ):
                parseError( "{0} is not a valid client object name".format( value ) )
            self.clientName = value
        elif key == 'file':
            if self.fileName:
                parseError( "A file was already given: {0}".format( self.fileName ) )
            if not isValidName( value ):
                parseError( "{0} is not a valid file object name".format( value ) )
            self.fileName = value
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
        if not self.fileName:
            raise Exception( "Execution defined at line {0} must have a file.".format( self.declarationLine ) )
        if self.timeout == None:
            self.timeout = 0
        if not self.isSeeder() and self.keepSeeding:
            Campaign.logger.log( "Warning: Execution define at line {0} is declared to keep seeding, but it's not a seeder.".format( self.declarationLine ))

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        if self.hostName not in self.scenario.getObjectsDict('host'):
            raise Exception( "Execution defined at line {0} refers to host {1} which is never declared".format( self.declarationLine, self.hostName ) )
        if self.clientName not in self.scenario.getObjectsDict('client'):
            raise Exception( "Execution defined at line {0} refers to client {1} which is never declared".format( self.declarationLine, self.clientName ) )
        if self.fileName not in self.scenario.getObjectsDict('file'):
            raise Exception( "Execution defined at line {0} refers to file {1} which is never declared".format( self.declarationLine, self.fileName ) )
        if self.parserNames:
            for parser in self.parserNames:
                if parser not in self.scenario.getObjectsDict('parser'):
                    try:
                        Campaign.loadModule( 'parser', parser )
                    except ImportError:
                        raise Exception( "Execution defined at line {0} refers to parser {1} which is never declared".format( self.declarationLine, parser ) )
        self.host = self.scenario.getObjectsDict('host')[self.hostName]
        self.client = self.scenario.getObjectsDict('client')[self.clientName]
        self.file = self.scenario.getObjectsDict('file')[self.fileName]
        if self.parserNames:
            self.parsers = []
            pdict = self.scenario.getObjectsDict( 'parser' )
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

    @staticmethod
    def APIVersion():
        return "2.1.0-core"

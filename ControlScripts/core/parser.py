from core.parsing import isValidName
from core.campaign import Campaign
from core.coreObject import coreObject

def parseError( msg ):
    raise Exception( "Parse error for parser object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class parser(coreObject):
    """
    The parent class for all parsers.

    This object contains all the default implementations for every parser.
    When subclassing parser be sure to use the skeleton class as a basis: it saves you a lot of time.
    """

    def __init__(self, scenario):
        """
        Initialization of a generic parser object.

        @param  scenario        The ScenarioRunner object this parser object is part of.
        """
        coreObject.__init__(self, scenario)

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
            if value in self.scenario.getObjectsDict('parser'):
                parseError( 'Parser object called {0} already exists'.format( value ) )
            self.name = value
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
            if self.__class__.__name__ in self.scenario.getObjectsDict('parser'):
                raise Exception( "Parser object declared at line {0} was not given a name and default name for this parser ({1}) was already used".format( self.declarationLine, self.__class__.__name__ ) )
            else:
                self.name = self.__class__.__name__

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        pass

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
    def parseLogs(self, execution, logDir, outputDir):
        """
        Parse the logs for the current execution.

        Be sure to document in the header of your module which logs you expect to be present and with which filename.

        Subclassers must override this method.

        @param  execution   The execution for which to parse the logs.
        @param  logDir      The path to the directory on the local machine where the logs reside.
        @param  outputDir   The path to the directory on the local machine where the parsed logs are to be stored.
        """
        raise Exception( "Not implemented" )
    # pylint: enable-msg=W0613

    def getModuleType(self):
        """
        Return the moduleType string.
        
        @return    The module type.
        """
        return 'parser'
    
    def getName(self):
        """
        Return the name of the object.
        
        @return    The name.
        """
        return self.name

    @staticmethod
    def APIVersion():
        return "2.3.0-core"

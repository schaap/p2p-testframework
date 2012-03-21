from core.campaign import Campaign
from core.processor import processor

import os

class test__(processor):
    """
    A test implementation for the processor API.
    
    Extra parameters:
    - [none]
    
    Raw logs expected:
    - none
    
    Parsed logs expected:
    - none
    
    Processed log files created:
    - processed.txt
    -- pure bogus text proclaiming it has been processed
    """

    def __init__(self, scenario):
        """
        Initialization of a generic processor object.

        @param  scenario        The ScenarioRunner object this processor object is part of.
        """
        processor.__init__(self, scenario)

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
        processor.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        processor.checkSettings(self)

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        processor.resolveNames(self)

    def processLogs(self, baseDir, outputDir):
        """
        Process the raw and parsed logs found in the base directory.

        The raw logs are found in self.getRawLogDir( execution, baseDir ).
        The parsed logs are found in self.getParsedLogDir( execution, baseDir ).

        Be sure to document in the header of your module which (parsed) logs you expect to be present and with which filename.

        Subclassers must override this method.

        @param  baseDir     The base directory for the logs.
        @param  outputDir   The path to the directory on the local machine where the processed logs are to be stored.
        """
        if not os.path.exists( baseDir ) or not os.path.isdir( baseDir ):
            raise Exception( "That base directory is not a real directory: {0}".format( baseDir ) )
        if not os.path.exists( outputDir ) or not os.path.isdir( outputDir ):
            raise Exception( "That ouput directory is not a real directory: {0}".format( outputDir ) )
        
        for e in self.scenario.getObjects( 'execution' ):
            rawlogdir = self.getRawLogDir(e, baseDir)
            parsedlogdir = self.getParsedLogDir(e, baseDir)
            if not os.path.exists( rawlogdir ) or not os.path.isdir( rawlogdir ):
                raise Exception( "That raw log directory is not a real directory: {0}".format( rawlogdir ) )
            if not os.path.exists( parsedlogdir ) or not os.path.isdir( parsedlogdir ):
                raise Exception( "That parsed log directory is not a real directory: {0}".format( parsedlogdir ) )
        
        f = open( os.path.join( outputDir, 'processed.txt' ), 'w' )
        f.write( "I haz bin processored!!!!1!11!111one1!eleven" )
        f.close()

    @staticmethod
    def APIVersion():
        return "2.1.0"

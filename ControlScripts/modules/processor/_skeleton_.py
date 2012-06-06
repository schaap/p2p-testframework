# These imports are needed to access the parsing functions (which you're likely to use in parameter parsing),
# the Campaign data object and the processor parent class.
from core.parsing import *
from core.campaign import Campaign
from core.processor import processor

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/processor/useless.py then the name of your class would be useless.

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for processor object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

# TODO: Change the name of the class. See the remark above abou the names of the module and the class. Example:
#
#   class useless(processor):
class _skeleton_(processor):
    """
    A skeleton implementation of a processor subclass.
            
    Please use this file as a basis for your subclasses but DO NOT actually instantiate it.
    It will fail.
                                                
    Look at the TODO in this file to know where you come in.
    """
    # TODO: Update the description above. Example:
    #
    #   """
    #   Useless processor.
    #
    #   Extra parameters:
    #   - content   A line of content for the processed log. Must not be "". May be specified multiple times.
    #
    #   Raw logs expected:
    #   - log.log   Any log of a client.
    #
    #   Parsed logs expected:
    #   - log.useless   Any useless log of a client.
    #
    #   Processed log files created:
    #   - useless-processed
    #   -- Useless data. Very useless.
    #   """
    #
    # Please be sure to documen the expected logs and produced results well.

    def __init__(self, scenario):
        """
        Initialization of a generic processor object.

        @param  scenario        The ScenarioRunner object this processor object is part of.
        """
        processor.__init__(self, scenario)
        # TODO: Your initialization, if any (not likely). Oh, and remove the next line.
        raise Exception( "DO NOT instantiate the skeleton implementation" )

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
        # TODO: Parse your settings. Example:
        #
        #   if key == 'content':
        #       if content = '':
        #           parseError( "We're not going to write nothing, are we? That'd be useless." )
        #       if not self.content:
        #           self.content = [value]
        #       else:
        #           self.content.append( value )
        #   else:
        #       processor.parseSetting(self, key, value)
        #
        # Do not forget that last case!
        #
        # The following implementation assumes you have no parameters specific to your processor:
        processor.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        processor.checkSettings(self)
        # TODO: Check your settings. Example:
        #
        #   if not self.content:
        #       self.content = ["This is useless"]

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        processor.resolveNames(self)
        # TODO: Do any name resolutions here.
        # The names of other objects this object refers to, either intrinsically or in its parameters, should be checked here.

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
        # TODO: Implement this method. Example:
        #
        #   for execution in self.scenario.getObjects('execution'):
        #       if not os.path.exists( os.path.join( self.getRawLogDir( execution, baseDir ), 'log.log' ) ):
        #           raise Exception( "Raw log file log.log expected for execution {2} of client {0} on host {1}".format( execution.client.name, execution.host.name, execution.getNumber() ) )
        #       if not os.path.exists( os.path.join( self.getParsedLogDir( execution, baseDir ), 'log.useless' ) ):
        #           raise Exception( "Parsed log file log.useless expected for execution {2} of client {0} on host {1}".format( execution.client.name, execution.host.name, execution.getNumber() ) )
        #   f = open( os.path.join( outputDir, 'useless-processed' ), 'w' )
        #   f.write( "All logs present\n" );
        #   for c in self.content:
        #       f.write( c+"\n" );
        #   f.close()
        #
        # You must really implement this:
        raise Exception( "Not implemented" )

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version
        return "2.4.0"

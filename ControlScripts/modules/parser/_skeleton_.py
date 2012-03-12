# These imports are needed to access the parsing functions (which you're likely to use in parameter parsing),
# the Campaign data object and the parser parent class.
from core.parsing import *
from core.campaign import Campaign
from core.parser import parser

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/parser/useless.py then the name of your class would be useless.

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for parser object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

# TODO: Change the name of the class. See the remark above about the names of the module and the class. Example:
#
#   class useless(parser):
class _skeleton_(parser):
    """
    A skeleton implementation of a parser subclass.
        
    Please use this file as a basis for your subclasses but DO NOT actually instantiate it.
    It will fail.
                            
    Look at the TODO in this file to know where you come in.
    """
    # TODO: Update the description above. Example:
    #
    #   """
    #   Useless parser.
    #
    #   Extra parameters:
    #   - content   A line of content for the parsed log. Must not be "". May be specified multiple times.
    #
    #   Raw logs expected:
    #   - log.log   Any log of a client.
    #
    #   Parse log files created:
    #   - log.useless
    #   -- Useless data that begin with one at least slightly usefull line indicating the role of the execution.
    #   """
    #
    # Please be sure to document the expected and produced logs well.

    def __init__(self, scenario):
        """
        Initialization of a generic parser object.

        @param  scenario        The ScenarioRunner object this parser object is part of.
        """
        parser.__init__(self, scenario)
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
        #       parser.parseSetting(self, key, value)
        #
        # Do not forget that last case!
        #
        # The following implementation assumes you have no parameters specific to your parser:
        parser.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        parser.checkSettings(self)
        # TODO: Check your settings. Example:
        #
        #   if not self.content:
        #       self.content = ["This is useless"]
        #
        # Note that this method should result in a valid parser object if called directly after the constructor.
        # That is the default parser setting.

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        parser.resolveNames(self)
        # TODO: Do any name resolutions here.
        # The names of other objects this object refers to, either intrinsically or in its parameters, should be checked here.

    def parseLogs(self, execution, logDir, outputDir):
        """
        Parse the logs for the current execution.

        Be sure to document in the header of your module which logs you expect to be present and with which filename.

        Subclassers must override this method.

        @param  execution   The execution for which to parse the logs.
        @param  logDir      The path to the directory on the local machine where the logs reside.
        @param  outputDir   The path to the directory on the local machine where the parsed logs are to be stored.
        """
        # TODO: Parse those logs. Example:
        #
        #   if not os.path.exists( os.path.join( logDir, 'log.log' ) ):
        #       raise Exception( "Log file log.log expected for execution {2} of client {0} on host {1}".format( execution.client.name, execution.host.name, execution.getNumber() ) )
        #   f = open( os.path.join( outputDir, 'log.useless' ), 'w' )
        #   if execution.isSeeder():
        #       f.write( "SEEDER\n" );
        #   else:
        #       f.write( "LEECHER\n" );
        #   for c in self.content:
        #       f.write( c+"\n" );
        #   f.close()
        #
        # You really must implement this:
        raise Exception( "Not implemented" )

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version
        return "2.0.0"

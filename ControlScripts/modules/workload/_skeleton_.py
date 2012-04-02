# These imports are needed to access the parsing functions (which you're likely to use in parameter parsing),
# the Campaign data object and the processor parent class.
from core.parsing import *
from core.campaign import Campaign
from core.workload import workload

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/workload/linear.py then the name of your class would be linear.

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for workload object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

# TODO: Change the name of the class. See the remark above abou the names of the module and the class. Example:
#
#   class linear(workload):
class _skeleton_(workload):
    """
    A skeleton implementation of a workload subclass.
                
    Please use this file as a basis for your subclasses but DO NOT actually instantiate it.
    It will fail.
                                                                        
    Look at the TODO in this file to know where you come in.
    """
    # TODO: Update the description above. Example:
    #
    #   """
    #   Linear workload generator.
    #
    #   The workload will have the clients equally spread over a given time.
    #
    #   Note that the three possible parameters are different ways of specifying the same parameter.
    #   Only one should be specified. The third piece of data is automatically calculated.
    #
    #   Extra parameters:
    #   - duration        Time in seconds over which the peers should arrive. Arrival rate is calculated.
    #   - rate            Arrival rate in number of peers per second. Duration is calculated.
    #   - interval        Interval between the arrival of 2 peers in seconds. Duration is calculated.
    #   """
    #
    # Please be sure to document the generated workload well.

    def __init__(self, scenario):
        """
        Initialization of a generic workload object.

        @param  scenario        The ScenarioRunner object this viewer object is part of.
        """
        workload.__init__(self, scenario)
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
        #   if key == 'duration':
        #       if self.duration:
        #           parseError( "Duration was already specified: {0}".format( self.duration ) )
        #       if self.interval:
        #           parseError( "Interval was already specified: {0}".format( self.interval ) )
        #       if not isPositiveFloat( value, True ):
        #           parseError( "Duration should be a non-zero positive floating point number." )
        #       self.duration = float(value)
        #   elif key == 'interval':
        #       if self.duration:
        #           parseError( "Duration was already specified: {0}".format( self.duration ) )
        #       if self.interval:
        #           parseError( "Interval was already specified: {0}".format( self.interval ) )
        #       if not isPositiveFloat( value, True ):
        #           parseError( "Interval should be a non-zero positive floating point number." )
        #       self.interval = float(value)
        #   elif key == 'rate':
        #       if self.duration:
        #           parseError( "Duration was already specified: {0}".format( self.duration ) )
        #       if self.interval:
        #           parseError( "Interval was already specified: {0}".format( self.interval ) )
        #       if not isPositiveFloat( value, True ):
        #           parseError( "Rate should be a non-zero positive floating point number." )
        #       self.interval = 1.0 / float(value)
        #   else:
        #       workload.parseSetting(self, key, value)
        #
        # Do not forget that last case!
        #
        # The following implementation assumes you have no parameters specific to your workload:
        workload.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        workload.checkSettings(self)
        # TODO: Check your settings. Example:
        #
        #   if not ( self.duration or self.interval ):
        #       raise Exception( "One of duration, interval or rate is requried for a linear workload." ) 

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        workload.resolveNames(self)
        # TODO: Do any name resolutions here.
        # The names of other objects this object refers to, either intrinsically or in its parameters, should be checked here.

    def applyWorkload(self):
        """
        Applies the workload parameters to the scenario.
        
        This methods will set the timeout parameter of those executions it is instructed to.
        
        The parent implementation will check each of those executions to see if no timeout was set, yet.
        If any non-zero timeout is found a warning will be generated in the log.
        """
        # TODO: Implement this method. Be sure to call the parent moethod first to have the executions checked.
        # Example:
        #
        #   workload.applyWorkload( self )
        #   if self.applySeeders:
        #       executions = [e for e in self.scenario.getObjects('execution') if e.client.name in self.applyList]
        #   else:
        #       executions = [e for e in self.scenario.getObjects('execution') if e.client.name in self.applyList and not e.isSeeder()]
        #   timeout = self.offset
        #   if self.interval:
        #       interval = self.interval
        #   elif len(executions) > 1:
        #       interval = self.duration / (len(executions) - 1)
        #   else:
        #       interval = self.duration
        #   for e in executions:
        #       e.timeout = timeout
        #       timeout += interval
        #
        # You must really implement this:
        raise Exception( "Not implemented" )

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version
        return "2.2.0"


from core.parsing import isPositiveFloat
from core.campaign import Campaign
from core.workload import workload

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for workload object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class linear(workload):
    """
    Linear workload generator.
    
    The workload will have the clients equally spread over a given time.
    
    Note that the three possible parameters are different ways of specifying the same parameter.
    Only one should be specified. The third piece of data is automatically calculated.
    
    Extra parameters:
    - duration        Time in seconds over which the peers should arrive. Arrival rate is calculated.
    - rate            Arrival rate in number of peers per second. Duration is calculated.
    - interval        Interval between the arrival of 2 peers in seconds. Duration is calculated.
    """
    
    duration = None     # Duration of the full linear workload
    interval = None     # Inter-arrival time between two clients in the workload

    def __init__(self, scenario):
        """
        Initialization of a generic workload object.

        @param  scenario        The ScenarioRunner object this viewer object is part of.
        """
        workload.__init__(self, scenario)

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
        if key == 'duration':
            if self.duration:
                parseError( "Duration was already specified: {0}".format( self.duration ) )
            if self.interval:
                parseError( "Interval was already specified: {0}".format( self.interval ) )
            if not isPositiveFloat( value, True ):
                parseError( "Duration should be a non-zero positive floating point number." )
            self.duration = float(value)
        elif key == 'interval':
            if self.duration:
                parseError( "Duration was already specified: {0}".format( self.duration ) )
            if self.interval:
                parseError( "Interval was already specified: {0}".format( self.interval ) )
            if not isPositiveFloat( value, True ):
                parseError( "Interval should be a non-zero positive floating point number." )
            self.interval = float(value)
        elif key == 'rate':
            if self.duration:
                parseError( "Duration was already specified: {0}".format( self.duration ) )
            if self.interval:
                parseError( "Interval was already specified: {0}".format( self.interval ) )
            if not isPositiveFloat( value, True ):
                parseError( "Rate should be a non-zero positive floating point number." )
            self.interval = 1.0 / float(value)
        else:
            workload.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        workload.checkSettings(self)
        if not ( self.duration or self.interval ):
            raise Exception( "One of duration, interval or rate is requried for a linear workload." ) 

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        workload.resolveNames(self)

    def applyWorkload(self):
        """
        Applies the workload parameters to the scenario.
        
        This methods will set the timeout parameter of those executions it is instructed to.
        
        The parent implementation will check each of those executions to see if no timeout was set, yet.
        If any non-zero timeout is found a warning will be generated in the log.
        """
        workload.applyWorkload( self )
        if self.applySeeders:
            executions = [e for e in self.scenario.getObjects('execution') if e.client.name in self.applyList]
        else:
            executions = [e for e in self.scenario.getObjects('execution') if e.client.name in self.applyList and not e.isSeeder()]
        if len(executions) == 0:
            return

        timeout = self.offset
        if self.interval:
            interval = self.interval
        elif len(executions) > 1:
            interval = self.duration / (len(executions) - 1)
        else:
            interval = self.duration
        for e in executions:
            e.timeout = timeout
            timeout += interval

    @staticmethod
    def APIVersion():
        return "2.3.0"


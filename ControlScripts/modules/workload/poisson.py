from core.parsing import isPositiveFloat
from core.campaign import Campaign
from core.workload import workload

import random

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for workload object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class poisson(workload):
    """
    Poisson workload generator.
    
    Note that the two possible parameters are different ways of specifying the same parameter.
    Only one should be specified. The other is automatically calculated.
    
    Extra parameters:
    - duration        Time in seconds over which the peers should arrive. Arrival rate is calculated.
    - rate            Arrival rate in number of peers per second. Duration is calculated.
    """

    duration = None     # Duration of the full poisson workload
    rate = None         # Arrival rate of peers (will be used to calculate duration when number of peers is known)

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
            if self.rate:
                parseError( "Rate was already specified: {0}".format( self.rate ) )
            if not isPositiveFloat( value, True ):
                parseError( "Duration should be a non-zero positive floating point number." )
            self.duration = float(value)
        elif key == 'rate':
            if self.duration:
                parseError( "Duration was already specified: {0}".format( self.duration ) )
            if self.rate:
                parseError( "Rate was already specified: {0}".format( self.rate ) )
            if not isPositiveFloat( value, True ):
                parseError( "Rate should be a non-zero positive floating point number." )
            self.rate = float(value)
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
        if not ( self.duration or self.rate ):
            raise Exception( "One of duration or rate is requried for a poisson workload." ) 

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
        
        # The easiest way to get a poisson distribution is to just get random numbers
        times = sorted([random.uniform(0,1000) for _ in range( len(executions) * 1000 )])[::1000]
        
        # Actual duration
        if self.duration:
            duration = self.duration
        else:
            duration = self.rate * len(executions)
        
        # Now shift and stretch
        offset = times[0] - self.offset
        if times[-1] != times[0]:
            scale = duration / (times[-1] - times[0])
        else:
            scale = duration
        actualTimes = [(t - offset) * scale for t in times]
        
        cnt = 0
        for execution in executions:
            execution.timeout = actualTimes[cnt]
            cnt += 1

    @staticmethod
    def APIVersion():
        return "2.3.0"


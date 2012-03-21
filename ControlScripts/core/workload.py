from core.parsing import isPositiveFloat
from core.campaign import Campaign
from core.coreObject import coreObject

def parseError( msg ):
    raise Exception( "Parse error for workload object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class workload(coreObject):
    """
    The parent class for all workload generators.

    This object contains all the default implementations for every workload generator.
    When subclassing workload be sure to use the skeleton class as a basis: it saves you a lot of time.
    """

    number = None           # The number of this workload generator

    # @static
    workloadCount = 0       # The total number of workload generators
    
    applyList = None        # List of names of client objects to apply this workload generator to
    applySeeders = False    # Flag to check whether this workload generator should apply to seeder executions as well
    offset = None           # Time in seconds to delay before starting the first client for this workload

    def __init__(self, scenario):
        """
        Initialization of a generic workload object.

        @param  scenario        The ScenarioRunner object this workload object is part of.
        """
        coreObject.__init__(self, scenario)
        self.number = workload.workloadCount
        workload.workloadCount += 1

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
        if key == 'apply':
            if not self.applyList:
                self.applyList = [value]
            else:
                self.applyList.append( value )
        elif key == 'offset':
            if self.offset != None:
                parseError( "Offset has already been set: {0}".format( self.offset ) )
            if not isPositiveFloat( value ):
                parseError( "Offset should be a non-negative floating point number" )
            self.offset = float(value)
        elif key == 'applyToSeeders':
            if value == 'yes':
                self.applySeeders = True
        else:
            parseError( 'Unknown parameter name: {0}'.format( key ) )

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        if not self.offset:
            self.offset = 0
    
    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        if not self.applyList:
            self.applyList = [c for c in self.scenario.getObjectsDict('client')]
        self.applyList = list(set(self.applyList))
        found = False
        for c in self.applyList:
            if c not in self.scenario.getObjectsDict('client'):
                raise Exception( "Workload {0} is instructed to apply itself to client {1}, but that client does not exist.".format( self.__class__.__name__, c ) )
            for e in [e for e in self.scenario.getObjects('execution') if e.client.name == c]:
                if not e.isSeeder() or self.applySeeders:
                    found = True
        if not found:
            Campaign.logger.log( "Workload {0} has not found any executions to which it will apply itself." )

    def applyWorkload(self):
        """
        Applies the workload parameters to the scenario.
        
        This methods will set the timeout parameter of those executions it is instructed to.
        
        The parent implementation will check each of those executions to see if no timeout was set, yet.
        If any non-zero timeout is found a warning will be generated in the log.
        """
        for e in [e for e in self.scenario.getObjects('execution') if e.client.name in self.applyList]:
            if self.applySeeders or not e.isSeeder():
                if e.timeout != 0:
                    Campaign.logger.log( "Workload {0} is instructed to apply to client {1}, which includes execution {2}. That execution already has a timeout, however, which will be overwritten. Note that it is not supported to have multiple workloads apply to the same client, nor is it supported to have manual timeout parameters on execution that will be touched by a workload.".format( self.__class__.__name__, e.client.name, e.getNumber() ) )
    
    def getModuleType(self):
        """
        Return the moduleType string.
        
        @return    The module type.
        """
        return 'workload'
    
    def getName(self):
        """
        Return the name of the object.
        
        @return    The name.
        """
        return self.number

    @staticmethod
    def APIVersion():
        return "2.1.0-core"

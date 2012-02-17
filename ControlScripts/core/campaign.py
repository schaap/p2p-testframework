import core.logger

# We have unused arguments; that's fine
# pylint: disable-msg=W0613

class Campaign:
    """
    Campaign class for the global environment of all campaigns.
    """
    ######
    # Static part of the class: initialization and option parsing
    ######

    doCheckRun = True       # True iff a checking run is to be done
    doRealRun = True        # True iff a real run is to be done

    logger = core.logger.logger()       # The global logging object, always available through Campaign.logger

    currentCampaign = None  # The campaign object currently running

    currentLineNumber = 0   # Global variable for easy tracking of the line number when parsing files
    
    def __init__(self):
        raise Exception( "Do not instantiate" )
    
    @staticmethod
    def getCurrentCampaign():
        """
        Returns the current campaign object.
        
        @return    The current campaign object.
        """
        # This method is mainly preferred to fool static analysers
        return Campaign.currentCampaign
    
    @staticmethod
    def notInitialized():
        """
        A method that raises an exception unless an impossible situation occurs.
        Used for protecting loadModule and loadCoreModule and, more importantly, to fool static analysis.
        
        @return    None
        """
        if Campaign.doCheckRun or Campaign.doRealRun:
            raise Exception( "Campaign.loadModule and Campaign.loadCoreModule have not been reinitialized. This can really only come from using them incorrectly / too early." )
        # The use of getattr here is quite simple: pylint does not do type checking over calls to getattr and
        # hence will not whine when we expect random classes from this.
        # Of course, the drawback is that pylint then does no typechecking on those classes.
        return getattr( Campaign, 'doCheckRun' )

    @staticmethod
    def loadModule(moduleType, moduleSubType):
        """
        Load a single module from the extension modules and return the class.

        Modules with sub type '' are redirected to loadCoreModule( moduleType ).
        This function will check several things:
        - whether the moduleType is actually supported;
        - whether the combination with moduleSubType is valid;
        - whether the API Verion of the loaded module is correct.

        Example:
            sshHostClass = Campaign.loadModule( 'host', 'ssh' )
            sshHostObject = sshHostClass( )

        @param  The module type of the module.
        @param  The module sub type of the module, which is the name of the module itself as well as the name of the class inside that module that will be returned.

        @return The class with the name moduleSubType in the module modules.moduleType.moduleSubType
        """
        # Will be changed on-the-fly when a campaign is run
        return Campaign.notInitialized

    @staticmethod
    def loadCoreModule(moduleType):
        """
        Load a single module from the core and return the class.

        This function will check whether the API Version of the loaded module is correct.

        Example:
            executionClass = Campaign.loadCoreModule( 'execution' )
            executionObject = executionClass( )

        @param  The name of the core module, which is also the name of the class inside that module that will be returned.

        @return The class with the name moduleType in the module core.moduleType
        """
        # Will be changed on-the-fly when a campaign is run
        return Campaign.notInitialized


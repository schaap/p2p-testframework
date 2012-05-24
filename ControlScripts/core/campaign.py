import core.logger
import core.debuglogger
import os

# We have unused arguments; that's fine
# pylint: disable-msg=W0613

class Campaign:
    """
    Campaign class for the global environment of all campaigns.

    Also holds a few miscellaneous helper functions that are useful throughout all modules.
    """
    ######
    # Static part of the class: initialization and option parsing
    ######

    doCheckRun = True       # True iff a checking run is to be done
    doRealRun = True        # True iff a real run is to be done

    logger = core.logger.logger()                   # The global logging object, always available through Campaign.logger
    debuglogger = core.debuglogger.debuglogger()    # Global channel debug logger object.

    currentCampaign = None  # The campaign object currently running

    currentLineNumber = 0   # Global variable for easy tracking of the line number when parsing files
    
    testEnvDir = None       # Global location of the testing environment directory (the one containing
                            # the ControlScripts directory
    resultsDir = None       # Global location of the results for any campaign
    
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

    @staticmethod
    def which(name):
        """
        Returns a list of programs found in the PATH that are called name.

        @param  name    The name of the program to find.

        @return A list of full paths that can refer to the program, [] if the program wasn't found.
        """
        result = []
        exts = [ex for ex in os.environ.get('PATHEXT', '').split(os.pathsep) if ex]
        path = os.environ.get('PATH', None)
        if path is None:
            return []
        for p in os.environ.get('PATH', '').split(os.pathsep):
            p = os.path.join(p, name)
            if os.access(p, os.X_OK):
                result.append(p)
            for ex in exts:
                pext = p + ex
                if os.access(pext, os.X_OK):
                    result.append(pext)
        return result


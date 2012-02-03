class Campaign:
    """
    Campaign class for the global environment of all campaigns.
    """
    ######
    # Static part of the class: initialization and option parsing
    ######

    doCheckRun = True       # True iff a checking run is to be done
    doRealRun = True        # True iff a real run is to be done

    logger = None           # The global logging object, always available through Campaign.logger

    currentCampaign = None  # The campaign object currently running

    currentLineNumber = 0   # Global variable for easy tracking of the line number when parsing files

    @staticmethod
    def loadModule(self, moduleType, moduleSubType):
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
        pass

    @staticmethod
    def loadCoreModule(self, moduleType):
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
        pass

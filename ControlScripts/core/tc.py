from core.coreObject import coreObject

class tc(coreObject):
    """
    The parent class for all traffic control modules (TC).

    This object contains all the default implementations for every TC.
    When subclassing tc be sure to use the skeleton class as a basis: it saves you a lot of time.
    """

    def __init__(self, scenario):
        """
        Initialization of a generic tc object.

        @param  scenario        The ScenarioRunner object this tc object is part of.
        """
        coreObject.__init__(self, scenario)

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
    def check(self, host):
        """
        Checks whether traffic control can be set up on the host.

        @param  host    The host on which TC would be installed.

        @return True iff traffic control can be set up.
        """
        raise Exception( "Not implemented" )
    # pylint: enable-msg=W0613

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
    def install(self, host, otherhosts):
        """
        Installs the traffic control on the host.

        @param  host        The host on which to install TC.
        @param  otherhosts  List of subnets of other hosts.
        """
        raise Exception( "Not implemented" )
    # pylint: enable-msg=W0613

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
    def remove(self, host, reuseConnection = None):
        """
        Removes the traffic control from the host.

        @param  host            The host from which to remove TC.
        @param  reuseConnection If not None, force the use of this connection object for commands to the host.
        """
        raise Exception( "Not implemented" )
    # pylint: enable-msg=W0613

    def getModuleType(self):
        """
        Return the moduleType string.
        
        @return    The module type.
        """
        return 'tc'
    
    def getName(self):
        """
        Return the name of the object.
        
        @return    The name.
        """
        return self.__class__.__name__

    @staticmethod
    def APIVersion():
        return "2.0.0-core"

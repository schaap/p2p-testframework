from core.campaign import Campaign
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

    def check(self, host):
        """
        Checks whether traffic control can be set up on the host.

        @param  host    The host on which TC would be installed.

        @return True iff traffic control can be set up.
        """
        raise Exception( "Not implemented" )

    def install(self, host):
        """
        Installs the traffic control on the host.

        @param  host    The host on which to install TC.
        """
        raise Exception( "Not implemented" )

    def remove(self, host):
        """
        Removes the traffic control from the host.

        @param  host    The host from which to remove TC.
        """
        raise Exception( "Not implemented" )

    @staticmethod
    def APIVersion():
        return "2.0.0-core"

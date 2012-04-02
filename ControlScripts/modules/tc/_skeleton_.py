# These imports are needed to access the Campaign data object and the tc parent class.
from core.campaign import Campaign
from core.tc import tc

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/tc/nonfunctional.py then the name of your class would be nonfunctional.

# TODO: Note that most methods here have no examples. TC is too complicated a subject to work from examples.

# TODO: Change the name of the class. See the remark above abou the names of the module and the class. Example:
#
#   class nonfunctional(tc):
class _skeleton_(tc):
    """
    A skeleton implementation of a tc subclass.
                
    Please use this file as a basis for your subclasses but DO NOT actually instantiate it.
    It will fail.
                                                                        
    Look at the TODO in this file to know where you come in.
    """
    # TODO: Update the description above.

    def __init__(self, scenario):
        """
        Initialization of a generic tc object.

        @param  scenario        The ScenarioRunner object this tc object is part of.
        """
        tc.__init__(self, scenario)
        # TODO: Your initialization, if any (not likely). Oh, and remove the next line.
        raise Exception( "DO NOT instantiate the skeleton implementation" )

    def check(self, host):
        """
        Checks whether traffic control can be set up on the host.

        @param  host    The host on which TC would be installed.

        @return True iff traffic control can be set up.
        """
        # TODO: Implement this. Be sure to return True only if it's possible to set it up.
        # Also, don't actually set it up just yet.
        raise Exception( "Not implemented" )

    def install(self, host, otherhosts):
        """
        Installs the traffic control on the host.

        @param  host        The host on which to install TC.
        @param  otherhosts  List of subnets of other hosts.
        """
        # TODO: Implement this.
        raise Exception( "Not implemented" )

    def remove(self, host, reuseConnection = None):
        """
        Removes the traffic control from the host.

        @param  host    The host from which to remove TC.
        @param  reuseConnection If not None, force the use of this connection object for commands to the host.
        """
        # TODO: Implement this.
        raise Exception( "Not implemented" )

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version
        return "2.2.0"

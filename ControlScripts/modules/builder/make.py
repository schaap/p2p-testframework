from core.builder import builder

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/builder/make.py then the name of your class would be rudeClient.

class make(builder):
    """
    Builder object for (GNU) make.
    """

    def __init__(self, scenario):
        """
        Initialization of a generic builder object.

        @param  scenario        The ScenarioRunner object this builder object is part of.
        """
        builder.__init__(self, scenario)

    def buildCommand(self, client):
        """
        Return the command to build the client.

        Does not do the building itself! This method is used by buildLocal(...) and buildRemote(...) to find out what they are
        supposed to do.

        The default implementation returns None, which will tell buildLocal(...) and buildRemote(...) not to do anything.

        @param  client      The client for which the sources are to be built.
        """
        return 'make'

    @staticmethod
    def APIVersion():
        return "2.3.0"

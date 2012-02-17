from core.builder import builder

class none(builder):
    """
    Dummy builder.

    Builds nothing.
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
        return None

    @staticmethod
    def APIVersion():
        return "2.0.0"

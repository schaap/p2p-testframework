from core.source import source

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/source/svn.py then the name of your class would be svn.

class git(source):
    """
    git source implementation using the command line utility git.

    client.location is interpreted as a git repository ready to be cloned.
    """

    def __init__(self, scenario):
        """
        Initialization of a generic source object.

        @param  scenario        The ScenarioRunner object this builder object is part of.
        """
        source.__init__(self, scenario)

    def prepareCommand(self, client):
        """
        Return the command to prepare the sources.

        This method interprets and verifies client.location, where the location of the sources is specified.

        Does not do the preparing itself! This method is used by prepareLocal(...) and prepareRemote(...) to find out
        what they are supposed to do.

        The default implementation returns None, which will tell prepareLocal(...) and prepareRemote(...) not to do
        anything.

        @param  client      The client for which the sources are to be prepared.
        """
        return 'git clone {0} .'.format( client.location )

    @staticmethod
    def APIVersion():
        return "2.2.0"

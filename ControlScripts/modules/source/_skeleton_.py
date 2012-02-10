from core.source import source

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/source/svn.py then the name of your class would be svn.

# TODO: Change the name of the class. See the remark above about the names of the module and the class. Example:
#
#   class svn(source):
class _skeleton_(source):
    """
    The skeleton implementation of the source class.

    Please use this file as a basis for your subclasses but DO NOT actually instantiate it.
    It will fail.

    Look at the TODO in this file to know where you come in.
    """

    def __init__(self, scenario):
        """
        Initialization of a generic source object.

        @param  scenario        The ScenarioRunner object this builder object is part of.
        """
        source.__init__(self, scenario)
        # TODO: Your initialization, if any (not likely). Oh, and remove the next line.
        raise Exception( "DO NOT instantiate the skeleton implementation" )

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
        # TODO: Return the command you'd like to have executed to build the sources. Example:
        #   return 'svn co {0}'.format( client.location )
        return None

    # TODO: If you require more advanced/different handling of your source acquisition than just some commands then you
    # should reimplement prepareLocal(...), prepareRemote(...) and possibly cleanup(...).

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version
        return "2.0.0"

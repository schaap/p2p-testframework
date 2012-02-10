from core.builder import builder

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/client/rudeClient.py then the name of your class would be rudeClient.

# TODO: Change the name of the class. See the remark above about the names of the module and the class. Example:
#
#   class make(builder):
class _skelaton_(coreObject):
    """
    The skeleton implementation of the builder class.

    Please use this file as a basis for your subclasses but DO NOT actually instantiate it.
    It will fail.

    Look at the TODO in this file to know where you come in.
    """

    # TODO: Set the following parameter to a command you'd like to have executed to build the sources. Example:
    #   buildCommand = 'make'
    buildCommand = None         # If this is set to a string, that command can be used by the default implementation
                                # for buildLocal(...) and buildRemote(...).

    def __init__(self, scenario):
        """
        Initialization of a generic builder object.

        @param  scenario        The ScenarioRunner object this builder object is part of.
        """
        builder.__init__(self, scenario)
        # TODO: Your initialization, if any (not likely). Oh, and remove the next line.
        raise Exception( "DO NOT instantiate the skeleton implementation" )

    # TODO: If you require more advanced/different handling of your build process than just some commands then you
    # should reimplement buildLocal(...) and buildRemote(...)

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version
        return "2.0.0"

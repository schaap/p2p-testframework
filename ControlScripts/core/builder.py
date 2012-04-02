from subprocess import STDOUT
from subprocess import PIPE
from subprocess import Popen

from core.campaign import Campaign
from core.coreObject import coreObject

class builder(coreObject):
    """
    The parent class for all builders.

    This object contains all the default implementations for every builder.
    When subclassing builder be sure to use the skeleton class as a basis: it saves you a lot of time.
    """

    def __init__(self, scenario):
        """
        Initialization of a generic builder object.

        @param  scenario        The ScenarioRunner object this builder object is part of.
        """
        coreObject.__init__(self, scenario)
    
    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
    def buildCommand(self, client):
        """
        Return the command to build the client.

        Does not do the building itself! This method is used by buildLocal(...) and buildRemote(...) to find out what they are
        supposed to do.

        The default implementation returns None, which will tell buildLocal(...) and buildRemote(...) not to do anything.

        @param  client      The client for which the sources are to be built.
        """
        return None
    # pylint: enable-msg=W0613

    def buildLocal(self, client):
        """
        Build the local sources for the client.
        
        This default implementation does nothing if buildCommand(...) returns None.
        Otherwise it starts a local bash instance and gives the buildCommand(...) as input to that.

        @param  client      The client for which the sources are to be built locally.
        
        @return True iff the building was succesful.
        """
        buildCommand = self.buildCommand(client)
        if buildCommand:
            result = ''
            try:
                if self.isInCleanup():
                    return False
                proc = Popen('bash', bufsize=8192, stdin=PIPE, stdout=PIPE, stderr=STDOUT, cwd=client.sourceObj.localLocation(client) )
                if self.isInCleanup():
                    proc.kill()
                    return False
                result = proc.communicate(buildCommand)
            except Exception:
                Campaign.logger.log( result )
                raise Exception( "Could not build client {0} locally using builder {1}".format( client.name, self.__class__.__name__ ) )
        return True
    
    def buildRemote(self, client, host):
        """
        Build the remote source for the client on the host.

        This default implementation does nothing if buildCommand(...) returns None.
        Otherwise it sends the buildCommand(...) to the host.

        @param  client      The client for which the sources are to be built remotely.
        @param  host        The remote host on which the source are to be built.
        
        @return True iff the building was succesful.
        """
        buildCommand = self.buildCommand(client)
        if buildCommand:
            result = ''
            try:
                if self.isInCleanup():
                    return False
                host.sendCommand( 'cd "{0}"'.format( client.sourceObj.remoteLocation(client, host) ) )
                if self.isInCleanup():
                    return False
                result = host.sendCommand(buildCommand)
            except Exception:
                Campaign.logger.log( result )
                raise Exception( "Could not build client {0} remotely on host {2} using builder {1}".format( client.name, self.__class__.__name__, host.name ) )
        return True

    def getModuleType(self):
        """
        Return the moduleType string.
        
        @return    The module type.
        """
        return 'builder'
    
    def getName(self):
        """
        Return the name of the object.
        
        @return    The name.
        """
        return self.__class__.__name__

    @staticmethod
    def APIVersion():
        return "2.2.0-core"

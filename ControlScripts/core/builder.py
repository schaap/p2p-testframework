import os
from subprocess import STDOUT
from subprocess import PIPE
from subprocess import Popen

from core.parsing import *
from core.campaign import Campaign
from core.coreObject import coreObject

def parseError( msg ):
    raise Exception( "Parse error for client object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class builder(coreObject):
    """
    The parent class for all builder.

    This object contains all the default implementations for every builder.
    When subclassing builder be sure to use the skeleton class as a basis: it saves you a lot of time.
    """

    buildCommand = None         # If this is set to a string, that command can be used by the default implementation
                                # for buildLocal(...) and buildRemote(...).

    def __init__(self, scenario):
        """
        Initialization of a generic builder object.

        @param  scenario        The ScenarioRunner object this builder object is part of.
        """
        coreObject.__init__(self, scenario)

    def buildLocal(self, client):
        """
        Build the local sources for the client.
        
        This default implementation does nothing if buildCommand is not set.
        Otherwise it starts a local bash instance and gives the buildCommand as input to that.

        @param  client      The client for which the sources are to be built locally.
        """
        if self.buildCommand:
            result = ''
            try:
                if self.isInCleanup():
                    return
                proc = Popen('bash', bufsize=8192, stdin=PIPE, stdout=PIPE, stderr=STDOUT, cwd=client.sourceObj.localLocation() )
                if self.isInCleanup():
                    proc.kill()
                    return
                result = proc.communicate(self.buildCommand)
            except Exception exc:
                Campaign.logger.log( result )
                raise Exception( "Could not build client {0} locally using builder {1}".format( client.name, self.__class__.__name__ ) )
    
    def buildRemote(self, client, host):
        """
        Build the remote source for the client on the host.

        This default implementation does nothing if buildCommand is not set.
        Otherwise it sends the buildCommand to the host.

        @param  client      The client for which the sources are to be built remotely.
        @param  host        The remote host on which the source are to be built.
        """
        if self.buildCommand:
            # FIXME: CONTINUE

    @staticmethod
    def APIVersion():
        return "2.0.0-core"

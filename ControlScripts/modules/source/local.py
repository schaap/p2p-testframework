from core.source import source
from core.campaign import Campaign
import os
import re
import subprocess
from subprocess import STDOUT

def escapeFileName(f):
    """
    Internal function.
    """
    return re.sub( '\"', '\\\"', re.sub( '\\\\', '\\\\\\\\', f ) )
        
class local(source):
    """
    Source implementation for locally available sources.
    
    Whenever using this module, please make sure your source directory is small,
    for each and every file in it is copied to each host where it is to be compiled.
    Don't say you have not been warned.
    
    client.location is interpreted as the path to a directory on the local machine where
    the source resides. It will be copied to a temporary directory to be built.
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
        # No command, just create the dirs
        return ''
    
    def prepareLocal(self, client):
        """
        Prepare the source code of the client on the local machine.

        The default implementation creates a local temporary directory and runs self.prepareCommand(...) in that
        directory if it was specified.

        If self.prepareCommand(...) returns None the default implementation does nothing.

        @param  client      The client for which the sources are to be prepared.
        
        @return True iff the preparation was succesful.
        """
        if not os.path.exists( client.location ) or not os.path.isdir( client.location ):
            raise Exception( "The sources of client {0} should be found in local directory '{1}', but that either doesn't exist or is not a directory.".format( client.name, client.location ) )
        if not source.prepareLocal(self, client):
            return False
        try:
            subprocess.check_output( 'cp -r "{0}/"* "{1}/"'.format( escapeFileName( client.location ), escapeFileName( self.localLocation( client ) ) ), shell=True, stderr=STDOUT )
        except subprocess.CalledProcessError as cpe:
            Campaign.logger.log( "Could not locally prepare source for client {0}: {1}".format( client.name, cpe.output ) )
            raise cpe
        return True
    
    def prepareRemote(self, client, host):
        """
        Prepare the source code of the client on the remote host.

        The default implementation creates the directory self.remoteLocation(...) and runs self.prepareCommand(...)
        in that directory.

        If self.prepareCommand(...) returns None the default implementation does nothing.

        @param  client      The client for which the sources are to be prepared.
        @param  host        The host on which the sources are to be prepared.
        
        @return True iff the preparation was succesful.
        """
        if not os.path.exists( client.location ) or not os.path.isdir( client.location ):
            raise Exception( "The sources of client {0} should be found in local directory '{1}', but that either doesn't exist or is not a directory.".format( client.name, client.location ) )
        if not source.prepareRemote(self, client, host):
            return False
        if self.isInCleanup():
            return
        host.sendFiles( client.location, self.remoteLocation(client, host) )
        return True

    @staticmethod
    def APIVersion():
        return "2.2.0"

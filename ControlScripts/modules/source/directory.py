import os

from core.source import source

class directory(source):
    """
    Default implementation of source.
    
    This source object assumes that the directory pointed to by client.location exists and contains the source.
    
    The location parameter is interpreted as a path to a directory either locally or remotely (depending on the remoteClient parameter).
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
        return None

    def prepareLocal(self, client):
        """
        Prepare the source code of the client on the local machine.

        The default implementation creates a local temporary directory and runs self.prepareCommand(...) in that
        directory.

        If self.prepareCommand(...) returns None the default implementation does nothing.

        @param  client      The client for which the sources are to be prepared.
        
        @return True iff the preparation was succesful.
        """
        if not client.location:
            raise Exception( "Client {0} does not have its location parameter set, but source module directory requires it to be set.".format( client.name ) )
        if not os.path.exists( client.location ) or not os.path.isdir( client.location ):
            raise Exception( "The location parameter of client {0} does not point to an existing local directory: '{1}'".format( client.name, client.location ) )
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
        if not client.location:
            raise Exception( "Client {0} does not have its location parameter set, but source module directory requires it to be set.".format( client.name ) )
        res = host.sendCommand( '[ -e "{0}" -a -d "{0}" ] && echo -n "OK" || echo -n "E"'.format( client.location ) )
        if res[0:2] != "OK":
            raise Exception( "The location parameter of client {0} does not point to an existing remote directory: '{1}'".format( client.name, client.location ) )
        return True

    def localLocation(self, client):
        """
        Returns the local location of the client sources.

        Raises an Exception if no local sources are available (e.g. when prepareLocal has not yet been called).

        Note that when cleanup(...) is called, this directory will be removed.
        
        @param  client      The client for which the local source is needed.
        """
        return client.location

    # Unused arguments; oh well
    # pylint: disable-msg=W0613
    def remoteLocation(self, client, host):
        """
        Returns the remote location of the client sources on the host.

        No guarantees exist that the location exists. Be sure to call prepareRemote(...) for that.

        @param  client      The client for which the location is needed.
        @param  host        The host on which the location should reside.
        """
        return client.location
    # pylint: enable-msg=W0613

    @staticmethod
    def APIVersion():
        return "2.2.0"

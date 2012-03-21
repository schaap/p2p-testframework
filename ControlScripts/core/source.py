import tempfile
import shutil
import threading
from subprocess import Popen
from subprocess import PIPE
from subprocess import STDOUT

from core.campaign import Campaign
from core.coreObject import coreObject

class source(coreObject):
    """
    The parent class for all sources.

    This object contains all the default implementations for every source.
    When subclassing source be sure to use the skeleton class as a basis: it saves you a lot of time.
    """

    localSourceDir = None       # If this is set then that very directory needs to be removed when cleaning up.
    localSourceDir__lock = None # threading.Lock() guarding localSourceDir

    def __init__(self, scenario):
        """
        Initialization of a generic source object.

        @param  scenario        The ScenarioRunner object this source object is part of.
        """
        coreObject.__init__(self, scenario)
        self.localSourceDir__lock = threading.Lock()

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
    def prepareCommand(self, client):
        """
        Return the command to prepare the sources.

        This method interprets and verifies client.location, where the location of the sources is specified.

        Does not do the preparing itself! This method is used by prepareLocal(...) and prepareRemote(...) to find out
        what they are supposed to do.

        The default implementation returns None, which will tell prepareLocal(...) and prepareRemote(...) not to do
        anything. It is also possible to return '', in which case temporary directories will be created, but no
        command will be executed.

        @param  client      The client for which the sources are to be prepared.
        
        @return The command line to prepare the sources.
        """
        return None
    # pylint: enable-msg=W0613

    def prepareLocal(self, client):
        """
        Prepare the source code of the client on the local machine.

        The default implementation creates a local temporary directory and runs self.prepareCommand(...) in that
        directory if it was specified.

        If self.prepareCommand(...) returns None the default implementation does nothing.

        @param  client      The client for which the sources are to be prepared.
        
        @return True iff the preparation was succesful.
        """
        prepareCommand = self.prepareCommand(client)
        if prepareCommand is not None:
            try:
                self.localSourceDir__lock.acquire()
                if self.isInCleanup():
                    return False
                if self.localSourceDir:
                    raise Exception( "prepareLocal(...) of a source object should really be called only once!" )
                self.localSourceDir = tempfile.mkdtemp( )
                if not self.localSourceDir:
                    raise Exception( "prepareLocal(...) could not create a temporary directory on the local host" )
                if self.isInCleanup():
                    shutil.rmtree( self.localSourceDir )
                    self.localSourceDir = ''
                    return False
                if prepareCommand != '':
                    proc = Popen('bash', bufsize=8192, stdin=PIPE, stdout=PIPE, stderr=STDOUT, cwd=self.localSourceDir )
                    if self.isInCleanup():
                        shutil.rmtree( self.localSourceDir )
                        self.localSourceDir = ''
                        proc.kill()
                        return False
                    try:
                        result = proc.communicate(prepareCommand)
                    except Exception:
                        Campaign.logger.log( result )
                        raise Exception( "Could not prepare sources for client {0} locally using source {1}".format( client.name, self.__class__.__name__ ) )
            finally:
                try:
                    self.localSourceDir__lock.release()
                except RuntimeError:
                    pass
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
        prepareCommand = self.prepareCommand(client)
        if prepareCommand:
            try:
                if self.isInCleanup():
                    return False
                host.sendCommand( 'mkdir -p "{0}"'.format( self.remoteLocation(client, host) ) )
                if self.isInCleanup():
                    return False
                if prepareCommand != '':
                    result = host.sendCommand("( cd {0}; {1} )".format( self.remoteLocation(client, host), prepareCommand ) )
            except Exception:
                Campaign.logger.log( result )
                raise Exception( "Could not prepare sources for client {0} remotely on host {2} using builder {1}".format( client.name, self.__class__.__name__, host.name ) )
        return True

    # This method has unused arguments; that's fine
    # pylint: disable-msg=W0613
    def localLocation(self, client):
        """
        Returns the local location of the client sources.

        Raises an Exception if no local sources are available (e.g. when prepareLocal has not yet been called).

        Note that when cleanup(...) is called, this directory will be removed.
        
        @param  client      The client for which the local source is needed.
        """
        self.localSourceDir__lock.acquire()
        try:
            return self.localSourceDir
        finally:
            self.localSourceDir__lock.release()
    # pylint: enable-msg=W0613

    def remoteLocation(self, client, host):
        """
        Returns the remote location of the client sources on the host.

        During cleanup this may return None! 

        No guarantees exist that the location exists. Be sure to call prepareRemote(...) for that.

        @param  client      The client for which the location is needed.
        @param  host        The host on which the location should reside.
        """
        if client.getClientDir( host ):
            return "{0}/source".format( client.getClientDir( host ) )
        return None

    def cleanup(self):
        """
        Cleans up the sources.
        """
        try:
            self.localSourceDir__lock.acquire()
            if self.localSourceDir:
                shutil.rmtree( self.localSourceDir )
                self.localSourceDir = ''
        finally:
            try:
                self.localSourceDir__lock.release()
            except RuntimeError:
                pass

    def getModuleType(self):
        """
        Return the moduleType string.
        
        @return    The module type.
        """
        return 'source'
    
    def getName(self):
        """
        Return the name of the object.
        
        @return    The name.
        """
        return self.__class__.__name__

    @staticmethod
    def APIVersion():
        return "2.1.0-core"

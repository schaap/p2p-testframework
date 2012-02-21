import threading
import os

from core.campaign import Campaign
from core.host import host

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for host object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class connObj:
    connID = None
    closed = False

    def __init__(self, connID):
        self.connID = connID

class test__(host):
    """
    A test host implementation.

    All interactions with the host are logged in the __host__test__.log in the campaign results directory.
    Note that the commands will always output "", since they are not actually run. This is a clear limitation of the test host, use host:local for actually functioning test on the local host.
    """

    the__lock = None

    def __init__(self, scenario):
        """
        Initialization of a generic host object.
        
        @param  scenario        The ScenarioRunner object this host object is part of.
        """
        host.__init__(self, scenario)
        self.the__lock = threading.Lock()

    def parseSetting(self, key, value):
        """
        Parse a single setting for this object.

        Settings are written in text files in a key=value fashion.
        For each such setting that belongs to this object this method will be called.

        After all settings have been given, the method checkSettings will be called.

        If a setting does not parse correctly, this method raises an Exception with a descriptive message.

        Subclassers should first parse their own settings and then call this implementation to have the
        generic settings parsed and to have any unknown settings raise an Exception.
        
        @param  key     The name of the parameter, i.e. the key from the key=value pair.
        @param  value   The value of the parameter, i.e. the value from the key=value pair.
        """
        host.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        if not self.remoteDirectory:
            self.remoteDirectory = '.'  # Since a temporary directory would otherwise be created...
        host.checkSettings(self)

    def setupNewConnection(self):
        """
        Create a new connection to the host.

        The returned object has no specific type, but should be usable as a connection object either by uniquely identifying it or 
        simply by containing the needed information for it.

        Connections created using this function can be closed with closeConnection(...). When cleanup(...) is called all created
        connections will automatically closed and, hence, any calls using those connections will then fail.

        @return The connection object for a new connection.
        """
        self.connections__lock.acquire()
        co = None
        try:
            co = connObj(len(self.connections))
            self.connections.append(co)
        finally:
            self.connections__lock.release()
        return co

    def closeConnection(self, connection):
        """
        Close a previously created connection to the host.

        Any calls afterwards to methods of this host with the close connection will fail.

        @param  The connection to be closed.
        """
        if connection.closed:
            raise Exception( "Trying to close an already closed connection" )
        try:
            self.connections__lock.acquire()
            theIndex = None
            for index in range(0, len(self.connections)):
                if self.connections[index].connID == connection.connID:
                    theIndex = index
                    break
            if theIndex:
                if theIndex == 0 and len(self.connections) > 1:
                    raise Exception( "Can't close the default connection while others are still open" )
                del self.connections[theIndex]
        finally:
            try:
                self.connections__lock.release()
            except RuntimeError:
                pass
        connection.closed = True

    def decideConnection(self, reuseConnection):
        connection = None
        if not reuseConnection:
            connection = self.setupNewConnection()
        elif reuseConnection == True:
            try:
                self.connections__lock.acquire()
                connection = self.connections[0]
            finally:
                try:
                    self.connections__lock.release()
                except RuntimeError:
                    pass
        else:
            connection = reuseConnection
        if connection.closed:
            raise Exception( "Trying to use closed connection {0} for host {1}".format( connection.connID, self.name ) )
        return connection

    def writeCommandLog(self, log):
        try:
            self.the__lock.acquire()
            f = open( os.path.join( Campaign.getCurrentCampaign().campaignResultsDir, '__host__test__{0}__.log'.format( self.name ) ), 'a' )
            f.write( log )
            f.close()
        finally:
            try:
                self.the__lock.release()
            except RuntimeError:
                pass

    def sendCommand(self, command, reuseConnection = True):
        """
        Sends a bash command to the remote host.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     True for commands that are shortlived or are expected not to be parallel with other commands.
                                    False to build a new connection for this command and use that.
                                    A specific connection object as obtained through setupNewConnection(...) to reuse that connection.

        @return The result from the command. The result is stripped of leading and trailing whitespace before being returned.
        """
        if command == '':
            Campaign.logger.log( "Empty command to host {0}?".format( self.name ) )
        connection = self.decideConnection(reuseConnection)
        self.writeCommandLog( "CONN {0}: ".format(connection.connID) + command + "\n" )
        if not reuseConnection:
            self.closeConnection( connection )
        return ""

    def sendFile(self, localSourcePath, remoteDestinationPath, overwrite = False, reuseConnection = True):
        """
        Sends a file to the remote host.

        Regarding reuseConnection it is possible the value may be ignored: a new connection may be needed for file transfer, anyway.

        @param  localSourcePath         Path to the local file that is to be sent.
        @param  remoteDestinationPath   Path to the destination file on the remote host.
        @param  overwrite               Set to True to not raise an Exception if the destination already exists.
        @param  reuseConnection         True to try and reuse the default connection for sending the file.
                                        False to build a new connection for sending this file and use that.
                                        A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
        """
        if not os.path.exists( localSourcePath ) or not os.path.isfile( localSourcePath ):
            raise Exception( "Local source file '{0}' seems not to exist or is not a file".format( localSourcePath ) )
        if remoteDestinationPath == '' or not isinstance( remoteDestinationPath, basestring ):
            raise Exception( "Insane remote destination '{0}'".format( remoteDestinationPath ) )
        connection = self.decideConnection(reuseConnection)
        self.writeCommandLog( "CONN {0} SEND {1} TO {2}\n".format( connection.connID, localSourcePath, remoteDestinationPath ) )
        if not reuseConnection:
            self.closeConnection( connection )

    def getFile(self, remoteSourcePath, localDestinationPath, overwrite = False, reuseConnection = True):
        """
        Retrieves a file from the remote host.

        Regarding reuseConnection it is possible the value may be ignored: a new connection may be needed for file transfer, anyway.

        @param  remoteSourcePath        Path to the file to be retrieved on the remote host.
        @param  localDestinationPath    Path to the local destination file.
        @param  overwrite               Set to True to not raise an Exception if the destination already exists.
        @param  reuseConnection         True to try and reuse the default connection for sending the file.
                                        False to build a new connection for sending this file and use that.
                                        A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
        """
        if remoteSourcePath == '' or not isinstance( remoteSourcePath, basestring ):
            raise Exception( "Insane remote source '{0}'".format( remoteSourcePath ) )
        if os.path.exists( localDestinationPath ):
            if os.path.isdir( localDestinationPath ):
                raise Exception( "localDestinationPath '{0}' is a directory".format( localDestinationPath ) )
            elif not overwrite:
                raise Exception( "localDestinationPath '{0}' already exists and overwrite is not specified".format( localDestinationPath ) )
        connection = self.decideConnection(reuseConnection)
        self.writeCommandLog( "CONN {0} GET {1} TO {2}\n".format( connection.connID, remoteSourcePath, localDestinationPath ) )
        if not reuseConnection:
            self.closeConnection( connection )

    def prepare(self):
        """
        Execute commands on the remote host needed for host specific preparation.

        The default implementation simply ensures the existence of a remote directory.
        """
        host.prepare(self)

    def cleanup(self):
        """
        Executes commands to do host specific cleanup.
        
        The default implementation removes the remote temporary directory, if one was created.

        Subclassers are advised to first call this implementation and then proceed with their own steps.
        """
        host.cleanup(self)

    def getSubNet(self):
        """
        Return the subnet of the external addresses of the host.

        @return The subnet of the host(s).
        """
        return "127.0.0.1"

    def getAddress(self):
        """
        Return the single address (IP or hostname) of the remote host, if any.

        An obvious example of this method returning '' would be a host implementation that actually uses a number
        of remote hosts in one host object: one couldn't possibly return exactly one address for that and be
        correct about it in the process.

        Default implementation just returns ''.

        @return The address of the remote host, or '' if no such address can be given.
        """
        return ''

    @staticmethod
    def APIVersion():
        return "2.0.0"

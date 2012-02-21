from subprocess import Popen
from subprocess import STDOUT
from subprocess import PIPE
import threading
import subprocess
import os
import re

from core.campaign import Campaign
from core.host import host

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for host object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

def escapeFileName(f):
    """
    Internal function.
    """
    return re.sub( '\"', '\\\"', re.sub( '\\\\', '\\\\\\\\', f ) )
        
class ConnectionObject:
    counter = 0
    counter__lock = threading.Lock()

    proc = None
    closed = False
    close__lock = None
    ident = 0
    def __init__(self, proc):
        self.proc = proc
        self.close__lock = threading.Lock()
        ConnectionObject.counter__lock.acquire()
        ConnectionObject.counter += 1
        self.ident = ConnectionObject.counter
        ConnectionObject.counter__lock.release()
        self.counter__lock = None

    def close(self):
        self.close__lock.acquire()
        self.closed = True
        self.close__lock.release()

    def isClosed(self):
        self.close__lock.acquire()
        self.closed = True
        self.close__lock.release()

    def closeIfNotClosed(self):
        self.close__lock.acquire()
        res = self.closed
        self.closed = True
        self.close__lock.release()
        return res

    def stdin(self):
        return self.proc.stdin

    def stdout(self):
        return self.proc.stdout

class local(host):
    """
    A local host implementation.
    """
    
    # @static
    bashProgram = None              # Holds the path to bash

    def __init__(self, scenario):
        """
        Initialization of a generic host object.
        
        @param  scenario        The ScenarioRunner object this host object is part of.
        """
        host.__init__(self, scenario)
        if not local.bashProgram:
            if os.path.exists( '/bin/bash' ):
                local.bashProgram = '/bin/bash'
            elif os.path.exists( '/usr/bin/bash' ):
                local.bashProgram = '/usr/bin/bash'
            else:
                out, _ = Popen( 'which bash', stdout = PIPE, shell = True ).communicate()
                if out is None or out == '' or not os.path.exists( 'out' ):
                    raise Exception( "host:local requires bash to be present" )
                local.bashProgram = out

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
        if self.isInCleanup():
            return
        proc = Popen(['{0}'.format(local.bashProgram), '-l'], bufsize=8192, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        try:
            self.connections__lock.acquire()
            if self.isInCleanup():
                proc.communicate( 'exit' )
                return
            obj = ConnectionObject( proc )
            self.connections.append( obj )
            if self.isInCleanup():
                self.connections.pop()
                proc.communicate( 'exit' )
                return
        finally:
            try:
                self.connections__lock.release()
            except RuntimeError:
                pass
        self.sendCommand('echo "READY"', obj )
        return obj

    def closeConnection(self, connection):
        """
        Close a previously created connection to the host.

        Any calls afterwards to methods of this host with the close connection will fail.

        @param  The connection to be closed.
        """
        if connection.closeIfNotClosed():
            return
        connection.proc.communicate( 'exit' )
        try:
            self.connections__lock.acquire()
            index = 0
            while index < len(self.connections):
                if self.connections[index].ident == connection.ident:
                    self.connections.pop(index)
                    break
            else:
                raise Exception( "Closing connection that is not in the list of connections?" )
        finally:
            try:
                self.connections__lock.release()
            except RuntimeError:
                pass

    def __chooseConnection(self, reuseConnection):
        """
        Internal method
        """
        if reuseConnection is None:
            raise ValueError( "reuseConnection may never be None" )
        connection = None
        if not reuseConnection:
            connection = self.setupNewConnection()
        elif reuseConnection == True:
            try:
                self.connections__lock.acquire()
                if self.isInCleanup():
                    return
                connection = self.connections[0]
            finally:
                try:
                    self.connections__lock.release()
                except RuntimeError:
                    pass
        else:
            connection = reuseConnection

        if not connection:
            if reuseConnection == False:
                raise Exception( "Could not create a new connection on host {0}".format( self.name ) )
            elif reuseConnection == True:
                raise Exception( "Could not use default connection on host {0}".format( self.name ) )
            else:
                raise Exception( "Could not use connection {1} on host {0}".format( self.name, reuseConnection.ident ) )

        if connection.isClosed():
            raise Exception( "Trying to send a command over a closed connection." )
        
        return connection

    def sendCommand(self, command, reuseConnection = True):
        """
        Sends a bash command to the remote host.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     True for commands that are shortlived or are expected not to be parallel with other commands.
                                    False to build a new connection for this command and use that.
                                    A specific connection object as obtained through setupNewConnection(...) to reuse that connection.

        @return The result from the command. The result is stripped of leading and trailing whitespace before being returned.
        """
        connection = self.__chooseConnection(reuseConnection)
        if not connection and self.isInCleanup():
            return

        try:
            # Send command
            connection.stdin().write( command+'\necho "\nblabladibla__156987349253457979__noonesGonnaUseThis__right__p2ptestframework"\n' )
            connection.stdin().flush()
            # Read output of command
            out = connection.stdout()
            res = ''
            line = out.readline()
            while line != '' and line != 'blabladibla__156987349253457979__noonesGonnaUseThis__right__p2ptestframework\n':
                res += line
                line = out.readline()
            # Return output (ditch the last trailing \n)
            return res.strip()
        finally:
            if not reuseConnection:
                self.closeConnection( connection )
    
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
        connection = self.__chooseConnection(reuseConnection)

        try:
            if not os.path.exists( localSourcePath ) or not os.path.isfile( localSourcePath ):
                raise Exception( "Sending local file {0} to remote file {1}: local source should point to an existing file".format( localSourcePath, remoteDestinationPath ) )
            if not overwrite and os.path.exists( remoteDestinationPath ):
                raise Exception( "Sending local file {0} to remote file {1}: destination already exists".format( localSourcePath, remoteDestinationPath ) )
            elif os.path.isdir( remoteDestinationPath ):
                raise Exception( "Sending local file {0} to remote file {1}: destination would be overwritten, but is a directory".format( localSourcePath, remoteDestinationPath ) )
            try:
                subprocess.check_output( 'cp "{0}" "{1}"'.format( escapeFileName( localSourcePath ), escapeFileName( remoteDestinationPath ) ), shell=True, stderr=STDOUT )
            except subprocess.CalledProcessError as cpe:
                Campaign.logger.log( cpe.output )
                raise cpe
        finally:
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
        connection = self.__chooseConnection(reuseConnection)

        try:
            if not os.path.exists( remoteSourcePath ) or not os.path.isfile( remoteSourcePath ):
                raise Exception( "Getting remote file {0} to local file {1}: remote source should point to an existing file".format( remoteSourcePath, localDestinationPath ) )
            if not overwrite and os.path.exists( localDestinationPath ):
                raise Exception( "Getting remote file {0} to local file {1}: destination already exists".format( remoteSourcePath, localDestinationPath ) )
            elif os.path.isdir( localDestinationPath ):
                raise Exception( "Getting remote file {0} to local file {1}: destination would be overwritten, but is a directory".format( remoteSourcePath, localDestinationPath ) )
            try:
                subprocess.check_output( 'cp "{0}" "{1}"'.format( escapeFileName( remoteSourcePath ), escapeFileName( localDestinationPath ) ), shell=True, stderr=STDOUT )
            except subprocess.CalledProcessError as cpe:
                Campaign.logger.log( cpe.output )
                raise cpe
        finally:
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
        return '127.0.0.1'

    @staticmethod
    def APIVersion():
        return "2.0.0"
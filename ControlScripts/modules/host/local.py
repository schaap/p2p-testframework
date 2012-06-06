from subprocess import Popen
from subprocess import STDOUT
from subprocess import PIPE
import subprocess
import os
import re
import errno

from core.campaign import Campaign
from core.host import host, countedConnectionObject

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
        
class localConnectionObject(countedConnectionObject):
    proc = None
    def __init__(self, proc):
        countedConnectionObject.__init__(self)
        self.proc = proc

    def stdin(self):
        return self.proc.stdin

    def stdout(self):
        return self.proc.stdout
    
    def close(self):
        countedConnectionObject.close(self)
        self.proc.stdin.close()
        self.proc.stdout.close()
        del self.proc
        self.proc = None

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

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        host.resolveNames(self)

    def setupNewConnection(self):
        """
        Create a new connection to the host.

        The returned object has no specific type, but should be usable as a connection object either by uniquely identifying it or 
        simply by containing the needed information for it.

        Connections created using this function can be closed with closeConnection(...). When cleanup(...) is called all created
        connections will automatically closed and, hence, any calls using those connections will then fail.

        @return The connection object for a new connection. This should be an instance of a subclass of core.host.connectionObject.
        """
        if self.isInCleanup():
            return
        proc = Popen(['{0}'.format(local.bashProgram), '-l'], bufsize=8192, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        Campaign.debuglogger.log( 'local_{0}'.format(self.name), 'CREATED in scenario {1} for LOCAL host {0}'.format( self.name, self.scenario.name ) )
        try:
            self.connections__lock.acquire()
            if self.isInCleanup():
                try:
                    proc.communicate( 'exit' )
                except OSError as e:
                    if not e.errno == errno.EPIPE: # This one is expected
                        raise e
                return
            obj = localConnectionObject( proc )
            self.connections.append( obj )
            if self.isInCleanup():
                self.connections.pop()
                try:
                    proc.communicate( 'exit' )
                except OSError as e:
                    if not e.errno == errno.EPIPE: # This one is expected
                        raise e
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
        Campaign.debuglogger.closeChannel( 'local_{0}'.format(self.name) )
        host.closeConnection(self, connection)

    def sendCommand(self, command, reuseConnection = True):
        """
        Sends a bash command to the remote host.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     True for commands that are shortlived or are expected not to be parallel with other commands.
                                    False to build a new connection for this command and use that.
                                    A specific connection object as obtained through setupNewConnection(...) to reuse that connection.

        @return The result from the command. The result is stripped of leading and trailing whitespace before being returned.
        """
        connection = None
        try:
            connection = self.getConnection(reuseConnection)
            # Send command
            self.sendCommandAsyncStart(command, connection)
            # Read output of command
            return self.sendCommandAsyncEnd(connection)

        finally:
            self.releaseConnection(reuseConnection, connection)
    
    def sendCommandAsyncStart(self, command, reuseConnection):
        """
        Sends a bash command to the remote host without waiting for the answer.
        
        Note that it is imperative that you call sendCommandAsyncEnd(...) after this call, or you will screw up your connection!

        Be sure to call connection.setInAsync() as well.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
                                    Contrary to other methods True of False are explicitly not accepted.
        """
        try:
            connection = self.getConnection(reuseConnection)
            if connection.isInAsync():
                Campaign.logger.log( "WARNING! Connection {0} of host {1} started an async command, but an async command was still running.".format( connection.getIdentification(), self.name ), True )
                Campaign.logger.localTraceback( True )
                res = self.sendCommandAsyncEnd(connection)
                Campaign.logger.log( "WARNING! Output of ending the connection: {0}".format( res ), True )
                connection.outOfOrderResult = res
            connection.stdin().write( command+'\n# `\n# \'\n# \"\necho "\nblabladibla__156987349253457979__noonesGonnaUseThis__right__p2ptestframework"\n' )
            connection.stdin().flush()
            connection.setInAsync()
            Campaign.debuglogger.log( 'local_{0}'.format(self.name), 'SEND {0}'.format( command ) )
        finally:
            self.releaseConnection(reuseConnection, connection)

    def sendCommandAsyncEnd(self, reuseConnection):
        """
        Retrieves the response to a bash command to the remote host that was sent earlier on.
        
        Note that this must not be called other than directly after sendCommandAsyncStart(...).
        Do not call on just any connection or you will screw it up!

        Be sure to call connection.clearInAsync() as well.

        @param  reuseConnection     A specific connection object as obtained through setupNewConnection(...) to reuse that connection.
                                    Contrary to other methods True of False are explicitly not accepted.
        
        @return The result from the command. The result is stripped of leading and trailing whitespace before being returned.
        """
        try:
            connection = self.getConnection(reuseConnection)
            if not connection.isInAsync():
                Campaign.logger.log( "WARNING! Connection {0} of host {1} ended an async command, but none was running. Returning ''.".format( connection.getIdentification(), self.name ), True )
                Campaign.logger.localTraceback(True)
                res = connection.outOfOrderResult
                connection.outOfOrderResult = ''
                return res
            out = connection.stdout()
            res = ''
            line = out.readline()
            while line != '' and line != 'blabladibla__156987349253457979__noonesGonnaUseThis__right__p2ptestframework\n':
                Campaign.debuglogger.log( 'local_{0}'.format(self.name), 'RECV {0}'.format( line ) )
                res += line
                line = out.readline()
            connection.clearInAsync()
            # Return output (ditch the last trailing \n)
            return res.strip()
        finally:
            self.releaseConnection(reuseConnection, connection)

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
        connection = None
        try:
            connection = self.getConnection(reuseConnection)
            if not os.path.exists( localSourcePath ) or not os.path.isfile( localSourcePath ):
                raise Exception( "Sending local file {0} to remote file {1}: local source should point to an existing file".format( localSourcePath, remoteDestinationPath ) )
            if not overwrite and os.path.exists( remoteDestinationPath ):
                raise Exception( "Sending local file {0} to remote file {1}: destination already exists".format( localSourcePath, remoteDestinationPath ) )
            elif os.path.isdir( remoteDestinationPath ):
                raise Exception( "Sending local file {0} to remote file {1}: destination would be overwritten, but is a directory".format( localSourcePath, remoteDestinationPath ) )
            try:
                Campaign.debuglogger.log( 'local_{0}'.format(self.name), 'CP SEND FILE {0} TO {1}'.format( localSourcePath, remoteDestinationPath ) )
                subprocess.check_output( 'cp "{0}" "{1}"'.format( escapeFileName( localSourcePath ), escapeFileName( remoteDestinationPath ) ), shell=True, stderr=STDOUT )
            except subprocess.CalledProcessError as cpe:
                Campaign.logger.log( cpe.output )
                raise cpe
        finally:
            self.releaseConnection(reuseConnection, connection)
    
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
        connection = None
        try:
            connection = self.getConnection(reuseConnection)
            if not os.path.exists( remoteSourcePath ) or not os.path.isfile( remoteSourcePath ):
                raise Exception( "Getting remote file {0} to local file {1}: remote source should point to an existing file".format( remoteSourcePath, localDestinationPath ) )
            if not overwrite and os.path.exists( localDestinationPath ):
                raise Exception( "Getting remote file {0} to local file {1}: destination already exists".format( remoteSourcePath, localDestinationPath ) )
            elif os.path.isdir( localDestinationPath ):
                raise Exception( "Getting remote file {0} to local file {1}: destination would be overwritten, but is a directory".format( remoteSourcePath, localDestinationPath ) )
            try:
                Campaign.debuglogger.log( 'local_{0}'.format(self.name), 'CP RETRIEVE FILE {0} TO {1}'.format( remoteSourcePath, localDestinationPath ) )
                subprocess.check_output( 'cp "{0}" "{1}"'.format( escapeFileName( remoteSourcePath ), escapeFileName( localDestinationPath ) ), shell=True, stderr=STDOUT )
            except subprocess.CalledProcessError as cpe:
                Campaign.logger.log( cpe.output )
                raise cpe
        finally:
            self.releaseConnection(reuseConnection, connection)

    def prepare(self):
        """
        Execute commands on the remote host needed for host specific preparation.

        The default implementation simply ensures the existence of a remote directory.
        """
        host.prepare(self)

    def cleanup(self, reuseConnection = None):
        """
        Executes commands to do host specific cleanup.
        
        The default implementation removes the remote temporary directory, if one was created.

        Subclassers are advised to first call this implementation and then proceed with their own steps.
        
        @param  reuseConnection If not None, force the use of this connection object for commands to the host.
        """
        host.cleanup(self, reuseConnection)

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
        return "2.4.0"

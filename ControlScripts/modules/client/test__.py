import os

from core.parsing import *
from core.campaign import Campaign
from core.client import client

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for client object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class test__(client):
    """
    A test implementation of the client class.

    This client does nothing but wait a bit.

    Note that, unless you make sure yourself that it works, this client will make any builder fail for the simple reason that it doesn't have source ode.

    Extra parameters:
    - testTime      The number of second the 'client' should 'run' (i.e. sleep), default to 1 (positive integer)
    """

    testTime = None

    def __init__(self, scenario):
        """
        Initialization of a generic client object.

        @param  scenario        The ScenarioRunner object this client object is part of.
        """
        client.__init__(self, scenario)

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
        if key == 'testTime':
            if self.testTime is not None:
                parseError( "Test time already set to {0}".format( self.testTime ) )
            if not isPositiveInt( value, True ):
                parseError( "The number of seconds to wait must be a non-zero positive integer" )
            self.testTime = value
        else:
            host.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        client.checkSettings(self)
        if self.testTime is None:
            self.testTime = 1

    def prepare(self):
        """
        Generic preparations for the client, irrespective of executions or hosts.
        """
        client.prepare(self)

    def prepareHost(self, host):
        """
        Client specific preparations on a host, irrespective of execution.

        This usually includes send files to the host, such as binaries.

        Note that the sendToHost and sendToSeedingHost methods of the file objects have not been called, yet.
        This means that any data files are not available.

        @param  host            The host on which to prepare the client.
        """
        client.prepareHost(self, host)

        theDir = self.location
        if client.isRemote:
            theDir = self.getClientDir(host)

        if self.isInCleanup():
            return
        host.sendCommand( 'touch "{0}/client_bin"'.format( theDir ) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "#!/bin/bash" >> "{0}/client_bin"'.format( theDir ) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "cat <<232EOF454" >> "{0}/client_bin"'.format( theDir ) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "Full configuration of test client:" >> "{0}/client_bin"'.format( theDir ) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'getClientDir(host)', self.getClientDir(host)) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'getClientDir(host, True)', self.getClientDir(host, True)) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'getLogDir(host)', self.getLogDir(host)) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'getLogDir(host, True)', self.getLogDir(host, True)) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'testTime', self.testTime) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'extraParameters', self.extraParameters) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'defaultParser', self.defaultParser) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'source', self.source) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'builder', self.builder) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'location', self.location) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "{1}: {2}" >> "{0}/client_bin"'.format( theDir, 'isRemote', self.isRemote) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "232EOF454" >> "{0}/client_bin"'.format( theDir ) )
        if self.isInCleanup():
            return
        host.sendCommand( 'echo "sleep {1}" >> "{0}/client_bin"'.format( theDir, self.testTime ) )
        if self.isInCleanup():
            return
        host.sendCommand( 'chmod +x "{0}/client_bin"'.format( theDir ) )

    def prepareExecution(self, execution, simpleCommandLine = None, complexCommandLine = None):
        """
        Client specific preparations for a specific execution.

        If any scripts for running the client on the host are needed, this is the place to build them.
        Be sure to take self.extraParameters into account, in that case.

        @param  execution           The execution to prepare this client for.
        """
        client.prepareExecution(self, execution, simpleCommandLine = './client_bin > "{0}/log.log"'.format( self.getExecutionLogDir( execution ) ) )

    def start(self, execution):
        """
        Run the client for the provided execution.

        All necessary files are already available on the host at this point.
        Be sure to take self.extraParameters into account, here.

        The PID of the running client should be saved in the dictionary self.pids, which is guarded by
        self.pid__lock

        @param  execution       The execution this client is to be run for.
        """
        client.start(execution)

    def retrieveLogs(self, execution, localLogDestination):
        """
        Retrieve client specific logs for the given execution.
        
        The logs are to be stored in the directory pointed to by localLogDestination.
        
        @param  execution               The execution for which to retrieve logs.
        @param  localLogDestination     A string that is the path to a local directory in which the logs are to be stored.
        """
        if not os.path.exists( localLogDestination ) or not os.path.isdir( localLogDestination ):
            raise Exception( "Insane localLogDestination {0}".format( localLogDestination ) )
        
    def cleanupHost(self, host):
        """
        Client specific cleanup for a host, irrespective of execution.

        Should also remove the client from the host as far as it wasn't already there.

        @param  host            The host on which to clean up the client.
        """
        client.cleanupHost(self, host)

    def cleanup(self):
        """
        Client specific cleanup, irrespective of host or execution.

        The default calls any required cleanup on the sources.
        """
        client.cleanup(self)

    def trafficProtocol(self):
        """
        Returns the protocol on which the client will communicate.

        This value is used for setting up restricted traffic control (TC), if requested.
        Typical values are "TCP", "UDP", etc.

        When a TC module finds a protocol it can't handle explicitly, or '' as a protocol, it will fall back to
        full traffic control, i.e. all traffic between involved hosts.

        If possible, specify this correctly, otherwise leave it '' (default).

        @return The protocol the client uses for communication.
        """
        return client.trafficProtocol(self)

    def trafficInboundPorts(self):
        """
        Returns a list of inbound ports on which all incoming traffic can be controlled.
        
        This list is used to set up traffic control, if requested.

        The list should only be given if it is definite: if dynamic ports can be assigned to the clients it is best
        to just return () to force full traffic control. This also goes if the list can't be given for other reasons.

        The exact notation of ports depends on the value returned by self.trafficProtocol().

        The default implementation just returns [].

        @return A list of all ports on which incoming traffic can come, or [] if no such list can be given.
        """
        return client.trafficInboundPorts(self)

    def trafficOutboundPorts(self):
        """
        Returns a list of outbound ports on which all outgoing traffic can be controlled.

        This list is used to set up traffic control, if requested.

        The list should only be given if it is definite: if dynamic ports can be assigned to the clients it is best
        to just return () to force full traffic control. This also goes if the list can't be given for other reasons.

        The exact notation of ports depends on the value returned by self.trafficProtocol().

        The default implementation just returns [].

        @return A list of all ports from which outgoing traffic can come, or [] if no such list can be given.
        """
        return client.trafficOutboundPorts(self)

    @staticmethod
    def APIVersion():
        return "2.0.0"

from core.parsing import isPositiveInt, containsSpace
from core.campaign import Campaign
from core.client import client

import os.path

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for client object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class swift(client):
    """
    libswift command line client implementation.
    
    Extra parameters:
                        
    - listenAddress     Which address to listen on
                        (i.e. --listen to swift, together with listenPort)
    - listenPort        Which port to listen on
                        (i.e. --listen to swift, together with listenAddress)
    - tracker           Specifies a tracker address (i.e. --tracker to swift);
                        the tracker may be specified as @name or @name:port to load
                        the named host inside the testing framework after all hosts
                        have been prepared, and use that host's address.
    - wait              Specified the number of seconds to wait
                        (i.e. --wait to swift in seconds)
    - chunkSize         Chunk size to be used by the swift process in bytes.
                        Optional, defaults to 1024.
    
    The libswift client will require --wait for seeders. By default it is set to 900s for seeders.
    
    Example using dynamic tracker addressing:
    
        [host:ssh]
        name=yourSeeder
        hostname=seeder.host.org
        
        [client:swift]
        name=leeching_swift_client
        tracker=@yourSeeder:2000
    
    This will have all instances of leeching_swift_client use yourSeeder as its tracker,
    whatever address is actually used for that host. This function is extremely useful
    with host modules like the DAS4, for which the address of the host isn't known before
    you're actually running the test.
    """

    listenAddress = None        # Address to listen on
    listenPort = None           # Port to listen on
    tracker = None              # Tracker address
    wait = None                 # Time to wait
    chunkSize = None            # base bin size

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
        if key == 'listenAddress':
            if self.listenAddress:
                parseError( "listenAddress is already set: {0}".format( self.listenAddress ) )
            if containsSpace(value):
                parseError( "listenAddress may not contain any whitespace" )
            self.listenAddress = value
        elif key == 'listenPort':
            if self.listenPort:
                parseError( "listenPort is already set: {0}".format( self.listenPort ) )
            if not isPositiveInt( value, True ):
                parseError( "listenPort must be a positive integer" )
            self.listenPort = int(value)
        elif key == 'tracker':
            if self.tracker:
                parseError( "tracker is already set: {0}".format( self.tracker ) )
            if containsSpace(value):
                parseError( "tracker may not contain any whitespace" )
            self.tracker = value
        elif key == 'wait':
            if self.wait:
                parseError( "wait is already set: {0}".format( self.wait ) )
            if not isPositiveInt( value, True ):
                parseError( "wait must be a positive integer" )
            self.wait = int(value)
        elif key == 'chunkSize':
            if self.chunkSize:
                parseError( "chunck size is already set: {0}".format( self.chunkSize ) )
            if not isPositiveInt( value, True ):
                parseError( "chunck size must be a positive integer" )                
            self.chunkSize = int(value)
        else:
            client.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        client.checkSettings(self)
        if self.listenPort:
            if self.listenAddress:
                self.listenAddress = "{0}:{1}".format( self.listenAddress, self.listenPort )
            else:
                self.listenAddress = ":{0}".format( self.listenPort )

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        client.resolveNames(self)

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

    # That's right, 2 arguments less.
    # pylint: disable-msg=W0221
    def prepareExecution(self, execution):
        """
        Client specific preparations for a specific execution.

        If any scripts for running the client on the host are needed, this is the place to build them.
        Be sure to take self.extraParameters into account, in that case.

        @param  execution           The execution to prepare this client for.
        """
        allParams = ""
        if execution.isSeeder():
            allParams += ' --file {0}'.format( execution.file.getFile(execution.host) )
            if not self.wait:
                allParams += ' --wait 900s'
        else:
            roothash = execution.file.getRootHash()
            if not roothash:
                raise Exception( "The swift client, when leeching, requires the root hash of the file to be set. Execution {0} of client {1} on host {2} is leeching, but file {3} does not have a root hash set.".format( execution.getNumber(), self.name, execution.host.name, execution.file.name ) )        
            allParams += ' --hash {0} --file "{1}/outputFile"'.format( roothash, self.getExecutionClientDir(execution) )
        if self.wait:
            allParams += ' --wait {0}s'.format( self.wait )
        if self.listenAddress:
            allParams += ' --listen {0}'.format( self.listenAddress )
        if self.chunkSize:
            allParams += ' --chunksize {0}'.format( self.chunkSize )
        if self.tracker:
            if self.tracker[0] == '@':
                indirecttracker = self.tracker[1:]
                colonindex = self.tracker.find(':')
                if colonindex != -1:
                    indirecttracker = self.tracker[1:colonindex]
                if indirecttracker not in self.scenario.getObjectsDict('host'):
                    raise Exception( "Swift client {0} has specified {1} as its indirect tracker, but host {2} does not exist.".format( self.name, self.tracker, indirecttracker ) )
                trackeraddress = self.scenario.getObjectsDict('host')[indirecttracker].getAddress()
                if trackeraddress == '':
                    raise Exception( "Swift client {0} has specified {1} as its indirect tracker, but host {2} can't give a specific address.".format( self.name, self.tracker, indirecttracker ) )
                if colonindex != -1:
                    trackeraddress += self.tracker[colonindex:]
                allParams += ' --tracker {0}'.format( trackeraddress )
            else:
                allParams += ' --tracker {0}'.format( self.tracker )
        if self.extraParameters:
            allParams += ' {0}'.format( self.extraParameters )
        if self.isInCleanup():
            return
        client.prepareExecution(self, execution, simpleCommandLine = 'LD_LIBRARY_PATH=$LD_LIBRARY_PATH:. ./swift --progress {0} 2> "{1}/log.log"'.format( allParams, self.getExecutionLogDir(execution) ) )
    # pylint: enable-msg=W0221

    def start(self, execution):
        """
        Run the client for the provided execution.

        All necessary files are already available on the host at this point.
        Be sure to take self.extraParameters into account, here.

        The PID of the running client should be saved in the dictionary self.pids, which is guarded by
        self.pid__lock

        @param  execution       The execution this client is to be run for.
        """
        client.start(self, execution)

    def retrieveLogs(self, execution, localLogDestination):
        """
        Retrieve client specific logs for the given execution.
        
        The logs are to be stored in the directory pointed to by localLogDestination.
        
        @param  execution               The execution for which to retrieve logs.
        @param  localLogDestination     A string that is the path to a local directory in which the logs are to be stored.
        """
        if self.getExecutionLogDir(execution):
            execution.host.getFile( '{0}/log.log'.format( self.getExecutionLogDir(execution) ), os.path.join( localLogDestination, 'log.log' ), reuseConnection = execution.getRunnerConnection() )
        client.retrieveLogs(self, execution, localLogDestination)

    def cleanupHost(self, host, reuseConnection = None):
        """
        Client specific cleanup for a host, irrespective of execution.

        Should also remove the client from the host as far as it wasn't already there.

        @param  host            The host on which to clean up the client.
        """
        client.cleanupHost(self, host, reuseConnection)

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
        return ''

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
        if self.listenPort:
            return [self.listenPort]
        return []

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
        if self.listenPort:
            return [self.listenPort]
        return []

    def getBinaryLayout(self):
        """
        Return a list of binaries that need to be present on the server.
        
        Add directories to be created as well, have them end with a /.
        
        Return None to handle the uploading or moving yourself.
        
        @return    List of binaries.
        """
        return ['swift']
    
    def getSourceLayout(self):
        """
        Return a list of tuples that describe the layout of the source.
        
        Each tuple in the list corresponds to (sourcelocation, binarylocation),
        where the binarylocation is one of the entries returned by getBinaryLayout().
        
        Each entry in getBinaryLayout() that is not directory needs to be present.
        
        Return None to handle the uploading or moving yourself.
        
        @return    The layout of the source.
        """
        return [('swift','swift')]

    def getExtraUploadLayout(self):
        """
        Returns a list of local files that are always uploaded to the remote host.
        
        Each tuple in the list corresponds to (locallocation, remotelocation),
        where the first is the location of the local file and the second is the
        relative location of the file on the remote host (relative to the location
        of the client's directory).
        
        Add directories to be created as well, have their locallocation be '' and 
        have their remotelocation end with a /.
                
        This method is especially useful for wrappers and the like.
        
        Return None to handle the uploading yourself.
        
        @return    The files that are always to be uploaded.
        """
        return None

    @staticmethod
    def APIVersion():
        return "2.0.0"

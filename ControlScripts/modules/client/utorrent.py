from core.campaign import Campaign
from core.client import client

import os

class utorrent(client):
    """
    uTorrent client runner.
    
    Extra parameters:
    - useWine       If set to "yes" this will instruct client:utorrent to use the windows client under wine.
                    Note that this requires the user to make sure wine and xvfb-run function correctly on
                    the target hosts!
    """

    useWine = False

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
        if key == 'useWine':
            if value == 'yes':
                self.useWine = True
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
        
        if self.builder:
            raise Exception( "client:utorrent does not support compilation from source... Where did you get those sources, anyway?" )
        
        if self.useWine:
            if not os.path.exists( os.path.join( Campaign.testEnvDir, 'ClientWrappers', 'utorrent-windows', 'ut_server_logging' ) ) or not os.path.exists( os.path.join( Campaign.testEnvDir, 'ClientWrappers', 'utorrent-windows', 'settings.dat' ) ):
                raise Exception( "The uTorrent client runner, when using wine, needs the utorrent runner scripts for wine. These are expected to be present in ClientWrappers/utorrent-windows/, but they aren't." )
        else:
            if not os.path.exists( os.path.join( Campaign.testEnvDir, 'ClientWrappers', 'utorrent', 'ut_server_logging' ) ):
                raise Exception( "The uTorrent client runner needs the utorrent runner scripts for wine. These are expected to be present in ClientWrappers/utorrent-windows/, but they aren't." )

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
        if not execution.file.getMetaFile(execution.host):
            raise Exception( "In order to use uTorrent a .torrent file needs to be associated with file {0}.".format( execution.file.name ) )
        if execution.isSeeder():
            client.prepareExecution(self, execution, simpleCommandLine = 'LD_LIBRARY_PATH=$LD_LIBRARY_PATH:~/lib {0}/ut_server_logging {0} {1} {2} {3} > {4}/log.log 2> {4}/errlog.log'.format( self.getClientDir(execution.host), self.getExecutionClientDir(execution), execution.file.getMetaFile(execution.host), execution.file.getFile(execution.host), self.getExecutionLogDir(execution) ) )
        else:
            client.prepareExecution(self, execution, simpleCommandLine = 'LD_LIBRARY_PATH=$LD_LIBRARY_PATH:~/lib {0}/ut_server_logging {0} {1} {2}     > {4}/log.log 2> {4}/errlog.log'.format( self.getClientDir(execution.host), self.getExecutionClientDir(execution), execution.file.getMetaFile(execution.host), execution.file.getFile(execution.host), self.getExecutionLogDir(execution) ) )
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
        execution.host.getFile( '{0}/log.log'.format( self.getExecutionLogDir( execution ) ), '{0}/log.log'.format( localLogDestination ), reuseConnection = execution.getRunnerConnection() )
        execution.host.getFile( '{0}/errlog.log'.format( self.getExecutionLogDir( execution ) ), '{0}/errlog.log'.format( localLogDestination ), reuseConnection = execution.getRunnerConnection() )

    def cleanupHost(self, host, reuseConnection = None):
        """
        Client specific cleanup for a host, irrespective of execution.

        Should also remove the client from the host as far as it wasn't already there.

        @param  host            The host on which to clean up the client.
        @param  reuseConnection If not None, force the use of this connection for command to the host.
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

    def getBinaryLayout(self):
        """
        Return a list of binaries that need to be present on the server.
        
        Add directories to be created as well, have them end with a /.
        
        Return None to handle the uploading or moving yourself.
        
        @return    List of binaries.
        """
        if self.useWine:
            return [ 'webui.zip', 'utorrent.exe' ]
        else:
            return [ 'webui.zip', 'utserver' ]
    
    def getSourceLayout(self):
        """
        Return a list of tuples that describe the layout of the source.
        
        Each tuple in the list corresponds to (sourcelocation, binarylocation),
        where the binarylocation is one of the entries returned by getBinaryLayout().
        
        Each entry in getBinaryLayout() that is not directory needs to be present.
        
        Return None to handle the uploading or moving yourself.
        
        @return    The layout of the source.
        """
        return None

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
        if self.useWine:
            return [(os.path.join( Campaign.testEnvDir, 'ClientWrappers', 'utorrent-windows', 'ut_server_logging' ), 'ut_server_logging'),
                    (os.path.join( Campaign.testEnvDir, 'ClientWrappers', 'utorrent-windows', 'settings.dat' ), 'settings.dat')]
        else:
            return [(os.path.join( Campaign.testEnvDir, 'ClientWrappers', 'utorrent', 'ut_server_logging' ), 'ut_server_logging')]
        return None

    @staticmethod
    def APIVersion():
        return "2.0.0"

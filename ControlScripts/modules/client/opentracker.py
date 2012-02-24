from core.parsing import isPositiveInt, isValidName
from core.campaign import Campaign
from core.client import client

import os

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for client object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class opentracker(client):
    """
    A client implementation for the Opentracker torrent tracker software
    
    You can retrieve the Opentracker software from http://erdgeist.org/arts/software/opentracker/
    
    Extra parameters:
    - port              The port on which the tracker will be listening; required, 1023 < positive int < 65536
    - changeTracker     The name of a file object for which the metaFile parameter has been set and points
                        to a .torrent file; the torrent file will be changed to point to the dynamically
                        retrieved address of the first host running this client; the file object will be
                        altered to have their metaFile point to the changed torrent file before the files
                        will be uploaded; can be specified multiple times.
    """
    
    port = None                 # The port openTracker will listen on
    changeTrackers = None       # List of names of file objects for which to change the torrent files
    hasUpdatedTrackers = False  # Flag to keep track of whether the trackers have already been updated or not
    tempUpdatedFiles = []       # List of all the temporary files (which need to be erased on cleanup)

    def __init__(self, scenario):
        """
        Initialization of a generic client object.

        @param  scenario        The ScenarioRunner object this client object is part of.
        """
        client.__init__(self, scenario)
        self.changeTrackers = []

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
        if key == 'port':
            if self.port:
                parseError( "Port already set: {0}".format( self.port ) )
            if not isPositiveInt( value ) or int(value) < 1024 or int(value) > 65535:
                parseError( "Port must be a positive integer greater than 1023 and smaller than 65536, not {0}".format( value ) )
            self.port = int(value)
        elif key == 'changeTracker':
            if not isValidName( value ):
                parseError( "{0} is not a valid name for a file object.".format( value ) )
            self.changeTrackers.append( value )
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
        
        if not self.port:
            raise Exception( "The port parameter is required for host {0}".format( self.name ) )

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
        # The default implementations takes care of creating client specific directories on the host, as well as
        # compilation of the client on the host, if needed. Be sure to call it.
        client.prepareHost(self, host)
        # The client specific directories on the remote host can be found using self.getClientDir(...) and
        # self.getLogsDir(...)
        #
        # TODO: Prepare the host for running your client. This usually includes uploading the binaries from local,
        # or moving some things around remotely. The end goal of this method is that the method start() works, no
        # matter how the client was built or sent. Four cases are to be considered:
        #   -   The client binaries are available locally; they have to be sent to the remote host
        #   -   The client sources have been built locally; the binaries have to be sent to the remote host
        #   -   The client binaries are available remotely; no action should be required
        #   -   The client sources have been built remotely; the binaries may need to be moved around
        # The thing to keep in mind is that, when using the default implementation with the runner script made by
        # prepareExecution(...), the script will first change directory as follows:
        #   -   Local binaries or sources:      self.getClientDir( host, False )
        #   -   Remote binaries or sources:     self.sourceObj.remoteLocation()
        # From that point on the client should be runnable with the same commands. This will most likely mean that
        # the client binaries have to end up in the same place (relative to the used remote directory), no matter
        # where they came from (local or remote) and how they were provided at first (binary or source).
        #
        # Example:
        #
        #   if self.isInCleanup():      # Don't make a mess while cleaning up
        #       return
        #   if self.isRemote:
        #       # If any fiels on the remote host need to be moved around, be sure to do so here.
        #       # Example that moves the binary if it was built from source on the remote host:
        #       host.sendCommand( '[ -d "{0}/src" ] && mv "{0}/src/yourClientBinary" "{0}/"'.format(
        #                                   self.sourceObj.remoteLocation(self, host) ) )
        #   else:
        #       # Send your client files here, either from the source location (where building took place) or the
        #       # location where the binaries already reside.
        #
        #       # The following is a version for a simple, single-binary client, which is compiled in-place:
        #       # host.sendFile( '{0}/yourClientBinary'.format( self.sourceObj.localLocation(self) ),
        #       #                '{0}/yourClientBinary'.format( self.getClientDir( host ) ), True )
        #
        #       # A more extended example, which takes the source structure into account:
        #       if os.path.exists( '{0}/src'.format( self.sourceObj.localLocation(self) ) ):
        #           host.sendFile( '{0}/src/yourClientBinary'.format( self.sourceObj.localLocation(self) ),
        #                          '{0}/yourClientBinary'.format( self.getClientDir( host ) ), True )
        #       else:
        #           host.sendFile( '{0}/yourClientBinary'.format( self.sourceObj.localLocation(self) ),
        #                          '{0}/yourClientBinary'.format( self.getClientDir( host ) ), True )
        #
        # This is quite an elaborate method, but it is important to take into account all four cases. That will
        # ensure that your client runs well. If you need extra files available on the remote host you can copy them
        # here as well, of course, and/or check their availability to make sure the client will run.
        #
        if self.isRemote:
            host.sendFile( os.path.join( self.sourceObj.localLocation(self), 'opentracker' ), '{0}/opentracker'.format(self.getClientDir(host)), True )
        
        if not self.hasUpdatedTrackers and len( self.changeTrackers ) > 0:
            self.hasUpdatedTrackers = True
            newTracker = host.getAddress()
            if not newTracker:
                raise Exception( "Client {0} was instructed to change some torrent files to update their trackers, but host {1} won't give an address for that.".format( self.name, host.name ) )
            newTracker = 'http://{0}:{1}/announce'.format( newTracker, self.port )
            for f in self.changeTrackers:
                if f not in self.scenario.getObjectsDict( 'file' ):
                    raise Exception( "Client {0} was instructed to change the torrent file of file {1}, but the latter was never declared.".format( self.name, f ) )
                
                

    # That's right, 2 arguments less.
    # pylint: disable-msg=W0221
    def prepareExecution(self, execution):
        """
        Client specific preparations for a specific execution.

        If any scripts for running the client on the host are needed, this is the place to build them.
        Be sure to take self.extraParameters into account, in that case.

        @param  execution           The execution to prepare this client for.
        """
        # The default implementation will create the client/execution specific directories, which can be found using
        # self.getExecutionClientDir(...) and self.getExecutionLogDir(...)
        #
        # The default implemenation can also build a runner script that can be used with the default start(...)
        # implementation. Subclassers are encouraged to use this possibility when they don't need much more elaborate
        # ways of running their client.
        #
        # The runner script can be created in two ways, both are well documented at client.prepareExecution(...).
        # This example below shows the most common use:
        #
        #   client.prepareExecution(self, execution, simpleCommandLine =
        #       "./yourClientBinary > {0}/log.log".format( self.getExecutionLogDir( execution ) ))
        #
        # This example is a bit more elaborate; the complexCommandLine is to be used if any but the last command
        # in the sequence takes significant time to run:
        #
        #   allParams = '{0} --logdir {1}'.format( self.extraParameters, self.getExecutionLogDir( execution ) )
        #   if self.protocolVersion:
        #       allParams += " --prot {0}".format(self.protocolVersion)
        #   if self.postFixParams:
        #       allParams += " {0}".format(self.postFixParams)
        #   if execution.isSeeder():
        #       client.prepareExecution(self, execution, simpleCommandLine =
        #           "./yourClientBinary --seed {0}".format( allParams ) )
        #   else:
        #       client.prepareExecution(self, execution, complexCommandLine =
        #           "./yourClientBinary --leech {0} && ./yourClientBinary --seed {0}".format( allParams ) )
        #
        # Be sure to take self.extraParameters and your own parameters into account when building the command line
        # for the runner script. Also don't forget to make sure logs end up where you want them.
        #
        # The following implementation assumes you won't be using the runner script and is hence highly discouraged.
        #
        # TODO: Prepare the execution/client specific part on the host; specifically subclassers are encouraged to
        # use either the simpleCommandLine or complexCommandLine named arguments to client.prepareExecution(...) to
        # have a runner script built that will be used by the default implementation of start(...).
        client.prepareExecution(self, execution)
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
        # The default implementation is very well usable is you have created a runner script in
        # prepareExecution(...). If not, this is where you should run your client. A small example that assumes a lot
        # of preparation has been done elsewhere (which is not done in the examples above):
        #
        #   try:
        #       self.pid__lock.acquire()
        #       if self.isInCleanup():
        #           self.pid__lock.release()
        #           return
        #       if execution.getNumber() in self.pids:
        #           self.pid__lock.release()
        #           raise Exception( "Don't run twice!" )
        #       resp = execution.host.sendCommand(
        #           'cd "{0}"; ./yourClientBinary --pidFile "{1}/pidFile" &; cat "{1}/pidFile"'.format(
        #               self.getClientDir( execution.host ), self.getExecutionClientDir( execution ) ) )
        #       m = re.match( "^([0-9][0-9]*)", resp )
        #       if not m:
        #           raise Exception( "Failure to start... or get PID, anyway." )
        #       self.pids[execution.getNumber()] = m.group( 1 )
        #   finally:
        #       try:
        #           self.pid__lock.release()
        #       except RuntimeError:
        #           pass
        #
        # As you can see the start(...) method quite quickly becomes quite elaborate with quite some possibilities
        # for errors. That is why all of the above is highly discouraged: please use the simpleCommandLine or
        # complexCommandLine named parameters to client.prepareExecution(...) in your implementation of
        # prepareExecution(...) above and just use the following implementation:
        client.start(self, execution)
        #
        # TODO: If you really, really must: override this implementation. Your risk.
        #

    # TODO: If you really need a different detection whether your client is running, override isRunning(...)

    # TODO: If you can kill your client more effectively than sending a signal, override kill(...)

    def retrieveLogs(self, execution, localLogDestination):
        """
        Retrieve client specific logs for the given execution.
        
        The logs are to be stored in the directory pointed to by localLogDestination.
        
        @param  execution               The execution for which to retrieve logs.
        @param  localLogDestination     A string that is the path to a local directory in which the logs are to be stored.
        """
        # TODO: Implement this in order to get your logs out. Example:
        #
        #   execution.host.getFile( '{0}/log.log'.format( self.getExecutionLogDir( execution ) ),
        #       '{0}/log.log'.format( localLogDestination ), reuseConnection = execution.getRunnerConnection() )
        #
        # The use of the execution.getRunnerConnection() connection prevents errors with multi-threading.
        pass

    def cleanupHost(self, host, reuseConnection = None):
        """
        Client specific cleanup for a host, irrespective of execution.

        Should also remove the client from the host as far as it wasn't already there.

        @param  host            The host on which to clean up the client.
        @param  reuseConnection If not None, force the use of this connection for command to the host.
        """
        # Just calling the default implementation is usually enough, here. Be sure to be symmetrical with
        # prepareHost(...).
        #
        # TODO: Add any cleanup on the host you might need.
        #
        client.cleanupHost(self, host, reuseConnection)

    def cleanup(self):
        """
        Client specific cleanup, irrespective of host or execution.

        The default calls any required cleanup on the sources.
        """
        #
        # TODO: Implement this if needed, be symmetrical with prepare(...)
        #
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
        #
        # TODO: Reimplement this if possible.
        #
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
        #
        # TODO: Reimplement this if possible
        #
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
        #
        # TODO: Reimplement this if possible
        #
        return client.trafficOutboundPorts(self)

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version
        return "2.0.0"

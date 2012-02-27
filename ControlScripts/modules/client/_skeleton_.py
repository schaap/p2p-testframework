# These imports are needed to access the parsing functions (which you're likely to use in parameter parsing),
# the Campaign data object and the client parent class.
from core.parsing import *
from core.campaign import Campaign
from core.client import client

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/client/rudeClient.py then the name of your class would be rudeClient.

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for client object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

# TODO: Change the name of the class. See the remark above about the names of the module and the class. Example:
#
#   class rudeClient(client):
class _skeleton_(client):
    """
    A skeleton implementation of a client subclass.

    Please use this file as a basis for your subclasses but DO NOT actually instantiate it.
    It will fail.

    Look at the TODO in this file to know where you come in.
    """
    # TODO: Update the description above. Example:
    #
    #   """
    #   Client object for rudeClient programs.
    #
    #   Extra parameters:
    #   - postFixParams     Extra parameters to be placed at the end of the command line. At most protocolVersion characters long.
    #   - protocolVersion   A non-zero positive integer indicating the ProtRude version.
    #   """

    # The parent class handles most of the interactions between source, isRemote, location and builder; where needed
    # the comments in this skeleton implementation will guide you enough for a simple implementation. If you plan on
    # building more complex implementations that override part of the parent functionality, please make sure to read
    # the comments in the parent class very carefully.

    # TODO: For almost all the methods in this class it goes that, whenever you're about to do something that takes
    # significant time or that will introduce something that would need to be cleaned up, check self.isInCleanup()
    # and bail out if that returns True.

    def __init__(self, scenario):
        """
        Initialization of a generic client object.

        @param  scenario        The ScenarioRunner object this client object is part of.
        """
        client.__init__(self, scenario)
        # TODO: Your initialization, if any (not likely). Oh, and remove the next line.
        raise Exception( "DO NOT instantiate the skeleton implementation" )

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
        # TODO: Parse your settings. Example:
        #
        #   if key == 'postFixParams':
        #       if self.postFixParams:
        #           parseError( 'Seriously. How many parameters do you need? Go clean up your stuff!' )
        #       self.postFixParams = value
        #   elif key == 'protocolVersion':
        #       if not isPositiveInt( value, False ):
        #           parseError( 'Can you even count? Because {0} is definitely not a valid protocol number.'.format( value ) )
        #       self.protocolVersion = value
        #   else:
        #       client.parseSetting( self, key, value )
        #
        # Do not forget that last case!
        #
        # The following implementation assumes you have no parameters specific to your client:
        client.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        client.checkSettings(self)
        # TODO: Check your settings. Example:
        #
        #   if self.postFixParams and len(self.postFixParams) > self.protocolVersion:
        #       raise Exception( "You really don't know how this client works, do you? ... Do I, actually?" )

    def prepare(self):
        """
        Generic preparations for the client, irrespective of executions or hosts.
        """
        # The default implementation takes care of local compilation of the client, if needed. Be sure to call it.
        client.prepare(self)
        # TODO: Add any additional preparations if needed. You're not likely to need those, though.

    def prepareHost(self, host):
        """
        Client specific preparations on a host, irrespective of execution.

        This usually includes send files to the host, such as binaries.

        Note that the sendToHost and sendToSeedingHost methods of the file objects have not been called, yet.
        This means that any data files are not available.

        @param  host            The host on which to prepare the client.
        """
        # The default implementations takes care of creating client specific directories on the host, as well as
        # compilation of the client on the host, if needed. It also uploads or moves your client if you have
        # implemted getBinaryLayout(), getSourceLayout() and getExtraUploadLayout(). Be sure to call it.
        client.prepareHost(self, host)
        # The client specific directories on the remote host can be found using self.getClientDir(...) and
        # self.getLogsDir(...)
        #
        # TODO: If you really need to go beyond the possibilities of getBinaryLayout(), getSourceLayout() and
        # getExtraUploadLayout(), then this is the location to do that. Make sure to take every case into account!
        #

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

    def getBinaryLayout(self):
        """
        Return a list of binaries that need to be present on the server.
        
        Add directories to be created as well, have them end with a /.
        
        Return None to handle the uploading or moving yourself.
        
        @return    List of binaries.
        """
        #
        # TODO: Implement this for your convenience. Example:
        #
        #    return ['yourClientBinary']
        #
        # For more extensive clients:
        #
        #    return ['executableFile', 'data/', 'data/peerlist', 'data/translationfile']
        return None
    
    def getSourceLayout(self):
        """
        Return a list of tuples that describe the layout of the source.
        
        Each tuple in the list corresponds to (sourcelocation, binarylocation),
        where the binarylocation is one of the entries returned by getBinaryLayout().
        
        Each entry in getBinaryLayout() that is not directory needs to be present.
        
        Return None to handle the uploading or moving yourself.
        
        @return    The layout of the source.
        """
        #
        # TODO: Implement this for your convenience. Example:
        #
        #    return [('src/yourClientBinary', 'yourClientBinary')]
        #
        # For more extensive clients:
        #
        #    return [('src/executableFile', 'executableFile'),
        #            ('peerlists/alllists/most_recent', 'data/peerlist'),
        #            ('po/english.po', 'data/translationfile')]
        #
        # Note that for each entry in getBinaryLayout that is not a directory, exactly one entry must be present in getSourceLayout.
        # Also note that each entry in getSourceLayout corresponds to exactly one entry in getBinaryLayout.
        # This means, in particular, that if self.getBinaryLayout() == None then also self.getSourceLayout() == None.
        #
        # If your sources compile nicely in-place, be sure to fill this in, anyway. Something like:
        #
        #    return [('yourClientBinary', 'yourClientBinary')]
        #
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
        #
        # TODO: Implement this for your convenience. Example:
        #
        #    return [(os.path.join(Campaign.testEnvDir, 'ClientWrappers', 'yourclient', 'yourclient_runner'), 'yourclient_runner')]
        #
        # This example would have ClientWrappers/yourclient/yourclient_runner uploaded to '{0}/yourclient_runner'.format( self.getClientDir( host ) ).
        return None

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version
        return "2.0.0"

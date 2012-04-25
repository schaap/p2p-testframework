from core.parsing import isPositiveInt
from core.campaign import Campaign
from core.client import client

import os

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for client object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class http(client):
    """
    lighttpd / aria2 implementation for the client.
    
    Note that you probably wish to use this client with precompiled binaries on the hosts, especially
    since the binaries come from 2 different programs.
    
    Due to the dual client setup the params parameter is ignored.
    
    Extra parameters:
    - useSSL :      Set to anything but "no" to enable HTTPS instead of HTTP; may be specified multiple
                    times, last declaration counts; optional, defaults to "no"
    - port :        Use the specified port for server instances (positive integer < 65536; default 3000)
    
    When using SSL it is important to note that lighttpd then needs to be compiled with --with-openssl,
    which is not default. Also, the openssl utility must be available on the target seeding machines, or
    the server will fail to start.
    """

    useSSL = False          # Whether we use SSL
    port = None             # The port to use for servers

    # @static
    sourcelocations_lighttpd = [
                              ['src','lighttpd'],
                              ['src','mod_status.la'],
                              ['src','.libs','mod_status.so'],
                              ['src','mod_indexfile.la'],
                              ['src','.libs','mod_indexfile.so'],
                              ['src','mod_dirlisting.la'],
                              ['src','.libs','mod_dirlisting.so'],
                              ['src','mod_staticfile.la'],
                              ['src','.libs','mod_staticfile.so'],
                             ]
    # @static
    binarylocations_lighttpd = [
                              ['bin','lighttpd'],
                              ['lib','mod_status.la'],
                              ['lib','mod_status.so'],
                              ['lib','mod_indexfile.la'],
                              ['lib','mod_indexfile.so'],
                              ['lib','mod_dirlisting.la'],
                              ['lib','mod_dirlisting.so'],
                              ['lib','mod_staticfile.la'],
                              ['lib','mod_staticfile.so'],
                             ]
    # @static
    sourcelocations_aria = [
                              ['src','aria2c'],
                             ]
    # @static
    binarylocations_aria = [
                              ['bin','aria2c'],
                             ]
        
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
        if key == 'useSSL':
            self.useSSL = (value != "no")
        elif key == 'port':
            if self.port:
                parseError( "Port already set: {0}".format( self.port ) )
            if not isPositiveInt( value, True ) or int(value) > 65535:
                parseError( "Port should be a non-zero integer < 65536" )
            self.port = int(value)
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
            self.port = 3000
        elif self.port < 1024:
            Campaign.logger.log( "Using a privileged port for host {0} is not recommended: {1}.".format( self.name, self.port ) )

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

        if self.isInCleanup():
            return
        
        # Make sure client is uploaded/present
        if self.isRemote:
            entries = []
            res = host.sendCommand( '[ -d "{0}"/lighttpd-*/src -a -f "{0}"/lighttpd-*/src/lighttpd ] && echo "E" || echo "N"'.format( self.sourceObj.remoteLocation( self, host ) ) )
            if res.splitlines()[-1] == 'E':
                # Remote source location of lighttpd with in-place build
                entries += ['/'.join(['lighttpd-*']+f) for f in http.sourcelocations_lighttpd]
            else:
                # Remote binary installation of lighttpd
                entries += ['/'.join(f) for f in http.binarylocations_lighttpd]
            res = host.sendCommand( '[ -d "{0}"/aria2-*/src -a -f "{0}"/aria2-*/src/aria2c ] && echo "E" || echo "N"'.format( self.sourceObj.remoteLocation( self, host ) ) )
            if res.splitlines()[-1] == 'E':
                # Remote source location of aria2 with in-place build
                entries += ['/'.join(['aria2-*']+f) for f in http.sourcelocations_aria]
            else:
                # Remote binary installation of aria2
                entries += ['/'.join(f) for f in http.binarylocations_aria]
            for entry in entries:
                if self.isInCleanup():
                    return
                res = host.sendCommand( '[ -f "{0}"/{1} ] && cp "{0}"/{1} "{2}/" && echo "OK"'.format( self.sourceObj.remoteLocation( self, host ), entry, self.getClientDir(host) ) )
                if res != "OK":
                    raise Exception( "Client {0} failed to prepare host {1}: checking for existence of file {2} after building and copying it failed. Response: {4}.".format( self.name, host.name, entry, res ) )
        else:
            entries = []
            dirs = [d for d in os.listdir(self.sourceObj.localLocation( self )) if d[:9] == 'lighttpd-']
            if len(dirs) > 0 and os.path.isfile( os.path.join( self.sourceObj.localLocation( self ), dirs[0], 'src', 'lighttpd' ) ):
                # Local source location of lighttpd with in-place build
                entries += [[dirs[0]] + f for f in http.sourcelocations_lighttpd]
            else:
                # Local binary installation of lighttpd
                entries += [f for f in http.binarylocations_lighttpd]
            dirs = [d for d in os.listdir(self.sourceObj.localLocation( self )) if d[:6] == 'aria2-']
            if len(dirs) > 0 and os.path.isfile( os.path.join( self.sourceObj.localLocation( self ), dirs[0], 'src', 'aria2c' ) ):
                # Local source location of aria2 with in-place build
                entries += [[dirs[0]] + f for f in http.sourcelocations_aria]
            else:
                # Local binary installation of aria2
                entries += [f for f in http.binarylocations_lighttpd]
            for entry in entries:
                # pylint: disable-msg=W0142
                f = os.path.join( self.sourceObj.localLocation( self ), *entry )
                # pylint: enable-msg=W0142
                if not os.path.isfile( f ):
                    raise Exception( "Client {0} failed to prepare host {1}: local file {2} is missing".format( self.name, host.name, f ) )
                host.sendFile( f, '{0}/{1}'.format( self.getClientDir(host), entry[-1] ), True )
        f = os.path.join( Campaign.testEnvDir, 'ClientWrappers', 'lighttpd', 'lighttpd_logging' )
        if not os.path.isfile( f ):
            raise Exception( "Client {0} failed to prepare host {1} since the client wrapper for lighttpd seems to be missing: {2} not found.".format( self.name, host.name, f ) )
        host.sendFile( f, '{0}/lighttpd_logging'.format( self.getClientDir(host) ) )

    # That's right, 2 arguments less.
    # pylint: disable-msg=W0221
    def prepareExecution(self, execution):
        """
        Client specific preparations for a specific execution.

        If any scripts for running the client on the host are needed, this is the place to build them.
        Be sure to take self.extraParameters into account, in that case.

        @param  execution           The execution to prepare this client for.
        """
        if execution.isSeeder():
            if len([f for f in execution.host.seedingFiles if f.getDataDir() is not None]) < 1:
                Campaign.logger.log( 'WARNING! Client {0} is being prepared in seeding mode for execution {1} which has no seeding files associated. The execution will be a noop.' )
                command = 'echo "Not running: no files" > "{0}/log.log"; sleep 5'.format( self.getExecutionLogDir(execution) )
            else:
                ssl = "NOSSL"
                if self.useSSL:
                    ssl = "SSL"
                command = '"{0}/lighttpd_logging" "{1}" {2} {3} {4} > "{5}/log.log"'.format(
                                                                                            self.getClientDir(execution.host),
                                                                                            self.getExecutionClientDir(execution),
                                                                                            self.port,
                                                                                            ssl,
                                                                                            " ".join(['"'+d+'"' for d in execution.getDataDirList()]),
                                                                                            self.getExecutionLogDir(execution)
                                                                                            )
            client.prepareExecution(self, execution, simpleCommandLine=command)
        else:
            if len(execution.files) < 1:
                Campaign.logger.log( 'WARNING! Client {0} is being prepared for execution {1} which has no files associated. The execution will be a noop.' )
                client.prepareExecution(self, execution, simpleCommandLine='echo "Not running: no files" > "{0}/log.log"; sleep 5'.format( self.getExecutionLogDir(execution)))
                return
            # Figure out all the servers (yes, HTTP cheats by knowing all the servers ahead)
            servers = []
            for e in [e for e in self.scenario.getObjects('execution') if e.isSeeder()]:
                if e.host.getAddress() == '':
                    raise Exception( 'client:http requires each seeding host to return a valid address in their getAddress() method, but host {0} return ""'.format( e.host.name ) )
                p = self.port
                if isinstance(e.client, http):
                    p = e.client.port
                    if e.client.useSSL:
                        servers.append( 'https://{0}:{1}/'.format( e.host.getAddress(), p ) )
                    else:
                        servers.append( 'http://{0}:{1}/'.format( e.host.getAddress(), p ) )
                else:
                    if self.useSSL:
                        servers.append( 'https://{0}:{1}/'.format( e.host.getAddress(), p ) )
                    else:
                        servers.append( 'http://{0}:{1}/'.format( e.host.getAddress(), p ) )
            if len(servers) == 0:
                raise Exception( 'Client {0} could not find a single seeding execution in the scenario. This is not supported by client:http.'.format( self.name ) )
            # Build a URI list:
            # Each file should have its own line, each line should have multiple URIs for that file separated by \t
            URIlist = ''
            for file_ in execution.files:
                f = os.path.basename(file_.getFile(execution.host))
                URIlist += "\t".join( ["{0}/{1}".format( s, f ) for s in servers] ) + "\n"
            # Calculate other settings
            connperhost = len(servers) * 2
            if connperhost > 16:
                connperhost = 16
            # Build the huge command
            command = (
                        'sleep 30; '
                        'echo | ./aria2c '
                        '-j {0} '                               # maximum concurrent downloads
                        '-s {0} '                               # split file in n parts
                        '-x {1} '                               # allow at most #seeders connection to each host (necessary for multiple servers on the same host, max 16!)
                        '--uri-selector=inorder '               # forces aria to choose the next URI whenver trying to download another piece
                        '--human-readable=false '               # full output
                        '--summary-interval=1 '                 # give output every 1 sec
                        '--no-conf=true '                       # don't read global conf
                        '--truncate-console-readout=false '     # don't truncate output
                        '-n '                                   # don't read global .netrc conf
                        '--max-tries=0 '                        # don't give up
                        '--retry-wait=1 '                       # wait 1 sec between retries
                        '--dir={2} '                            # save here
                        '--check-certificate=false '            # don't check our on-the-fly-generated self-signed certificates [SSL]
                        '--input-file=- '                       # read URI lists from stdin
                        '> {3}/log.log '                        # redirect log
                        '<<__EOF__\n'                           # start input of URI lists
                        '{4}'                                   # URI lists
                        '__EOF__\n'                             # end input of URI lists
                        # (SSL options are given anyway, since they don't matter for non-SSL)
                        # The sleep 30 is a hack to work around slower setup of lighttpd which would cause aria2 to fail when connecting to the server
                    ).format(
                             len(servers),
                             connperhost,
                             self.getExecutionClientDir(execution),
                             self.getExecutionLogDir(execution),
                             URIlist
                            )
            client.prepareExecution(self, execution, complexCommandLine=command)
    # pylint: enable-msg=W0221

    def retrieveLogs(self, execution, localLogDestination):
        """
        Retrieve client specific logs for the given execution.
        
        The logs are to be stored in the directory pointed to by localLogDestination.
        
        @param  execution               The execution for which to retrieve logs.
        @param  localLogDestination     A string that is the path to a local directory in which the logs are to be stored.
        """
        if self.getExecutionLogDir(execution):
            execution.host.getFile( '{0}/log.log'.format( self.getExecutionLogDir( execution ) ), os.path.join( localLogDestination, 'log.log' ), reuseConnection = execution.getRunnerConnection() )
        client.retrieveLogs(self, execution, localLogDestination)

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
        return 'TCP'

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
        return [self.port]

    def loadDefaultParsers(self, execution):
        """
        Loads the default parsers for the given execution.

        The order in which parsers are determined is this (first hit goes):
        - The parsers given in the execution object
        - The parsers given in the client object
        - The parser object with the same name as the client
        - The parser with the same name as the client
        The second, third and fourth are to be loaded by this method.
        
        @param  execution       The execution for which to load a parser.

        @return The list of parser instances.
        """
        if self.parsers:
            return self.loadDefaultParsers(execution)
        else:
            if execution.isSeeder():
                parserType = 'lighttpd'
            else:
                parserType = 'aria2'
            if parserType in self.scenario.getObjectsDict( 'parser' ):
                return [self.scenario.getObjectsDict( 'parser' )[parserType]]
            else:
                modclass = Campaign.loadModule( 'parser', parserType )
                # *Sigh*. PyLint. Dynamic loading!
                # pylint: disable-msg=E1121
                obj = modclass( self.scenario )
                # pylint: enable-msg=E1121
                obj.checkSettings()
                return [obj]

    @staticmethod
    def APIVersion():
        return "2.2.0"

# These imports are needed to access the parsing functions (which you're likely to use in parameter parsing),
# the Campaign data object and the host parent class.
from core.parsing import *
from core.campaign import Campaign
from core.host import host, countedConnectionObject

import threading
import errno
import stat
import subprocess
import os

# ==== Paramiko is used for the SSH connections ====
paramiko = None
try:
    paramiko = __import__('paramiko', globals(), locals() )
except ImportError:
    raise Exception( "The host:das4 module requires the paramiko package to be available. Please make sure it's available." )
# ==== /Paramiko ====

# ==== parseError parsing helper function ====
def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for host object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )
# ==== /parseError ====

# ==== getIPAddresses() generator function, returns IP adresses of this host ====
# Below several implementations are tested for availability and the best is chosen
have_windll = False
have_ifconfig = None
try:
    __import__('ctypes', globals(), locals(), ['windll', 'Structure', 'sizeof', 'POINTER', 'byref', 'c_ulong', 'c_uint', 'c_ubyte', 'c_char'])
    have_windll = True
except ImportError:
    if os.path.exists( '/sbin/ifconfig' ):
        have_ifconfig = '/sbin/ifconfig'
    elif os.path.exists( '/usr/sbin/ifconfig' ):
        have_ifconfig = '/usr/sbin/ifconfig'
    else:
        out, _ = subprocess.Popen( 'which ifconfig', stdout = subprocess.PIPE, shell = True ).communicate()
        if out is None or out == '' or not os.path.exists( 'out' ):
            Campaign.logger.log( "Warning: host:das4 may need to try and find the network you're in. You don't seem to be on windows and ifconfig can't be found either; falling back to contacting gmail.com to get a local IP. Please specify your headNode to prevent problems from this." )
        else:
            have_ifconfig = out

if have_windll:
    # Windows based method using windll magic
    # Thanks for this method goes to DzinX in http://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
    def getIPAddresses():
        from ctypes import Structure, windll, sizeof
        from ctypes import POINTER, byref
        from ctypes import c_ulong, c_uint, c_ubyte, c_char
        MAX_ADAPTER_DESCRIPTION_LENGTH = 128
        MAX_ADAPTER_NAME_LENGTH = 256
        MAX_ADAPTER_ADDRESS_LENGTH = 8
        class IP_ADDR_STRING(Structure):
            pass
        LP_IP_ADDR_STRING = POINTER(IP_ADDR_STRING)
        IP_ADDR_STRING._fields_ = [
            ("next", LP_IP_ADDR_STRING),
            ("ipAddress", c_char * 16),
            ("ipMask", c_char * 16),
            ("context", c_ulong)]
        class IP_ADAPTER_INFO (Structure):
            pass
        LP_IP_ADAPTER_INFO = POINTER(IP_ADAPTER_INFO)
        IP_ADAPTER_INFO._fields_ = [
            ("next", LP_IP_ADAPTER_INFO),
            ("comboIndex", c_ulong),
            ("adapterName", c_char * (MAX_ADAPTER_NAME_LENGTH + 4)),
            ("description", c_char * (MAX_ADAPTER_DESCRIPTION_LENGTH + 4)),
            ("addressLength", c_uint),
            ("address", c_ubyte * MAX_ADAPTER_ADDRESS_LENGTH),
            ("index", c_ulong),
            ("type", c_uint),
            ("dhcpEnabled", c_uint),
            ("currentIpAddress", LP_IP_ADDR_STRING),
            ("ipAddressList", IP_ADDR_STRING),
            ("gatewayList", IP_ADDR_STRING),
            ("dhcpServer", IP_ADDR_STRING),
            ("haveWins", c_uint),
            ("primaryWinsServer", IP_ADDR_STRING),
            ("secondaryWinsServer", IP_ADDR_STRING),
            ("leaseObtained", c_ulong),
            ("leaseExpires", c_ulong)]
        GetAdaptersInfo = windll.iphlpapi.GetAdaptersInfo
        GetAdaptersInfo.restype = c_ulong
        GetAdaptersInfo.argtypes = [LP_IP_ADAPTER_INFO, POINTER(c_ulong)]
        adapterList = (IP_ADAPTER_INFO * 10)()
        buflen = c_ulong(sizeof(adapterList))
        rc = GetAdaptersInfo(byref(adapterList[0]), byref(buflen))
        if rc == 0:
            for a in adapterList:
                adNode = a.ipAddressList
                while True:
                    # Added per comment on the original code. Not tested:
                    if not hasattr(adNode, 'ipAddress'):
                        adNode = adNode.content
                    # /Added
                    ipAddr = adNode.ipAddress
                    # Added check for 127.0.0.1
                    if ipAddr and ipAddr != '127.0.0.1':
                        yield ipAddr
                    adNode = adNode.next
                    if not adNode:
                        break
elif have_ifconfig:
    # *nix based method based on reading the output of ifconfig
    def getIPAddresses():
        import re
        co = subprocess.Popen([have_ifconfig], stdout = subprocess.PIPE)
        ifconfig = co.stdout.read()
        del co
        ip_regex = re.compile('((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-4]|2[0-5][0-9]|[01]?[0-9][0-9]?)).*')
        ips = [match[0] for match in ip_regex.findall(ifconfig, re.MULTILINE) if not match[0] == '127.0.0.1']
        for ip in ips:
            yield ip
else:
    # Unreliable platform-independent method (requires the ability to connect to gmail.com:80)
    def getIPAddresses():
        import socket
        s = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        s.connect( ( 'gmail.com', 80 ) )
        ip = s.getsockname()[0]
        s.close()
        yield ip
# ==== /getIPAddresses() ====     

# ==== getHostnameByIP(ip) Returns the hostname of the given IP ====
def getHostnameByIP(ip):
    import socket
    socket.setdefaulttimeout(10)
    return socket.gethostbyaddr("69.59.196.211")[0]
# ==== /getHostnameByIP(ip)  
   
class das4ConnectionObject(countedConnectionObject):
    """
    SSH connection object for paramiko connections
    
    This connection object is copied here from host:ssh.
    """
    
    client = None
    interactiveChannel = None
    io = None
    
    sftpChannel = None
    sftp__lock = None
    
    def __init__(self, client, interactiveChannel, io ):
        countedConnectionObject.__init__(self)
        self.client = client
        self.interactiveChannel = interactiveChannel
        self.sftp__lock = threading.Lock()
        self.io = io
    
    def close(self):
        countedConnectionObject.close(self)
        try:
            self.sftp__lock.acquire()
            if self.sftpChannel:
                self.sftpChannel.close()
                del self.sftpChannel
                self.sftpChannel = None
        finally:
            self.sftp__lock.release()
            try:
                self.interactiveChannel.shutdown( 2 )
                self.interactiveChannel.close()
                del self.interactiveChannel
                self.interactiveChannel = None
            except Exception:
                self.client.close()
                del self.client
                self.client = None
    
    def write(self, msg):
        print "DEBUG: CONN {0} SEND:\n{1}".format( self.getIdentification(), msg )
        self.io[0].write( msg )
        self.io[0].flush()
    
    def readline(self):
        line = self.io[1].readline()
        print "DEBUG: CONN {0} READLINE:\n{1}".format( self.getIdentification(), line )
        return line
    
    def createSFTPChannel(self):
        if self.isClosed():
            raise Exception( "Can't create an SFTP channel for a closed SSH connection on connection {0}".format( self.getIdentification( ) ) )
        try:
            self.sftp__lock.acquire()
            if self.sftpChannel:
                return True
            self.sftpChannel = self.client.open_sftp()
        finally:
            self.sftp__lock.release()
        return False
    
    def removeSFTPChannel(self):
        if self.isClosed():
            return
        try:
            self.sftp__lock.acquire()
            if not self.sftpChannel:
                return
            self.sftpChannel.close()
            del self.sftpChannel
            self.sftpChannel = None
        finally:
            self.sftp__lock.release()
    
    @staticmethod
    def existsRemote(sftp, remotePath):
        found = True
        try:
            sftp.stat( remotePath )
        except IOError as e:
            found = False
            if not e.errno == errno.ENOENT:
                raise e
        return found

    @staticmethod
    def isRemoteDir(sftp, remotePath):
        attribs = sftp.stat(remotePath)
        return stat.S_ISDIR( attribs.st_mode )

class das4(host):
    """
    DAS4 host implementation.
    
    Extra parameters:
    - headnode              The hostname of the DAS4 host to SSH to initially. Optional, if left out the module
                            will try and determine which network you're on and use the local entry node. If
                            you're not on one of the networks of the institutes hosting DAS4 this will give an
                            error.
                            
                            The automated lookup test uses dig -x for a reverse lookup on any inet address found
                            in ifconfig, except 127.0.0.1, and tries to see if it matches any of the following
                            networks:
                                network        headnode
                                -------        --------
                                .vu.nl         fs0.das4.vu.nl
                                .liacs.nl      fs1.das4.liacs.nl
                                .uva.nl        fs4.das4.science.uva.nl
                                .tudelft.nl    fs3.das4.tudelft.nl
                                .astron.nl     fs5.das4.astron.nl
                            Note that fs2.das4.science.uva.nl won't be used automatically.
                            
                            The above table also holds all valid values for this parameter, unless the
                            headNodeOverride parameters is set.
    - nNodes                The number of nodes to request, a positive integer. Optional, defaults to 2.
    - reserveTime           A positive number of seconds to reserve the nodes; note that you should take into 
                            account that the nodes need to be reserved during setup, so some setup steps can
                            still occur between reservation and the actual running of the test scenarios. It
                            is recommended to reserve the nodes for a few minutes more than the maximum
                            execution time of the scenario. Optional, defaults to 900.
    - user                  The username to use for logging in on the DAS4 system. Required.
    - headnodeOverride      Set to anything but "" to override the validity checks on the headNode parameter.
                            Use this for custom headNodes or to bypass DNS lookups by providing the IP of the
                            headnode. Optional.
    
    Requirements of the DAS4 module:
    - You must be able to use SSH from the specified (or selected) headnode to the other nodes without interaction
        (i.e. passwordless)
    - It is HIGHLY RECOMMENDED to place SGE_KEEP_TMPFILES="no" in ~/.bashrc on your headnode: the test framework
        will try and cleanup nicely,  but will first and foremost honor the reservation system. This means that if
        an execution takes too long with regard to the reservation time, for example due to a longer setup than
        anticipated, the reserved nodes can't be cleaned by the test framework. Specifically files in /local will
        not be removed in that case. Setting SGE_KEEP_TMPFILES="no" prevents this.
    
    It is important to understand that while the DAS4 is well equipped to commandeer your nodes in parallel, this
    module will actually split itself into one host per node. This means that, after setup, you will end up with
    each node as a separate host and they will hence be used as single hosts.
    
    Traffic control on the DAS4 is currently not supported. If you try and use it, anyway, results are
    unpredictable. Most likely it will break the moment any DAS4 node needs to fall back to full IP-range based
    traffic control; thereby also breaking it for other users. For your convenience and experimentation no
    warnings or errors will pop up if you try, though.  
    """
    # TODO: Update description for automated lookup test method

    # TODO: For almost all the methods in this class it goes that, whenever you're about to do something that takes
    # significant time or that will introduce something that would need to be cleaned up, check self.isInCleanup()
    # and bail out if that returns True.
    
    headNode = None             # Address of the headNode to use
    nNodes = None               # Number of nodes to reserve
    reserveTime = None          # Number of seconds to reserve the nodes
    user = None                 # Username to use as login name on the DAS4
    headNode_override = False   # Set to True to disable headNode validity checks

    def __init__(self, scenario):
        """
        Initialization of a generic host object.
        
        @param  scenario        The ScenarioRunner object this host object is part of.
        """
        host.__init__(self, scenario)

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
        if key == 'headNode' or key == 'headnode':
            if key == 'headNode':
                Campaign.logger.log( "headNode is a strange camelcase. It has been deprecated in favor of headnode.")
            if self.headNode:
                parseError( "headNode already set: {0}".format( self.headNode ) )
            self.headNode = value
        elif key == 'headNodeOverride' or key == 'headnodeOverride':
            if key == 'headNodeOverride':
                Campaign.logger.log( "headNodeOverride is a strange camelcase. It has been deprecated in favor of headnodeOverride.")
            if value != '':
                self.headNode_override = True
        elif key == 'nNodes':
            if self.nNodes:
                parseError( "Number of nodes already set: {0}".format( self.nNodes ) )
            if not isPositiveInt( value, True ):
                parseError( "Number of nodes should be a positive, non-zero integer" )
            self.nNodes = int(value)
        elif key == 'reserveTime':
            if self.reserveTime:
                parseError( "Reserve time already set: {0}".format( self.reserveTime ) )
            if not isPositiveInt( value, True ):
                parseError( "Reserve time should be a positive, non-zero integer number of seconds" )
            self.reserveTime = int(value)
        elif key == 'user':
            if self.user:
                parseError( "User already set: {0}".format( self.user ) )
            self.user = value
        else:
            host.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        if self.name == '':
            if 'das4' in self.scenario.getObjectsDict( 'host' ):
                raise Exception( "Name not set for host object declared at line {0}, but the default name (das4) was already taken.".format( self.declarationLine ) )
            else:
                self.name = 'das4'
        host.checkSettings(self)
        if not self.user:
            raise Exception( "The user parameter is not optional for host {0}.".format( self.name ) )
        if not self.reserveTime:
            self.reserveTime = 900
        if not self.nNodes:
            self.nNodes = 2
        if not self.headNode_override and self.headNode:
            if self.headNode not in [ 'fs0.das4.vu.nl', 'fs1.das4.liacs.nl', 'fs4.das4.science.uva.nl', 'fs3.das4.tudelft.nl', 'fs5.das4.astron.nl', 'fs2.das4.science.uva.nl' ]:
                raise Exception( "The host {1} was given {0} as headnode, but that is not a headnode of DAS4. Please use fs0.das4.cs.vu.nl, fs1.das4.liacs.nl, fs2.das4.science.uva.nl, fs3.das4.tudelft.nl, fs4.das4.science.uva.nl or fs5.das4.astron.nl. Alternatively you can set headNodeOverride if you're sure the headNode you gave is correct.".format( self.headNode, self.name ) )
        if not self.headNode:
            for ip in getIPAddresses():
                hostname = getHostnameByIP(ip)
                if hostname[-6:] == '.vu.nl':
                    self.headNode = 'fs0.das4.vu.nl'
                elif hostname[-9:] == '.liacs.nl':
                    self.headNode = 'fs1.das4.liacs.nl'
                elif hostname[-7:] == '.uva.nl':
                    self.headNode = 'fs4.das4.science.uva.nl'
                elif hostname[-11:] == '.tudelft.nl':
                    self.headNode = 'fs3.das4.tudelft.nl'
                elif hostname[-10:] == '.astron.nl':
                    self.headNode = 'fs5.das4.astron.nl'
            if not self.headNode:
                raise Exception( "No headnode was specified for host {0} and this host was not detected to be in one of the hosting networks. Please specify a headnode.")

    def setupNewConnection(self):
        """
        Create a new connection to the host.

        The returned object has no specific type, but should be usable as a connection object either by uniquely identifying it or 
        simply by containing the needed information for it.

        Connections created using this function can be closed with closeConnection(...). When cleanup(...) is called all created
        connections will automatically closed and, hence, any calls using those connections will then fail.

        @return The connection object for a new connection. This should be an instance of a subclass of core.host.connectionObject.
        """
        # TODO: Implement this! Example:
        #
        #   FIXME: WRITE EXAMPLE
        #
        # Be sure to include the new connection in the self.connections list after acquiring self.connections__lock
        raise Exception( "Not implemented" )

    def closeConnection(self, connection):
        """
        Close a previously created connection to the host.

        Any calls afterwards to methods of this host with the close connection will fail.
        
        The default implementation will close the connection if it wasn't already closed
        and remove it from self.connections.

        @param  The connection to be closed.
        """
        # TODO: Actually close the connection. Then call host.closeConnection(connection). Example:
        #
        #    FIXME: WRITE EXAMPLE
        #
        # Always include the next call:
        host.closeConnection(self, connection)

    # TODO: If you really must you can override getConnection. This is needed in case your connection object
    # is not a subclass of core.host.connectionObject. There is no real need for that, though.

    def sendCommand(self, command, reuseConnection = True):
        """
        Sends a bash command to the remote host.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     True for commands that are shortlived or are expected not to be parallel with other commands.
                                    False to build a new connection for this command and use that.
                                    A specific connection object as obtained through setupNewConnection(...) to reuse that connection.

        @return The result from the command. The result is stripped of leading and trailing whitespace before being returned.
        """
        # TODO: Implement this! Example:
        #
        #   connection = None
        #   try:
        #       connection = self.getConnection( reuseConnection )
        #   FIXME: WRITE MORE EXAMPLE
        #   finally:
        #       self.releaseConnection( reuseConnection, connection )
        #
        raise Exception( "Not implemented" )

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
        # TODO: Implement this! Example:
        #
        #   FIXME: WRITE EXAMPLE
        #
        raise Exception( "Not implemented" )
    
    # TODO: If you have a more effective way of sending multiple files at once, override sendFiles as well.

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
        # TODO: Implement this! Example:
        #
        #   FIXME: WRITE EXAMPLE
        #
        raise Exception( "Not implemented" )

    def prepare(self):
        """
        Execute commands on the remote host needed for host specific preparation.

        The default implementation simply ensures the existence of a remote directory.
        """
        # TODO: Prepare anything you may need before being able to set up a connection, first.
        #
        # Then do this call, and definitely do this call unless you know what you're doing:
        host.prepare(self)
        # After that you can do any other less-important host-specific preparation
        #
        # Usually this one call will be enough if you just need to set up the connection.

    def cleanup(self, reuseConnection = None):
        """
        Executes commands to do host specific cleanup.
        
        The default implementation removes the remote temporary directory, if one was created.

        Subclassers are advised to first call this implementation and then proceed with their own steps.
        
        @param  reuseConnection If not None, force the use of this connection object for commands to the host.
        """
        # Be symmetrical with prepare(), clean up the less-important host-specific stuff here
        # Then do this call, and definitely do this call unless you know what you're doing:
        host.cleanup(self, reuseConnection)
        # TODO: Cleanup all of the host, be sure to check what has and what has not been done and needs cleanup.
        # Don't just assume you're at the end of everything. Example:
        #
        #   FIXME: WRITE EXAMPLE
        #

    # TODO: If you need a separate location to store data to ensure that data survives until the end of the test,
    # override getPersistentTestDir() and make sure to initialize correctly to have both the test dir and the
    # persistent test dir set up on the remote host

    def getSubNet(self):
        """
        Return the subnet of the external addresses of the host.

        @return The subnet of the host(s).
        """
        # TODO: Implement this! Example:
        #
        #   return self.hostname
        #
        raise Exception( "Not implemented" )

    def getAddress(self):
        """
        Return the single address (IP or hostname) of the remote host, if any.

        An obvious example of this method returning '' would be a host implementation that actually uses a number
        of remote hosts in one host object: one couldn't possibly return exactly one address for that and be
        correct about it in the process.

        Default implementation just returns ''.

        @return The address of the remote host, or '' if no such address can be given.
        """
        # TODO: Implement this, if possible. Example:
        #
        #   return self.hostname
        #
        return ''

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version.
        return "2.0.0"

# These imports are needed to access the parsing functions (which you're likely to use in parameter parsing),
# the Campaign data object and the host parent class.
from core.parsing import *
from core.campaign import Campaign
from core.host import host

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/host/rudeHost.py then the name of your class would be rudeHost.

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for host object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

# TODO: Change the name of the class. See the remark above about the names of the module and the class. Example:
#
#   class rudeHost(host):
class _skeleton_(host):
    """
    A skeleton implementation of a host subclass.

    Please use this file as a basis for your subclasses but DO NOT actually instantiate it.
    It will fail.

    Look at the TODO in this file to know where you come in.
    """
    # TODO: Update the description above. Example:
    #
    #   """
    #   A rudeHost host implementation.
    #
    #   Use with care to subdue rude hosts.
    #
    #   Extra parameters:
    #   - hostname  The hostname to connect to.
    #   - username  The username to use when connecting. Optional.
    #   """

    # TODO: For almost all the methods in this class it goes that, whenever you're about to do something that takes
    # significant time or that will introduce something that would need to be cleaned up, check self.isInCleanup()
    # and bail out if that returns True.

    def __init__(self, scenario):
        """
        Initialization of a generic host object.
        
        @param  scenario        The ScenarioRunner object this host object is part of.
        """
        host.__init__(self, scenario)
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
        #   if key == 'hostname':
        #       if self.hostname:
        #           parseError( 'Bollocks! You already gave me a hostname' )
        #       self.hostname = value
        #   elif key == 'username':
        #       if self.username:
        #           parseError( 'Need a shrink?' )
        #       self.username = value
        #   else:
        #       host.parseSetting(key, value)
        #
        # Be sure not to forget that last case!
        #
        # The following implementation assumes you have no parameters specific to your host type:
        host.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        host.checkSettings(self)
        # TODO: Check your settings. Example:
        #
        #   if not self.hostname:
        #       raise Exception( "You're very Zen. You don't need host. You won't need object." )
        #   if self.hostname == self.username:
        #       raise Exception( "You're either confused or incredibly vain. Not acceptable either way." )

    def setupNewConnection(self):
        """
        Create a new connection to the host.

        The returned object has no specific type, but should be usable as a connection object either by uniquely identifying it or 
        simply by containing the needed information for it.

        Connections created using this function can be closed with closeConnection(...). When cleanup(...) is called all created
        connections will automatically closed and, hence, any calls using those connections will then fail.

        @return The connection object for a new connection.
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

        @param  The connection to be closed.
        """
        # TODO: Implement this! Example:
        #
        #   FIXME: WRITE EXAMPLE
        #
        # Be sure to remove the connection from the self.connections list after acquiring self.connections__lock
        raise Exception( "Not implemented" )

    def sendCommand(self, command, reuseConnection = True):
        """
        Sends a bash command to the remote host.

        @param  command             The command to be executed on the remote host.
        @param  reuseConnection     True for commands that are shortlived or are expected not to be parallel with other commands.
                                    False to build a new connection for this command and use that.
                                    A specific connection object as obtained through setupNewConnection(...) to reuse that connection.

        @return The result from the command.
        """
        # TODO: Implement this! Example:
        #
        #   connection = None
        #   if not reuseConnection:
        #       connection = self.setupNewConnection()
        #   elif reuseConnection == True:
        #       self.connections__lock.acquire()
        #       connection = self.connections[0]
        #       self.connections__lock.release()
        #   else:
        #       connection = reuseConnection
        #   FIXME: WRITE MORE EXAMPLE
        #   if not reuseConnection:
        #       self.closeConnection( connection )
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

    def cleanup(self):
        """
        Executes commands to do host specific cleanup.
        
        The default implementation removes the remote temporary directory, if one was created.

        Subclassers are advised to first call this implementation and then proceed with their own steps.
        """
        # Be symmetrical with prepare(), clean up the less-important host-specific stuff here
        # Then do this call, and definitely do this call unless you know what you're doing:
        host.cleanup(self)
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

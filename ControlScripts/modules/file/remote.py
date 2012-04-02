# These imports are needed to access the parsing functions (which you're likely to use in parameter parsing),
# the Campaign data object and the file parent class.
from core.campaign import Campaign
import core.file

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for file object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class remote(core.file.file):
    """
    File implementation for remote files or directories.
    
    This file module is similar to file:local, except that it uses already available upload to prevent uploading it for
    every scenario. This can be a great boost in scenario speed when dealing with large files.

    Extra parameters:
    - path                  The path to the actual file or directory on the remote machine.
    - renameFile            Set this to "yes" to have the file renamed when uploaded to an automatically generated
                            name. Not valid if path points to a directory.
    """

    path = None                 # The path of the local file or directory
    renameFile = False          # True iff the single file is to be renamed after uploading

    def __init__(self, scenario):
        """
        Initialization of a generic file object.

        @param  scenario        The ScenarioRunner object this client object is part of.
        """
        core.file.file.__init__(self, scenario)

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
        if key == 'path':
            if self.path:
                parseError( "A file or directory was already given" )
            self.path = value
        elif key == 'renameFile':
            if value == 'yes':
                self.renameFile = True
        else:
            core.file.file.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        core.file.file.checkSettings(self)

        if not self.path:
            raise Exception( "file:local {0} must have a local path specified".format( self.name ) )

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        core.file.file.resolveNames(self)

    def sendToHost(self, host):
        """
        Send any required file to the host.

        This function will be called for each host.

        The default implementation uploads the metafile to the remote host, if one was given.
        Use self.getMetaFile(...) to get the path to the meta file on the remote host.

        By default the meta file will be renamed to meta_file.postfix where postfix is replaced by the postfix of the original file name.
        E.g. a metaFile parameter "video.large.torrent" will result in a file on the remote host named "meta_file.torrent".

        The default implementation uses self.getMetaFile(...) to get the path of the meta file on the remote host, so if you just wish to
        change the name overriding that method is enough.

        @param  host        The host to which to send the files.
        """
        core.file.file.sendToHost(self, host)
        if not self.getFileDir(host):
            return
        host.sendCommand( 'mkdir -p "{0}/files/"'.format( self.getFileDir(host) ) )

    def sendToSeedingHost(self, host):
        """
        Send any files required for seeding hosts.
        
        This function will be called for each host on which seeding of the file is needed.

        Note that self.sendToHost(...) will also be called before this function is called.

        The default implementation does nothing.

        @param  host        The host to which to send the files.
        """
        if not self.getFileDir(host):
            return
        core.file.file.sendToSeedingHost(self, host)
        res = host.sendCommand( '[ -d "{0}" ] && echo "D" || echo "F"'.format( self.path ) )
        isdir = res.splitlines()[-1] 
        if isdir == "D":
            if self.renameFile:
                raise Exception( "The renameFile parameter to file:remote is not allowed for directories and {0} seems to be a directory on host {1}.".format( self.path, host.name ) )
            host.sendCommand( 'cp -r "{0}" "{1}"'.format( self.path, self.getFile(host) ) )
        elif isdir == "F":
            host.sendCommand( 'cp "{0}" "{1}"'.format( self.path, self.getFile(host) ) )
        else:
            raise Exception( "file:remote got an unexpected response from host {2} when trying to see if {0} is a directory or a file: {1}".format( self.path, res, host.name ) )

    def getFile(self, host):
        """
        Returns the path to the files on the remote seeding host.

        The path can be to a single file or to the root directory of a collection of files.

        These files are only available if self.sendToSeedingHost(...) has been called for this host.

        Note that, although this method can signal None, the only certainty is that nothing is available if None is returned.
        If anything else is returned you should verify that the host is a seeding host and sendToSeedingHost(...) has been called for it.

        The default implementation returns None, signalling no files are available (yet).

        @param  host        The host on which to find the file(s).

        @return The path to the (root of) the file(s) on the remote host, or None if they are not (yet) available.
        """
        if not self.getFileDir(host):
            return None
        res = host.sendCommand( '[ -d "{0}" ] && echo "D" || echo "F"'.format( self.path ) )
        isdir = res.splitlines()[-1] 
        if isdir == "D":
            if self.path[-1:] == '/':
                p = self.path[:-1].rfind('/')
                if p == -1:
                    name = self.path[:-1]
                else:
                    name = self.path[:p]
            else:
                p = self.path.rfind('/')
                if p == -1:
                    name = self.path
                else:
                    name = self.path[:p]
        elif isdir == "F":
            if self.renameFile:
                name = 'inputFile'
            else:
                p = self.path.rfind('/')
                if p == -1:
                    name = self.path
                else:
                    name = self.path[:p]
        else:
            raise Exception( "file:remote got an unexpected response from host {2} when trying to see if {0} is a directory or a file: {1}".format( self.path, res, host.name ) )
        return '{0}/files/{1}'.format( self.getFileDir(host), name )
    
    @staticmethod
    def APIVersion():
        return "2.2.0"

import os
import tempfile

from core.campaign import Campaign
import core.file

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for file object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class local(core.file.file):
    """
    File implementation for local files or directories.

    Extra parameters:
    - path                  The path to the actual file or directory on the local machine.
    - generateTorrent       Set this to "yes" to have a torrent file automatically generated from the file;
                            the torrent file will be uplaoded and its location available through getMetaFile(...).
                            The metaFile parameter must not be set in this case.
    - generateRootHash      Set this to "yes" to have the SHA1 root hash automatically generated from the file;
                            the rootHash parameter must not be set in this case. path must refer to a single file
                            for a root hash to be calculated.
    - renameFile            Set this to "yes" to have the file renamed when uploaded to an automatically generated
                            name. This is forbidden when automated torent generation is requested. Not valid if
                            path points to a directory.
    """

    path = None                 # The path of the local file or directory
    generateTorrent = False     # True iff automated torrent generation is requested
    generateRootHash = False    # True iff automated root hash calculation is requested
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
            if not os.path.exists( value ):
                parseError( "File or directory '{0}' does not exist".format( value ) )
            if self.path:
                parseError( "A file or directory was already given" )
            self.path = value
        elif key == 'torrent' or key == 'generateTorrent':
            if key == 'torrent':
                Campaign.logger.log( "Please do not use the torrent parameter of file:local anymore. It is deprecated. Use generateTorrent instead." )
            if value == 'yes':
                self.generateTorrent = True
        elif key == 'generateRootHash':
            if value == 'yes':
                self.generateRootHash = True
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
        if self.metaFile and self.generateTorrent:
            raise Exception( "file:local {0} has requested automated torrent generation, but a meta file was already given".format( self.name ) )
        if self.rootHash and self.generateRootHash:
            raise Exception( "file:local {0} has requested automated root hash calculation, but a root hash was already given".format( self.name ) )
        if os.path.isdir( self.path ):
            if self.generateRootHash:
                raise Exception( "file:local {0} has requested automated root hash calculation, but {1} is a directory, for which root hashes aren't supported".format( self.name, self.path ) )
            if self.renameFile:
                raise Exception( "file:local {0} has requested the uploaded file to be renamed, but {1} is a directory, for which this is not supported".format( self.name, self.path ) )
        meta = Campaign.loadCoreModule('meta')
        # PyLint really doesn't understand dynamic loading
        # pylint: disable-msg=E1101
        if self.generateRootHash:
            self.rootHash = meta.calculateMerkleRootHash( self.path ).encode( 'hex' )
        if self.generateTorrent:
            if self.isInCleanup():
                return
            _, self.metaFile = tempfile.mkstemp()
            meta.generateTorrentFile( self.path, self.metaFile)
        # pylint: enable-msg=E1101

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

    def sendToSeedingHost(self, host):
        """
        Send any files required for seeding hosts.
        
        This function will be called for each host on which seeding of the file is needed.

        Note that self.sendToHost(...) will also be called before this function is called.

        The default implementation does nothing.

        @param  host        The host to which to send the files.
        """
        core.file.file.sendToSeedingHost(self, host)
        host.sendCommand( 'mkdir -p "{0}/files/"'.format( self.getFileDir(host) ) )
        if os.path.isdir( self.path ):
            host.sendFiles( self.path, '{0}'.format( self.getFile(host) ) )
        else:
            host.sendFile( self.path, '{0}'.format( self.getFile(host) ) )

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
        if os.path.isdir( self.path ):
            if self.path[-1:] == '/':
                name = os.path.basename( self.path[:-1] )
            else:
                name = os.path.basename( self.path )
            return '{0}/files/{1}'.format( self.getFileDir(host), name )
        else:
            name = os.path.basename( self.path )
            if self.renameFile:
                name = 'inputFile'
            return '{0}/files/{1}'.format( self.getFileDir(host), name )

    @staticmethod
    def APIVersion():
        return "2.0.0"

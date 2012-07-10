import os
import tempfile

from core.parsing import isPositiveInt
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
    - generateRootHash      Set to a chunksize in kbytes to generate root hashes for that chunksize. Chunksizes may
                            be postfixed with L to generate legacy root hashes. Optional, can be specified multiple
                            times, requires that the rootHash parameter for the requested chunksize is not set.
                            For backward compatibility any illegal chunksize is read as 1, but this deprecated
                            behavior will disappear in 2.5.0.
    - renameFile            Set this to "yes" to have the file renamed when uploaded to an automatically generated
                            name. This is forbidden when automated torent generation is requested. Not valid if
                            path points to a directory.
    """

    path = None                 # The path of the local file or directory
    generateTorrent = False     # True iff automated torrent generation is requested
    generateRootHashes = None   # List of chunksizes for which root hash calculation is requested
    renameFile = False          # True iff the single file is to be renamed after uploading
    
    tempMetaFile = None         # The temporary file created for the meta file

    def __init__(self, scenario):
        """
        Initialization of a generic file object.

        @param  scenario        The ScenarioRunner object this client object is part of.
        """
        core.file.file.__init__(self, scenario)
        self.generateRootHashes = []

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
            fallback = False
            if value[-1:] == 'L':
                if not isPositiveInt(value[:-1], True):
                    fallback = True
            else:
                if not isPositiveInt(value, True):
                    fallback = True
                else:
                    value = int(value)
            if fallback:
                Campaign.logger.log( "Warning! Chunksize {0} was detected as the value of a generateRootHash parameter to a file:local. This is not a valid chunksize (which would be a positive non-zero integer possible postfixed by L) and is replaced by 1 for backwards compatibility. This behavior will disappear in 2.5.0.".format( value ) )
                value = 1
            if value in self.generateRootHashes:
                parseError( "Generation of root hashes for chunksize {0} was already requested.".format( value ) )
            self.generateRootHashes.append(value)
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
        for cs in self.generateRootHashes:
            if cs in self.rootHashes:
                raise Exception( "Generation of root hash for chunksize {0} was requested, but that root hash was already set on the file.".format( cs ) )
        if os.path.isdir( self.path ):
            if len(self.generateRootHashes) > 0:
                raise Exception( "file:local {0} has requested automated root hash calculation, but {1} is a directory, for which root hashes aren't supported".format( self.name, self.path ) )
            if self.renameFile:
                raise Exception( "file:local {0} has requested the uploaded file to be renamed, but {1} is a directory, for which this is not supported".format( self.name, self.path ) )
        if len(self.generateRootHashes) > 0 or self.generateTorrent:
            meta = Campaign.loadCoreModule('meta')
            # PyLint really doesn't understand dynamic loading
            # pylint: disable-msg=E1101
            for cs in self.generateRootHashes:
                if type(cs) != int and cs[-1:] == 'L':
                    self.rootHashes[cs] = meta.calculateMerkleRootHash( self.path, False, int(cs[:-1]) ).encode( 'hex' )
                else:
                    self.rootHashes[cs] = meta.calculateMerkleRootHash( self.path, True, cs).encode( 'hex' )
                if cs == 1:
                    self.rootHash = self.rootHashes[1]
            if self.generateTorrent:
                if self.isInCleanup():
                    return
                tempfd, self.tempMetaFile = tempfile.mkstemp('.torrent')
                os.close(tempfd)
                self.metaFile = self.tempMetaFile
                meta.generateTorrentFile( self.path, self.metaFile )
            # pylint: enable-msg=E1101

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
        host.sendCommand( '[ -d "{0}/files/" ] || mkdir -p "{0}/files/"'.format( self.getFileDir(host) ) )

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
        if not self.getFileDir(host):
            return None
        if os.path.isdir( self.path ):
            if self.path[-1:] == '/':
                name = os.path.basename( self.path[:-1] )
            else:
                name = os.path.basename( self.path )
        else:
            if self.renameFile:
                name = 'inputFile'
            else:
                name = os.path.basename( self.path )
        return '{0}/files/{1}'.format( self.getFileDir(host), name )

    def getDataDirTree(self):
        """
        Returns the directory tree of the data found in getFile().
        
        This is the list of directories with getFile() as their common root, including getFile() itself. An empty list is returned in case
        getFile() is not a directory.
        
        E.g. a file that points to a directory called Videos with the following structure:
            Videos/
                generic.avi
                Humor/
                    humor1.avi
                    humor2.avi
                Drama/
                Horror/
                    Bloody/
                        blood1.mpg
                    Comedy/
                Action/
                    take1001.avi
                    take1002.avi
        getDataDirTree() would return the list:
            [
                ['Videos'],
                ['Videos','Humor'],
                ['Videos','Drama'],
                ['Videos','Horror'],
                ['Videos','Horror','Bloody'],
                ['Videos','Horror','Comedy'],
                ['Videos','Action']
            ]
        Note that this says nothing whatsoever about actual files inside those directories.
        
        This list may not be available before sendToSeedingHost(...) has been called.
        
        @return    A list of directories in list notation.
        """
        if not os.path.isdir( self.path ):
            return []
        if self.path[-1:] == '/':
            name = os.path.basename( self.path[:-1] )
        else:
            name = os.path.basename( self.path )
        dirstack = []
        dirstack.append( [] )
        result = [[name]]
        while len(dirstack) > 0:
            d = dirstack.pop()
            # pylint: disable-msg=W0142
            fullpath = os.path.join( self.path, *d )
            # pylint: enable-msg=W0142
            l = os.listdir(fullpath)
            for a in l:
                if os.path.isdir( os.path.join( fullpath, a ) ):
                    result.append( [name] + d + [a] )
                    dirstack.append( d + [a] )
        return result

    def getDataFileTree(self):
        """
        Returns the file tree of the data found in getFile().
        
        This is the list of files with getFile() as their common root (if it's a directory), including getFile() itself.
        This also holds for file objects pointing to a single file: the returned list will then contain 1 element.
        
        E.g. a file that points to a directory called Videos with the following structure:
            Videos/
                generic.avi
                Humor/
                    humor1.avi
                    humor2.avi
                Drama/
                Horror/
                    Bloody/
                        blood1.mpg
                    Comedy/
                Action/
                    take1001.avi
                    take1002.avi
        getDataFileTree() would return the list:
            [
                ['Videos', 'generic.avi'],
                ['Videos','Humor', 'humor1.avi'],
                ['Videos','Humor', 'humor2.avi'],
                ['Videos','Horror','Bloody', 'blood1.mpg'],
                ['Videos','Action','take1001.avi']
                ['Videos','Action','take1002.avi']
            ]
        Note that this does not reflect the complete directory structure.
        
        This list may not be available before sendToSeedingHost(...) has been called.
        
        The default implementation return None.
        
        @return    A list of files in list notation.
        """
        if self.path[-1:] == '/':
            name = os.path.basename( self.path[:-1] )
        else:
            name = os.path.basename( self.path )
        if not os.path.isdir( self.path ):
            return [[name]]
        dirstack = []
        dirstack.append( [] )
        result = []
        while len(dirstack) > 0:
            d = dirstack.pop()
            # pylint: disable-msg=W0142
            fullpath = os.path.join( self.path, *d )
            # pylint: enable-msg=W0142
            l = os.listdir(fullpath)
            for a in l:
                if os.path.isdir( os.path.join( fullpath, a ) ):
                    dirstack.append( d + [a] )
                else:
                    result.append( [name] + d + [a] )
        return result
    
    def cleanup(self):
        """
        Cleans up the file object.
        
        Do not assume anything has been or has not been done.
        Check everything and make sure things are clean when you're done.
        
        The default implementation does nothing.
        """
        core.file.file.cleanup(self)
        if self.tempMetaFile:
            os.remove( self.tempMetaFile )
            self.tempMetaFile = None

    @staticmethod
    def APIVersion():
        return "2.4.0"

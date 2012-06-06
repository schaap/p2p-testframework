# These imports are needed to access the parsing functions (which you're likely to use in parameter parsing),
# the Campaign data object and the file parent class.
from core.campaign import Campaign
import core.file

import posixpath

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
    
    Note that if multiple hosts are used with the same remote file, the remote file will check that the directory structure
    if equal, i.e. the same directories and files are referenced (recursively over directories). An exception will occur
    during sendToSeedingHost(...) if this check fails.

    Extra parameters:
    - path                  The path to the actual file or directory on the remote machine.
    - renameFile            Set this to "yes" to have the file renamed when uploaded to an automatically generated
                            name. Not valid if path points to a directory.
    """

    path = None                 # The path of the local file or directory
    renameFile = False          # True iff the single file is to be renamed after uploading
    
    remoteTree = None           # The list containing the directory tree of the remote file. [] for unknown. Each element is [relativePath, type] with
                                # realativePath in list notation and type either 'd' (directory) or 'f'. This means that a remote file pointing to a file
                                # has, after the first sendToSeedingHost call:
                                # len(self.remoteTree) == 1 and len(self.remoteTree[0][0]) == 1 and self.remoteTree[0][1] == 'f'

    def __init__(self, scenario):
        """
        Initialization of a generic file object.

        @param  scenario        The ScenarioRunner object this client object is part of.
        """
        core.file.file.__init__(self, scenario)
        self.remoteTree = []

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
        # Don't do anything if host isn't prepared well
        if not self.getFileDir(host):
            return
        core.file.file.sendToSeedingHost(self, host)
        # Get the base name of our file
        if self.path[-1:] == '/':
            name = posixpath.basename(self.path[:-1])
        else:
            name = posixpath.basename(self.path)
        # Extract the complete file tree from the remote host
        remoteTree = []
        dirStack = [[]]
        while len(dirStack) > 0:
            d = dirStack.pop()
            # pylint: disable-msg=W0142
            fullpath = posixpath.join( self.path, *d )
            # pylint: enable-msg=W0142
            res = host.sendCommand( '[ -d "{0}" ] && echo "D" || echo "F"'.format( fullpath ) )
            isdir = res.splitlines()[-1]
            if isdir == 'D':
                remoteTree.append( ([name] + d, 'd') )
                res = host.sendCommand( 'echo "____START____!!!!____STARTLIST____" && ls "{0}"'.format( fullpath ) )
                dirlist = res.splitlines()
                startFound = False
                for i in dirlist:
                    if startFound:
                        if i == '.' or i == '..':
                            continue
                        dirStack.append( d + [i] )
                    else:
                        if i == '____START____!!!!____STARTLIST____':
                            startFound = True
                if not startFound:
                    raise Exception( "file:remote got an unexpected response from host {2} when requesting the directory listing of directory {0}: {1}".format( fullpath, res, host.name ) )
            elif isdir == 'F':
                if len(remoteTree) == 0 and self.renameFile:
                    remoteTree.append( ( ['inputFile'], 'f') )
                else: 
                    remoteTree.append( ([name] + d, 'f') )
            else:
                raise Exception( "file:remote got an unexpected response from host {2} when trying to see if {0} is a directory or a file: {1}".format( self.path, res, host.name ) )
        # Compare the file tree to an earlier found one, or set this one as the base comparison
        if len(self.remoteTree) < 1:
            self.remoteTree = remoteTree
        elif self.remoteTree != remoteTree:
            raise Exception( "file:remote found a remote instance of the file on host {0} that is different from an earlier found instance on another host; this is not supported".format( host.name ) )
        # Check validity of some options based on what the remote file turned out to be, and copy it
        if remoteTree[0][1] == 'd':
            if self.renameFile:
                raise Exception( "The renameFile parameter to file:remote is not allowed for directories and {0} seems to be a directory on host {1}.".format( self.path, host.name ) )
            host.sendCommand( 'cp -r "{0}" "{1}"'.format( self.path, self.getFile(host) ) )
        else:
            host.sendCommand( 'cp "{0}" "{1}"'.format( self.path, self.getFile(host) ) )

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
        
        The default implementation returns an empty list.
        
        @return    A list of directories in list notation.
        """
        return [d[0] for d in self.remoteTree if d[1] == 'd']

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
        return [d[0] for d in self.remoteTree if d[1] == 'f']

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
        if len(self.remoteTree) < 1 or self.getFileDir(host) is None:
            return None
        if self.remoteTree[0][1] == 'f' and self.renameFile:
            name = 'inputFile'
        else:
            name = self.remoteTree[0][0]
        return '{0}/files/{1}'.format( self.getFileDir(host), name )
    
    @staticmethod
    def APIVersion():
        return "2.4.0"

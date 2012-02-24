import os

from core.parsing import isValidName
from core.campaign import Campaign
from core.coreObject import coreObject

def parseError( msg ):
    raise Exception( "Parse error for file object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

# Yes, that's a warning below. That's OK, though.
class file(coreObject):
    """
    The parent class for all files.

    This object contains all the default implementations for every file.
    When subclassing file be sure to use the skeleton class as a basis: it saves you a lot of time.
    """

    rootHash = None         # The root hash of the file.
    metaFile = None         # The meta file of the file, such as a torrent file.

    def __init__(self, scenario):
        """
        Initialization of a generic file object.

        @param  scenario        The ScenarioRunner object this file object is part of.
        """
        coreObject.__init__(self, scenario)

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
        if key == 'name':
            if self.name != '':
                parseError( 'Name already set: {0}'.format( self.name ) )
            if not isValidName( value ):
                parseError( '"{0}" is not a valid name'.format( value ) )
            if value in self.scenario.getObjectsDict('file'):
                parseError( 'File object called {0} already exists'.format( value ) )
            self.name = value
        elif key == "rootHash":
            if self.rootHash:
                parseError( 'Root hash already set: {0}'.format( self.rootHash ) )
            if not isinstance( value, basestring ) or len( value ) != 40 or reduce( lambda x, y: x or not ( ( y >= '0' and y <= '9' ) or ( y >= 'A' and y <= 'F' ) or ( y >= 'a' and y <= 'f' ) ), value, False ):
                parseError( 'Valid root hashes consist of exactly 40 hexadecimal digits, unlike "{0}"'.format( value ) )
            self.rootHash = value
        elif key == "metaFile":
            if self.metaFile:
                parseError( 'Meta file already set: {0}'.format( self.metaFile ) )
            if not os.path.exists( value ):
                parseError( 'Meta file {0} seems not to exist'.format( value ) )
            self.metaFile = value
        else:
            parseError( 'Unknown parameter name: {0}'.format( key ) )

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        if self.name == '':
            raise Exception( "File object declared at line {0} was not given a name".format( self.declarationLine ) )

    def getFileDir(self, host):
        """
        Returns the path on the remote host where this file's files can reside.

        No guarantees are given as to the existence of this path.
        
        During cleanup this may return None! 

        @param  host        The host on which the remote path is requested.

        @return The path to the file dir on the remote host.
        """
        if host.getTestDir():
            return host.getTestDir()+"/files/{0}".format(self.name)
        return None

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
        if self.metaFile:
            if self.getFileDir(host):
                host.sendCommand( 'mkdir -p "{0}/meta/"'.format( self.getFileDir( host ) ) )
                host.sendFile( self.metaFile, self.getMetaFile( host ) )

    # There's an unused argument host here; that's fine
    # pylint: disable-msg=W0613
    def sendToSeedingHost(self, host):
        """
        Send any files required for seeding hosts.
        
        This function will be called for each host on which seeding of the file is needed.

        Note that self.sendToHost(...) will also be called before this function is called.

        The default implementation does nothing.

        @param  host        The host to which to send the files.
        """
        pass
    # pylint: enable-msg=W0613

    # There's an unused argument host here; that's fine
    # pylint: disable-msg=W0613
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
        # Note that this is the new name of getName(...), which made no sense in naming
        return None
    # pylint: enable-msg=W0613

    def getMetaFile(self, host):
        """
        Returns the path to the meta file on the remote host.

        If no meta file was given, None is returned.

        An example of a meta file is a torrent file: a file that describes the actual data file(s).

        Note that you should verify yourself that the file is actually there. This should be true after sendToHost(...) has been
        called for this host.

        The default implementation returns the path on the remote host to the meta file as uploaded in the default implementation
        of sendToHost(...), or None if no meta file was given.

        @param  host        The host on which to find the meta file.

        @return The path to the meta file on the remote host, or None is no meta file is available.
        """
        # Note that this is the new name of getMetaName(...), which made no sense in naming
        if not self.metaFile or not self.getFileDir( host ):
            return None
        postfix = ''
        index = self.metaFile.rfind( '.' )
        if index != -1:
            postfix = self.metaFile[index:]
        return "{0}/meta/meta_file{1}".format( self.getFileDir( host ), postfix )

    def getRootHash(self):
        """
        Returns the root hash of the file.

        @return The root hash of the file, or None is no root hash was specified.
        """
        return self.rootHash

    def getModuleType(self):
        """
        Return the moduleType string.
        
        @return    The module type.
        """
        return 'file'
    
    def getName(self):
        """
        Return the name of the object.
        
        @return    The name.
        """
        return self.name

    @staticmethod
    def APIVersion():
        return "2.0.0-core"

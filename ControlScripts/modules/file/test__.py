import core.file
import tempfile
import os

class test__(core.file.file):
    """
    A test implementation of the file object.

    The implementation uses the file testseedingfile, which contains "abcdef" as data. A testfile is also sent to each host, but never used.

    If no root hash is given a hardcoded root hash for the seeding file is used.

    Use file:fakedata for more elaborate testing.
    """

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
        core.file.file.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        core.file.file.checkSettings(self)

        if not self.rootHash:
            self.rootHash = '97bb2117ad9bc68bc8bec3cca3a113ef30aebc37'

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

        if self.isInCleanup():
            return
        f, path = tempfile.mkstemp()
        fileObj = os.fdopen( f, 'w' )
        for _ in range( 0, 1024 ):
            fileObj.write( 'hijklmn' )
        fileObj.close()
        if self.isInCleanup():
            os.remove( path )
            return
        host.sendCommand( 'mkdir -p "{0}/files/"'.format( self.getFileDir( host ) ) )
        host.sendFile( path, "{0}/files/testfile".format( self.getFileDir( host ) ) )
        os.remove( path )

    def sendToSeedingHost(self, host):
        """
        Send any files required for seeding hosts.
        
        This function will be called for each host on which seeding of the file is needed.

        Note that self.sendToHost(...) will also be called before this function is called.

        The default implementation does nothing.

        @param  host        The host to which to send the files.
        """
        core.file.file.sendToSeedingHost(self, host)
        if self.isInCleanup():
            return
        f, path = tempfile.mkstemp()
        fileObj = os.fdopen( f )
        for _ in range( 0, 1024 ):
            fileObj.write( 'abcdefg' )
        fileObj.close()
        if self.isInCleanup():
            os.remove( path )
            return
        host.sendCommand( 'mkdir "{0}/files/"'.format( self.getFileDir( host ) ) )
        host.sendFile( path, "{0}/files/testseedingfile".format( self.getFileDir( host ) ) )
        os.remove( path )

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
        return "{0}/files/testseedingfile".format( self.getFileDir( host ) )

    @staticmethod
    def APIVersion():
        return "2.1.0"

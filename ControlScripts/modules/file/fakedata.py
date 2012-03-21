from core.parsing import isPositiveInt
from core.campaign import Campaign
import core.file

import os

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for file object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

# The list of files needed for the fakedata utility
fakedataGeneratorFiles = ['compat.h', 'fakedata.h', 'fakedata.cpp', 'genfakedata.cpp']

class fakedata(core.file.file):
    """
    A file implementation for generated, fake data.
    
    This module uses Utils/fakedata to generate the data for the files.
    
    Extra parameters:
    - ksize     A positive integer, divisible by 4, that denotes the size of the generated file in kbytes. Required.
    - binary    The path of the remote binary to use. This might be needed when g++ does not work on one of the hosts
                this file is used on. Optional, defaults to "" which will have the binary compiled on the fly.
    - filename  The name of the file that will be created. Optional, defaults to "fakedata".
    """
    
    size = None         # The size of the file in kbytes
    binary = None       # Path to the remote binary to use
    filename = None     # The filename the resulting file should have  

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
        if key == 'size':
            Campaign.logger.log( "WARNING! The size parameter to file:fakedata is deprecated. Please use ksize instead.")
            if not isPositiveInt( value, True ):
                parseError( "The size must be a positive, non-zero integer" )
            if self.size:
                parseError( "Size already set: {0}".format(self.size) )
            self.size = int(value)/4096
        elif key == 'ksize':
            if not isPositiveInt( value, True ):
                parseError( "The ksize must be a positive, non-zero integer" )
            if self.size:
                parseError( "Size already set: {0}".format(self.size) )
            if int(value) % 4 != 0:
                parseError( "The ksize parameter should be a multiple of 4")
            self.size = int(value)
        elif key == 'binary':
            if self.binary:
                parseError( "The path to the fakedata binary has already been set: {0}".format( self.binary ) )
            self.binary = value
        elif key == 'filename' or key == 'fileName':
            if key == 'fileName':
                Campaign.logger.log( "Warning: the parameter fileName to file:fakedata has been deprecated. Use filename instead." )
            if self.filename:
                parseError( "The filename has already been set: {0}".format( self.filename ) )
            self.filename = value
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
        
        if not self.size:
            raise Exception( "The ksize parameter to file {0} is not optional".format( self.name ) )
        if not self.filename:
            self.filename = 'fakedata'
        if not self.binary:
            if not os.path.exists( os.path.join( Campaign.testEnvDir, 'Utils', 'fakedata' ) ):
                raise Exception( "The Utils/fakedata directory is required to build a fakedata file" )
            for f in fakedataGeneratorFiles:
                if not os.path.exists( os.path.join( Campaign.testEnvDir, 'Utils', 'fakedata', f ) ):
                    raise Exception( "A file seems to be missing from Utils/fakedata: {0} is required to build the fakedata utility.".format( f ) )

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

        host.sendCommand( 'mkdir -p "{0}/files"'.format( self.getFileDir(host) ) )

    def sendToSeedingHost(self, host):
        """
        Send any files required for seeding hosts.
        
        This function will be called for each host on which seeding of the file is needed.

        Note that self.sendToHost(...) will also be called before this function is called.

        The default implementation does nothing.

        @param  host        The host to which to send the files.
        """
        core.file.file.sendToSeedingHost(self, host)
        
        binaryCommand = None
        if not self.binary:
            remoteBaseDir = '{0}/fakedata-source'.format( self.getFileDir(host) )
            host.sendCommand( 'mkdir -p "{0}"'.format( remoteBaseDir ) )
            for f in fakedataGeneratorFiles:
                host.sendFile( os.path.join( Campaign.testEnvDir, 'Utils', 'fakedata', f ), '{0}/{1}'.format( remoteBaseDir, f ), True )
            res = host.sendCommand( '( cd "{0}"; g++ *.cpp -o genfakedata && echo && echo "OK" )'.format( remoteBaseDir ) )
            if len(res) < 2:
                raise Exception( "Too short a response when trying to build genfakedata for file {0} in directory {1} on host {2}: {3}".format( self.name, remoteBaseDir, host.name, res ) )
            if res[-2:] != "OK":
                raise Exception( "Could not build genfakedata for file {0} in directory {1} on host {2}. Reponse: {3}".format( self.name, remoteBaseDir, host.name, res ) )
            binaryCommand = '{0}/genfakedata'.format( remoteBaseDir )
        else:
            res = host.sendCommand( '[ -e "{0}" -a -x "{0}" ] && echo "Y" || echo "N"' )
            if res != 'Y':
                raise Exception( "Binary {0} for file {1} does not exist on host {2}".format( self.binary, self.name, host.name ) )
            binaryCommand = self.binary
        res = host.sendCommand( '"{0}" "{1}/files/{2}" {3} && echo && echo "OK"'.format( binaryCommand, self.getFileDir(host), self.filename, self.size ) )
        if len(res) < 2:
            raise Exception( "Too short a response when trying to generate the fake data file {0} on host {1}: {2}".format( self.name, host.name, res ) )
        if res[-2:] != "OK":
            raise Exception( "Could not generate fake data file {0} on host {1}: {2}".format( self.name, host.name, res ) )

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
        return "{0}/files/{1}".format( self.getFileDir(host), self.filename )

    @staticmethod
    def APIVersion():
        return "2.1.0"

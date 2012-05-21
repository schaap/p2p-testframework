from core.parsing import isPositiveInt
from core.campaign import Campaign
import core.file
from core.meta import meta

import os
import pickle
import tempfile
import shutil
import subprocess
import random

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
    - ksize             A positive integer, divisible by 4, that denotes the size of the generated file in kbytes. Required.
    - binary            The path of the remote binary to use. This might be needed when g++ does not work on one of the hosts
                        this file is used on. Optional, defaults to "" which will have the binary compiled on the fly.
    - filename          The name of the file that will be created. Optional, defaults to "fakedata".
    - multiple          The number of fake data files to generate. Optional positive integer, defaults to 1. If a multiple
                        higher than 1 is specified, the filenames will be "{0}_{1}".format( filename, filecounter ) for
                        filecounter from 0 to (multiple-1)
    - generateTorrent   If set to anything but "" the file:fakedata will create torrent meta files for each fake data file
                        and associate the file:fakedata instances with those meta files. Optional, requires metaFile to not
                        be set.
    - generateRootHash  If set to anything but "" the file:fakedata will calculate the root hash for each fake data file and
                        associate the file:fakedata instances with those root hashes. Optional, requires rootHash to not be
                        set.
    - torrentCache      Path to a local directory. If set, this directory is taken to contain a cache of torrents for fakedata
                        files. Each torrent is named '{0}_{1}.torrent'.format( self.size, self.slaveNumber ) (no _{1} if
                        multiple is 1). Any present torrent files will be used from cache, others will be added to the cache.
                        Optional, must point to an existing directory.
    - rootHashCache     Path to a local file. If set, this file is taken to be a root hash cache for fakedata files. The cache
                        is a binary file containing a pickled python dictionary. Any present root hashes will be used from
                        cache, others will be added. Optional, must point to a writable (possibly not existing) file.
    
    Selection arguments:
    - '?'               Will select a random file object from this file:fakedata's collection. Especially useful if multiple > 1
                        to select a random file from the set. E.g. file=myfile@? 
    - n                 The positive zero-based index of the file in the list of files. Allowed ranges [0, multiple). Useful for
                        selecting one specific file when using multiple > 1. E.g. file=myfile@2    (assumes multiple=3 or larger)
    """
    
    size = None                 # The size of the file in kbytes
    binary = None               # Path to the remote binary to use
    filename = None             # The filename the resulting file should have
    multiple = None             # The number of fake data files to generate
    
    slave = False               # Flag to mark slave objects
    slaveNumber = 0             # Number of the slave object (starts at 1: non-slave is always 0)
    master = None               # The master object, set only for slave objects
    slaves = None               # Map of slave objects, only validly filled if not self.slave. Maps from count to file object.
    
    generateRootHash = False    # Flag whether root hashes are to be generated
    generateTorrent = False     # Flag whether torents are to be generated
    torrentCacheDir = None      # Path to local directory containing nothing but cached torrent files for fakedata
    rootHashCacheFile = None    # Path to local file containing cached root hashes for fakedata
    rootHashMap = None          # Map of generated root hashes
    tmpTorrentDir = None        # Path to a temporary torrent directory
    
    seedingHostSeen = None      # A list of seeding hosts which have already been seen for sendToSeedingHost
    
    def __init__(self, scenario):
        """
        Initialization of a generic file object.

        @param  scenario        The ScenarioRunner object this client object is part of.
        """
        core.file.file.__init__(self, scenario)
        self.slaves = {}
        self.seedingHostSeen = []

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
            self.size = int(value)/1024
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
        elif key == 'multiple':
            if self.multiple:
                parseError( "multiple may be specified only once" )
            if not isPositiveInt( value, True ):
                parseError( "multiple must be a positive, non-zero integer" )
            self.multiple = int(value)
        elif key == 'generateRootHash':
            self.generateRootHash = (value != '')
        elif key == 'generateTorrent':
            self.generateTorrent = (value != '')
        elif key == 'torrentCache':
            if self.torrentCacheDir:
                parseError( "A torrent cache directory has already been set: {0}".format( self.torrentCacheDir ) )
            if not os.path.isdir( value ):
                parseError( "{0} is not a directory".format( value ) )
            self.torrentCacheDir = value
        elif key == 'rootHashCache':
            if self.rootHashCacheFile:
                parseError( "A root hash cache file has already been set: {0}".format( self.rootHashCacheFile ) )
            if os.path.exists( value ) and not os.path.isfile( value ):
                parseError( "{0} is not a file".format( value ) )
            if os.path.dirname( value ) == '' or not os.path.isdir( os.path.dirname( value ) ):
                parseError( "{0} does not point to a new file in an existing directory".format( value ) )
            self.rootHashCacheFile = value
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
        if not self.multiple:
            self.multiple = 1
        elif self.multiple > 1:
            if self.metaFile:
                raise Exception( "Meta files are not supported when setting multiple > 1." )
            if self.rootHash:
                raise Exception( "Preset root hashes are not supported when setting multiple > 1." )
        if self.generateTorrent and self.metaFile:
            raise Exception( "If generateTorrent is specified, no meta file is allowed." )
        if self.generateRootHash and self.rootHash:
            raise Exception( "If generateRootHash is specified, no rootHash is allowed." )
        if self.torrentCacheDir and not self.generateTorrent:
            raise Exception( "A torrent cache without generating torrents? You've forgotten something." )
        if self.rootHashCacheFile and not self.generateRootHash:
            raise Exception( "A root hash cache without generating root hashes? You've forgotten something." )

        if self.generateRootHash or self.generateTorrent:        
            if self.generateRootHash:
                # Initialize root hash map and load root hash cache
                if self.rootHashCacheFile and os.path.exists( self.rootHashCacheFile ):
                    f = open( self.rootHashCacheFile, 'r' )
                    self.rootHashMap = pickle.load( f )
                    f.close()
                    if type(self.rootHashMap) != dict:
                        raise Exception( "Root hash cache file {0} does not contain a map. Type of unpickled object: {1}".format( self.rootHashCacheFile, type(self.rootHashMap) ) )
                else:
                    self.rootHashMap = {}
            torrentDir = '' # So os.path.join(torrentDir,...) won't complain
            if self.generateTorrent:
                # Set torrentDir to either the cache dir or a new temporary dir
                if self.torrentCacheDir:
                    torrentDir = self.torrentCacheDir
                else:
                    self.tmpTorrentDir = tempfile.mkdtemp()
                    torrentDir = self.tmpTorrentDir
            tempdir = ''
            torrentFound = 0
            rootHashFound = 0
            for count in range(self.multiple):
                if self.generateRootHash and (self.size, count) in self.rootHashMap:
                    rootHashFound += 1
                if self.generateTorrent:
                    if count == 0 and self.multiple == 1:
                        if os.path.isfile( os.path.join( torrentDir, '{0}.torrent'.format( self.size ) ) ):
                            torrentFound += 1
                    else:
                        if os.path.isfile( os.path.join( torrentDir, '{0}_{1}.torrent'.format( self.size, count ) ) ):
                            torrentFound += 1
            print "Generation of meta data requested for {1} files of file:fakedata {0}".format( self.name, self.multiple )
            needGeneration = False
            if self.generateTorrent:
                if torrentFound == self.multiple:
                    print "- All .torrent files are cached, not generating"
                else:
                    print "- {0} out of {1} .torrent files are cached, generating {2}".format( torrentFound, self.multiple, self.multiple - torrentFound )
                    needGeneration = True
            if self.generateRootHash:
                if rootHashFound == self.multiple:
                    print "- All root hashes are cached, not calculating"
                else:
                    print "- {0} out of {1} root hashes are cached, calculating {2}".format( rootHashFound, self.multiple, self.multiple - rootHashFound )
                    needGeneration = True
            if needGeneration:
                if not os.path.exists( os.path.join( Campaign.testEnvDir, 'Utils', 'fakedata', 'genfakedata' ) ):
                    raise Exception( "The Utils/fakedata/genfakedata utility is required to build a fakedata file for on-the-fly torrent and root hash creation. Please run something like 'g++ *.cpp -o genfakedata' inside Utils/fakedata/ to create it." )
                try:
                    tempdir = tempfile.mkdtemp()
                    for count in range(self.multiple):
                        # Figure out the would-be names of the file and the torrent file
                        if count == 0 and self.multiple == 1:
                            # Special naming convention for multiple == 1
                            torrentName = os.path.join( torrentDir, '{0}.torrent'.format( self.size ) )
                            filename = os.path.join( tempdir, self.filename )
                        else: 
                            torrentName = os.path.join( torrentDir, '{0}_{1}.torrent'.format( self.size, count ) )
                            filename = os.path.join( tempdir, '{0}_{1}'.format( self.filename, count ) )
                        # Check whether root hashes and/or torrent files are needed and not cached
                        needRootHash = self.generateRootHash and (self.size, count) not in self.rootHashMap
                        needTorrent = self.generateTorrent and not os.path.isfile( torrentName )
                        if needRootHash or needTorrent:
                            # Only create data file if either is needed and not cached
                            # Creation is done by external process, since python is TOO RUDDY SLOW for it! Takes about the same time to build (not write) a handful of kilobytes of data as the external (native) program needs to write 50M of it
                            proc = subprocess.Popen([os.path.abspath(os.path.join( Campaign.testEnvDir, 'Utils', 'fakedata', 'genfakedata' )), os.path.abspath(filename), '{0}'.format(self.size), '{0}'.format(count)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                            (out,_) = proc.communicate()
                            if proc.returncode != 0:
                                raise Exception( "Generating file {0} of file:fakedata {1} failed. Output: {2}".format( count, self.name, out ) )
                            
                            if needRootHash:
                                # Only calculate root hash if needed and not cached
                                self.rootHashMap[(self.size, count)] = meta.calculateMerkleRootHash( filename, True )
                            if needTorrent:
                                # Only generate torrent file if needed and not cached
                                meta.generateTorrentFile( filename, torrentName )
                            # Better remove the file after calculating and generating: don't need it anymore and we might need the space
                            os.remove(filename)
                finally:
                    # Clean up temp dir with data files
                    if tempdir and tempdir != '':
                        shutil.rmtree(tempdir, True)
                        #pass
                if self.generateRootHash:
                    if self.rootHashCacheFile: 
                        # Save root hash cache
                        f = open( self.rootHashCacheFile, 'w' )
                        pickle.dump( self.rootHashMap, f )
                        f.close()
            if self.generateRootHash:
                # Set own roothash
                self.rootHash = self.rootHashMap[(self.size, 0)].encode( 'hex' )
            if self.generateTorrent:
                if self.multiple == 1:
                    self.metaFile = os.path.join( torrentDir, '{0}.torrent'.format( self.size ) )
                else:
                    self.metaFile = os.path.join( torrentDir, '{0}_0.torrent'.format( self.size ) )
    
    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        core.file.file.resolveNames(self)
    
    def doPreprocessing(self):
        """
        Run directly before all objects in the scenario will run resolveNames and before cross referenced data is filled in.
        Host preprocessing is run before file preprocessing.
        
        This method may alter executions as it sees fit, mainly to allow the file object to add more file objects to executions as needed.
        Take care to select executions by looking at their fileNames attribute, not the files attribute. Also take into account that
        file=blabla@ is equal to file=blabla . You'll need to select both if you want either.
        
        When creating extra file objects, don't forget to also register them with the scenario via self.scenario.addObject(theNewFileObject)!
        Also note that those objects will have their resolveNames method called as well.
        """
        self.slaves[0] = self
        if self.multiple > 1:
            name1 = self.getName()
            name2 = '{0}@'.format(name1)
            # Build slave objects that refer to this master for each fake data file beyond number 0
            for count in range(1, self.multiple):
                fd = fakedata(self.scenario)
                fd.name = "{0}!{1}".format( self.name, count )
                fd.size = self.size
                fd.binary = self.binary
                fd.filename = self.filename
                fd.multiple = self.multiple
                fd.slave = True
                fd.master = self
                fd.slaveNumber = count
                fd.generateRootHash = self.generateRootHash
                fd.generateTorrent = self.generateTorrent
                if self.generateRootHash:
                    fd.rootHash = self.rootHashMap[(self.size, count)].encode( 'hex' )
                if self.generateTorrent:
                    if self.torrentCacheDir:
                        fd.metaFile = os.path.join( self.torrentCacheDir, '{0}_{1}.torrent'.format( self.size, count ) )
                    else:
                        fd.metaFile = os.path.join( self.tmpTorrentDir, '{0}_{1}.torrent'.format( self.size, count ) )
                self.scenario.addObject(fd)
                self.slaves[count] = fd
                for e in [e for e in self.scenario.getObjects('execution') if e.fileNames and (name1 in e.fileNames or name2 in e.fileNames)]:
                    e.fileNames.append("{0}@{1}".format( self.getName(), count ))

    def getByArguments(self, argumentString):
        """
        Selects a file object by specific arguments.
        
        The arguments can be used to return a different file object than the one this is called on.
        
        This is called for the execution's file parameter's selection syntax:
            file=name@args
        Invariant: self.scenario.getObjectsDict('file')[name] == self and argumentString == args
        
        The primary use of selection by arguments is to select a single file object from a file object that multiplies itself.
        
        The default implementation returns self for no arguments and raises an exception for any other argument.
        
        @param     argumentString    The arguments passed in the selection
        
        @return    A single, specific file object.
        """
        if argumentString == '?':
            return self.slaves[random.randint(0,self.multiple - 1)]
        if argumentString == '':
            return self
        try:
            i = int(argumentString)
            if i < 0 or i >= self.multiple:
                raise Exception( "File {1}@{0} requested but only {1}@0 through {1}@{2} are available".format( i, self.name, self.multiple - 1 ) )
            return self.slaves[i]
        except ValueError:
            raise Exception( "Argument string '{0}' not supported by file:fakedata in request '{1}@{0}'".format( argumentString, self.name ) )
    
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
        
        host.sendCommand( '[ -d "{0}/files" ] || mkdir -p "{0}/files"'.format( self.getFileDir(host) ) )

    def sendToSeedingHost(self, host):
        """
        Send any files required for seeding hosts.
        
        This function will be called for each host on which seeding of the file is needed.

        Note that self.sendToHost(...) will also be called before this function is called.

        The default implementation does nothing.

        @param  host        The host to which to send the files.
        """
        if self.slave:
            self.master.sendToSeedingHost(host)
            return
        
        if host in self.seedingHostSeen:
            return
        self.seedingHostSeen.append(host)
        
        core.file.file.sendToSeedingHost(self, host)
        
        # Figure out command
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

        # Generate files
        if self.multiple > 1:
            for filecounter in range(self.multiple):
                res = host.sendCommand( '"{0}" "{1}/files/{2}_{4}" {3} {4} && echo && echo "OK"'.format( binaryCommand, self.getFileDir(host), self.filename, self.size, filecounter ) )
                if len(res) < 2:
                    raise Exception( "Too short a response when trying to generate the fake data file {0}_{3} on host {1}: {2}".format( self.name, host.name, res, filecounter ) )
                if res[-2:] != "OK":
                    raise Exception( "Could not generate fake data file {0}_{3} on host {1}: {2}".format( self.name, host.name, res, filecounter ) )
        else:
            res = host.sendCommand( '"{0}" "{1}/files/{2}" {3} && echo && echo "OK"'.format( binaryCommand, self.getFileDir(host), self.filename, self.size ) )
            if len(res) < 2:
                raise Exception( "Too short a response when trying to generate the fake data file {0} on host {1}: {2}".format( self.name, host.name, res ) )
            if res[-2:] != "OK":
                raise Exception( "Could not generate fake data file {0} on host {1}: {2}".format( self.name, host.name, res ) )

    def getFileDir(self, host):
        """
        Returns the path on the remote host where this file's files can reside.

        No guarantees are given as to the existence of this path.
        
        During cleanup this may return None! 

        @param  host        The host on which the remote path is requested.

        @return The path to the file dir on the remote host.
        """
        if self.slave:
            return self.master.getFileDir(host)
        return core.file.file.getFileDir(self, host)

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
        if self.multiple > 1:
            return "{0}/files/{1}_{2}".format( self.getFileDir(host), self.filename, self.slaveNumber )
        else:
            return "{0}/files/{1}".format( self.getFileDir(host), self.filename )

    def getMetaFile(self, host):
        """
        Returns the path to the meta file on the remote host.

        If no meta file was given, None is returned.

        An example of a meta file is a torrent file: a file that describes the actual data file(s).

        Note that you should verify yourself that the file is actually there. This should be true after sendToHost(...) has been
        called for this host.


        @param  host        The host on which to find the meta file.

        @return The path to the meta file on the remote host, or None is no meta file is available.
        """
        if not self.metaFile or not self.getFileDir( host ):
            return None
        if self.generateTorrent:
            return '{0}/meta/meta_file_{1}.torrent'.format( self.getFileDir( host ), self.slaveNumber )
        return core.file.file.getMetaFile(self, host)
    
    def cleanup(self):
        """
        Cleans up the file object.
        
        Do not assume anything has been or has not been done.
        Check everything and make sure things are clean when you're done.
        """
        if self.tmpTorrentDir:
            if os.path.exists( self.tmpTorrentDir ):
                shutil.rmtree(self.tmpTorrentDir, True)
            self.tmpTorrentDir = None

    @staticmethod
    def APIVersion():
        return "2.2.0"

# These imports are needed to access the parsing functions (which you're likely to use in parameter parsing),
# the Campaign data object and the file parent class.
from core.parsing import *
from core.campaign import Campaign
import core.file

# NOTE: The last import above (import core.file) is different from usual. This is done to prevent trouble with python's
# builtin file type. The import
#   from core.file import file
# works perfectly, but hides the normal file type. The tradeoff is between a bit more typing (core.file.file instead of file)
# and possible errors with regard to file and file (??).

# You can define anything you like in the scope of your own module: the only thing that will be imported from it
# is the actual object you're creating, which, incidentally, must be named equal to the module it is in. For example:
# suppose you copy this file to modules/file/empty.py then the name of your class would be empty.

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for file object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

# TODO: Change the name of the class. See the remark above about the names of the module and the class. Example:
#
#   class empty(core.file.file):
class _skeleton_(core.file.file):
    """
    A skeleton implementation of a file subclass.
    
    Please use this file as a basis for your subclasses but DO NOT actually instantiate it.
    It will fail.
            
    Look at the TODO in this file to know where you come in.
    """
    # TODO: Update the description above. Example:
    #
    #   """
    #   An empty file object.
    #
    #   To be used just to create an empty file.
    #
    #   Extra parameters:
    #   - filename  The name of the file to be created.
    #   """

    def __init__(self, scenario):
        """
        Initialization of a generic file object.

        @param  scenario        The ScenarioRunner object this client object is part of.
        """
        core.file.file.__init__(self, scenario)
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
        #   if key == 'filename':
        #       if self.filename:
        #           parseError( "Really? Two names? ... No." )
        #       self.filename = value
        #   else:
        #       core.file.file.parseSetting(self, key, value)
        #
        # Do not forget that last case!
        #
        # The following implementation assumes you have no parameters specific to your file:
        core.file.file.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        core.file.file.checkSettings(self)
        # TODO: Check your settings. Example:
        #
        #   if not self.filename:
        #       raise Exception( "A dummy file still needs a filename, dummy." )

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        core.file.file.resolveNames(self)
        # TODO: Do any name resolutions here.
        # The names of other objects this object refers to, either intrinsically or in its parameters, should be checked here.
    
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
        # TODO: Send any extra files here. These are the files that are required by all executions, whether they're seeding or leeching.
        # Seeding specific files are to be sent in sendToSeedingHost(...).
        #
        # The default implementation will send the meta file. It is usually needed to create the remote data directory here. Example:
        #    host.sendCommand( 'mkdir -p "{0}/files"'.format( self.getFileDir(host) )

    def sendToSeedingHost(self, host):
        """
        Send any files required for seeding hosts.
        
        This function will be called for each host on which seeding of the file is needed.

        Note that self.sendToHost(...) will also be called before this function is called.

        The default implementation does nothing.

        @param  host        The host to which to send the files.
        """
        core.file.file.sendToSeedingHost(self, host)
        # TODO: Send the actual files to a seeding host. sendToHost(...) has already been called.
        # Note that self.getFileDir(...) is not guaranteed to exist yet. Example:
        #
        #   host.sendCommand( 'touch "{0}/files/{1}"'.format( self.getFileDir(host), self.filename ) )

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
        #
        # TODO: Send the path to the file uploaded to a seeding host. Example:
        #
        #   "{0}/files/{1}".format( self.getFileDir(host), self.filename )
        #
        # This implementation assumes you don't really have files, which is unlikely but possible:
        return None
    
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
        # TODO: Return the list of directories in the directory pointed to by getFile(), if applicable.
        #
        # This implementation assumes getFile() points to a single file:
        return []

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
        # TODO: Return the list of files (recursively) pointed to by getFile(), if applicable.
        # Take into acocunt that the return value is a list of lists! So if you have just one (statically named) file,
        # you should write something like:
        #
        #    return [['yourStaticFileName']]
        #
        #
        # This implementation assumes you have no files, which is unlikely:
        return None
    
    # TODO: If your getFile(...) does not always return a path (e.g. for non-seeding hosts) or not always a path in the same parent directory,
    # you may need to reimplement getDataDir(...)

    # TODO: More methods exist, but they are pretty standard and you're unlikely to want to change them. Look at core.file for more details.

    @staticmethod
    def APIVersion():
        # TODO: Make sure this is correct. You don't want to run the risk of running against the wrong API version
        return "2.4.0"

import os
import math
import hashlib

# ZERO contains 20 zero bytes. It's basically a zeroed SHA1 hash.
ZERO = '\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0'

def buildFileList( path, subdirs = [] ):
    fullpath = os.path.join( path, *subdirs )
    if os.path.isfile( fullpath ):
        return [{'length': os.stat(fullpath).st_size, 'path': subdirs}]
    else:
        names = os.listdir(fullpath)
        return reduce(lambda x,y: x+y, map(lambda x: buildFileList(path, subdirs+[x]), os.listdir(fullpath)))

def buildPieces( path, fileList_, blocksize ):
    fileList = list(fileList_)
    pieces = ''
    leftToRead = blocksize
    h = hashlib.new( 'sha1' )
    f = None
    while len(fileList) > 0:
        if not f:
            f = open(os.path.join(path, *(fileList.pop(0)['path'])))
        data = f.read( leftToRead )
        h.update( data )
        leftToRead -= len(data)
        if leftToRead == 0:
            pieces += h.digest()
            h = hashlib.new( 'sha1' )
            leftToRead = blocksize
        else:
            f.close()
            f = None
    if leftToRead > 0 and leftToRead < blocksize:
        pieces += h.digest()
    return pieces

class meta:
    """
    A fully static class with a number of methods to help you build
    meta data on the fly.
    """

    @staticmethod
    def calculateMerkleRootHash( path, compact = False, blocksize = 1 ):
        """
        Calculates the Merkle root hash for a file.

        The default is to calculate the root hash based on a binary hashtree of
        64 levels, the root of which is defined to be the root hash.

        Compact root hashes use the smallest binary tree covering the complete
        file and have the root of that as the root hash.

        Example: suppose we have a 3 KB file and use 1 KB blocks. Let's call
        these blocks B0, B1 and B2. H(l,i) is used as the hash in the binary
        hash tree at level l (l = 0 for leaves) index i, + is the concatenation
        operator and ZERO is just 40 zeroed bytes.

        For the example, the default hash calculation goes like this:

            H(0,0) = SHA1(B0)
            H(0,1) = SHA1(B1)
            H(0,2) = SHA1(B2)
            H(1,0) = SHA1(H(0,0) + H(0,1))
            H(1,1) = SHA1(H(0,2) + ZERO)
            H(2,0) = SHA1(H(1,0) + H(1,1))
            H(3,0) = SHA1(H(2,0) + ZERO)
            H(4,0) = SHA1(H(3,0) + ZERO)
            ...
            H(63,0) = SHA1(H(62,0) + ZERO)
            ROOTHASH = H(63,0)

        For the example, the compact hash calculation goes like this:

            H(0,0) = SHA1(B0)
            H(0,1) = SHA1(B1)
            H(0,2) = SHA1(B2)
            H(1,0) = SHA1(H(0,0) + H(0,1))
            H(1,1) = SHA1(H(0,2) + ZERO)
            H(2,0) = SHA1(H(1,0) + H(1,1))
            ROOTHASH = H(2,0)

        The compact hash calculation stopped at H(2,0) since 2 ^ 2 > 3. More
        generally speaking: 2 ^ l > #B, where l the level in the tree and
        #B the number of blocks in the file. In other words: H(2,0) is the
        smallest hash covering all of the file.

        @param  path        The path to the file to calculate the root hash for.
        @param  compact     True iff the compact hash calculation is to be used.
        @param  blocksize   The blocksize to use in kilobytes (default: 1).

        @return The binary string containing the root hash, which is an SHA1 hash.
        """
        if not isinstance( blocksize, int ):
            raise TypeError( "blocksize must be an int" )
        if blocksize < 1:
            raise ValueError( "blocksize must be > 0" )
        if not os.path.exists( path ):
            raise ValueError( "path must point to an existing file" )
        if not os.path.isfile( path ):
            raise ValueError( "path must point to a file" )

        if compact:
            st = os.stat( path )
            size = math.ceil( st.st_size / ( 1024.0 * blocksize ) );
            maxLevel = 0
            while maxLevel < 64 and 2**maxLevel < size:
                maxLevel += 1
            if maxLevel > 63:
                raise Exception( "files of size greater than {0}KB can't be hashed with blocksize {1}KB".format( ( 2**63 * blocksize ), blocksize ) )
        else:
            maxLevel = 63

        hashes = {}
        for a in range( 0, maxLevel + 1 ):
            hashes[a] = None

        f = open( path, 'r' )
        data = f.read( 1024 * blocksize )
        while data != '':
            h = hashlib.new( 'sha1' ) 
            h.update( data )
            h = h.digest()

            for a in range( 0, maxLevel + 1 ):
                if not hashes[a]:
                    hashes[a] = h
                    break
                else:
                    h2 = hashlib.new( 'sha1' )
                    h2.update( hashes[a] )
                    h2.update( h )
                    h = h2.digest()
                    hashes[a] = None
                    del h2
            data = f.read( 1024 * blocksize )
        f.close()

        h = ZERO
        index = 0
        while index <= maxLevel and not hashes[index]:
            index += 1

        if index == maxLevel:
            return hashes[maxLevel]

        while index < maxLevel:
            h2 = hashlib.new( 'sha1' )
            if not hashes[index]:
                h2.update( h )
                h2.update( ZERO )
            else:
                h2.update( hashes[index] )
                h2.update( h )
            h = h2.digest()
            index += 1

        return h

    @staticmethod
    def generateTorrentFile( path, torrentPath, blocksize = 1024, name = None, announce = 'http://127.0.0.1/announce', nodes = None, httpSeeds = None, URIList = None, private = False ):
        """
        Creates a .torrent file for the given path.

        The nodes parameter allows specifying nodes for the DHT. This is done according to
        specification BEP-0005. This also supports trackerless torrents.

        The announce parameter may be specified as a list of lists for multiple trackers
        in the torrent. This is according to specification BEP-0012. The first of the first
        item will be used for the usual announce field.

        HTTP seeds can be specified by giving a list in the httpSeeds parameter. These are
        added according to specification BEP-0017. HTTP seeds are HTTP servers running
        scripts talking the protocol of described in BEP-0017 to allow retrieving the
        torrent via that script. The httpSeeds list is a list of URLs that include the
        name of the script in each URL.

        HTTP and FTP URLs can be specified by giving a list in the URIList parameter.
        These are added according to specification BEP-0019. HTTP and FTP URLs specify
        download locations for the file(s) in the torrent for use with HTTP or FTP. The 
        items in this list may contain the file name if this is a single file torrent,
        but should otherwise end in a / signifying a root URL for all files in the torrent.
        In the case of multi file torrents, this / will be added when not detected.

        A private torrent can be created by setting private to True. The private key will
        be added as specified in specification BEP-0027.

        @param  path        The file or directory to create a torrent for. All files in a
                            directory will be included recursively.
        @param  torrentPath The file to save the torrent file to. Either an existing file
                            or one that can be created. The file will be overwritten.
        @param  blocksize   The chunk size for the torrent. Default: 1KB.
        @param  name        Specify a string to have that exact name used as the suggested
                            name for saving the file or root directory in the torrent, i.e.
                            the one pointed to by path. None to use the current name.
        @param  announce    The string specifying the tracker. None for a trackerless
                            torrent, in which case nodes must be given. A list of lists can
                            be given for a torrent with multiple trackers.
        @param  nodes       Possibly a list of nodes for the DHT, each node being a list
                            ["hostaddress", portnumber].
        @param  httpSeeds   A list of HTTP seed scripts, or None.
        @param  URIList     A list of HTTP or FTP URIs for extra seeds, or None.
        @param  private     True for a private torrent.
        """
        # A torrent file is just a bencoded dictionary.
        #
        # Keys in the dict:
        #
        # - announce
        #   The URL of the tracker
        # - info
        #   Dictionary of
        #   - name
        #       Purely advisory suggested file name to use when saving the file or directory.
        #   - piece length
        #       Number of bytes per chunk. Almost always power of 2.
        #   - pieces
        #       String, len of which multiple of 20, each 20-byte piece index i is
        #       SHA1 hash of piece i in the file.
        #   - one of:
        #       - length
        #           The size in bytes of the single file in the torrent.
        #       - files
        #           Indicates multiple files in the torrent. This is the list giving each of those
        #           files. For purpose of other keys in the info dict, all files are concatenated.
        #           List of dictionaries of
        #           - length
        #               The size in bytes of the file.
        #           - path
        #               List of UTF-8 encoded names corresponding to the path, e.g. ['foo','bar',
        #               'baz.txt'] for file foo/bar/baz.txt
        #
        # By extensions that are supported, add the following keys in the info dict:
        #
        # - private
        #   Present and equal to 1 for a private torrent.
        #
        # By extensions that are supported, add the following next to the info dict:
        #
        # - encoding
        #   'UTF-8'; not an official BEP, but used
        #
        # - nodes
        #   The list of nodes, each of which is a list of ["hostaddress", portnumber]. See BEP-0005.
        #
        # - httpseeds
        #   The list of URIs to HTTP seed scripts. See BEP-0017.
        #
        # - url-list
        #   The list of URIs to HTTP and FTP seeds. See BEP-0019.
        #
        # - announce-list
        #   A list of announce URIs. See BEP-0012.

        if not os.path.exists( path ):
            raise ValueError( "The file or directory '{0}' does not exist.".format( path ) )
        if os.path.exists( torrentPath ) and os.path.isdir( torrentPath ):
            raise ValueError( "{0} is a directory".format( torrentPath )

        torrent = {'encoding': 'UTF-8'}
        multiFile = os.path.isdir( path )
        if announce == '' or len( announce ) < 1:
            announce = None
        trackerless = False
        if announce:
            if isinstance( announce, list ):
                oneAnnounce = None
                for announceTier in announce:
                    if not isinstance( announceTier, list ):
                        raise TypeError( "If announce is given a list, it must be a list of lists of announce URIs." )
                    if len( announceTier ) < 1:
                        raise ValueError( "No sublists of the announce list may be empty." )
                    for announceURI in announceTier:
                        if not isinstance( announceURI, basestring )
                            raise TypeError( "Announce may be None, an URI string or a list of lists of URI strings." )
                        if not oneAnnounce:
                            oneAnnounce = announceURI
                torrent['announce'] = oneAnnounce
                torrent['announce-list'] = announce
            elif not isinstance( announce, basestring ):
                raise TypeError( "Announce may be None, an URI string or a list of lists of URI strings." )
            else:
                torrent['announce'] = announce
        else:
            trackerless = True
        if private:
            torrent['private'] = 1
        if nodes and len(nodes) < 1:
            nodes = None
        if nodes:
            if not isinstance( nodes, list ):
                raise TypeError( "Nodes is either None or a list or ['hostaddress', portnumber] items." )
            for node in nodes:
                if not isinstance( node, list ) or not isinstance( node[0], basestring ) or not isinstance( node[1], int ) or not len( node ) == 2:
                    raise TypeError( "Nodes is either None or a list or ['hostaddress', portnumber] items." )
            torrent['nodes'] = nodes
        elif trackerless:
            raise ValueError( "A torrent needs either an announce or a list of nodes." )
        if httpSeeds and len(httpSeeds) < 1:
            httpSeeds = None
        if httpSeeds:
            if not isinstance( httpSeeds, list ):
                raise TypeError( "httpSeeds is either None or a list of strings with HTTP seeding script URIs." )
            for seed in httpSeeds:
                if not isinstance( seed, basestring ):
                    raise TypeError( "httpSeeds is either None or a list of strings with HTTP seeding script URIs." )
            torrent['httpseeds'] = httpSeeds
        if URIList and len(URIList) < 1:
            URIList = None
        if URIList:
            if not isinstance( URIList, list ):
                raise TypeError( "URIList is either None or a list of strings with HTTP or FTP URIs." )
            for URI in URIList:
                if not isinstance( URI, basestring ):
                    raise TypeError( "URIList is either None or a list of strings with HTTP or FTP URIs." )
                if multiFile and URI[-1:] != '/':
                    URI += '/'
            torrent['url-list'] = URIList
        infodict = {}
        if name:
            if not isinstance( name, basestring ):
                raise TypeError( "name is either None or a string." )
            infodict['name'] = name
        else:
            if path[-1:] == '/':
                infodict['name'] = os.path.basename( path[:-1] )
            else
                infodict['name'] = os.path.basename( path )
        if not isinstance( blocksize, int ) or blocksize < 1:
            raise ValueError( "blocksize must be a positive integer" )
        infodict['piece length'] = blocksize
        if os.path.isfile( path ):
            st = os.stat( path )
            infodict['length'] = st.st_size
            infodict['pieces'] = buildPieces( path, [{'length': st.st_size, 'path': []}], blocksize )
        else:
            infodict['files'] = buildFileDict( path )
            infodict['pieces'] = buildPieces( path, infodict['files'], blocksize )
        # FIXME: Check correctness of pieces function
        # FIXME: CONTINUE

        # - info
        #   Dictionary of
        #   - name
        #       Purely advisory suggested file name to use when saving the file or directory.
        #   - piece length
        #       Number of bytes per chunk. Almost always power of 2.
        #   - pieces
        #       String, len of which multiple of 20, each 20-byte piece index i is
        #       SHA1 hash of piece i in the file.
        #   - one of:
        #       - length
        #           The size in bytes of the single file in the torrent.
        #       - files
        #           Indicates multiple files in the torrent. This is the list giving each of those
        #           files. For purpose of other keys in the info dict, all files are concatenated.
        #           List of dictionaries of
        #           - length
        #               The size in bytes of the file.
        #           - path
        #               List of UTF-8 encoded names corresponding to the path, e.g. ['foo','bar',
        #               'baz.txt'] for file foo/bar/baz.txt


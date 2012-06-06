from core.parsing import isPositiveInt, isValidName
from core.campaign import Campaign
from core.client import client

import os
import tempfile
import threading
import external.bencode

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for client object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class opentracker(client):
    """
    A client implementation for the Opentracker torrent tracker software
    
    You can retrieve the Opentracker software from http://erdgeist.org/arts/software/opentracker/
    
    Extra parameters:
    - port                  The port on which the tracker will be listening; required, 1023 < positive int < 65536
    - changeTracker         The name of a file object for which the metaFile parameter has been set and points
                            to a .torrent file; the torrent file will be changed to point to the dynamically
                            retrieved address of the first host running this client; the file object will be
                            altered to have their metaFile point to the changed torrent file before the files
                            will be uploaded; can be specified multiple times. Note that the .torrent files to
                            be altered must have a single tracker set already: the change is based on replacing
                            the existing single tracker. Please note this does not work with self-multiplying
                            files. Use changeClientTracker in such cases.
    - changeClientTracker   The name of a client object for which all associated files are to have their metaFile
                            parameters checked and, if they point to a .torrent file, the torrent file is to be
                            updated as if the file object was given as a changeTracker to this object. Note that
                            the metaFile of that very object will be updated, and hence all clients using that
                            file object will see the updated meta file.
    """
    
    port = None                     # The port openTracker will listen on
    changeTrackers = None           # List of names of file objects for which to change the torrent files
    changeClientTrackers = None     # List of names of client objects for which all torrent files are to be changed
    hasUpdatedTrackers = False      # Flag to keep track of whether the trackers have already been updated or not
    tempUpdatedFiles__lock = None   # List of all the temporary files (which need to be erased on cleanup)
    tempUpdatedFiles = None         # List of all the temporary files (which need to be erased on cleanup)

    def __init__(self, scenario):
        """
        Initialization of a generic client object.

        @param  scenario        The ScenarioRunner object this client object is part of.
        """
        client.__init__(self, scenario)
        self.changeTrackers = []
        self.tempUpdatedFiles = []
        self.tempUpdatedFiles__lock = threading.Lock()
        self.changeClientTrackers = []

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
        if key == 'port':
            if self.port:
                parseError( "Port already set: {0}".format( self.port ) )
            if not isPositiveInt( value ) or int(value) < 1024 or int(value) > 65535:
                parseError( "Port must be a positive integer greater than 1023 and smaller than 65536, not {0}".format( value ) )
            self.port = int(value)
        elif key == 'changeTracker' or key == 'changetracker':
            if not isValidName( value ):
                parseError( "{0} is not a valid name for a file object.".format( value ) )
            self.changeTrackers.append( value )
        elif key == 'changeClientTracker':
            if not isValidName( value ):
                parseError( "{0} is not a valid name for a client object.".format( value ) )
            self.changeClientTrackers.append( value )
        else:
            client.parseSetting(self, key, value)

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        client.resolveNames(self)
        for f in self.changeTrackers:
            if f not in self.scenario.getObjectsDict( 'file' ):
                raise Exception( "Client {0} was instructed to change the torrent file of file {1}, but the latter was never declared.".format( self.name, f ) )
            if not self.scenario.getObjectsDict( 'file' )[f].metaFile or not os.path.exists( self.scenario.getObjectsDict( 'file' )[f].metaFile ) or os.path.isdir( self.scenario.getObjectsDict( 'file' )[f].metaFile ):
                raise Exception( "Client {0} was instructed to change the torrent file of file {1}, but the metafile of the latter does not exist or is a directory.".format( self.name, f ) )
        for c in self.changeClientTrackers:
            if c not in self.scenario.getObjectsDict( 'client' ):
                raise Exception( "Client {0} was instructed to change the torrent files in client {1}, but the latter was never declared.".format( self.name, c ) )

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        client.checkSettings(self)
        
        if not self.port:
            raise Exception( "The port parameter is required for host {0}".format( self.name ) )

    def prepare(self):
        """
        Generic preparations for the client, irrespective of executions or hosts.
        """
        client.prepare(self)

    def prepareHost(self, host):
        """
        Client specific preparations on a host, irrespective of execution.

        This usually includes send files to the host, such as binaries.

        Note that the sendToHost and sendToSeedingHost methods of the file objects have not been called, yet.
        This means that any data files are not available.

        @param  host            The host on which to prepare the client.
        """
        client.prepareHost(self, host)
        
        if not self.hasUpdatedTrackers and ( len( self.changeTrackers ) > 0 or len( self.changeClientTrackers ) > 0 ):
            # Figure out the new tracker
            self.hasUpdatedTrackers = True
            newTracker = host.getAddress()
            if not newTracker:
                raise Exception( "Client {0} was instructed to change some torrent files to update their trackers, but host {1} won't give an address for that.".format( self.name, host.name ) )
            newTracker = 'http://{0}:{1}/announce'.format( newTracker, self.port )
            # Grab all executions for clients in our changeClientTrackers list and go over their files, adding them to changeTrackers as needed
            for e in [e for e in self.scenario.getObjects('execution') if e.client.getName() in self.changeClientTrackers]:
                for f in e.files:
                    if not f.metaFile or not os.path.exists( f.metaFile ) or os.path.isdir( f.metaFile ):
                        continue
                    if f.getName() not in self.changeTrackers:
                        self.changeTrackers.append( f.getName() )
            # Update all file objects mentioned in changeTrackers
            for f in self.changeTrackers:
                tmpfd = None
                tmpfobj = None
                tmpFile = None
                tmpSaved = False
                try:
                    tmpfd, tmpFile = tempfile.mkstemp('.torrent')
                    tmpfobj = os.fdopen(tmpfd, 'w')
                    tmpfd = None
                    try:
                        self.tempUpdatedFiles__lock.acquire()
                        if self.isInCleanup():
                            os.remove( tmpFile )
                            tmpFile = None
                            return
                        self.tempUpdatedFiles.append( tmpFile )
                        tmpSaved = True
                    finally:
                        self.tempUpdatedFiles__lock.release()
                    fobj = None
                    try:
                        fobj = open( self.scenario.getObjectsDict( 'file' )[f].metaFile, 'r' )
                        torrentdata = fobj.read( )
                    finally:
                        if fobj:
                            fobj.close()
                    torrentdict = external.bencode.bdecode( torrentdata )
                    if not torrentdict or not 'info' in torrentdict:
                        raise Exception( "Client {0} was instructed to change the torrent file of file {1}, but the metafile of the latter seems not to be a .torrent file." )
                    torrentdict['announce'] = newTracker
                    if 'announce-list' in torrentdict:
                        torrentdict['announce-list'] = [[newTracker]]
                    torrentdata = external.bencode.bencode( torrentdict )
                    tmpfobj.write( torrentdata )
                    tmpfobj.flush()
                finally:
                    if tmpfobj:
                        tmpfobj.close()
                    elif tmpfd is not None:
                        os.close(tmpfd)
                    if tmpFile and not tmpSaved:
                        try:
                            self.tempUpdatedFiles__lock.acquire()
                            if tmpFile not in self.tempUpdatedFiles:
                                os.remove( tmpFile )
                        finally:
                            self.tempUpdatedFiles__lock.release()
                self.scenario.getObjectsDict( 'file' )[f].metaFile = tmpFile

    # That's right, 2 arguments less.
    # pylint: disable-msg=W0221
    def prepareExecution(self, execution):
        """
        Client specific preparations for a specific execution.

        If any scripts for running the client on the host are needed, this is the place to build them.
        Be sure to take self.extraParameters into account, in that case.

        @param  execution           The execution to prepare this client for.
        """
        client.prepareExecution(self, execution, simpleCommandLine="./opentracker -p {0} -P {0}".format( self.port ) )
    # pylint: enable-msg=W0221

    def retrieveLogs(self, execution, localLogDestination):
        """
        Retrieve client specific logs for the given execution.
        
        The logs are to be stored in the directory pointed to by localLogDestination.
        
        @param  execution               The execution for which to retrieve logs.
        @param  localLogDestination     A string that is the path to a local directory in which the logs are to be stored.
        """
        client.retrieveLogs(self, execution, localLogDestination)

    def cleanupHost(self, host, reuseConnection = None):
        """
        Client specific cleanup for a host, irrespective of execution.

        Should also remove the client from the host as far as it wasn't already there.

        @param  host            The host on which to clean up the client.
        @param  reuseConnection If not None, force the use of this connection for command to the host.
        """
        client.cleanupHost(self, host, reuseConnection)

    def cleanup(self):
        """
        Client specific cleanup, irrespective of host or execution.

        The default calls any required cleanup on the sources.
        """
        client.cleanup(self)
        try:
            self.tempUpdatedFiles__lock.acquire()
            for tmpFile in self.tempUpdatedFiles:
                os.remove( tmpFile )
            self.tempUpdatedFiles = []
        finally:
            self.tempUpdatedFiles__lock.release()

    def trafficProtocol(self):
        """
        Returns the protocol on which the client will communicate.

        This value is used for setting up restricted traffic control (TC), if requested.
        Typical values are "TCP", "UDP", etc.

        When a TC module finds a protocol it can't handle explicitly, or '' as a protocol, it will fall back to
        full traffic control, i.e. all traffic between involved hosts.

        If possible, specify this correctly, otherwise leave it '' (default).

        @return The protocol the client uses for communication.
        """
        return client.trafficProtocol(self)

    def trafficInboundPorts(self):
        """
        Returns a list of inbound ports on which all incoming traffic can be controlled.
        
        This list is used to set up traffic control, if requested.

        The list should only be given if it is definite: if dynamic ports can be assigned to the clients it is best
        to just return () to force full traffic control. This also goes if the list can't be given for other reasons.

        The exact notation of ports depends on the value returned by self.trafficProtocol().

        The default implementation just returns [].

        @return A list of all ports on which incoming traffic can come, or [] if no such list can be given.
        """
        return [self.port]

    def trafficOutboundPorts(self):
        """
        Returns a list of outbound ports on which all outgoing traffic can be controlled.

        This list is used to set up traffic control, if requested.

        The list should only be given if it is definite: if dynamic ports can be assigned to the clients it is best
        to just return () to force full traffic control. This also goes if the list can't be given for other reasons.

        The exact notation of ports depends on the value returned by self.trafficProtocol().

        The default implementation just returns [].

        @return A list of all ports from which outgoing traffic can come, or [] if no such list can be given.
        """
        return [self.port]

    def getBinaryLayout(self):
        """
        Return a list of binaries that need to be present on the server.
        
        Add directories to be created as well, have them end with a /.
        
        Return None to handle the uploading or moving yourself.
        
        @return    List of binaries.
        """
        return ['opentracker']
    
    def getSourceLayout(self):
        """
        Return a list of tuples that describe the layout of the source.
        
        Each tuple in the list corresponds to (sourcelocation, binarylocation),
        where the binarylocation is one of the entries returned by getBinaryLayout().
        
        Each entry in getBinaryLayout() that is not directory needs to be present.
        
        Return None to handle the uploading or moving yourself.
        
        @return    The layout of the source.
        """
        return [('opentracker', 'opentracker')]

    def getExtraUploadLayout(self):
        """
        Returns a list of local files that are always uploaded to the remote host.
        
        Each tuple in the list corresponds to (locallocation, remotelocation),
        where the first is the location of the local file and the second is the
        relative location of the file on the remote host (relative to the location
        of the client's directory).
        
        Add directories to be created as well, have their locallocation be '' and 
        have their remotelocation end with a /.
                
        This method is especially useful for wrappers and the like.
        
        Return None to handle the uploading yourself.
        
        @return    The files that are always to be uploaded.
        """
        return None
    
    def isSideService(self):
        """
        Returns whether this client is an extra service needed for scenarios,
        rather than an actual client iself.
        
        Side services are clients such as torrent trackers or HTTP servers that only
        provide files to actually running clients.
        
        If a client is a side service it will be ignored for several purposes, such
        as when determining if all clients have finished yet and when retrieving and
        processing logs.
        
        @return     True iff this client is a side serice.
        """
        return True

    @staticmethod
    def APIVersion():
        return "2.4.0"

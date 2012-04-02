import os
import time

class debuglogger:
    fileObject = None       # The file to be logged to. (combined)
    fileObjects = {}        # The files to be logged to. (separate, indexed by channel number)
    
    separate = False
    combined = True
    
    zerotime = 0
    
    basedir = ''
    
    def __init__(self, basedir = None, separate = False, combined = False):
        self.zerotime = time.time()
        self.fileObjects = {}
        self.basedir = basedir
        self.separate = separate
        self.combined = combined
        if (combined or separate) and basedir == None:
            raise Exception( "Debug logging without basedir" )
        if basedir and not (combined or separate):
            raise Exception( "Debug logging without debug options" )
        if combined:
            self.fileObject = open( os.path.join( self.basedir, 'debug_channels' ), 'a' )

    def log(self, channelnumber, msg):
        """
        Logs the message.

        Sends the message to the file for the channelnumber (separate) and/or the combined logfile (combined).
        Newlines will be added if the message does not end with a newline.

        @param  channelnumber   The number of the channel.
        @param  msg             The message to be logged.
        """
        t = time.time() - self.zerotime
        if msg[-1:] != '\n':
            msg += '\n'
        if self.combined:
            self.fileObject.write( '{1:012.4f} CHANNEL {0}: '.format( channelnumber, float(t) ) + msg )
            self.fileObject.flush()
        if self.separate:
            if channelnumber not in self.fileObjects:
                self.fileObjects[channelnumber] = open( os.path.join( self.basedir, 'debug_channel_{0}'.format( channelnumber ) ), 'a' )
            self.fileObjects[channelnumber].write( '{0:012.4f}: '.format( float(t) ) + msg )
            self.fileObjects[channelnumber].flush()
    
    def closeChannel(self, channelnumber):
        """
        Closes the channel.
        
        @param  channelnumber   The number of the channel.
        """
        self.log( channelnumber, 'CLOSED' )
        if self.separate and channelnumber in self.fileObjects:
            self.fileObjects[channelnumber].close()
            del self.fileObjects[channelnumber]
    
    def cleanup(self):
        if self.combined:
            self.fileObject.close()
        delset = [f for f in self.fileObjects]
        for f in delset:
            self.fileObjects[f].close()
            
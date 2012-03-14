import os
import traceback

class logger:
    fileObject = None       # The file to be logged to. None for stdout
    
    def __init__(self):
        pass

    def log(self, msg, alwaysPrint = False):
        """
        Logs the message.

        The message msg is either sent to stdout (self.fileObject is None) or to the file being logged to.
        Newlines will be added.

        @param  msg             The message to be logged.
        @param  alwaysPrint     Set to True to make sure this message is printed to the screen as well as being logged.
        """
        if self.fileObject is None or alwaysPrint:
            print msg
        if self.fileObject:
            self.fileObject.write( msg + '\n' )

    def logPre(self, msg, alwaysPrint = False):
        """
        Like log, but without extra newlines.

        @param  msg             The message to be logged, which includes any needed newlines.
        @param  alwaysPrint     Set to True to make sure this message is printed to the screen as well as being logged.
        """
        if self.fileObject is None or alwaysPrint:
            print msg,
        if self.fileObject:
            self.fileObject.write( msg )

    def logToFile(self, pathname):
        """
        Redirects all logging to pathname.

        pathname should either point to an existing file, which will be appended, or to a non-existing file that can readily be created.
        Any current log file will be closed first.

        @param  pathname    The pathname to the file to be logged to
        """
        self.closeLogFile()
        if os.path.exists( pathname ) and not os.path.isfile( pathname ):
            raise Exception( 'Logging to "{0}" requested, but that already exists and is not a file' )
        self.fileObject = open( pathname, 'a', 0 )

    def closeLogFile(self):
        """
        Reset the logger to stdout logging.
        """
        if not self.fileObject is None:
            try:
                self.fileObject.close()
            except IOError:
                pass    # Ignore IOError on closing
            self.fileObject = None

    def loggingToFile(self):
        """
        Return whether this logger uses a file to log to.
        
        @return True iff a file is being used for logging.
        """
        return not self.fileObject is None

    def exceptionTraceback(self, alwaysPrint = False):
        """
        Logs the stacktrace of the exception currently being handled.

        This method should be called from a function currently handling an exception (e.g. in an except block).
        When no exception is currently being handled, this function does nothing.

        @param  alwaysPrint     Set to True to make sure this message is printed to the screen as well as being logged.
        """
        self.logPre( traceback.format_exc(), alwaysPrint )
    
    def localTraceback(self, alwaysPrint = False):
        """
        Logs the stacktrace of the current stack (including this call).
        
        This method can be called from a function to have the current calling stack logged.
        Note that this is for debugging purposes only!

        @param  alwaysPrint     Set to True to make sure this message is printed to the screen as well as being logged.
        """
        self.log( "DEBUG TRACEBACK: " )
        for line in traceback.format_stack():
            self.logPre( line, alwaysPrint )

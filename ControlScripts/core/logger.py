import os
import sys
import traceback

class logger:
    fileObject = None       # The file to be logged to. None for stdout
    
    def __init__(self):
        pass

    def log(self, msg):
        """
        Logs the message.

        The message msg is either sent to stdout (self.fileObject is None) or to the file being logged to.
        Newlines will be added.

        @param  msg     The message to be logged.
        """
        if self.fileObject is None:
            print msg
        else:
            self.fileObject.write( msg + '\n' )

    def logPre(self, msg):
        """
        Like log, but without extra newlines.

        @param  msg     The message to be logged, which includes any needed newlines.
        """
        if self.fileObject is None:
            print msg,
        else:
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

    def exceptionTraceback(self):
        """
        Logs the stacktrace of the exception currently being handled.

        This method should be called from a function currently handling an exception (e.g. in an except block).
        When no exception is currently being handled, this function does nothing.
        """
        tb = None
        try:
            _, _, tb = sys.exc_info()
            if not tb is None:
                for line in traceback.format_tb( tb ):
                    self.logPre( line )
        finally:
            tb = None

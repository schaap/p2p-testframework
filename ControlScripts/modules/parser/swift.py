from core.parser import parser

import os

class swift(parser):
    """
    Implementation of the basic swift parser.
    
    This module parses swift logs to create a data file.
    
    Extra parameters:
    - [none]
    
    Raw logs expected:
    - log.log
    
    Parsed log files creates by this module:
    - log.data
    -- relative time (seconds)
    -- % done
    -- upload speed (kB/s)
    -- download speed (kB/s)
    """

    def __init__(self, scenario):
        """
        Initialization of a generic parser object.

        @param  scenario        The ScenarioRunner object this parser object is part of.
        """
        parser.__init__(self, scenario)

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
        parser.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        parser.checkSettings(self)

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        parser.resolveNames(self)

    def parseLogs(self, execution, logDir, outputDir):
        """
        Parse the logs for the current execution.

        Be sure to document in the header of your module which logs you expect to be present and with which filename.

        Subclassers must override this method.

        @param  execution   The execution for which to parse the logs.
        @param  logDir      The path to the directory on the local machine where the logs reside.
        @param  outputDir   The path to the directory on the local machine where the parsed logs are to be stored.
        """
        logfile = os.path.join(logDir, 'log.log')
        datafile = os.path.join(outputDir, 'log.data')
        if not os.path.exists( logfile ) or not os.path.isfile( logfile ):
            raise Exception( "parser:swift expects the file log.log to be available for execution {0} of client {1} on host {2}".format( execution.getNumber(), execution.client.name, execution.host.name ) )
        if os.path.exists( datafile ):
            raise Exception( "parser:swift wants to create log.data, but that already exists for execution {0} of client {1} on host {2}".format( execution.getNumber(), execution.client.name, execution.host.name ) )
        fl = None
        fd = None
        try:
            fl = open( logfile, 'r' )
            fd = open( datafile, 'w' )
            fd.write( "time percent upspeed dlspeed\n0 0 0 0\n" )
            relTime = 0
            up_bytes = 0
            down_bytes = 0
            for line in fl:
                if line[:5] == 'SLEEP':
                    relTime += 1
                elif line[:4] == 'done' or line[:4] == 'DONE':
                    # Split over ' ', then over ',', then over '(', then over ')', and keep it all in one array
                    split = reduce( lambda x,y: x + y.split( ')' ), reduce(lambda x,y: x + y.split( '(' ), reduce(lambda x,y: x + y.split( ',' ), line.split( ' ' ), []), []), [])
                    dlspeed = (int(split[16]) - down_bytes) / 1024.0
                    down_bytes = int(split[16])
                    upspeed = (int(split[10]) - up_bytes) / 1024.0
                    up_bytes = int(split[10])
                                        
                    percent = 0
                    if int(split[3]) > 0:
                        percent = 100.0 * ( float(int(split[1])) / float(int(split[3])) )
                        
                    fd.write( "{0} {1} {2} {3}\n".format( relTime, percent, upspeed, dlspeed ) )
                    relTime += 1
        finally:
            try:
                if fd:
                    fd.close()
            except Exception:
                pass
            try:
                if fl:
                    fl.close()
            except Exception:
                pass

    @staticmethod
    def APIVersion():
        return "2.1.0"

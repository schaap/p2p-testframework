from core.parser import parser

import os
import re

class aria2(parser):
    """
    A parser for aria2 download logs (no upload is assumed).
    
    Extra parameters:
    - [none]
    
    Raw logs expected:
    - log.log
    -- contains the output of aria2 (preferably with a shorter interval than the default 60s) with
        --human-readable=false, --truncate-console-readout=false and only one file in the download
        queue (possibly multiple sources)
    
    Parsed log files created:
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
            raise Exception( "parser:aria2 expects the file log.log to be available for execution {0} of client {1} on host {2}".format( execution.getNumber(), execution.client.name, execution.host.name ) )
        if os.path.exists( datafile ) and not execution.isFake():
            raise Exception( "parser:aria2 wants to create log.data, but that already exists for execution {0} of client {1} on host {2}".format( execution.getNumber(), execution.client.name, execution.host.name ) )
        fl = None
        fd = None
        try:
            fl = open( logfile, 'r' )
            fd = open( datafile, 'w' )
            fd.write( "time percent upspeed dlspeed\n0 0 0 0\n" )
            firstTime = -1
            relTime = -1
            firstDay = ''
            lastRelTime = ''
            
            for line in fl:
                m = re.match( '^ \\*\\*\\* Download Progress Summary as of [^ ]* *[^ ]* *([0-9][0-9]*) *([0-9][0-9]*):([0-9][0-9]*):([0-9][0-9]*) .*$', line )
                if firstTime == -1:
                    if not m:
                        continue
                    firstDay = int(m.group(1))
                    firstTime = int(m.group(4)) + 60 * int(m.group(3)) + 3600 * int(m.group(2))
                    relTime = 1
                    continue
                
                if m:
                    relTime = int(m.group(4)) + 60 * int(m.group(3)) + 3600 * int(m.group(2))
                    if firstDay != int(m.group(1)):
                        relTime += 24 * 3600
                    relTime -= firstTime
                    continue
                
                if re.match( '.*NOTICE - Download complete', line ):
                    if relTime == -1:
                        relTime = lastRelTime + 1
                    fd.write( "{0} 100.0 0 0\n".format( relTime ) )
                    relTime = -1
                
                if relTime == -1:
                    continue
                
                m = re.match( '^\\[\\#1 SIZE:0B/0B CN:[0-9]* SPD:0Bs.*', line )
                if m:
                    fd.write( "{0} 0 0 0\n".format( relTime ) )
                    lastRelTime = relTime
                    relTime = -1
                
                m = re.match( '^\\[\\#1 SIZE:([0-9]*)B/([0-9]*)B\\([0-9]*%\\) CN:[0-9]* SPD:([0-9]*)Bs ETA:.*\\]$', line )
                if m:
                    percentDone = 100.0 * ( float(int(m.group(1))) / float(int(m.group(2))) )
                    downspeed = int(m.group(3)) / 1024.0
                    
                    fd.write( "{0} {1} 0 {2}\n".format( relTime, percentDone, downspeed ) )
                    
                    lastRelTime = relTime
                    relTime = -1
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

    def canReparse(self):
        """
        Return whether this parser can be used to reparse after a run has already been torn down.
        
        This mainly signals that this parser functions within the following constraints:
        - resolveNames is never called
        - host, client and file object are explicitly unavailable
        - Only part of the scenario object is available:
            - scenario.isFake() is available and returns True
            - scenario.name is available and correct
            - scenario.getObjects(...) is available and will return all executions but an empty list otherwise
            - scenario.getObjectsDict(...) is available and will return all executions but an empty dictionary otherwise
            - The executions returned by this scenario are limited as described below
            - The methods are not available during initialization
        - Only part of the static Campaign object is available:
            - Campaign.logger is available as normally and logs to stdout
            - Campaign.which is available as normally
        - Only part of the execution object is available:
            - execution.isFake() is available and returns True
            - execution.getNumber() is available and limited
            - execution.client is available but incomplete
                - execution.client.name is available and reads '__reparse__'
                - execution.client.isSideService() is available
                    - returns True unless any log exists for the execution
            - execution.timeout is available and 0.0 unless the data was saved using processor:savetimeout
            - execution.isSeeder() is available and False unless the data was saved using processor:isSeeder (and this was a seeder)
            - execution.host is available but limited 
                - execution.host.name is available and reads '__reparse__' unless the data was saved using processor:savehostname
        
        @return    True iff this parser can reparse.
        """
        return True

    @staticmethod
    def APIVersion():
        return "2.4.0"

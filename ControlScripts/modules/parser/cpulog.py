from core.parser import parser

import os
import re

class cpulog(parser):
    """
    Parser for the cpu.log file created by having the profile parameter on a client active.
    
    Extra parameters:
    - [none]
    
    Raw logs expected:
    - cpu.log    A cpu log as created by the profiling function. Not being present is not a problem.
    
    Parse log files created:
    - cpu.data
    -- relative time (seconds, float)
    -- % CPU
    -- resident memory size (bytes)
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
    
    fullDatePattern = '^([0-9]*-[0-9]*-[0-9]*) ([0-9]*):([0-9]*):([0-9]*)\\.([0-9]*)$'
    brokenDatePattern = '^([0-9]*-[0-9]*-[0-9]*) ([0-9]*):([0-9]*):([0-9]*)\\.%N$'
    
    def fullDateToSecs(self, m):
        return self.brokenDateToSecs(m) + float(m.group(5)) * 10**(-1 * len(m.group(5))) 

    def brokenDateToSecs(self, m):
        return int(m.group(2)) * 3600 + 60 * int(m.group(3)) + int(m.group(4))

    def parseLogs(self, execution, logDir, outputDir):
        """
        Parse the logs for the current execution.

        Be sure to document in the header of your module which logs you expect to be present and with which filename.

        Subclassers must override this method.

        @param  execution   The execution for which to parse the logs.
        @param  logDir      The path to the directory on the local machine where the logs reside.
        @param  outputDir   The path to the directory on the local machine where the parsed logs are to be stored.
        """
        logfile = os.path.join(logDir, 'cpu.log')
        datafile = os.path.join(outputDir, 'cpu.data')
        if not os.path.exists( logfile ) or not os.path.isfile( logfile ):
            return
        if os.path.exists( datafile ):
            raise Exception( "parser:cpulog wants to create cpu.data, but that already exists for execution {0} of client {1} on host {2}".format( execution.getNumber(), execution.client.name, execution.host.name ) )
        fl = None
        fd = None
        try:
            fl = open( logfile, 'r' )
            fd = open( datafile, 'w' )
            fd.write( "time cpu% mem\n0 0 0\n" )
            startTime = -1
            startDate = None
            datePattern = cpulog.fullDatePattern
            dateFunc = cpulog.fullDateToSecs
            relTime = -1
            for line in fl:
                #12-03-15 12:22:12.386824326
                m = re.match(datePattern, line)
                if startTime == -1:
                    if m:
                        startDate = m.group(1)
                        startTime = dateFunc(self, m)
                    else:
                        # See if we need to fall back to full secs due to unextended ps
                        m = re.match(cpulog.brokenDatePattern, line)
                        if m:
                            datePattern = cpulog.brokenDatePattern
                            dateFunc = cpulog.brokenDateToSecs
                            startDate = m.group(1)
                            startTime = dateFunc(self, m)
                    relTime = 0
                    continue
                if m:
                    relTime = dateFunc(self, m) - startTime
                    if m.group(1) != startDate:
                        relTime += 24 * 3600
                    continue
                m = re.match('^[ \\t]*([0-9]*\\.?[0-9]*)[ \\t]+([0-9]*)$', line)
                if m:
                    fd.write( '{0} {1} {2}\n'.format( relTime, m.group(1), m.group(2) ) )
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
        return "2.4.0"

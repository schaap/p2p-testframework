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
    -- virtual memory size (bytes)
    - peaks.data
    -- total CPU time (seconds, float)
    -- peak resident memory size (bytes)
    -- peak virtual memory size (bytes)
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
        peakfile = os.path.join(outputDir, 'peak.data')
        if not os.path.exists( logfile ) or not os.path.isfile( logfile ):
            return
        if os.path.exists( datafile ) and not execution.isFake():
            raise Exception( "parser:cpulog wants to create cpu.data, but that already exists for execution {0} of client {1} on host {2}".format( execution.getNumber(), execution.client.name, execution.host.name ) )
        if os.path.exists( peakfile ) and not execution.isFake():
            raise Exception( "parser:cpulog wants to create peak.data, but that already exists for execution {0} of client {1} on host {2}".format( execution.getNumber(), execution.client.name, execution.host.name ) )
        fl = None
        fd = None
        fp = None
        try:
            fl = open( logfile, 'r' )
            fd = open( datafile, 'w' )
            fp = open( peakfile, 'w' )
            fd.write( "time cpu% mem\n0 0 0\n" )
            fp.write( "cputime maxmem\n")
            startTime = -1
            startDate = None
            datePattern = cpulog.fullDatePattern
            dateFunc = cpulog.fullDateToSecs
            # pid (comm) state ppid pgrp session tty_nr tpgid flags minflt cminflt majflt cmajflt utime stime cutime cstime
            # %d  (%s)   %c    %d   %d   %d      %d     %d    %d    %d     %d      %d     %d      %d    %d    %d     %d
            statPattern = '^{0}\([^)]*\) +. +{0}{0}{0}{0}{0}{0}{0}{0}{0}{0}({0})({0})({0})({0})'.format( '-?[0-9]* +' )
            relTime = -1
            clockticks = -1
            cpuTime = -1
            utime = 0
            stime = 0
            cutime = 0
            cstime = 0
            cpuTime = 0.0
            prevRelTime = -1.0
            maxcputime = 0.0
            maxmemsize = 0
            maxvirtmemsize = 0
            for line in fl:
                # First line must be clocks ticks per sec (sysconf(_SC_CLK_TCK))
                if clockticks == -1:
                    clockticks = float(line)
                    continue                
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
                # pid (comm) state ppid pgrp session tty_nr tpgid flags minflt cminflt majflt cmajflt utime stime cutime cstime
                # %d  (%s)   %c    %d   %d   %d      %d     %d    %d    %d     %d      %d     %d      %d    %d    %d     %d
                m = re.match(statPattern, line)
                if m:
                    newutime = int(m.group(1))
                    newstime = int(m.group(2))
                    newcutime = int(m.group(3))
                    newcstime = int(m.group(4))
                    cpuTime = (((newutime - utime) + (newstime - stime) + (newcutime - cutime) + (newcstime - cstime)) / (clockticks * (relTime - prevRelTime))) * 100.0
                    utime = newutime
                    stime = newstime
                    cutime = newcutime
                    cstime = newcstime
                    maxcputime = 1.0 * (utime + stime + cutime + cstime) / clockticks
                    # By definition maxcputime will always grow (since the base data is cumulative and will always grow)
                    continue 
                # VSZ, RSS
                m = re.match('^[ \\t]*([0-9]*)[ \\t]+([0-9]*)$', line)
                if m:
                    if int(m.group(2)) > maxmemsize:
                        maxmemsize = int(m.group(2))
                    if int(m.group(1)) > maxvirtmemsize:
                        maxvirtmemsize = int(m.group(1))
                    fd.write( '{0} {1} {2} {3}\n'.format( relTime, cpuTime, m.group(2), m.group(1) ) )
                    prevRelTime = relTime
            fp.write( '{0} {1} {2}\n'.format( maxcputime, maxmemsize, maxvirtmemsize ) )
        finally:
            try:
                if fp:
                    fp.close()
            except Exception:
                pass
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

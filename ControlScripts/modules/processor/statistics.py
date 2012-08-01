# These imports are needed to access the parsing functions (which you're likely to use in parameter parsing),
# the Campaign data object and the processor parent class.
from core.processor import processor

import os
import re

class statistics(processor):
    """
    Statistics calculation for all executions in the execution.
    
    Statistics are separated by leechers and seeders.
    
    Results are skewed if the expected logs only exist for a part of the executions.
    
    Extra parameters:
    - [none]
    
    Raw logs expected:
    - [none]
    
    Parsed logs expected:
    - log.data    (optional, completion and download statistics are 0 without this)
    - peak.data   (optional, memory and CPU statistics are 0 without this)
    
    Processed log files created:
    - stats.leecher
    -- number of leechers
    -- maximum of peak residential memory usage of each leecher (bytes)
    -- average of peak residential memory usage of each leecher (bytes)
    -- average of final cumulative CPU time of each leecher (seconds, float)
    -- number of completed leechers
    -- average of download time of each complete leecher (seconds, float)
    -- average of final completion of each leecher (percentage, float)
    -- maximum of peak virtual memory usage of each leecher (bytes)
    -- average of peak virtual memory usage of each leecher (bytes)
    - stats.seeder
    -- number of seeders
    -- maximum of peak memory usage of each seeder (bytes)
    -- average of peak memory usage of each seeder (bytes)
    -- average of final cumulative CPU time of each seeder (seconds, float)
    -- maximum of peak virtual memory usage of each seeder (bytes)
    -- average of peak virtual memory usage of each seeder (bytes)
    """

    def __init__(self, scenario):
        """
        Initialization of a generic processor object.

        @param  scenario        The ScenarioRunner object this processor object is part of.
        """
        processor.__init__(self, scenario)

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
        processor.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        processor.checkSettings(self)

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        processor.resolveNames(self)

    def processLogs(self, baseDir, outputDir):
        """
        Process the raw and parsed logs found in the base directory.

        The raw logs are found in self.getRawLogDir( execution, baseDir ).
        The parsed logs are found in self.getParsedLogDir( execution, baseDir ).

        Be sure to document in the header of your module which (parsed) logs you expect to be present and with which filename.

        Subclassers must override this method.

        @param  baseDir     The base directory for the logs.
        @param  outputDir   The path to the directory on the local machine where the processed logs are to be stored.
        """
        if os.path.exists( os.path.join( outputDir, 'stats.leecher' ) ) and not self.scenario.isFake():
            raise Exception( 'processor:statistics wanted to create stats.leecher, but it already exists' )
        if os.path.exists( os.path.join( outputDir, 'stats.seeder' ) ) and not self.scenario.isFake():
            raise Exception( 'processor:statistics wanted to create stats.seeder, but it already exists' )
        maxmemleech = 0
        maxmemseed = 0
        totalmemleech = 0
        totalmemseed = 0
        leechcount = 0
        seedcount = 0
        totalCPUleech = 0
        totalCPUseed = 0
        totaldownloadtimeleech = 0
        leechcompletedcount = 0
        totalcompletionleech = 0
        maxvirtmemseed = 0
        totalvirtmemseed = 0
        maxvirtmemleech = 0
        totalvirtmemleech = 0
        for execution in self.scenario.getObjects('execution'):
            if execution.client.isSideService():
                continue
            if not execution.isSeeder():
                if os.path.exists( os.path.join( self.getParsedLogDir( execution, baseDir ), 'log.data' ) ):
                    fObj = None
                    try:
                        fObj = open( os.path.join( self.getParsedLogDir( execution, baseDir ), 'log.data' ), 'r' )
                        downloadTime = -1
                        completion = 0.0
                        for l in fObj.readlines():
                            # Download time is the time of the first line with completion == 100%
                            # Completion is tracked all the time
                            if l[:4] == 'time':
                                # header
                                continue
                            m = re.match( '^([^ ]*) ([^ ]*) .*', l )
                            if not m:
                                # should be last line only
                                continue
                            completion = float(m.group(2))
                            if downloadTime == -1 and completion > 99.999999:
                                downloadTime = float(m.group(1))
                                completion = 100.0
                                break
                    finally:
                        if fObj:
                            fObj.close()
                    totalcompletionleech += completion
                    if downloadTime > -0.5:
                        leechcompletedcount += 1
                        totaldownloadtimeleech += downloadTime
            if os.path.exists( os.path.join( self.getParsedLogDir( execution, baseDir ), 'peak.data' ) ):
                fObj = None
                try:
                    fObj = open( os.path.join( self.getParsedLogDir( execution, baseDir ), 'peak.data' ), 'r' )
                    for l in fObj.readlines():
                        if l[:7] == 'cputime':
                            # header
                            continue
                        m = re.match( '^([^ ]*) ([0-9]*) ([0-9]*)', l )
                        if not m:
                            # should be last line only
                            continue
                        cputime = float(m.group(1))
                        peakmem = int(m.group(2))
                        peakvirtmem = int(m.group(3))
                        if execution.isSeeder():
                            totalCPUseed += cputime
                            totalmemseed += peakmem
                            if peakmem > maxmemseed:
                                maxmemseed = peakmem
                            totalvirtmemseed += peakvirtmem
                            if peakvirtmem > maxvirtmemseed:
                                maxvirtmemseed = peakvirtmem
                        else:
                            totalCPUleech += cputime
                            totalmemleech += peakmem
                            if peakmem > maxmemleech:
                                maxmemleech = peakmem
                            totalvirtmemleech += peakvirtmem
                            if peakvirtmem > maxvirtmemleech:
                                maxvirtmemleech = peakvirtmem
                        # Should be only one line, so be done with it
                        break
                finally:
                    if fObj:
                        fObj.close()
            if execution.isSeeder():
                seedcount += 1
            else:
                leechcount += 1
        
        avgmemleech = 0
        avgcpuleech = 0.0
        avgcompletiontime = 0.0
        avgcompletion = 0.0
        if leechcount > 0:
            avgmemleech = int((float(totalmemleech) / leechcount))
            avgcpuleech = float(totalCPUleech) / leechcount
            avgcompletion = float(totalcompletionleech) / leechcount
            avgvirtmemleech = int(totalvirtmemleech / leechcount)
        if leechcompletedcount > 0:
            avgcompletiontime = float(totaldownloadtimeleech) / leechcompletedcount
        avgmemseed = 0
        avgcpuseed = 0.0
        if seedcount > 0:
            avgmemseed = int(totalmemseed / seedcount)
            avgcpuseed = totalCPUseed / seedcount
            avgvirtmemseed = int(totalvirtmemseed / seedcount)
        
        fObj = None
        try:
            fObj = open( os.path.join( outputDir, 'stats.leecher' ), 'w' )
            fObj.write( '{0} {1} {2} {3} {4} {5} {6} {7} {8}\n'.format( leechcount, maxmemleech, avgmemleech, avgcpuleech, leechcompletedcount, avgcompletiontime, avgcompletion, maxvirtmemleech, avgvirtmemleech ) )
        finally:
            if fObj:
                fObj.close()
        fObj = None
        try:
            fObj = open( os.path.join( outputDir, 'stats.seeder' ), 'w' )
            fObj.write( '{0} {1} {2} {3} {4} {5}\n'.format( seedcount, maxmemseed, avgmemseed, avgcpuseed, maxvirtmemseed, avgvirtmemseed ) )
        finally:
            if fObj:
                fObj.close()

    def canReprocess(self):
        """
        Return whether this processor can be used to reprocess after a run has already been torn down.
        
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
        
        @return    True iff this processor can reprocess.
        """
        return True

    @staticmethod
    def APIVersion():
        return "2.4.0"

#!/usr/bin/python

# System imports
import sys
import os
import time
import re
import shutil
import threading

# P2P Testing Framework imports
from core.campaign import Campaign
from core import logger
from core.parsing import *

# Global API version of the core
APIVersion="2.0.0"

def loadCoreModule( moduleType ):
    """
    Load a single module from the core and return the class.

    This function will check whether the API Version of the loaded module is correct.

    Example:
        executionClass = loadCoreModule( 'execution' )
        executionObject = executionClass( )

    @param  The name of the core module, which is also the name of the class inside that module that will be returned.

    @return The class with the name moduleType in the module core.moduleType
    """
    objectModule = __import__( 'core.' + moduleType, globals(), locals(), moduleType )
    objectClass = getattr( objectModule, moduleType )
    if objectClass.APIVersion() != APIVersion.'--core':
        raise Exception

def loadModule( moduleType, moduleSubType ):
    """
    Load a single module from the extension modules and return the class.

    Modules with sub type '' are redirected to loadCoreModule( moduleType ).
    This function will check several things:
    - whether the moduleType is actually supported;
    - whether the combination with moduleSubType is valid;
    - whether the API Verion of the loaded module is correct.

    Example:
        sshHostClass = loadModule( 'host', 'ssh' )
        sshHostObject = sshHostClass( )

    @param  The module type of the module.
    @param  The module sub type of the module, which is the name of the module itself as well as the name of the class inside that module that will be returned.

    @return The class with the name moduleSubType in the module modules.moduleType.moduleSubType
    """
    if moduleType == 'host' or moduleType == 'client' or moduleType == 'file' or moduleType == 'parser' or moduleType == 'processor' or moduleType == 'viewer':
        if moduleSubType == '':
            raise Exception( "A {0} must have a subtype (line {1}".format( moduleType, Campaign.currentLineNumber ) )
    elif moduleType == 'execution':
        if moduleSubType != '':
            raise Exception( "A {0} can never have a subtype (line {1}".format( moduleType, Campaign.currentLineNumber ) )
    else:
        raise Exception( "Unknown module type {0} on line {1}".format( moduleType, Campaign.currentLineNumber ) )
    if moduleSubType = '':
        return loadCoreModule( moduleType )
    else:
        objectModule = __import__( 'modules.' + moduleType + '.' + moduleSubType, globals(), locals(), moduleSubType )
        objectClass = getattr( objectModule, moduleSubType )
        if objectClass.APIVersion() != APIVersion:
            if objectClass.APIVersion() == APIVersion.'--core':
                raise Exception( "Module modules.{0}.{1} has not correctly overridden the APIVersion function. This is required for correctly functioning modules.".format( moduleType, moduleSubType ) )
            raise Exception( "Module modules.{0}.{1} was made for API version {2}, which is different from the core (version {3})".format( moduleType, moduleSubType, objectClass.APIVersion(), APIVersion ) )

class BusyExecutionThread(threading.Thread):
    """A small extension for Thread that can be tested for the run method currently being active."""
    busy = False
    raisedException = None
    execution = None
    cleanup = False
    def __init__(self, execution):
        self.execution = execution
        Thread.__init__(self)

    def doTask(self):
        """Be sure to override this to implement the actual task."""
        raise Exception( "Not implemented!" )

    def run(self):
        self.busy = True
        try:
            self.doTask()
        except Exception exc:
            self.raisedException = exc
            logger.log( "Exception while running task in class {3} for execution with client {0} on host {1}: {2}".format( self.execution.client.name, self.execution.host.name, exc.__str__(), self.__class__.__name__ ) )
            logger.exceptionTraceback()
        finally:
            self.busy = False

    def isBusy(self):
        """True if the run method has been invoked and not ended yet."""
        return self.busy

    def cleanup(self):
        """Cleans up the thread's execution, which is just setting self.cleanup by default."""
        self.cleanup = True
    
    def getException(self):
        return self.raisedException

    def __str__(self):
        return "Task thread type {2} for execution with client {0} on host {1}".format( self.execution.client.name, self.execution.host.name, self.__class__.__name__ );

class ClientRunner(BusyThread):
    """Simple runner for client.start()"""
    def doTask(self):
        self.execution.client.start( self.execution.host )

    def cleanup(self):
        if self.execution.client.isRunning( self.execution.host ):
            self.execution.client.kill( self.execution.host )

class ClientKiller(BusyThread):
    """Simple runner for client.kill()"""
    def doTask(self):
        if self.execution.client.isRunning( self.execution.host ):
            self.execution.client.kill( self.execution.host )

class LogProcessor(BusyThread):
    """Simple runner for client.retrieveLogs() and execution.runParsers()."""
    execdir = ''
    def __init__(self, execution, execdir):
        self.execdir = execdir
        BusyThread.__init__(self, execution)

    def doTask(self):
        self.execution.client.retrieveLogs( self.execution.host, os.path.join( self.execdir, 'logs' ) )
        if self.cleanup:
            return
        self.execution.runParsers( os.path.join( self.execdir, 'logs' ), os.path.join( self.execdir, 'parsedLogs' ) )

class ScenarioRunner:
    """
    Scenario runner class that will initialize a complete scenario and run it.
    """

    name = ''               # Name of the scenario
    files = []              # List of files that make up the scenario description
    timelimit = 0           # The time in seconds the scenario may at most be running
    doParallel = True       # Whether the scenario should be made sequential
    resultsDir = ''         # The directory where the results of this scenario will be placed

    campaign = None         # The campaignRunner object this scenario is part of

    objects = {}            # A dictionary from all module types to dictionaries of those objects by name
    threads = []            # Threads that do simple tasks, such as running a client. All these have the cleanup method and the isBusy method.

    def __init__(self, scenarioName, scenarioFiles, scenarioTime, scenarioParallel, campaign):
        """
        Sets up the scenario object and checks some sanity.

        @param  scenarioName        The name of the scenario.
        @param  scenarioFiles       A list of paths to files that combine into the scenario file.
        @param  scenarioTime        The time in seconds the scenario may last at most.
        @param  scenarioParallel    False iff the scenario should be run with clients being started sequentially.
        @param  campaign            The Campaign Runner this scenario is part of.
        """
        if scenarioName == '':
            raise Exception( "Scenario started on line {0} has no name parameter".format( Campaign.currentLineNumber ) )
        if len( scenarioFiles ) == 0:
            raise Exception( "Scenario {0} does not specify and files that describe the scenario".format( scenarioName ) )
        self.name = scenarioName
        self.files = scenarioFiles
        self.timelimit = scenarioTime
        self.doParallel = scenarioParallel
        self.campaign = campaign
        self.resultsDir = os.path.join( campaign.campaignResultsDir, 'scenarios', scenarioName )

    def getObjects(self, moduleType):
        """
        Returns a list of objects of type moduleType as placed in self.objects.

        This is literally self.getObjectsDict().values().
        
        @param  moduleType      The type of objects requested.

        @return A list with the objects, or [] if there are no objects.
        """
        return self.getObjectsDict(moduleType).values()

    def getObjectsDict(self, moduleType):
        """
        Returns a dictionary of objects of type moduleType as placed in self.objects.

        @param  moduleType      The type of objects requested.

        @return A dictionary with the objects, or {} if there are no objects.
        """
        if moduleType in self.objects and len(self.objects[moduleType]):
            return self.objects[moduleType]
        return {}

    def read(self):
        """
        Read the scenario files, parse them and set up the scenario accordingly.
        """
        # Read all the scenario files and take them together
        scenarioLines = []
        for f in self.files:
            fObj = open( f, 'r' )
            scenarioLines.append( '# {0}'.format( f ) )
            for line in fObj:
                scenarioLines.append( line )
            fObj.close()

        # Write the scenario file to the results dir
        fObj = open( os.path.join( self.resultsDir, 'scenarioFile' ), 'w' )
        for l in scenarioLines:
            fObj.write( l )
        fObj.close()

        # Parse scenario file
        obj = None
        for Campaign.currentLineNumber in range( 0, len( scenarioLines ) ):
            line = scenarioLines[Campaign.currentLineNumber]
            # Filter comments and empty lines
            if line == '' or re.match( '^\s*#', line ) is not None:
                continue
            print "Parsing " + line
            if isSectionHeader( line ):
                # Create the object and have it parse the settings
                if obj is not None:
                    obj.checkSettings()
                    self.objects[obj.moduleType][obj.name] = obj
                objectLine = Campaign.currentLineNumber
                objectClass = loadModule( getModuleType( getSectionName( line ) ), getSubModuleType( getSectionName( line ) )
                obj = objectClass()
            else:
                if obj is None:
                    raise Exception( "No parameters expected before any object headers. Line {0}.".format( Campaign.currentLineNumber ) )
                parameterName = getParameterName( line )
                parameterValue = getParameterValue( line )
                obj.parseSetting( parameterName, parameterValue )
        if obj is None:
            raise Exception( "No objects found in scenario {0}".format( self.name ) )
        obj.checkSettings()
        self.objects[obj.moduleType][obj.name] = obj

        # Check sanity
        if len( self.getObjects('execution') ) == 0:
            raise Exception( "No executions found in scenario {0}".format( self.name ) )

    def fallbackWarning(self, host, direction):
        """Log a warning that the host has to fall back to full traffic control in the given direction."""
        directionstring = ''
        if direction != '':
            directionstring = direction + ' '
        logger.log( "Host {0} could not initiate restricted {1}traffic control, falling back to unrestricted traffic control.".format( host.name, directionstring ) )
        self.unrestrictedWarning( host, direction )

    def unrestrictedTCWarning(self, host, direction):
        """Log a warning about using unrestricted traffic control on the given host in the given direction."""
        if direction != '':
            direction = direction + ' '
        logger.log( "Warning: using unrestricted traffic control for {1}traffic on host {0}. If the commanding host (i.e. your terminal) is also part of the nodes you configured for testing, then this WILL cause trouble.".format( host.name, direction ) )

    def setup(self, testRun = False):
        """
        Setup everything for the actual execution of the test.

        @param  testRun     True iff actual preparation should not be done for most objects, because we're just testing.
        """
        print "Preparing all objects for execution"
        if not os.path.exists( os.path.join( self.resultsDir, 'executions' ) ):
            os.makedirs( os.path.join( self.resultsDir, 'executions' ) )
        # All hosts that are actually used in executions
        executionHosts = set([execution.host for execution in self.objects['execution']])
        # Prepare all hosts
        for host in executionHosts:
            host.prepare()
        # Executions may by now have been altered by the host.prepare() calls, so rebuild the host list
        # All executions must refer to prepared hosts, which means that any host.prepare() that alters the executions
        # must take precautions to ensure this.
        executionHosts = set([execution.host for execution in self.objects['execution']])
        # Prepare all clients
        for client in self.getObjects('client'):
            client.prepare()
        # Prepare TC and clients
        for host in executionHosts:
            # Build traffic control instructions for each host, based on how the clients can be controlled
            if host.tc != '':
                # Sanity check: refuse to enable traffic control on the commanding host
                if host.getSubnet() == '127.0.0.1' or host.getSubnet() == 'localhost':
                    raise Exception( "Refusing to enable traffic control on local host {0}. This would be a very, very bad idea. Please only use traffic control when commanding a number of remote hosts not including the commanding host.".format( host.name ) )
                # Figure out how to set up TC for this host
                tcinbound = 1       # 0 = none, 1 = restricted, 2 = full
                tcoutbound = 1      # 0 = none, 1 = restricted, 2 = full
                host.tcProtocol = ''
                if host.tcDown == '' and host.tcLoss == 0 and host.tcCorruption == 0 and host.tcDuplication == 0:
                    # Download speed not restricted and no loss, corruption or duplication: no inbound TC
                    tcinbound = 0
                if host.tcUp = '' and host.tcDelay == 0:
                    # Upload speed not restricted and no delay is introduced: no outbound TC
                    tcoutbound = 0
                inboundrestrictedlist = []
                outboundrestrictedlist = []
                for client in hostClients:
                    # Go over all clients to see how they think they should be restricted. Aggregate data to be saved in the host.
                    if host.tcProtocol == '':
                        host.tcProtocol = client.trafficProtocol()
                    elif host.tcProtocol != client.trafficProtocol():
                        # TC at this point only supports restricted control on one protocol
                        logger.log( "Restricted traffic control using multiple protocols is not supported. Falling back to unrestricted traffic control on host {0}.".format( host.name ) )
                        tcinbound *= 2
                        tcoutbound *= 2
                    if tcinbound == 1:
                        if len(client.trafficInboundPorts()) == 0:
                            logger.log( "Client {0} can't have restricted inbound traffic control. Falling back to unrestricted inbound traffic control on host {1}.".format( client.name, host.name ) )
                            tcinbound = 2
                        inboundrestrictedlist += client.trafficInboundPorts()
                    if tcoutbound == 1:
                        if len(client.trafficOutboundPorts()) == 0:
                            logger.log( "Client {0} can't have restricted outbound traffic control. Falling back to unrestricted outbound traffic control on host {1}.".format( client.name, host.name ) )
                            tcoutbound = 2
                        outboundrestrictedlist += client.trafficOutboundPorts()
                    if tcoutbound != 1 and tcinbound != 1:
                        break
                if tcinbound == 2:
                    self.unrestrictedTCWarning( host, 'inbound' )
                    host.tcInboundPortList = -1
                else:
                    host.tcInboundPortList = list(set(inboundrestrictedlist))
                if tcoutbound == 2:
                    self.unrestrictedTCWarning( host, 'outbound' )
                    host.tcOutboundPortList = -1
                else:
                    host.tcOutboundPortList = list(set(outboundrestrictedlist))
                # Load TC module and check with that module to see what is possible
                tcClass = loadModule( 'tc', host.tc )
                host.tcObj = tcObj
                if not host.tcObj.check(host):
                    # Try to fall back to full control and see if that works
                    if host.tcInboundPortList != -1 and host.tcInboundPortList != []:
                        oldTcInboundPortList = host.tcInboundPortList
                        host.tcInboundPortList = -1
                        if host.tcObj.check(host):
                            self.fallbackWarning( host, 'inbound' )
                        else:
                            if host.tcOutboundPortList != -1 and host.tcOutboundPortList != []:
                                host.tcInboundPortList = oldTcInboundPortList
                                host.tcOutboundPortList = -1
                                if host.tcObj.check(host):
                                    self.fallbackWarning( host, 'outbound' )
                                else:
                                    host.tcInboundPortList = -1
                                    if host.tcObj.check(host):
                                        self.fallbackWarning( host, '' )
                                    else:
                                        raise Exception( "Host {0} could not initiate restricted or unrestricted traffic control, but traffic control was requested.".format( host.name ) )
                            else:
                                raise Exception( "Host {0} could not initiate restricted or unrestricted inbound traffic control, but traffic control was requested.".format( host.name ) )
                    elif host.tcOutboundPortList != -1 and host.tcOutboundPortList != []:
                        host.tcOutboundPortList = -1
                        if host.tcObj.check(host):
                            self.fallbackWarning( host, 'outbound' )
                        else:
                            raise Exception( "Host {0} could not initiate restricted or unrestricted outbound traffic control, but traffic control was requested.".format( host.name ) )
                    else:
                        raise Exception( "Host {0} could not initiate the requested traffic control.".format( host.name ) )
            # If we've reached this point, then we have a succeeding tc.check(), unless no TC was requested at all

            # If we're not just testing: prepare clients for this host
            if not testRun:
                for client in host.clients:
                    client.prepareHost( host )

        # If we're not just testing: prepare files
        if not testRun:
            for host in executionHosts:
                # Send all files to the host that do not have this host as seeder
                for file in host.files:
                    file.sendToHost( host )
                # Send all files to the host that have this host as seeder
                for file in host.seedingFiles:
                    file.sendToHost( host )
                    file.sendToSeedingHost( host )

    def executeRun(self):
        """
        Executes the actual run.

        This method assumes everything is set to go.
        Clients will be prepared for execution, TC will be applied and the clients then run.
        """
        # Prepare all clients for execution
        for execution in self.objects['execution']:
            execution.client.prepareExecution( execution )
        # All hosts that are part of an execution
        executionHosts = set([execution.host for execution in self.objects['execution']])
        # Apply traffic control to all hosts requiring it
        for host in executionHosts for
            if host.tc == '':
                continue
            host.tcObj.install( host, list(set([host.getSubnet() for host in executionHosts])) )
        # Start all clients
        execThreads = []
        for execution in self.objects['execution']:
            execThreads.append( ClientRunner( execution ) )
        self.threads += execThreads
        print "Starting all clients"
        if self.parallel:
            for thread in execThreads:
                thread.start()
        else:
            for thread in execThreads:
                thread.run()
        print "Running..."

        # While the time limit has not passed yet, keep checking whether all clients have ended, sleeping up to 5 seconds in between each check (note that a check takes time as well)
        endTime = time.time() + self.timelimit
        sleepTime = min( 5, self.timelimit )
        while sleepTime > 0:
            time.sleep( sleepTime )
            for execution in self.objects['execution']:
                if execution.client.isRunning():
                    break
            else:
                print "All client have finished before time is up"
                break
            sleepTime = max( 0, min( 5, endTime - time.time() ) )

        print "All clients should be done now, checking and killing if needed."
        
        killThreads = []
        for execution in self.objects['execution']:
            killThreads.append( ClientKiller( execution ) )
        self.threads += killThreads
        if self.parallel:
            for thread in killThreads:
                thread.start()
            for thread in killThreads:
                if thread.isAlive():
                    thread.join( 60 )
                    if thread.isAlive():
                        logger.log( "Warning! A client wasn't killed after 60 seconds: {0} on host {1}".format( thread.execution.client.name, thread.execution.host.name ) )
        else:
            for thread in killThreads:
                thread.run()

        print "Removing all traffic control from hosts."
        for host in executionHosts for
            if host.tc == '':
                continue
            host.tcObj.remove( host )

    def parseLogs(self):
        """
        Retrieve and parse logs.

        This function should be called after all executions have finished.
        """
        logThreads = []
        for execution in self.objects['execution']:
            execdir = os.path.join( self.resultsDir, 'executions', 'exec_{0}'.format( execution.name ) )
            makedirs( os.path.join( execdir, 'logs' ) )
            makedirs( os.path.join( execdir, 'parsedLogs' ) )
            logThreads = LogProcessor( execution )
        self.threads += logThreads
        print "Retrieving logs and parsing them"
        if self.parallel:
            for thread in logThreads:
                thread.start()
            for thread in logThreads:
                if thread.isAlive():
                    thread.join( 60 )
                    if thread.isAlive():
                        logger.log( "Warning! A log processor wasn't done after 60 seconds: {0}".format( thread.execution.client.name ) )
        else:
            for thread in logThreads:
                thread.run()
        for thread in logThreads:
            if thread.isAlive() or thread.getException() is not None:
                raise Exception( "One or more log processors failed." )

    def cleanup(self):
        """
        Clean up all objects in the scenario.

        The order of cleanup is:
        - threads
        - files
        - clients on hosts
        - clients
        - traffic control on hosts
        - hosts
        """
        print "Cleaning up threads"
        for thread in self.threads:
            if thread.isBusy():
                try:
                    thread.cleanup()
                    if thread.isAlive():
                        thread.join( 60 )
                        if thread.isAlive():
                            logger.log( "Warning! A thread is still running after waiting 60 seconds: {0}".format( thread.__str__() ) )
                except Exception as exc:
                    logger.log( "Exception while cleaning up thread, will be discarded: {0}".format( exc.__str__() ) )
                    logger.exceptionTraceback()
        print "Cleaning up files"
        for file in self.getObjects('file'):
            try:
                file.cleanup()
            except Exception as exc:
                logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                logger.exceptionTraceback()
        print "Cleaning up clients"
        for host in self.getObjects('host'):
            for client in host.clients:
                try:
                    client.cleanupHost( host )
                except Exception as exc:
                    logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                    logger.exceptionTraceback()
        for client in self.getObjects('client'):
            try:
                client.cleanup()
            except Exception as exc:
                logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                logger.exceptionTraceback()
        print "Cleaning up hosts"
        for host in self.getObjects('host'):
            if host.tc != '' and host.tcObj:
                try:
                    host.tcObj.remove( host )
                except Exception as exc:
                    logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                    logger.exceptionTraceback()
            try:
                host.cleanup()
            except Exception as exc:
                logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                logger.exceptionTraceback()

    def processLogs(self):
        """
        Process the logs and run viewers.

        This should be called after everything has been done, inclusing parsing and cleanup.
        """
        print "Processing logs"
        processeddir = os.path.join( self.resultsDir, 'processed' )
        makedirs( processeddir )
        for processor in self.getObjects('processor'):
            processor.processLogs( os.path.join( self.resultsDir, 'executions' ), processeddir )
        print "Running viewers"
        viewerdir = os.path.join( self.resultsDir, 'views' )
        makedirs( viewerdir )
        for viewer in self.getObjects('viewer'):
            viewer.createView( processeddir, viewerdir )

    def test(self):
        """
        Do a check run of the scenario, to find out whether everything is in order.
        """
        caughtExc = None
        try:
            self.setup( True )
        finally:
            self.cleanup()
            # We're just testing, ditch the results as well
            try:
                shutil.rmtree( self.resultsDir )
            except Exception as exc:
                logger.log( "Exception while removing results from test, will be discared: {0}".format( exc.__str__() ) )
                logger.exceptionTraceback()
        print "Scenario {0} checked".format( self.name )

    def run(self):
        """
        Do an actual run of the scenario.
        """
        try:
            self.setup()
            self.executeRun()
            self.parseLogs()
        finally:
            self.cleanup()
        self.processLogs()
        print "Scenario {0} completed".format( self.name )

class CampaignRunner:
    """
    Campaign runner class both for initialization of the full environment as well as for each campaign individually.
    The static parts of this class deal with global initialization (global as in: static attributes of the Campaign class).
    """
    ######
    # Dynamic part of the class: actual campaign and running of it
    ######

    campaignFile = ''       # Path to the campaign file for this campaign
    campaignID = ''         # The campaign ID, which is really just a timestamp
    campaignName = ''       # The full campaign name, which will be used as the name for the directory the results end up in
    campaignResultsDir = '' # The path to the results directory for this campaign

    def __init__(self, campaign_file):
        """
        Sets up the campaign object.

        @param  campaign_file   The path to the campaign file.
        """
        self.campaignFile = campaign_file
        self.campaignID = time.strftime( "%Y.%m.%d-%H.%M.%S", time.localtime() )
        self.campaignName = re.sub( '\.[^/]*$', '', os.path.basename( campaign_file ) ) + '-' + self.campaignID
        self.campaignResultsDir = os.path.join( Campaign.resultsDir, self.campaignName )
        if os.path.exists( self.campaignResultsDir ):
            raise Exception( 'Campaign results directory "{0}" already exists'.format( self.campaignResultsDir ) )
        os.makedirs( self.campaignResultsDir )
        if not os.path.exists( self.campaignResultsDir ):
            raise Exception( 'Could not create campaign results directory "{0}"'.format( self.campaignResultsDir ) )

        logger.logToFile( os.path.join( self.campaignResultsDir, 'err.log' ) )

    def readCampaignFile(self):
        """
        Reads and parses the campaign file.
        """
        print "Reading campaign from campaign file {0}".format( self.campaignFile )
        print "Results for this campaign will be stored in {0}".format( self.campaignResultsDir )

        fileObj = open( self.campaignFile, 'r' )
        Campaign.currentLineNumber = 1
        scenarioLine = 0
        scenarioName = ''
        scenarioFiles = []
        scenarioLine = Campaign.currentLineNumber
        scenarioTimeLimit = 300
        scenarioParallel = True
        for line in fileObj:
            print "Parsing {0}".format(line)
            line = line[:-1]
            if line == '':
                Campaign.currentLineNumber += 1
                continue
            elif isSectionHeader( line ):
                # New section, extract section name and check that it's a scenario
                sectionName = getSectionName( line )
                if sectionName != 'scenario':
                    raise Exception( "Unexpected section name {0} in campaign file on line {1}. Only scenario sections are allowed in campaign files.".format( sectionName, Campaign.currentLineNumber ) )
                # New scenario, so check sanity of the old one, but not for the scenario before the first scenario
                if scenarioLine != 0:
                    self.scenarios.append( ScenarioRunner( scenarioName, scenarioFiles, scenarioTimeLimit, scenarioParallel, self ) )
                # New scenario is OK, let's initialize for the next one
                scenarioName = ''
                scenarioFiles = []
                scenarioLine = Campaign.currentLineNumber
                scenarioTimeLimit = 300
                scenarioParallel = True
            else:
                # Not a section, so should be a parameter
                parameterName = getParameterName( line )
                parameterValue = getParameterValue( line )
                if scenarioLine == 0:
                    raise Exception( "Did not expect parameters before any section header (line {0})".format( Campaign.currentLineNumber ) )
                if parameterName == 'name':
                    # The name of the scenario: check uniqueness, validity as directory name and create directory
                    if scenarioName != '':
                        raise Exception( "Scenario started on line {0} has two names: {1} and {2}; only one name is allowed (line {3})".format( scenarioLine, scenarioName, parameterValue, Campaign.currentLineNumber ) )
                    if not isValidName( parameterValue ):
                        raise Exception( '"{0}" is not a valid scenario name on line {1}'.format( parameterValue, Campaign.currentLineNumber ) )
                    if os.path.exists( os.path.join( self.campaignResultsDir, 'scenarios', parameterValue ) ):
                        raise Exception( 'Scenario {0} already exists (line {1})'.format( parameterValue, Campaign.currentLineNumber ) )
                    os.makedirs( os.path.join( self.campaignResultsDir, 'scenarios', parameterValue ) )
                    if not os.path.exists( os.path.join( self.campaignResultsDir, 'scenarios', parameterValue ) ):
                        raise Exception( 'Could not create result directory "{0}" for scenario {1}'.format( os.path.join( self.campaignResultsDir, 'scenarios', parameterValue ), parameterValue )
                    scenarioName = parameterValue
                elif parameterName == 'file':
                    # A file for the scenario: check existence and add to files array
                    file = os.path.join( Campaign.testEnvDir, parameterValue )
                    if not os.path.exists( file ) or not os.path.isfile( file ):
                        raise Exception( 'Scenario file "{0}" does not exist or is not a file (line {1})'.format( file, Campaign.currentLineNumber ) )
                    scenarioFiles.append( file )
                elif parameterName == 'parallel':
                    # disable parallel handling of clients if it gives trouble
                    scenarioParallel = ( parameterValue != 'no' )
                elif parameterName == 'timelimit' or parameterName == 'timeout':
                    # I keep calling it timeout, so I'm guessing that is also/more natural
                    # Time limit for the execution of a scenario, in seconds
                    if not isPositiveInt( parameterValue, True ):
                        raise Exception( 'The time limit for the scenario defined on line {0} should be given in second, which is a positive non-zero integever value, unlike "{1}" (line {2})'.format( scenarioLine, parameterValue, Campaign.currentLineNumber ) )
                    scenarioTimeLimit = int(parameterValue)
                else:
                    raise Exception( 'Unsupported parameter "{0}" found on line {1}'.format( parameterName, Campaign.currentLineNumber ) )
            Campaign.currentLineNumber += 1
        self.scenarios.append( ScenarioRunner( scenarioName, scenarioFiles, scenarioTimeLimit, scenarioParallel, self ) )

        for scenario in self.scenarios:
            scenario.read()
        if Campaign.doCheckRun:
            for scenario in self.scenarios:
                scenario.test()
        if Campaign.doRealRun:
            for scenario in self.scenarios:
                scenario.run()

    ######
    # Static part of the class: initialization and option parsing
    ######

    doCheckRun = True       # True iff a checking run is to be done
    doRealRun = True        # True iff a real run is to be done

    logger = None           # The global logging object, always available through Campaign.logger

    currentCampaign = None  # The campaign object currently running

    @staticmethod
    def usage():
        """
        Prints a simple message informing the user how to use this script.
        """
        print """
P2P Testing Framework campaign runner
Run a test campaign, scenario by scenario.
Usage:
    {0} [--check|--nocheck] your_campaign_file
--check will check the correctness of the settings as well as try and see if what was requested is possible.
The checks made by --check may not be all-inclusive, but should eliminate a lot of possible errors during runs, andhence a lot of frustration when setting up tests.
--nocheck will skip the checking run and only do an actual run (useful for already tested setups)
When neither --check nor --nocheck is given, a test run is conducted first, followed by an actual run.
""".format( sys.argv[0] )

    @staticmethod
    def load(argv):
        """
        Interprets the arguments and starts of each campaign.

        @param  argv        The argument list as pass on by sys.argv
        """
        global logger

        campaign_files = []
        options = []
        # Split arguments in options and campaign files
        for arg in argv[1:]:
            if arg[:2] == '--':
                options.append( arg )
            else:
                campaign_files.append( arg )
        # Need at least 1 campaign file
        if len( campaign_files ) == 0:
            return CampaignRunner.usage( "No campaign file found." )

        # Check and process options
        for opt in options:
            if opt == '--check':
                if Campaign.doCheckRun and Campaign.doRealRun:
                    Campaign.doRealRun = False
                else:
                    return CampaignRunner.usage( "Only one of --check and --nocheck may be specified" )
            elif opt == '--nocheck':
                if Campaign.doCheckRun and Campaign.doRealRun:
                    Campaign.doCheckRun = False
                else:
                    return CampaignRunner.usage( "Only one of --check and --nocheck may be specified" )
            else:
                return CampaignRunner.usage( "Unknown option: {0}".format( opt ) )

        # Check for existence of campaign files
        for campaign_file in campaign_files:
            if not os.path.exists( campaign_file ) or not os.path.isfile( campaign_file ):
                return CampaignRunner.usage( "Campaign file {0} not found or not a file".format( campaign_file ) )

        # Initialize the global environment
        Campaign.testEnvDir = os.path.abspath(os.path.join( os.path.dirname(argv[0]), '..' ))
        if not os.getenv('RESULTS_DIR', '') == '':
            if not os.path.exists( os.getenv('RESULTS_DIR') ) or not os.path.isdir( os.getenv('RESULTS_DIR') ):
                print 'RESULTS_DIR is set to {0}, but that is not a valid directory. Please specify a valid directory in RESULTS_DIR or set it to ""'.format( os.getenv('RESULTS_DIR') )
                return
            Campaign.resultsDir = os.getenv('RESULTS_DIR')
        else:
            Campaign.resultsDir = os.path.join( Campaign.testEnvDir, 'Results' )
            if not os.path.exists( Campaign.resultsDir ):
                os.makedirs( Campaign.resultsDir )
                if not os.path.exists( Campaign.resultsDir ):
                    print 'Could not create results directory {0}'.format( Campaign.resultsDir )
                    return
            elif not os.path.isdir( Campaign.resultsDir ):
                print 'Results directory {0} already exists but is not a directory.'.format( Campaign.resultsDir )
                return

        Campaign.loadModule = staticmethod(loadModule)
        Campaign.loadCoreModule = staticmethod(loadCoreModule)

        Campaign.logger = logger.logger()
        logger = Campaign.logger

        # Let's run those campaign files
        for campaign_file in campaign_files:
            try:
                Campaign.currentCampaign = CampaignRunner(campaign_file)
                Campaign.currentCampaign.readCampaignFile()
            except Exception as exc:
                logger.log( exc.__str__() )
                logger.exceptionTraceback()
                if logger.loggingToFile():
                    logger.closeLogFile()
                    logger.log( exc.__str__() )
                    logger.exceptionTraceback()

if __name__ == "__main__":
    CampaignRunner.load(sys.argv)

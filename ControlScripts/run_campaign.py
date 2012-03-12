#!/usr/bin/python

#
# Future options
# - workload types (currently: all at once; allow timeout before starting client, make timeouts configurable using pluggable models)
# -- timeout added
#


# System imports
import sys
import os
import time
import shutil
import threading
import re

# P2P Testing Framework imports
from core.campaign import Campaign
from core.parsing import isSectionHeader, getModuleType, getSectionName, getModuleSubType, getParameterName, getParameterValue, isPositiveInt, isValidName
import core.debuglogger

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
    if objectClass.APIVersion() != APIVersion + '-core':
        raise Exception( "The running core is version {0}, but core module {2} is written for version {1}. This is a very clear signal for a broken translation which will hence break.".format( APIVersion, objectClass.APIVersion(), moduleType ) )
    return objectClass

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
    if moduleType == 'host' or moduleType == 'client' or moduleType == 'file' or moduleType == 'parser' or moduleType == 'processor' or moduleType == 'viewer' or moduleType == 'tc' or moduleType == 'builder' or moduleType =='source' or moduleType == 'workload':
        if moduleSubType == '':
            raise Exception( "A {0} must have a subtype (line {1}".format( moduleType, Campaign.currentLineNumber ) )
    elif moduleType == 'execution':
        if moduleSubType != '':
            raise Exception( "A {0} can never have a subtype (line {1}".format( moduleType, Campaign.currentLineNumber ) )
    else:
        raise Exception( "Unknown module type {0} on line {1}".format( moduleType, Campaign.currentLineNumber ) )
    if moduleSubType == '':
        return loadCoreModule( moduleType )
    else:
        objectModule = __import__( 'modules.' + moduleType + '.' + moduleSubType, globals(), locals(), moduleSubType )
        objectClass = getattr( objectModule, moduleSubType )
        if objectClass.APIVersion() != APIVersion:
            if objectClass.APIVersion() == APIVersion + '--core':
                raise Exception( "Module modules.{0}.{1} has not correctly overridden the APIVersion function. This is required for correctly functioning modules.".format( moduleType, moduleSubType ) )
            raise Exception( "Module modules.{0}.{1} was made for API version {2}, which is different from the core (version {3})".format( moduleType, moduleSubType, objectClass.APIVersion(), APIVersion ) )
        return objectClass

class BusyExecutionThread(threading.Thread):
    """A small extension for Thread that can be tested for the run method currently being active."""
    busy = False
    raisedException = None
    execution = None
    inCleanup = False
    def __init__(self, execution):
        self.execution = execution
        threading.Thread.__init__(self)

    def doTask(self):
        """Be sure to override this to implement the actual task."""
        raise Exception( "Not implemented!" )

    def run(self):
        self.busy = True
        try:
            self.doTask()
        except Exception as exc:
            self.raisedException = exc
            Campaign.logger.log( "Exception while running task in class {3} for execution with client {0} on host {1}: {2}".format( self.execution.client.name, self.execution.host.name, exc.__str__(), self.__class__.__name__ ) )
            Campaign.logger.exceptionTraceback()
        finally:
            self.busy = False

    def isBusy(self):
        """True if the run method has been invoked and not ended yet."""
        return self.busy

    def cleanup(self):
        """Cleans up the thread's execution, which is just setting self.cleanup by default."""
        self.inCleanup = True
    
    def getException(self):
        return self.raisedException

    def __str__(self):
        return "Task thread type {2} for execution with client {0} on host {1}".format( self.execution.client.name, self.execution.host.name, self.__class__.__name__ )

class ClientRunner(BusyExecutionThread):
    """Simple runner for client.start()"""
    def doTask(self):
        startTime = time.time() + self.execution.timeout
        diffTime = startTime - time.time()
        while diffTime > 0:
            if diffTime > 5:
                time.sleep(5)
            else:
                time.sleep(diffTime)
            if self.inCleanup:
                return
            diffTime = startTime - time.time()
        if self.inCleanup:
            return
        self.execution.client.start( self.execution )
    
    def prepareConnection(self):
        self.execution.createRunnerConnection( )

    def cleanup(self):
        if self.execution.client.isRunning( self.execution ):
            self.execution.client.kill( self.execution )

class ClientKiller(BusyExecutionThread):
    """Simple runner for client.kill()"""
    def doTask(self):
        if self.execution.client.isRunning( self.execution ):
            self.execution.client.kill( self.execution )

class LogProcessor(BusyExecutionThread):
    """Simple runner for client.retrieveLogs() and execution.runParsers()."""
    execdir = ''
    def __init__(self, execution, execdir):
        self.execdir = execdir
        BusyExecutionThread.__init__(self, execution)

    def doTask(self):
        self.execution.client.retrieveLogs( self.execution, os.path.join( self.execdir, 'logs' ) )
        if self.inCleanup:
            return
        self.execution.runParsers( os.path.join( self.execdir, 'logs' ), os.path.join( self.execdir, 'parsedLogs' ) )

class ScenarioRunner:
    """
    Scenario runner class that will initialize a complete scenario and run it.
    """

    name = ''               # Name of the scenario
    files = None            # List of files that make up the scenario description
    timelimit = 0           # The time in seconds the scenario may at most be running
    doParallel = True       # Whether the scenario should be made sequential
    resultsDir = ''         # The directory where the results of this scenario will be placed

    campaign = None         # The campaignRunner object this scenario is part of

    objects = None          # A dictionary from all module types to dictionaries of those objects by name
    threads = None          # Threads that do simple tasks, such as running a client. All these have the cleanup method and the isBusy method.

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
        self.objects = {}
        self.threads = []

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
        print "Reading scenario setup for scenario {0}".format( self.name )
        # Read all the scenario files and take them together
        scenarioLines = []
        for f in self.files:
            fObj = open( f, 'r' )
            scenarioLines.append( '# {0}'.format( f ) )
            for line in fObj:
                line = line.strip()
                scenarioLines.append( line )
            fObj.close()

        # Write the scenario file to the results dir
        fObj = open( os.path.join( self.resultsDir, 'scenarioFile' ), 'w' )
        for l in scenarioLines:
            fObj.write( l + "\n" )
        fObj.close()

        # Parse scenario file
        obj = None
        for Campaign.currentLineNumber in range( 0, len( scenarioLines ) ):
            line = scenarioLines[Campaign.currentLineNumber]
            # Filter comments and empty lines
            if line == '' or re.match( '^\s*#', line ) is not None:
                print "Parsing " + line
                continue
            if isSectionHeader( line ):
                # Create the object and have it parse the settings
                if obj is not None:
                    obj.checkSettings()
                    if not obj.getModuleType() in self.objects:
                        self.objects[obj.getModuleType()] = {}
                    elif obj.getName() in self.objects[obj.getModuleType()]:
                        raise Exception( "Element {0} in objects list of type {1} already present. Maybe you used the same name twice?".format( obj.getName(), obj.getModuleType() ) ) 
                    self.objects[obj.getModuleType()][obj.getName()] = obj
                print "Parsing " + line
                objectClass = loadModule( getModuleType( getSectionName( line ) ), getModuleSubType( getSectionName( line ) ) )
                obj = objectClass( self )
            else:
                print "Parsing " + line
                if obj is None:
                    raise Exception( "No parameters expected before any object headers. Line {0}.".format( Campaign.currentLineNumber ) )
                parameterName = getParameterName( line )
                parameterValue = getParameterValue( line )
                obj.parseSetting( parameterName, parameterValue )
        if obj is None:
            raise Exception( "No objects found in scenario {0}".format( self.name ) )
        obj.checkSettings()
        if not obj.getModuleType() in self.objects:
            self.objects[obj.getModuleType()] = {}
        elif obj.getName() in self.objects[obj.getModuleType()]:
            raise Exception( "Element {0} in objects list of type {1} already present. Maybe you used the same name twice?".format( obj.getName(), obj.getModuleType() ) ) 
        self.objects[obj.getModuleType()][obj.getName()] = obj

        # Check sanity
        if len( self.getObjects('execution') ) == 0:
            raise Exception( "No executions found in scenario {0}".format( self.name ) )
        for resolveObjects in ['execution', 'client', 'file', 'host', 'parser', 'processor', 'viewer', 'workload']:
            for obj in self.getObjects(resolveObjects):
                obj.resolveNames()
        
        # Fill in extra cross-object data
        for execution in self.getObjects('execution'):
            if execution.client not in execution.host.clients:
                execution.host.clients.append( execution.client )
            if execution.file not in execution.host.files:
                execution.host.files.append( execution.file )
            if execution.isSeeder() and execution.file not in execution.host.seedingFiles:
                execution.host.seedingFiles.append( execution.file )

    def fallbackWarning(self, host, direction):
        """Log a warning that the host has to fall back to full traffic control in the given direction."""
        directionstring = ''
        if direction != '':
            directionstring = direction + ' '
        Campaign.logger.log( "Host {0} could not initiate restricted {1}traffic control, falling back to unrestricted traffic control.".format( host.name, directionstring ) )
        self.unrestrictedTCWarning( host, direction )

    def unrestrictedTCWarning(self, host, direction):
        """Log a warning about using unrestricted traffic control on the given host in the given direction."""
        if direction != '':
            direction = direction + ' '
        Campaign.logger.log( "Warning: using unrestricted traffic control for {1}traffic on host {0}. If the commanding host (i.e. your terminal) is also part of the nodes you configured for testing, then this WILL cause trouble.".format( host.name, direction ) )

    def setup(self, testRun = False):
        """
        Setup everything for the actual execution of the test.

        @param  testRun     True iff actual preparation should not be done for most objects, because we're just testing.
        """
        print "Preparing all objects for execution"
        if not os.path.exists( os.path.join( self.resultsDir, 'executions' ) ):
            os.makedirs( os.path.join( self.resultsDir, 'executions' ) )
        # All hosts that are actually used in executions
        executionHosts = set([execution.host for execution in self.getObjects('execution')])
        # Prepare all hosts
        for host in executionHosts:
            host.prepare()
        # Executions may by now have been altered by the host.prepare() calls, so rebuild the host list
        # All executions must refer to prepared hosts, which means that any host.prepare() that alters the executions
        # must take precautions to ensure this.
        executionHosts = set([execution.host for execution in self.getObjects('execution')])
        # Now change all those executions as needed to get the right workloads
        for workload in self.getObjects('workload'):
            workload.applyWorkload()
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
                if host.tcUp == '' and host.tcDelay == 0:
                    # Upload speed not restricted and no delay is introduced: no outbound TC
                    tcoutbound = 0
                inboundrestrictedlist = []
                outboundrestrictedlist = []
                for client in host.clients:
                    # Go over all clients to see how they think they should be restricted. Aggregate data to be saved in the host.
                    if host.tcProtocol == '':
                        host.tcProtocol = client.trafficProtocol()
                    elif host.tcProtocol != client.trafficProtocol():
                        # TC at this point only supports restricted control on one protocol
                        Campaign.logger.log( "Restricted traffic control using multiple protocols is not supported. Falling back to unrestricted traffic control on host {0}.".format( host.name ) )
                        tcinbound *= 2
                        tcoutbound *= 2
                    if tcinbound == 1:
                        if len(client.trafficInboundPorts()) == 0:
                            Campaign.logger.log( "Client {0} can't have restricted inbound traffic control. Falling back to unrestricted inbound traffic control on host {1}.".format( client.name, host.name ) )
                            tcinbound = 2
                        inboundrestrictedlist += client.trafficInboundPorts()
                    if tcoutbound == 1:
                        if len(client.trafficOutboundPorts()) == 0:
                            Campaign.logger.log( "Client {0} can't have restricted outbound traffic control. Falling back to unrestricted outbound traffic control on host {1}.".format( client.name, host.name ) )
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
                host.tcObj = tcClass()
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
                for f in host.files:
                    f.sendToHost( host )
                # Send all files to the host that have this host as seeder
                for f in host.seedingFiles:
                    f.sendToSeedingHost( host )

    def executeRun(self):
        """
        Executes the actual run.

        This method assumes everything is set to go.
        Clients will be prepared for execution, TC will be applied and the clients then run.
        """
        # Prepare all clients for execution
        for execution in self.getObjects('execution'):
            execution.client.prepareExecution( execution )
        # All hosts that are part of an execution
        executionHosts = set([execution.host for execution in self.getObjects('execution')])
        # Apply traffic control to all hosts requiring it
        for host in executionHosts:
            if host.tc == '':
                continue
            host.tcObj.install( host, list(set([host.getSubnet() for host in executionHosts])) )
        # Start all clients
        execThreads = []
        for execution in self.getObjects('execution'):
            execThreads.append( ClientRunner( execution ) )
        self.threads += execThreads
        print "Starting all clients"
        if self.doParallel:
            # First prepare all connections (has to be done consecutively in order to allow throttling to prevent overloading)
            for thread in execThreads:
                thread.prepareConnection()
            # Then do the actual running as parallel as possible
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
            for execution in self.getObjects('execution'):
                if execution.client.isRunning(execution):
                    break
            else:
                print "All client have finished before time is up"
                break
            sleepTime = max( 0, min( 5, endTime - time.time() ) )

        print "All clients should be done now, checking and killing if needed."
        
        killThreads = []
        for execution in self.getObjects('execution'):
            killThreads.append( ClientKiller( execution ) )
        self.threads += killThreads
        if self.doParallel:
            for thread in killThreads:
                thread.start()
            for thread in killThreads:
                if thread.isAlive():
                    thread.join( 60 )
                    if thread.isAlive():
                        Campaign.logger.log( "Warning! A client wasn't killed after 60 seconds: {0} on host {1}".format( thread.execution.client.name, thread.execution.host.name ) )
        else:
            for thread in killThreads:
                thread.run()

        print "Removing all traffic control from hosts."
        for host in executionHosts:
            if host.tc == '':
                continue
            host.tcObj.remove( host )

    def parseLogs(self):
        """
        Retrieve and parse logs.

        This function should be called after all executions have finished.
        """
        logThreads = []
        for execution in self.getObjects('execution'):
            execdir = os.path.join( self.resultsDir, 'executions', 'exec_{0}'.format( execution.getNumber() ) )
            os.makedirs( os.path.join( execdir, 'logs' ) )
            os.makedirs( os.path.join( execdir, 'parsedLogs' ) )
            logThreads.append( LogProcessor( execution, execdir ) )
        self.threads += logThreads
        print "Retrieving logs and parsing them"
        if self.doParallel:
            for thread in logThreads:
                thread.start()
            for thread in logThreads:
                if thread.isAlive():
                    thread.join( 60 )
                    if thread.isAlive():
                        Campaign.logger.log( "Warning! A log processor wasn't done after 60 seconds: {0}".format( thread.execution.client.name ) )
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
                            Campaign.logger.log( "Warning! A thread is still running after waiting 60 seconds: {0}".format( thread.__str__() ) )
                except Exception as exc:
                    Campaign.logger.log( "Exception while cleaning up thread, will be discarded: {0}".format( exc.__str__() ) )
                    Campaign.logger.exceptionTraceback()
        cleanupConnections = {}
        print "Setting up cleanup connections"
        for h in self.getObjects( 'host' ):
            try:
                cleanupConnections[h] = h.setupNewConnection()
                if cleanupConnections[h] is None:
                    cleanupConnections[h] = True
            except Exception as exc:
                Campaign.logger.log( "Could not create cleanup connection for host {0}, exception will be discarded.\nWarning! This might mean the cleanup will partially fail.\n{1}".format( h.name, exc.__str__() ) )
                Campaign.logger.exceptionTraceback()
                cleanupConnections[h] = True
        print "Checking and killing clients"
        for e in self.getObjects('execution'):
            try:
                if e.client.hasStarted( e ) and e.client.isRunning( e, cleanupConnections[e.host] ):
                    e.client.kill( e, cleanupConnections[e.host] )
            except Exception as exc:
                Campaign.logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                Campaign.logger.exceptionTraceback()
        print "Cleaning up files"
        for f in self.getObjects('file'):
            try:
                f.cleanup()
            except Exception as exc:
                Campaign.logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                Campaign.logger.exceptionTraceback()
        print "Cleaning up clients"
        for host in self.getObjects('host'):
            for client in host.clients:
                try:
                    client.cleanupHost( host, cleanupConnections[host] )
                except Exception as exc:
                    Campaign.logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                    Campaign.logger.exceptionTraceback()
        for client in self.getObjects('client'):
            try:
                client.cleanup()
            except Exception as exc:
                Campaign.logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                Campaign.logger.exceptionTraceback()
        print "Cleaning up hosts"
        for host in self.getObjects('host'):
            if host.tc != '' and host.tcObj:
                try:
                    host.tcObj.remove( host, cleanupConnections[host] )
                except Exception as exc:
                    Campaign.logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                    Campaign.logger.exceptionTraceback()
            try:
                host.cleanup( cleanupConnections[host] )
            except Exception as exc:
                Campaign.logger.log( "Exception while cleaning up, will be discarded: {0}".format( exc.__str__() ) )
                Campaign.logger.exceptionTraceback()

    def processLogs(self):
        """
        Process the logs and run viewers.

        This should be called after everything has been done, inclusing parsing and cleanup.
        """
        print "Processing logs"
        processeddir = os.path.join( self.resultsDir, 'processed' )
        os.makedirs( processeddir )
        for processor in self.getObjects('processor'):
            processor.processLogs( os.path.join( self.resultsDir, 'executions' ), processeddir )
        print "Running viewers"
        viewerdir = os.path.join( self.resultsDir, 'views' )
        os.makedirs( viewerdir )
        for viewer in self.getObjects('viewer'):
            viewer.createView( processeddir, viewerdir )

    def test(self):
        """
        Do a check run of the scenario, to find out whether everything is in order.
        """
        Campaign.logger.log( "=== Checking scenario {0} ===".format( self.name ), True )
        try:
            self.setup( True )
        finally:
            self.cleanup()
            # We're just testing, ditch the results as well
            try:
                shutil.rmtree( self.resultsDir )
            except Exception as exc:
                Campaign.logger.log( "Exception while removing results from test, will be discarded: {0}".format( exc.__str__() ) )
                Campaign.logger.exceptionTraceback()
        Campaign.logger.log( "=== Scenario {0} checked ===".format( self.name ), True )
        print ""

    def run(self):
        """
        Do an actual run of the scenario.
        """
        Campaign.logger.log( "=== Running scenario {0} ===".format( self.name ), True )
        try:
            self.setup()
            self.executeRun()
            self.parseLogs()
        finally:
            self.cleanup()
        self.processLogs()
        Campaign.logger.log( "=== Scenario {0} completed ===".format( self.name ), True )
        print ""

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
    
    deadlyScenarios = True  # False if a failing scenario should not stop the rest of the campaign
    
    scenarios = []          # List of scenarios to run

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

        Campaign.logger.logToFile( os.path.join( self.campaignResultsDir, 'err.log' ) )

    def readCampaignFile(self, justScenario = None):
        """
        Reads and parses the campaign file.
        
        @param  justScenario    A list of scenario names to run, or None to run all scenarios.
        """
        print "Reading campaign from campaign file {0}".format( self.campaignFile )
        print "Results for this campaign will be stored in {0}".format( self.campaignResultsDir )

        fileObj = open( self.campaignFile, 'r' )
        Campaign.currentLineNumber = 1
        scenarioName = ''
        scenarioFiles = []
        scenarioLine = 0
        scenarioTimeLimit = 300
        scenarioParallel = True
        for line in fileObj:
            line = line.strip()
            print "Parsing {0}".format(line)
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
                        raise Exception( 'Could not create result directory "{0}" for scenario {1}'.format( os.path.join( self.campaignResultsDir, 'scenarios', parameterValue ), parameterValue ) )
                    scenarioName = parameterValue
                elif parameterName == 'file':
                    # A file for the scenario: check existence and add to files array
                    f = os.path.join( Campaign.testEnvDir, parameterValue )
                    if not os.path.exists( f ) or not os.path.isfile( f ):
                        raise Exception( 'Scenario file "{0}" does not exist or is not a file (line {1})'.format( f, Campaign.currentLineNumber ) )
                    scenarioFiles.append( f )
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
        
        if justScenario:
            for scName in justScenario:
                for sc in self.scenarios:
                    if sc.name == scName:
                        break
                else:
                    return CampaignRunner.usage("Scenario {0} is to be run, but does not exist.".format(scName))
        else:
            justScenario = [scenario.name for scenario in self.scenarios]
        
        print ""
        print "Reading scenarios"
        print ""
        
        badScenarios = []

        if self.deadlyScenarios:
            for scenario in self.scenarios:
                if scenario.name in justScenario:
                    scenario.read()
        else:
            for scenario in self.scenarios:
                if scenario.name in justScenario:
                    try:
                        scenario.read()
                    except Exception as exc:
                        if isinstance( exc, KeyboardInterrupt ):
                            raise exc
                        else:
                            Campaign.logger.log( "{0}: {1}".format( exc.__class__.__name__, exc.__str__() ), True )
                            Campaign.logger.exceptionTraceback( True )
                            Campaign.logger.log( "Scenarios are not deadly. Marking this scenario as bad and continuing.", True )
                            badScenarios.append( scenario.name )

        if Campaign.doCheckRun:
            print ""
            print "Checking scenarios"
            print ""
            if self.deadlyScenarios:
                for scenario in self.scenarios:
                    if scenario.name in justScenario:
                        scenario.test()
            else:
                for scenario in self.scenarios:
                    if scenario.name in justScenario and scenario.name not in badScenarios:
                        try:
                            scenario.test()
                        except Exception as exc:
                            if isinstance( exc, KeyboardInterrupt ):
                                raise exc
                            else:
                                Campaign.logger.log( "{0}: {1}".format( exc.__class__.__name__, exc.__str__() ), True )
                                Campaign.logger.exceptionTraceback( True )
                                Campaign.logger.log( "Scenarios are not deadly. Marking this scenario as bad and continuing.", True )
                                badScenarios.append( scenario.name )
        if Campaign.doRealRun:
            print ""
            print "Running scenarios"
            print ""
            if self.deadlyScenarios:
                for scenario in self.scenarios:
                    if scenario.name in justScenario:
                        scenario.run()
            else:
                for scenario in self.scenarios:
                    if scenario.name in justScenario and scenario.name not in badScenarios:
                        try:
                            scenario.run()
                        except Exception as exc:
                            if isinstance( exc, KeyboardInterrupt ):
                                raise exc
                            else:
                                Campaign.logger.log( "{0}: {1}".format( exc.__class__.__name__, exc.__str__() ), True )
                                Campaign.logger.exceptionTraceback( True )
                                Campaign.logger.log( "Scenarios are not deadly. Marking this scenario as bad and continuing.", True )
                                badScenarios.append( scenario.name )
        
        print "Campaign finished"
        print "Results for this campaign will be stored in {0}".format( self.campaignResultsDir )

    ######
    # Static part of the class: initialization and option parsing
    ######

    @staticmethod
    def usage( msg = None ):
        """
        Prints a simple message informing the user how to use this script.

        @param  msg     If given, the message is printed first.
        """
        if msg:
            print msg
        print """
P2P Testing Framework campaign runner
Run a test campaign, scenario by scenario.
Usage:
    {0} [--check|--nocheck] [--scenario=name [...]] [--debuglog[=basedir]] [--debugseparate] [--debugboth] [--deadly] your_campaign_file

--check will check the correctness of the settings as well as try and see if what was requested is possible.
The checks made by --check may not be all-inclusive, but should eliminate a lot of possible errors during runs, and hence a lot of frustration when setting up tests.
--nocheck will skip the checking run and only do an actual run (useful for already tested setups).
When neither --check nor --nocheck is given, an actual run is done.

--scenario=name will only run the named scenario; --scenario= can be given multiple times for a list of scenarios.

--debuglog[=basedir] will turn on channel debug logging, which logs every outgoing and incoming communication over channels to hosts.
Providing a basedir will use that directory as a base directory for the logs instead of the campaign's result directory.
The normal debugging log is a combined log of all channels that will be written to debug_channels, no separate logs will be made.
--debugseparate turns off the combined log and instead creates a separate log file for each channel. Note that this may result in many files!
--debugboth does both the combined and the separate logging.
Debug options are read from left to right; the last basedir is chosen. E.g. --debugseparate --debuglog=. --debugboth --debuglog will set, in order,
[separate, not combined, default dir], [not separate, combined, .], [separate, combined, .], [not separate, combined, .].

--deadly specified that a single failing scenario will stop the complete campaign. Normally the next scenario will just be started.
""".format( sys.argv[0] )

    @staticmethod
    def load(argv):
        """
        Interprets the arguments and starts of each campaign.

        @param  argv        The argument list as pass on by sys.argv
        """
        campaign_files = []
        options = []
        justScenario = None
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
        doDebug = False
        doDebugSeparate = False
        doDebugCombined = True
        deadlyScenarios = False
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
            elif opt[:11] == '--scenario=':
                if justScenario:
                    justScenario.append( opt[11:] )
                else:
                    justScenario = [opt[11:]]
            elif opt == '--debuglog':
                if doDebug == False:
                    doDebug = True
                doDebugCombined = True
                doDebugSeparate = False
            elif opt == '--debugseparate':
                if doDebug == False:
                    doDebug = True
                doDebugSeparate = True
                doDebugCombined = False
            elif opt == '--debugboth':
                if doDebug == False:
                    doDebug = True
                doDebugSeparate = True
            elif opt[:11] == '--debuglog=':
                doDebug = opt[11:]
            elif opt == '--deadly':
                deadlyScenarios = True
            else:
                return CampaignRunner.usage( "Unknown option: {0}".format( opt ) )
        
        # Set default if neither --check nor --nocheck was given
        if Campaign.doCheckRun and Campaign.doRealRun:
            Campaign.doCheckRun = False

        # Check for existence of campaign files
        for campaign_file in campaign_files:
            if not os.path.exists( campaign_file ) or not os.path.isfile( campaign_file ):
                return CampaignRunner.usage( "Campaign file {0} not found or not a file".format( campaign_file ) )

        # Initialize the global environment
        Campaign.testEnvDir = os.path.abspath(os.path.join( os.path.dirname(argv[0]), '..' ))
        if os.getenv('RESULTS_DIR', '') != '':
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

        # Let's run those campaign files
        for campaign_file in campaign_files:
            try:
                Campaign.currentCampaign = CampaignRunner(campaign_file)
                if doDebug == True:
                    Campaign.debuglogger = core.debuglogger.debuglogger( Campaign.getCurrentCampaign().campaignResultsDir, doDebugSeparate, doDebugCombined )
                elif doDebug != False:
                    os.makedirs( os.path.join( doDebug, Campaign.getCurrentCampaign().campaignName ) )
                    Campaign.debuglogger = core.debuglogger.debuglogger( os.path.join( doDebug, Campaign.getCurrentCampaign().campaignName ), doDebugSeparate, doDebugCombined )
                Campaign.getCurrentCampaign().deadlyScenarios = deadlyScenarios
                Campaign.getCurrentCampaign().readCampaignFile(justScenario)
            except Exception as exc:
                Campaign.logger.log( "{0}: {1}".format( exc.__class__.__name__, exc.__str__() ), True )
                Campaign.logger.exceptionTraceback( True )
            finally:
                Campaign.debuglogger.cleanup()

if __name__ == "__main__":
    CampaignRunner.load(sys.argv)

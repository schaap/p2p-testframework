#!/usr/bin/python

from run_campaign import loadModule
from core.parsing import isPositiveInt, getParameterName, getParameterValue
import os
import traceback
import sys

if __name__ != "__main__":
    raise Exception( "Do not import" )

leechers = True
seeders = True
dirNames = []
parserNames = []
processorNames = []
viewerNames = []
lastObject = None

class NameOptions:
    name = ''
    args = []
    def __init__(self, name):
        self.name = name
        self.args = []

# Parse arguments
for arg in sys.argv[1:]:
    if arg == '--leechers':
        if not leechers:
            raise Exception( "Only one of --leechers and --seeders allowed" )
        seeders = False
    elif arg == '--seeders':
        if not seeders:
            raise Exception( "Only one of --leechers and --seeders allowed" )
        leechers = False
    elif arg[:9] == '--parser=':
        lastObject = NameOptions( arg[9:] )
        parserNames.append( lastObject )
    elif arg[:12] == '--processor=':
        lastObject = NameOptions( arg[12:] )
        processorNames.append( lastObject )
    elif arg[:9] == '--viewer=':
        lastObject = NameOptions( arg[9:] )
        viewerNames.append( lastObject )
    elif arg[:6] == '--arg=':
        if not lastObject:
            raise Exception( "Given --arg before an object (--parser, --processor or --viewer)." )
        lastObject.args.append( arg[6:] )
    elif arg == '--help':
        print """
reparse.py [options] [directory [directory [...]]

reparses existing scenario results
Arguments:
    --leechers        Only reparse leechers
    --seeders         Only reparse seeders
    --parser=name     Use parser:name for parsing
    --processor=name  Use processor:name to process the scenario
    --viewer=name     Use viewer:name to view the scenario
    --arg=argument    Add argument as an argument to the last declared object
    --help            This text and exit

Arguments to objects have the same syntax as in normal scenario declaration files.
Example:
    reparse.py --seeders --parser=cpulog --processor=gnuplot --arg=script=TestSpecs/processors/simple_cpu_plot --viewer=htmlcollection /path/to/results/scenarios/scenario_1 /path/to/results/scenarios/scenario_2
"""
        sys.exit()
    elif arg[:2] == '--':
        raise Exception( "Unknown argument: {0}. Try --help.".format( arg ) )
    else:
        dirNames.append( arg )

# Fake classes
class FakeScenario:
    executions = []
    executionDict = {}
    name = ''
    def __init__(self, name):
        self.executions = []
        self.executionDict = {}
        self.name = name
    def getObjects(self, name):
        if name != 'execution':
            return []
        return self.executions
    def getObjectsDict(self, name):
        if name != 'execution':
            return {}
        return self.executionDict
    def addExecution(self, execution):
        self.executions.append( execution )
        self.executionDict[execution.getNumber()] = execution
    def isFake(self):
        return True

class FakeHost:
    name = '__reparse__'
    def __init__(self):
        pass

class FakeClient:
    name = '__reparse__'
    sideservice = False
    def __init__(self, sideservice):
        self.sideservice = sideservice
    def isSideService(self):
        return self.sideservice
    
class FakeExecution:
    n = -1
    client = None
    host = None
    seeder = False
    timeout = 0.0
    def __init__(self, n, basedir):
        self.n = n
        sideservice = len( os.listdir( os.path.join( basedir, 'executions', 'exec_{0}'.format( n ), 'logs' ) ) ) == 0
        self.client = FakeClient(sideservice)
        self.host = FakeHost()
        if os.path.exists( os.path.join( basedir, 'processed', 'timeout_{0}'.format( n ) ) ):
            fObj_ = None
            try:
                fObj_ = open( os.path.join( basedir, 'processed', 'timeout_{0}'.format( n ) ), 'r' )
                self.timeout = float(fObj_.read())
            except Exception:
                self.timeout = 0.0
            finally:
                if fObj_:
                    fObj_.close()
        if os.path.exists( os.path.join( basedir, 'processed', 'isSeeder_{0}'.format( n ) ) ):
            fObj_ = None
            try:
                fObj_ = open( os.path.join( basedir, 'processed', 'isSeeder_{0}'.format( n ) ), 'r' )
                self.seeder = ( fObj_.read() == 'YES' )
            except Exception:
                self.seeder = False
            finally:
                if fObj_:
                    fObj_.close()
        if os.path.exists( os.path.join( basedir, 'processed', 'hostname_{0}'.format( n ) ) ):
            fObj_ = None
            try:
                fObj_ = open( os.path.join( basedir, 'processed', 'hostname_{0}'.format( n ) ), 'r' )
                self.host.name = fObj_.read()
            except Exception:
                self.host.name = '__reparse__'
            finally:
                if fObj_:
                    fObj_.close() 
    def getNumber(self):
        return self.n
    def isSeeder(self):
        return self.seeder
    def isFake(self):
        return True

# Go over all directories
seenDirNames = {}
for dirName in dirNames:
    if dirName in seenDirNames:
        print "Warning! Directory {0} already seen, skipping.".format( dirName )
        continue
    seenDirNames[dirName] = True
    if not ( os.path.exists( dirName ) and os.path.isdir( dirName ) ):
        print "Warning! Directory {0} seems not to exist, skipping.".format( dirName )
        continue
    execDir = os.path.join( dirName, 'executions' )
    processedDir = os.path.join( dirName, 'processed' )
    viewDir = os.path.join( dirName, 'views' )
    if not ( os.path.exists( execDir ) and os.path.isdir( dirName ) and os.path.exists( processedDir ) and os.path.isdir( processedDir ) and os.path.exists( viewDir ) and os.path.isdir( viewDir ) ):
        print "Warning! Directory {0} seems not to be a scenario directory, skipping.".format( dirName )
        continue

    scenarioObject = FakeScenario(os.path.basename(dirName))
    
    # Load all the parsers
    parserObjects = []
    for parser in parserNames:
        parserClass = loadModule( 'parser', parser.name )
        parserObject = parserClass( scenarioObject )
        if not parserObject.canReparse():
            raise Exception( "Parser {0} can't be used to reparse (canReparse() returns False).".format( parser.name ) )
        for arg in parser.args:
            parameterName = getParameterName( arg )
            parameterValue = getParameterValue( arg )
            parserObject.parseSetting( parameterName, parameterValue )
        parserObjects.append(parserObject)

    # Load all the processors
    processorObjects = []
    for processor in processorNames:
        processorClass = loadModule( 'processor', processor.name )
        processorObject = processorClass( scenarioObject )
        if not processorObject.canReprocess():
            raise Exception( "Processor {0} can't be used to reprocess (canReprocess() returns False).".format( processor.name ) )
        for arg in processor.args:
            parameterName = getParameterName( arg )
            parameterValue = getParameterValue( arg )
            processorObject.parseSetting( parameterName, parameterValue )
        processorObject.checkSettings()
        processorObjects.append( processorObject )
    
    # Load all the viewers
    viewerObjects = []
    for viewer in viewerNames:
        viewerClass = loadModule( 'viewer', viewer.name )
        viewerObject = viewerClass( scenarioObject )
        if not viewerObject.canReview():
            raise Exception( "Viewer {0} can't be used to review (canReview() returns False).".format( viewer.name ) )
        for arg in viewer.args:
            parameterName = getParameterName( arg )
            parameterValue = getParameterValue( arg )
            viewerObject.parseSettings( parameterName, parameterValue )
        viewerObject.checkSettings()
        viewerObjects.append( viewerObject )
    
    executionNumbers = []
    extraExecutionNumbers = []
    if not ( leechers and seeders ):
        for f in os.listdir( processedDir ):
            if f[:9] == 'isSeeder_':
                if not isPositiveInt( f[9:] ):
                    print "Warning! '{0}' is not a valid execution number in the seeder data of directory {1}.".format( f[9:], dirName )
                    executionNumbers = []
                    break
                fObj = open( os.path.join( processedDir, f ), 'r' )
                if not fObj:
                    print "Warning! Can't open {0}.".format( os.path.join( processedDir, f ) )
                    executionNumbers = []
                    break
                data = fObj.read()
                fObj.close()
                if data != 'NO' and data != 'YES':
                    print "Warning! Expected 'YES' or 'NO' in {0}, but found '{1}'.".format( os.path.join( processedDir, f ), data )
                    executionNumbers = []
                    break
                if int(f[9:]) in executionNumbers:
                    print "Warning! Execution number {0} was already found. This is not sane.".format( f[9:] )
                    executionNumbers = []
                    break
                if data == 'NO':
                    if leechers:
                        executionNumbers.append( int(f[9:]) )
                    else:
                        extraExecutionNumbers.append( int(f[9:]) )
                else:
                    if seeders:
                        executionNumbers.append( int(f[9:]) )
                    else:
                        extraExecutionNumbers.append( int(f[9:]) )
        for e in executionNumbers:
            if not os.path.exists( os.path.join( execDir, 'exec_{0}'.format( e ) ) ):
                print "Warning! Execution {0} was found in the seeder data of directory {1}, but seems not to be an execution of that scenario.".format( e, dirName )
                executionNumbers = []
                break
        for e in extraExecutionNumbers:
            if not os.path.exists( os.path.join( execDir, 'exec_{0}'.format( e ) ) ):
                print "Warning! Execution {0} was found in the seeder data of directory {1}, but seems not to be an execution of that scenario.".format( e, dirName )
                executionNumbers = []
                break
        if len(executionNumbers) == 0:
            print "Warning! --seeders or --leechers was specified, but the seeder data of directory {0} could not be read correctly, skipping.".format( dirName )
            continue
    else:
        for d in os.listdir( execDir ):
            if d[:5] != 'exec_':
                print "Warning! Unexpected child of executions directory of directory {0}: '{1}'.".format( d, dirName )
                executionNumbers = []
                break
            if not isPositiveInt( d[5:] ):
                print "Warning! '{0}' is not a valid execution number of directory {1}.".format( d[5:], dirName )
                executionNumbers = []
                break
            if int( d[5:] ) in executionNumbers:
                print "Warning! Execution number {0} was already found. This is not sane.".format( d[5:] )
                executionNumbers = []
                break
            executionNumbers.append( int(d[5:]) )
        if len(executionNumbers) == 0:
            print "Warning! Could not find the execution numbers of directory {0}, skipping.".format( dirName )
            continue
    realExecutionNumbers = []
    for e in executionNumbers:
        logDir = os.path.join( execDir, 'exec_{0}'.format( e ), 'logs' )
        parsedLogDir = os.path.join( execDir, 'exec_{0}'.format( e ), 'parsedLogs' )
        if not ( os.path.exists( logDir ) and os.path.isdir( logDir ) and os.path.exists( parsedLogDir ) and os.path.isdir( parsedLogDir ) ):
            print "Warning! Execution {0} of directory {1} seems not to have a completely set up directory. Skipping execution.".format( e, dirName )
            continue
        executionObject = FakeExecution( e, dirName )
        if not executionObject.client.isSideService():
            realExecutionNumbers.append( e )
        scenarioObject.addExecution( executionObject )
    executionNumbers = realExecutionNumbers
    for e in extraExecutionNumbers:
        logDir = os.path.join( execDir, 'exec_{0}'.format( e ), 'logs' )
        parsedLogDir = os.path.join( execDir, 'exec_{0}'.format( e ), 'parsedLogs' )
        if not ( os.path.exists( logDir ) and os.path.isdir( logDir ) and os.path.exists( parsedLogDir ) and os.path.isdir( parsedLogDir ) ):
            print "Warning! Execution {0} of directory {1} seems not to have a completely set up directory. Skipping execution.".format( e, dirName )
            continue
        executionObject = FakeExecution( e, dirName )
        scenarioObject.addExecution( executionObject )
    for e in executionNumbers:
        logDir = os.path.join( execDir, 'exec_{0}'.format( e ), 'logs' )
        parsedLogDir = os.path.join( execDir, 'exec_{0}'.format( e ), 'parsedLogs' )
        executionObject = FakeExecution( e, dirName )
        for p in parserObjects:
            try:
                p.parseLogs( executionObject, logDir, parsedLogDir )
            except Exception as e:
                print "Warning! Exception occurred while running parser {0} on execution {1} of directory {2}, ignoring.".format( p.__class__.__name__, e, dirName )
                print traceback.format_exc()
    for p in processorObjects:
        try:
            p.processLogs( os.path.join( dirName, 'executions' ), processedDir )
        except Exception as e:
            print "Warning! Exception occurred while running processor {0} on directory {1}, ignoring.".format( p.__class__.__name__, dirName )
            print traceback.format_exc()
    for v in viewerObjects:
        try:
            v.createView( processedDir, viewDir )
        except Exception as e:
            print "Warning! Exception occurred while running viewer {0} on directory {1}, ignoring.".format( v.__class__.__name__, dirName )
            print traceback.format_exc()

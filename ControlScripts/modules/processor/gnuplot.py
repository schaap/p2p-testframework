from core.campaign import Campaign
from core.processor import processor

import os
import tempfile
import subprocess
from subprocess import Popen, PIPE

def parseError( msg ):
    """
    A simple helper function to make parsing a lot of parameters a bit nicer.
    """
    raise Exception( "Parse error for processor object on line {0}: {1}".format( Campaign.currentLineNumber, msg ) )

class gnuplot(processor):
    """
    A gnuplot processor.
    
    This processor loads a defined script that will run on the (parsed) logs.
    Scripts to be run using this processor will be prepended with four string variables:
    - indir        The path to the directory on the local machine containing the parsed logs
    - rawdir       The path to the directory on the local machine containing the raw logs
    - outdir       The path to the directory on the local machine where the output files should be stored
    - execnum      The number of the execution begin processed
    
    Extra parameters:
    - script       Path to the fnuplot script to be run
    
    Raw logs expected:
    - depends on the gnuplot script
    
    Parsed logs expected:
    - depends on the gnuplot script
    
    Processed log files created:
    - depends on the gnuplot script
    """
    
    script = None       # Location of the script file
    
    # @static
    gnuplot = None      # The location of gnuplot

    def __init__(self, scenario):
        """
        Initialization of a generic processor object.

        @param  scenario        The ScenarioRunner object this processor object is part of.
        """
        processor.__init__(self, scenario)
        if not gnuplot.gnuplot:
            if os.path.exists( '/bin/gnuplot' ):
                gnuplot.gnuplot = '/bin/gnuplot'
            elif os.path.exists( '/usr/bin/gnuplot' ):
                gnuplot.gnuplot = '/usr/bin/gnuplot'
            else:
                out, _ = Popen( 'which gnuplot', stdout = PIPE, shell = True ).communicate()
                if out is None or out == '' or not os.path.exists( 'out' ):
                    raise Exception( "processor:gnuplot requires the gnuplot utility to be present" )
                gnuplot.gnuplot = out

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
        if key == 'script':
            if self.script:
                parseError( "Script has already been set: {0}".format( self.script ) )
            if not os.path.exists( value ) or not os.path.isfile( value ):
                parseError( "Script file '{0}' seems not be an existing file".format( value ) )
            self.script = value
        else:
            processor.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        processor.checkSettings(self)
        
        if not self.script:
            raise Exception( "Gnuplot processor must have a script defined" )

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
        f = None
        tmpFile = None
        try:
            f = open( self.script, 'r' )
            scriptdata = f.read()
            f.close()
            _, tmpFile = tempfile.mkstemp()
            for e in self.scenario.getObjects('execution'):
                f = open( tmpFile, 'w' )
                f.write( "indir='{0}'\n".format( self.getParsedLogDir(e, baseDir) ) )
                f.write( "rawdir='{0}'\n".format( self.getRawLogDir(e, baseDir) ) )
                f.write( "outdir='{0}'\n".format( outputDir ) )
                f.write( "execnum='{0}'\n".format( e.getNumber() ) )
                f.write( scriptdata )
                f.close()
                try:
                    subprocess.check_output( [gnuplot.gnuplot, tmpFile], bufsize=8192, stderr=subprocess.STDOUT )
                except subprocess.CalledProcessError as e:
                    Campaign.logger.log( "Running gnuplot failed: {0}. Ignoring.".format( e.output ) )
        finally:
            if f:
                try:
                    f.close()
                except Exception:
                    pass
            if tmpFile:
                os.remove( tmpFile )

    @staticmethod
    def APIVersion():
        return "2.2.0"

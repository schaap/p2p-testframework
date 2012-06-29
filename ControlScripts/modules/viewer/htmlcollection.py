from core.campaign import Campaign
from core.viewer import viewer
import external.magic.magic

import os
import re
import subprocess
from subprocess import Popen, PIPE

class htmlcollection(viewer):
    """
    This viewer builds an HTML page based on all the processed data.
    
    Note that it does not care what the data is, it uses all files.
    
    It does, however, understand a couple of formats and will make some sense of them:
    - based on mime magic, either using the python magic package or the unix file utility, the output can be adjusted
    - hostname_X, with X being the execution number, is looked for and, if available, executions are separated
    -- a table is built with one row per execution
    -- each file that matches the regular expression ..*_X(\..*)? with X begin the execution number, is take to be
        part of that very execution
    - subdirectories of the processed directory will not be recursed
    
    Extra parameters:
    - [none]
    
    Processed data expected:
    - hostname_X, for exection based output (optional); use processor:savehostname to generate these
    """
    
    # @static
    convert = None       # The path to the convert utility

    def __init__(self, scenario):
        """
        Initialization of a generic viewer object.

        @param  scenario        The ScenarioRunner object this viewer object is part of.
        """
        viewer.__init__(self, scenario)
        if not htmlcollection.convert:
            if os.path.exists( '/bin/convert' ):
                htmlcollection.convert = '/bin/convert'
            elif os.path.exists( '/usr/bin/convert' ):
                htmlcollection.convert = '/usr/bin/convert'
            else:
                out, _ = Popen( 'which convert', stdout = PIPE, shell = True ).communicate()
                if out is None or out == '' or not os.path.exists( 'out' ):
                    Campaign.logger.log( "viewer:htmlcollection could not find the convert utility. Images will not be presented nicely shrunk. Please install ImageMagick to have better functionality." )
                else:
                    htmlcollection.convert = out

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
        viewer.parseSetting(self, key, value)

    def checkSettings(self):
        """
        Check the sanity of the settings in this object.

        This method is called after all calls to parseSetting(...) have been done.
        Any defaults may be set here as well.

        An Exception is raised in the case of insanity.
        """
        viewer.checkSettings(self)

    def resolveNames(self):
        """
        Resolve any names given in the parameters.
        
        This methods is called after all objects have been initialized.
        """
        viewer.resolveNames(self)

    def createView(self, processedDir, viewDir):
        """
        Create the view from the processed data.

        @param  processedDir    The path to the directory on the local machine with the processed data.
        @param  viewDir         The path to the directory on the local machine where the view should be stored.
        """
        # Get the relative path from the viewDir to the processedDir
        relpath = os.path.relpath( processedDir, viewDir )
        
        # Test for availability of hostname_X files
        useExecutions = []
        for e in self.scenario.getObjects( 'execution' ):
            if e.client.isSideService():
                continue
            if not os.path.exists( os.path.join( processedDir, 'hostname_{0}'.format( e.getNumber() ) ) ):
                useExecutions = None
                break
            useExecutions.append(e)
        
        if htmlcollection.convert and not os.path.exists( os.path.join( viewDir, 'thumbs' ) ):
            os.makedirs(os.path.join( viewDir, 'thumbs' ))
        
        fOut = open( os.path.join( viewDir, 'collection.html' ), 'w' )
        try:
            fOut.write( "<html><head><title>{0} : HTML collection output</title></head>\n".format( self.scenario.name ) )
            fOut.write( "<body><h1>{0}</h1><h3>Contents</h3>\n".format( self.scenario.name ) )
            fOut.write( "<table>\n" )
            if useExecutions is not None:
                fOut.write( "<tr><td><a href='#execs'>Executions</a></td></tr>\n" )
                for e in useExecutions:
                    fOut.write( "<tr><td><a href='#exec_{0}'>- Execution {0} @ {1}</a></td></tr>\n".format( e.getNumber(), e.host.name ) )
            fOut.write( "<tr><td><a href='#other'>Other data</a></td></tr>\n" )
            fOut.write( "</table>\n" )
            
            otherFiles = [entry for entry in os.listdir( processedDir ) if os.path.isfile( os.path.join( processedDir, entry ) )]
            
            if useExecutions is not None:
                fOut.write( "<h3><a name='execs'>Executions</a></h3>\n" )
                fOut.write( "<table>\n" )
                columns = []
                for e in useExecutions:
                    i = 0
                    while i < len(otherFiles):
                        if otherFiles[i] == 'hostname_{0}'.format( e.getNumber() ):
                            del otherFiles[i]
                            continue
                        m = re.match( '^(..*)_{0}(\\..*)?'.format( e.getNumber() ), otherFiles[i] )
                        i += 1
                        if not m:
                            continue
                        if m.group(2):
                            col = (m.group(1), m.group(2))
                        else:
                            col = (m.group(1), '')
                        if col not in columns:
                            columns.append( col )
                fOut.write( "<thead><tr>\n" )
                fOut.write( "<td>Execution number</td>\n" )
                fOut.write( "<td>Host name</td>\n" )
                for col in columns:
                    fOut.write( "<td>{0}_X{1}</td>\n".format( col[0], col[1] ) )
                fOut.write( "</tr></thead>\n" )
                fOut.write( "<tbody>\n" )
                for e in useExecutions:
                    fOut.write( "<tr><td><a name='exec_{0}'>{0}</a></td><td>{1}</td>".format( e.getNumber(), e.host.name ) )
                    for col in columns:
                        name = '{0}_{1}{2}'.format( col[0], e.getNumber(), col[1] )
                        f = os.path.join( processedDir, name )
                        if os.path.exists( f ):
                            if name in otherFiles:
                                otherFiles.remove( name )
                            st = os.stat( f )
                            if st.st_size == 0:
                                fOut.write( '<td></td>' )
                                continue
                            if ('isSeeder', '') == col:
                                if e.isSeeder():
                                    fOut.write( '<td>YES</td>' )
                                else:
                                    fOut.write( '<td>NO</td>' )
                                continue
                            if ('timeout', '') == col:
                                fOut.write( '<td>{0} s</td>'.format( e.timeout ) )
                                continue
                            mime = external.magic.magic.Magic( mime=True ).from_file( f )
                            if mime[:6] == 'image/':
                                if htmlcollection.convert:
                                    thumb = os.path.join( 'thumbs', name )
                                    subprocess.check_output( [htmlcollection.convert, '-thumbnail', '200x150', f, os.path.join( viewDir, thumb ) ])
                                    fOut.write( '<td><a href="{1}"><img src="{0}" alt="{2}" /></a></td>'.format( thumb, os.path.join( relpath, name ), name ) )
                                else:
                                    fOut.write( '<td><a href="{0}"><img src="{0}" alt="{1}" /></a></td>'.format( os.path.join( relpath, name ), name ) )
                            else:
                                fOut.write( '<td><a href="{0}">{1}</a></td>'.format( os.path.join( relpath, name ), name ) )
                        else:
                            fOut.write( '<td></td>' )
                    fOut.write( "</tr>\n" )
                fOut.write( "</tbody></table>\n" )
            fOut.write( '<h3><a name="other">Other data</a></h3><ul>\n' )
            for name in otherFiles:
                f = os.path.join( processedDir, name )
                st = os.stat( f )
                if st.st_size == 0:
                    continue
                mime = external.magic.magic.Magic( mime=True ).from_file( f )
                if mime[:6] == 'image/':
                    if htmlcollection.convert:
                        thumb = os.path.join( 'thumbs', name )
                        subprocess.check_output( [htmlcollection.convert, '-thumbnail', '200x150', f, os.path.join( viewDir, thumb ) ])
                        fOut.write( '<li><a href="{1}"><img src="{0}" alt="{2}" /></a></li>\n'.format( thumb, os.path.join( relpath, name ), name ) )
                    else:
                        fOut.write( '<li><a href="{0}"><img src="{0}" alt="{1}" /></a></li>\n'.format( os.path.join( relpath, name ), name ) )
                else:
                    fOut.write( '<li><a href="{0}">{1}</a></li>\n'.format( os.path.join( relpath, name ), name ) )
            fOut.write( '</ul></body></html>\n')
        finally:
            fOut.close()

    def canReview(self):
        """
        Return whether this viewer can be used to review after a run has already been torn down.
        
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
        
        @return    True iff this viewer can review.
        """
        return True
    
    @staticmethod
    def APIVersion():
        return "2.4.0"

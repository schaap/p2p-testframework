from core.viewer import viewer

import os

class test__(viewer):
    """
    A test implementation for the viewer API.
    
    This implementation outputs some bogus HTML (view.html) that just begs to be viewed.
    
    Extra parameters:
    - [none]
    
    Processed data expected:
    - none
    """

    def __init__(self, scenario):
        """
        Initialization of a generic viewer object.

        @param  scenario        The ScenarioRunner object this viewer object is part of.
        """
        viewer.__init__(self, scenario)

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
        if not os.path.exists( processedDir ) or not os.path.isdir( processedDir ):
            raise Exception( "That processedDir is not a real directory: {0}".format( processedDir ) )
        if not os.path.exists( viewDir ) or not os.path.isdir( viewDir ):
            raise Exception( "That viewDir is not a real directory: {0}".format( viewDir ) )
        f = open( os.path.join( viewDir, 'testview.html' ), 'w' )
        f.write( "<html><head><title>The Viewable Test</title></head>\n" )
        f.write( "<body><h1>View</h1>README! Please, README! I beg of you: have mercy and README...</body>" )
        f.write( "</html>" )
        f.close()
        
    @staticmethod
    def APIVersion():
        return "2.2.0"

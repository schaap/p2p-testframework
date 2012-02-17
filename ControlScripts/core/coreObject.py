import threading

from core.campaign import Campaign

class coreObject:
    """
    Parent class for all core objects that are to be subclassed as modules.
    """

    scenario = None                     # The ScenarioRunner this object is part of
    name = ''                           # String containing the name of this object; unique among all instances of the same subclass (e.g. unique among hosts, or unique among clients, etc)
    declarationLine = -1                # Line number of the declaration of this host object, read during __init__

    inCleanup = False                   # Flag for cleanup phase. Please use isInCleanup() and cleanup().
    inCleanup__lock = None              # Mutex for the inCleanup variable. Please do NOT acquire this.

    def __init__(self, scenario):
        """
        Initialization of a generic module object.

        @param  scenario            The ScenarioRunner object this module object is part of.
        """
        self.scenario = scenario
        self.declarationLine = Campaign.currentLineNumber
        self.inCleanup__lock = threading.Lock()

    def cleanup(self):
        """
        Cleanup the object.

        This base implementation just sets some internal state to signal cleanup has started. See isInCleanup().
        
        Be sure this implementation is called as soon as possible.
        """
        self.inCleanup__lock.acquire()
        self.inCleanup = True
        self.inCleanup__lock.release()
    
    def isInCleanup(self):
        """
        Report whether this object is in cleanup phase.

        If so, no operations should be done which may introduce delays or would need to be cleaned up.

        Any operations that can't have their cleanup in the generic cleanup method, but do need cleanup and can be
        interrupted (as any operation SHOULD be able to) should use this method to check whether to abort and clean
        up.
        
        @return True iff this object has started cleanup.
        """
        self.inCleanup__lock.acquire()
        res = self.inCleanup
        self.inCleanup__lock.release()
        return res

    def getModuleType(self):
        """
        Return the moduleType string.
        
        @return    The module type.
        """
        raise Exception( "Not implemented!" )
    
    def getName(self):
        """
        Return the name of the object.
        
        @return    The name.
        """
        raise Exception( "Not implemented!" )

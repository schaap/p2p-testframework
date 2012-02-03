import re

from core.campaign import Campaign

def isSectionHeader( str ):
    """
    Returns whether str is a section header (i.e. starts with a [).

    @param  str     A string containing a single line.

    @return True iff str is a section header.
    """
    return str[0] == '['

def getSectionName( str ):
    """
    Returns the section name of the given section header.

    Will throw an exception if the section is not clean.
    
    @param  str     A string containing a single line.

    @return The section name (i.e. the string between []).
    """
    if not re.match( "\[.*\].", str ) is None:
        raise Exception( "Found garbage after section header on line {0}".format( Campaign.currentLineNumber ) )
    if not re.match( "\[.*\s.*\]", str ) is None:
        raise Exception( "Section names are not allowd to have whitespace in them (line {0})".format( Campaign.currentLineNumber )
    if str == '[]':
        raise Exception( "Empty section name on line {0}".format( Campaign.currentLineNumber ) )
    return str[1:-1]

def getParameterName( str ):
    """
    Returns the parameter name of the given parameter line.

    Will throw an exception is the parameter is malformed.

    @param  str     A string containing a single line.

    @return The parameter name (i.e. the string before =).
    """
    m = re.match( "^([^=].*)=..*$", str )
    if m is None:
        raise Exception( "Malformed parameter on line {0}".format( Campaign.currentLineNumber ) )
    if not re.match( ".*\s.*", m.group(1) ) is None:
        raise Exception( "Parameter names are not allowed to have whitespace in them (line {0})".format( Campaign.currentLineNumber )
    return m.group(1)

def getParameterValue( str ):
    """
    Returns the parameter value of the given parameter line.

    Will throw an exception is the parameter is malformed.

    @param  str     A string containing a single line.

    @return The parameter value (i.e. the string after =).
    """
    m = re.match( "^[^=].*=(.*)$", str )
    if m is None:
        raise Exception( "Malformed parameter on line {0}".format( Campaign.currentLineNumber ) )
    return m.group(1)

def hasModuleSubType( section ):
    """
    Returns whether the section name consists of a module type and subtype.

    @param  section     A string with the section name.

    @return True iff the section consists of a module type and subtype (i.e. contains a :).
    """
    return not re.search( ':', section ) is None

def getModuleType( section ):
    """
    Returns the module type of a section name.

    This is the part before the : or the complete section name if no : is present.

    @param  section     A string with the section name.

    @return The module type in the section name.
    """
    m = re.match( '^(.*):.*$', section )
    return m.group( 1 )

def getModuleSubType( section ):
    """
    Returns the module subtype of a section name.

    This is the part after the : or "" if no : is present.

    @param  section     A string with the section name.

    @return The module subtype in the section name.
    """
    m = re.match( '^.*:(.*)$', section )
    if m is None:
        return ''
    return m.group( 1 )

def isValidName( name ):
    """
    Returns whether the specified string is a valid name (i.e. /^[a-zA-Z][a-zA-Z0-9_-\.]*$/)

    @param  name        A string with a name to be checked.

    @return True iff the name is valid.
    """
    return not re.match( '^[a-zA-Z][a-zA-Z0-9_-\.]*$', name ) is None

def isPositiveInt( value, nonZero = False ):
    """
    Returns whether the specified value string is a positive (nonzero) integer.

    @param  value       The string with the value.
    @param  nonZero     Set to True if the value 0 is not allowed.

    @return True iff the string value represents a positive integer.
    """
    if re.search( "\\D", value ) is not None:
        return False
    return value != '' and ((not nonZero) or (value != "0"))

def isPositiveFloat( value, nonZero = False ):
    """
    Returns whether the specific value string is a positive (nonzero) floating point number.

    @param  value       The string with the value.
    @param  nonZero     Set to True if the value 0 is not allowed.

    @return True iff the string value represents a positive float.
    """
    if value == '' or re.search( "[^0-9\\.]", value ) is not None:
        return False
    return (not nonZero) or (float(value) != 0)

#!/bin/bash

#
#
# Requires: logError
# Provides: isSectionHeader, getSectionName, getParameterName, getParameterValue
#

# === Set up configuration parsing API ===

##
# Returns true if the given line looks like a section header (i.e. starts with a [)
#
# @param    A single line in a string
#
# @return   0 iff the line seems to be a section header
##
function isSectionHeader() {
    if [ "${1:0:1}" = "[" ]; then
        return 0
    else
        return 1
    fi
}

##
# Outputs the section name of the given section header. Will write an error and fail if the section is not clean.
# Callers of this function should call checkFail to fail on errors that occurred in this functions.
#
# @param    A single line in a string
#
# @output   The name of the section (i.e. the string between [])
##
function getSectionName() {
    if echo "$1" | grep -E "\[.*\]..*" > /dev/null; then
        logError "Found garbage after section header on line $LINE_NUMBER"
        signalFail
    fi
    if echo "$1" | grep -E "\[.*\s.*\]" > /dev/null; then
        logError "Section names are not allowed to have whitespace in them (line $LINE_NUMBER)"
        signalFail
    fi
    if [ "$1" = "[]" ]; then
        logError "Empty section name on line $LINE_NUMBER"
        signalFail
    fi
    echo "$1" | sed -e "s/\[\(.*\)\]/\\1/"
}

##
# Outputs the parameter name of the given parameter line. Will write an error and fail if the parameter is malformed.
# Callers of this function should call checkFail to fail on errors that occurred in this functions.
#
# @param    A single line in a string
#
# @output   The name of the parameter (i.e. the string before the first =)
##
function getParameterName() {
    if ! (echo "$1" | grep -E "[^=].*=..*" > /dev/null); then
        logError "Parameter malformed on line $LINE_NUMBER"
        signalFail
    fi
    local parameterName=`echo "$1" | sed -e"s/\([^=]*\)=.*/\\1/"`
    if echo "$parameterName" | grep -E "\s" > /dev/null; then
        logError "Parameter names are not allowed to have whitespace in them (line $LINE_NUMBER)"
        signalFail
    fi
    echo $parameterName
}

##
# Outputs the parameter value of the given parameter line. Will write an error and fail if the parameter is malformed beyond what is checked by getParameterName
#
# @param    A single line in a string.
#
# @output   The value of the parameter (i.e. the string after the first =)
##
function getParameterValue() {
    echo "$1" | sed -e"s/[^=]*=\(.*\)/\\1/"
}

##
# Returns whether the section name consists of a module type and subtype.
#
# @param    The section name in a string.
#
# @return   True (0) iff the section consists of a module type and subtype (i.e. contains a :).
##
function hasModuleSubType() {
    echo "$1" | grep ":" > /dev/null
    return $?
}

##
# Outputs the module type of a section name. This is the part before the : or the complete section name if no : is present.
#
# @param    The section name in a string.
#
# @output   The module type in the section name.
##
function getModuleType() {
    if hasModuleSubType "$1"; then
        echo "$1" | sed -e "s/:.*//"
    else
        echo "$1"
    fi
}

##
# Outputs the module subtype of a section name. This is the part after the : or "" if no : is present.
#
# @param    The section name in a string.
#
# @output   The module subtype in the section name.
##
function getModuleSubType() {
    if hasModuleSubType "$1"; then
        echo "$1" | sed -e "s/^[^:]*://"
    else
        echo ""
    fi
}

##
# Returns whether the specified string is a valid name (i.e. /^[a-zA-Z][a-zA-Z0-9_-\.]*$/)
#
# @param    The name in a string
#
# @return   True (0) iff the name is valid.
##
function isValidName() {
    echo "$1" | grep -E "^[a-zA-Z][a-zA-Z0-9_\-\.]*$" > /dev/null
    return $?
}

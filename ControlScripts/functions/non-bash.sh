#!/bin/bash

#
# Provides support for non-bash execution of functions. Primary use is speeding up parts of the framework.
#
# Requires: logError, fail
# Provides: callNonBash
#

##
# On behalf of the caller:
# - check whether a non-bash caller exists
# - call the non-bash caller with the arguments to callNonBash (with a maximum of 9 arguments, if more are given the first 9 are passed)
# - log any output of the non-bash caller as an error (uses logError) and fail if that output isn't ""
# - return 0 if the non-bash caller could run a non-bash script instead, return non-zero otherwise
#
# This function derives the following data about its caller:
# - the function name, using the function field of "caller 0"
# - the module name, using the file field of "caller 0" (just the part after the last /)
# - the module type, derived from the function name: if the first part of that name matches a supported module type, it is recognized as such
#
# Supported module types are:
# - builder
# - client
# - execution
# - file
# - host
# - parser
# - processor
# - source
# - tc
# - viewer
#
# To prevent insanity, the following checks are in place:
# - the module type is supported
# - the module type/name combination is a valid module
# - a module of that type is actually loaded at this point
# If any of these checks fails, the function returns 2 after logging an error.
#
# When calling this function, always check the return value: iff it's 0 you should return from your function straight away
#
# Note that, because of the semantics used, non-bash calls are not supported for functions that should output anything or return anything but always 0.
#
# An example of usage:
#
#   function parserParseLogs() {
#       if callNonBash $1 $2; then
#           return
#       fi
#
#       # ... do actual log parsing in bash
#   }
#
# The script that is used for non-bash function calls is a simple bash script that will be sourced in a sub-process of the callNonBash function.
# The arguments passed to the non-bash function call script are the same as those passed to the callNonBash function, up to and including the first 9 arguments.
# The script for a function called X inside a module T:S is to be found in file modules/T/non-bash/S/X .
# This script should do the following:
# - detect the possibility to run a non-bash function call (e.g. check whether PHP CLI is available)
# - run the non-bash function call if possible (e.g. run a PHP script for the function)
# - reflect any output from the non-bash function call as being an error to be logged (the existence of output means the function will fail)
# - return 0 if a non-bash function call was made
# - return 1 if, for any reason, no non-bash function call was done
# Note in particular that the non-bash function call script ensures the non-bash function is called. This also means that it has the responsibility to translate
# any environment or arguments in a way the non-bash function can handle it.
# As an important reminder when writing a non-bash function call script: the modules are always found in "${TEST_ENV_DIR}/modules/"
#
# The non-bash function itself, finally, is expected to fulfill the contract of the function it replaces.
#
# It can be very useful to, while still developing, alter the non-bash function itself to place some output somewhere else (e.g. a different directory or file) and return 1
# from the non-bash function call script, anyway, to make sure the non-bash function is called, but the framework continues as if it wasn't.
#
# @return   0 if a non-bash script was called and the calling function can return, 1 if no non-bash was called, 2 if no sane function information could be derived
##
function callNonBash() {
    # Derive information about the caller, based on reflection of the call stack
    local callerLine=`caller 0`
    local callerFunc=`echo $callerLine | sed -e "s/^[0-9]* \([^ ]*\) .*$/\\1/"`
    local callerFile=`echo $callerLine | sed -e "s%^[0-9]* [^ ]* .*/\([^/]*\)$%\\1%"`
    # Derive the caller's module type from the caller's function name, also check whether that module type is supported and a module of the already found subtype seems to be loaded
    local callerModType=""
    case "${callerFunc:0:2}" in
        "bu")
            if [ "${callerFunc:0:7}" = "builder" ]; then
                callerModType="builder"
                if [ "$CLIENT_BUILDER" != "$callerFile" ]; then
                    logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but no $callerModType:$callerFile seems loaded at this point."
                    return 2
                fi
            fi
            ;;
        "cl")
            if [ "${callerFunc:0:6}" = "client" ]; then
                callerModType="client"
                if [ "$CLIENT_SUBTYPE" != "$callerFile" ]; then
                    logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but no $callerModType:$callerFile seems loaded at this point."
                    return 2
                fi
            fi
            ;;
        "ex")
            if [ "${callerFunc:0:9}" = "execution" ]; then
                callerModType="execution"
                if [ -z "$EXECUTION_NUMBER" -o "$callerFile" != "execution" ]; then
                    logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but no $callerModType:$callerFile seems loaded at this point."
                    return 2
                fi
            fi
            ;;
        "fi")
            if [ "${callerFunc:0:4}" = "file" ]; then
                callerModType="file"
                if [ "$FILE_SUBTYPE" != "$callerFile" ]; then
                    logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but no $callerModType:$callerFile seems loaded at this point."
                    return 2
                fi
            fi
            ;;
        "ho")
            if [ "${callerFunc:0:4}" = "host" ]; then
                callerModType="host"
                if [ "$HOST_SUBTYPE" != "$callerFile" ]; then
                    logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but no $callerModType:$callerFile seems loaded at this point."
                    return 2
                fi
            fi
            ;;
        "pa")
            if [ "${callerFunc:0:6}" = "parser" ]; then
                callerModType="parser"
                if [ "$PARSER_SUBTYPE" != "$callerFile" ]; then
                    logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but no $callerModType:$callerFile seems loaded at this point."
                    return 2
                fi
            fi
            ;;
        "pr")
            if [ "${callerFunc:0:9}" = "processor" ]; then
                callerModType="processor"
                if [ "$PROCESSOR_SUBTYPE" != "$callerFile" ]; then
                    logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but no $callerModType:$callerFile seems loaded at this point."
                    return 2
                fi
            fi
            ;;
        "so")
            if [ "${callerFunc:0:6}" = "source" ]; then
                callerModType="source"
                if [ "$CLIENT_SOURCE" != "$callerFile" ]; then
                    logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but no $callerModType:$callerFile seems loaded at this point."
                    return 2
                fi
            fi
            ;;
        "tc")
            callerModType="tc"
            if [ "$HOST_TC" != "$callerFile" ]; then
                logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but no $callerModType:$callerFile seems loaded at this point."
                return 2
            fi
            ;;
        "vi")
            if [ "${callerFunc:0:6}" = "viewer" ]; then
                callerModType="viewer"
                if [ "$VIEWER_SUBTYPE" != "$callerFile" ]; then
                    logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but no $callerModType:$callerFile seems loaded at this point."
                    return 2
                fi
            fi
            ;;
        *)
            logError "callNonBash: Can't get a supported module type from $callerFunc"
            return 2
    esac

    # Test whether a module of the type:subtype does actually exist
    if [ ! -e "${TEST_ENV_DIR}/modules/$callerModType/$callerFile" ]; then
        logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but module $callerModType:$callerFile doesn't exist."
        return 2
    fi
    if [ ! -f "${TEST_ENV_DIR}/modules/$callerModType/$callerFile" ]; then
        logError "callNonBash: According to $callerFunc the call came from a $callerModType module, but modules/$callerModType/$callerFile is not a file."
        return 2
    fi

    # The derived information seems sane, proceed with actual functionality

    # Test for non-bash caller for function $callerFunc in module $callerModType:$callerFile
    local nonbashscript="${TEST_ENV_DIR}/modules/$callerModType/non-bash/$callerFile/$callerFunc"
    if [ ! -f "$nonbashscript" ]; then
        return 1
    fi

    # The non-bash caller exists, let's call it
    local ret=""
    local out=""
    case $# in
        0)
            out=`. "$nonbashscript"`
            ret=$?
            ;;
        1)
            out=`. "$nonbashscript" $1`
            ret=$?
            ;;
        2)
            out=`. "$nonbashscript" $1 $2`
            ret=$?
            ;;
        3)
            out=`. "$nonbashscript" $1 $2 $3`
            ret=$?
            ;;
        4)
            out=`. "$nonbashscript" $1 $2 $3 $4`
            ret=$?
            ;;
        5)
            out=`. "$nonbashscript" $1 $2 $3 $4 $5`
            ret=$?
            ;;
        6)
            out=`. "$nonbashscript" $1 $2 $3 $4 $5 $6`
            ret=$?
            ;;
        7)
            out=`. "$nonbashscript" $1 $2 $3 $4 $5 $6 $7`
            ret=$?
            ;;
        8)
            out=`. "$nonbashscript" $1 $2 $3 $4 $5 $6 $7 $8`
            ret=$?
            ;;
        *)
            out=`. "$nonbashscript" $1 $2 $3 $4 $5 $6 $7 $8 $9`
            ret=$?
            ;;
    esac

    if [ ! -z "$out" ]; then
        logError "$out"
        fail
    fi

    return $ret
}

#!/bin/bash

##
# Returns the version of this parser.
#
# @output   The version of this parser.
##
function parseAPIVersion() {
    echo "1.0.0"
}

##
# Parses the settings for a module.
# When a parse error occurs please call failScenarioFile "$6" instead of just fail.
#
# @param    The module type, which is always the same for this parser.
# @param    The module sub type, or "" if no sub type is specified.
# @param    The line number where this object was started (the first line in settings is on line $3 + 1).
# @param    The settings file to be parsed.
# @param    The name of the scenario.
# @param    The scenario file.
##
function parseSettings() {
    if [ ! -f "$4" ]; then
        logError "_skeletons_:_parser_.sh :: parseSettings called with invalid file argument"
        fail
    fi

    LINE_NUMBER=$(($3 + 1))
    local parameterName=""
    local parameterValue=""
    while IFS="" read LINE; do
        if [ "$LINE" = "" ]; then
            LINE_NUMBER=$(($LINE_NUMBER + 1))
            continue;
        fi
        parameterName=`getParameterName "$LINE"`
        checkFailScenarioFile "$6"
        parameterValue=`getParameterValue "$LINE"`
        case $parameterName in
            *)
                logError "_skeletons_:_parser_.sh :: Unknown parameter name ${parameterName} on line $LINE_NUMBER of scenario $5"
                failScenarioFile "$6"
                ;;
        esac
        LINE_NUMBER=$(($LINE_NUMBER + 1))
    done < "$4";
}

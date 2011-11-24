#!/bin/bash

##
# Returns the version of this parser.
#
# @output   The version of this parser.
##
function parseAPIVersion() {
    echo "1.0.2"
}

##
# Parses the settings for a viewer module.
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
        logError "viewer:_parser_.sh :: parseSettings called with invalid file argument"
        fail
    fi

    LINE_NUMBER=$(($3 + 1))
    local parameterName=""
    local parameterValue=""
    VIEWER_SUBTYPE="$2"
    VIEWER_NUMBER=$VIEWER_COUNT
    VIEWER_COUNT=$(($VIEWER_COUNT + 1))
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
                ;;
        esac
        LINE_NUMBER=$(($LINE_NUMBER + 1))
    done < "$4";

    # = Load the viewer subtype module =
    function viewerAPIVersion() {
        echo "wrong"
    }
    loadModule "viewer/$VIEWER_SUBTYPE"
    if [ "`viewerAPIVersion`" != `parseAPIVersion` ]; then
        logError "viewer:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but module viewer:$VIEWER_SUBTYPE seems to have API version `viewerAPIVersion`."
        failScenarioFile "$6"
    fi

    if ! viewerReadSettings "$4" $3; then
        logError "viewer:_parser_.sh :: Error in reading viewer settings of the viewer defined on line $3 in scenario $5."
        failScenarioFile "$6"
    fi

    if [ ! -e "${LOCAL_TEST_DIR}/viewers/view_$VIEWER_NUMBER" ]; then
        logError "viewer:_parser_.sh :: Something apparently has gone wrong in writing the settings of viewer $VIEWER_NUMBER."
        failScenarioFile "$6"
    fi
}

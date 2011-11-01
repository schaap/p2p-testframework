#!/bin/bash

##
# Returns the version of this parser.
#
# @output   The version of this parser.
##
function parseAPIVersion() {
    echo "1.0.1"
}

##
# Parses the settings for a processor module.
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
        logError "processor:_parser_.sh :: parseSettings called with invalid file argument"
        fail
    fi

    LINE_NUMBER=$(($3 + 1))
    local parameterName=""
    local parameterValue=""
    PROCESSOR_SUBTYPE="$2"
    PROCESSOR_NUMBER=$PROCESSOR_COUNT
    PROCESSOR_COUNT=$(($PROCESSOR_COUNT + 1))
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

    # = Load the processor subtype module =
    function processorAPIVersion() {
        echo "wrong"
    }
    loadModule "processor/$PROCESSOR_SUBTYPE"
    if [ "`processorAPIVersion`" != `parseAPIVersion` ]; then
        logError "processor:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but module processor:$PROCESSOR_SUBTYPE seems to have API version `processorAPIVersion`."
        failScenarioFile "$6"
    fi

    if ! processorReadSettings "$4" $3; then
        logError "processor:_parser_.sh :: Error in reading processor settings of the processor defined on line $3 in scenario $5."
        failScenarioFile "$6"
    fi

    if [ ! -e "${LOCAL_TEST_DIR}/processors/proc_$PROCESSOR_NUMBER" ]; then
        logError "processor:_parser_.sh :: Something apparently has gone wrong in writing the settings of processor $PROCESSOR_NUMBER."
        failScenarioFile "$6"
    fi
}

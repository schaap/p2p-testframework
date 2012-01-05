#!/bin/bash

##
# Returns the version of this parser.
#
# @output   The version of this parser.
##
function parseAPIVersion() {
    echo "1.0.4"
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
        logError "parser:_parser_.sh :: parseSettings called with invalid file argument"
        fail
    fi

    LINE_NUMBER=$(($3 + 1))
    local parameterName=""
    local parameterValue=""
    PARSER_NAME=""
    PARSER_SUBTYPE="$2"
    while IFS="" read LINE; do
        if [ "$LINE" = "" ]; then
            LINE_NUMBER=$(($LINE_NUMBER + 1))
            continue;
        fi
        parameterName=`getParameterName "$LINE"`
        checkFailScenarioFile "$6"
        parameterValue=`getParameterValue "$LINE"`
        case $parameterName in
            name)
                if ! isValidName "$parameterValue"; then
                    logError "parser:_parser_.sh :: \"$parameterValue\" is not a valid name for the parser defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$PARSER_NAME" ]; then
                    logError "parser:_parser_.sh :: Parser defined at line $3 of scenario $5 already has a name (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ -e "${LOCAL_TEST_DIR}/parsers/$parameterValue" ]; then
                    logError "parser:_parser_.sh :: Parser $parameterValue already exists, redefined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                PARSER_NAME="$parameterValue"
                ;;
            *)
                ;;
        esac
        LINE_NUMBER=$(($LINE_NUMBER + 1))
    done < "$4";

    if [ -z "$PARSER_NAME" ]; then
        if [ ! -e "${LOCAL_TEST_DIR}/parsers/$PARSER_SUBTYPE" ]; then
            PARSER_NAME="$PARSER_SUBTYPE"
        else
            logError "parser:_parser_.sh :: Parser defined at line $3 of scenario $5 has no name specified and the default name for this parser type ($PARSER_SUBTYPE) is already used."
            failScenarioFile "$6"
        fi
    fi

    # = Load the parser subtype module =
    function parserAPIVersion() {
        echo "wrong"
    }
    loadModule "parser/$PARSER_SUBTYPE"
    if [ "`parserAPIVersion`" != `parseAPIVersion` ]; then
        logError "parser:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but module parser:$PARSER_SUBTYPE seems to have API version `parserAPIVersion`."
        failScenarioFile "$6"
    fi

    if ! parserReadSettings "$4" $3; then
        logError "parser:_parser_.sh :: Error in reading parser settings of parser $PARSER_NAME in scenario $5."
        failScenarioFile "$6"
    fi

    if [ ! -e "${LOCAL_TEST_DIR}/parsers/$PARSER_NAME" ]; then
        logError "parser:_parser_.sh :: Something apparently has gone wrong in writing the settings of parser $PARSER_NAME."
        failScenarioFile "$6"
    fi
}

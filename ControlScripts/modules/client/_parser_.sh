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
# Parses the settings for a client.
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
        logError "client:_parser_.sh :: parseSettings called with invalid file argument"
        fail
    fi

    # Make sure the directory for storing the client's settings exists
    mkdir -p "${LOCAL_TEST_DIR}/clients"

    LINE_NUMBER=$(($3 + 1))
    local parameterName=""
    local parameterValue=""
    CLIENT_NAME=""
    CLIENT_PARAMS=""
    CLIENT_LOCATION=""
    CLIENT_SUBTYPE="$2"
    CLIENT_PARSER=""
    CLIENT_REMOTECLIENT=""
    CLIENT_BUILDER=""
    CLIENT_SOURCE=""
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
                    logError "client:_parser_.sh :: \"$parameterValue\" is not a valid name for the client defined at line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$CLIENT_NAME" ]; then
                    logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 already has a name (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ -e "${LOCAL_TEST_DIR}/clients/$parameterValue" ]; then
                    logError "client:_parser_.sh :: Client $parameterValue already exists, redefined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                CLIENT_NAME="$parameterValue"
                ;;
            params)
                if [ ! -z "$CLIENT_PARAMS" ]; then
                    logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 already has some parameters (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                CLIENT_PARAMS="$parameterValue"
                ;;
            location)
                if [ ! -z "$CLIENT_LOCATION" ]; then
                    logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 already has a location (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                CLIENT_LOCATION="$parameterValue"
                ;;
            parser)
                if ! isValidName "$parameterValue"; then
                    logError "client:_parser_.sh :: \"$parameterValue\" is not a valid name for a parser, but is given as default parser to the client defined at line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$CLIENT_PARSER" ]; then
                    logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 already has a default parser set (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -e "${LOCAL_TEST_DIR}/parsers/$parameterValue" ]; then
                    logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 refers to parser named \"$parameterValue\", which does not exist (line $LINE_NUMBER). Maybe you defined the client before its default parser?"
                    failScenarioFile "$6"
                fi
                CLIENT_PARSER="$parameterValue"
                ;;
            builder)
                if ! isValidName "$parameterValue"; then
                    logError "client:_parser_.sh :: \"$parameterValue\" is not a valid name for a builder, but is given as such to the client defined at line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$CLIENT_BUILDER" ]; then
                    logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 already has a builder set (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! existsModule "builder/$parameterValue"; then
                    logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 was given the builder \"$parameterValue\", which seems not to exist."
                    failScenarioFile "$6"
                fi
                CLIENT_BUILDER="$parameterValue"
                ;;
            source)
                if ! isValidName "$parameterValue"; then
                    logError "client:_parser_.sh :: \"$parameterValue\" is not a valid name for a source module, but is given as such to the client defined at line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$CLIENT_SOURCE" ]; then
                    logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 already has a source module set (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! existsModule "source/$parameterValue"; then
                    logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 was given the source module \"$parameterValue\", which seems not to exist."
                    failScenarioFile "$6"
                fi
                CLIENT_SOURCE="$parameterValue"
                ;;
            remoteClient)
                if [ ! -z "$parameterValue" ]; then
                    CLIENT_REMOTECLIENT="1"
                fi
                ;;
            *)
                ;;
        esac
        LINE_NUMBER=$(($LINE_NUMBER + 1))
    done < "$4";

    if [ -z "$CLIENT_NAME" ]; then
        if [ -e "${LOCAL_TEST_DIR}/clients/${CLIENT_SUBTYPE}" ]; then
            logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 has no name specified and the default name ($CLIENT_SUBTYPE) is already in use."
            failScenarioFile "$6"
        fi
        CLIENT_NAME=$CLIENT_SUBTYPE
    fi

    if [ -z "$CLIENT_SOURCE" ]; then
        if ! existsModule "source/directory"; then
            logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 has no source location specified, but the default module source:directory doesn't exist."
            failScenarioFile "$6"
        else
            CLIENT_SOURCE="directory"
        fi
    fi

    if [ -z "$CLIENT_BUILDER" ]; then
        if ! existsModule "builder/none"; then
            logError "client:_parser_.sh :: Client defined at line $3 of scenario $5 has no builder specified, but the default module builder:none doesn't exist."
            failScenarioFile "$6"
        else
            CLIENT_BUILDER="none"
        fi
    fi

    if [ -z "$CLIENT_LOCATION" ]; then
        CLIENT_LOCATION="$CLIENT_NAME"
    fi

    if [ -z "$CLIENT_PARSER" ]; then
        if ! existsModule "parser/$CLIENT_SUBTYPE"; then
            logError "client:_parser_.sh :: Client $CLIENT_NAME defined at line $3 of scenario $5 specified no default parser object, but the default parser module which would be used in this case (parser:$CLIENT_SUBTYPE) does not exist. This usually means that the client module was not accompanied by a parser module (which it should), or that your installation is not complete."
            failScenarioFile "$6"
        fi
    fi

    # = Load source and builder modules, just to see if they're the right version =
    if [ ! -z "$CLIENT_BUILDER" ]; then
        function builderAPIVersion__default() {
            echo "wrong"
        }
        loadModule "builder/_defaults_"
        if [ "`builderAPIVersion__default`" != `parseAPIVersion` ]; then
            logError "client:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but defaults module builder:_defaults_ seems to have API version `builderAPIVersion__default`."
            failScenarioFile "$6"
        fi
        function builderAPIVersion() {
            echo "wrong"
        }
        loadModule "builder/$CLIENT_BUILDER"
        if [ "`builderAPIVersion`" != `parseAPIVersion` ]; then
            logError "client:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but module builder:$CLIENT_BUILDER seems to have API version `builderAPIVersion`."
            failScenarioFile "$6"
        fi
        function sourceAPIVersion__default() {
            echo "wrong"
        }
        loadModule "source/_defaults_"
        if [ "`sourceAPIVersion__default`" != `parseAPIVersion` ]; then
            logError "client:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but defaults module source:_defaults_ seems to have API version `sourceAPIVersion__default`."
            failScenarioFile "$6"
        fi
        function sourceAPIVersion() {
            echo "wrong"
        }
        loadModule "source/$CLIENT_SOURCE"
        if [ "`sourceAPIVersion`" != `parseAPIVersion` ]; then
            logError "client:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but module source:$CLIENT_SOURCE seems to have API version `sourceAPIVersion`."
            failScenarioFile "$6"
        fi
    fi

    # = Load the client subtype module =
    function clientAPIVersion() {
        echo "wrong"
    }
    loadModule "client/$CLIENT_SUBTYPE"
    if [ "`clientAPIVersion`" != `parseAPIVersion` ]; then
        logError "client:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but module client:$CLIENT_SUBTYPE seems to have API version `clientAPIVersion`."
        failScenarioFile "$6"
    fi

    if ! clientReadSettings "$4" $3; then
        logError "client:_parser_.sh :: Error in reading client settings of client $CLIENT_NAME in scenario $5."
        failScenarioFile "$6"
    fi

    if [ ! -e "${LOCAL_TEST_DIR}/clients/$CLIENT_NAME" ]; then
        logError "client:_parser_.sh :: Something apparently has gone wrong in writing the settings of client $CLIENT_NAME."
        failScenarioFile "$6"
    fi
}

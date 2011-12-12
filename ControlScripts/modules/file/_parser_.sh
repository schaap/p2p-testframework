#!/bin/bash

##
# Returns the version of this parser.
#
# @output   The version of this parser.
##
function parseAPIVersion() {
    echo "1.0.3"
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
        logError "file:_parser_.sh :: parseSettings called with invalid file argument"
        fail
    fi

    LINE_NUMBER=$(($3 + 1))
    local parameterName=""
    local parameterValue=""
    FILE_NAME=""
    FILE_SUBTYPE="$2"
    FILE_ROOTHASH=""
    FILE_METAFILE=""
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
                    logError "file:_parser_.sh :: \"$parameterValue\" is not a valid name for the file defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$FILE_NAME" ]; then
                    logError "file:_parser_.sh :: File defined at line $3 of scenario $5 already has a name (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ -e "${LOCAL_TEST_DIR}/files/$parameterValue" ]; then
                    logError "file:_parser_.sh :: File $parameterValue already exists, redefined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                FILE_NAME="$parameterValue"
                ;;
            rootHash)
                if ! echo "$parameterValue" | grep -E "[[:xdigit:]]{40}" > /dev/null; then
                    logError "file:_parser_.sh :: \"$parameterValue\" is not a valid SHA1 hash for the file defined on line $3 of scenario $5 (line $LINE_NUMBER); expected 40 hexadecimal digits."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$FILE_ROOTHASH" ]; then
                    logError "file:_parser_.sh :: File defined at line $3 of scenario $5 already has a Merkle Root Hash (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                FILE_ROOTHASH="$parameterValue"
                ;;
            metaFile)
                if [ ! -f "$parameterValue" ]; then
                    logError "file:_parser_.sh :: File defined at line $3 of scenario $5 is given meta file \"$parameterValue\", but that file does not exist locally."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$FILE_METAFILE" ]; then
                    logError "file:_parser_.sh :: File defined at line $3 of scenario $5 already has a meta file associated (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                FILE_METAFILE="$parameterValue"
                ;;
            *)
                ;;
        esac
        LINE_NUMBER=$(($LINE_NUMBER + 1))
    done < "$4";

    if [ -z "$FILE_NAME" ]; then
        logError "file:_parser_.sh :: File defined at line $3 of scenario $5 has no name specified."
        failScenarioFile "$6"
    fi

    # = Load the file subtype module =
    function fileAPIVersion() {
        echo "wrong"
    }
    loadModule "file/$FILE_SUBTYPE"
    if [ "`fileAPIVersion`" != `parseAPIVersion` ]; then
        logError "file:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but module file:$FILE_SUBTYPE seems to have API version `fileAPIVersion`."
        failScenarioFile "$6"
    fi

    if ! fileReadSettings "$4" $3; then
        logError "file:_parser_.sh :: Error in reading file settings of file $FILE_NAME in scenario $5."
        failScenarioFile "$6"
    fi

    if [ ! -e "${LOCAL_TEST_DIR}/files/$FILE_NAME" ]; then
        logError "file:_parser_.sh :: Something apparently has gone wrong in writing the settings of file $FILE_NAME."
        failScenarioFile "$6"
    fi
}

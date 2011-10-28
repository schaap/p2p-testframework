#!/bin/bash

#
#
#
#
#
#

# = Check for a campaign file. =

if [ ! $# -eq 1 ]; then
    echo "Usage: $0 campaign_file"
    exit 1
fi

# === Initialize global API ===

## Points to the local directory containing the testing environment's main script (i.e. the ControlScripts directory)
if [ -z "$TEST_ENV_DIR" ]; then
    TEST_ENV_DIR=`dirname \`readlink -e $0\``
else
    if [ ! -d "$TEST_ENV_DIR" ]; then
        echo "TEST_ENV_DIR is set to an invalid path" 1>&2
        exit -1
    fi
fi
# Check sanity of minimal requirements first
if [ ! -d "${TEST_ENV_DIR}/functions" ]; then
    echo "TEST_ENV_DIR does not contain the functions directory, which contains required files" 1>&2
    exit -1
fi
if [ ! -f "${TEST_ENV_DIR}/functions/stderrlogging.sh" ]; then
    echo "TEST_ENV_DIR does not contain functions/stderrlogging.sh, which is required" 1>&2
    exit -1
fi
if [ ! -f "${TEST_ENV_DIR}/functions/cleanup.sh" ]; then
    echo "TEST_ENV_DIR does not contain functions/cleanup.sh, which is required" 1>&2
    exit -1
fi

. "${TEST_ENV_DIR}/functions/stderrlogging.sh"
. "${TEST_ENV_DIR}/functions/cleanup.sh"

# Now that cleanup exists, let's make sure we clean up when we receive a signal
TEST_BASE_DIR=`pwd`
function trapHandlerHup() {
    cd "${TEST_BASE_DIR}"
    logError "Received signal SIGHUP"
    fail
}
function trapHandlerTerm() {
    cd "${TEST_BASE_DIR}"
    logError "Received signal SIGTERM"
    fail
}
function trapHandlerInt() {
    cd "${TEST_BASE_DIR}"
    logError "Received signal SIGINT"
    fail
}
trap trapHandlerHup SIGHUP
trap trapHandlerTerm SIGTERM
trap trapHandlerInt SIGINT

##
# Check whether the functions script in the first argument is available in ${TEST_ENV_DIR}/functions and loads it.
# Will not return if the script is not available.
#
# @param    The name of the file in ${TEST_ENV_DIR}/functions to load
##
function loadFunctionsScript() {
    if [ ! -f "${TEST_ENV_DIR}/functions/$1" ]; then
        logError "TEST_ENV_DIR does not contain functions/$1, which is required"
        fail
    fi
    . "${TEST_ENV_DIR}/functions/$1"
}

## Points to a local directory where temporary files for the testing environment can be stored
if [ -z "$LOCAL_TEST_DIR" ]; then
    LOCAL_TEST_DIR=`mktemp -d`
    if [ -z "$LOCAL_TEST_DIR" ]; then
        logError "Could not create temporary local test directory"
        fail
    fi
    mkdir "${LOCAL_TEST_DIR}/tmp"
    addCleanupCommand "rm -rf \"$LOCAL_TEST_DIR\""
else
    if [ ! -d "$LOCAL_TEST_DIR" ]; then
        logError "LOCAL_TEST_DIR is set to an invalid path"
        fail
    fi
    if [ -e "${LOCAL_TEST_DIR}/tmp" ]; then
        logError "${LOCAL_TEST_DIR}/tmp already exists, but was not expected to exist."
        fail
    fi
    addCleanupCommand "rm -rf \"${LOCAL_TEST_DIR}/tmp/\""
    mkdir -p "${LOCAL_TEST_DIR}/tmp/"
fi

## Points to a local directory where results from the campaign will be stored
if [ -z "$RESULTS_DIR" ]; then
    if [ ! -d "${TEST_ENV_DIR}/../Results" ]; then
        mkdir "${TEST_ENV_DIR}/../Results"
        if [ ! -d "${TEST_ENV_DIR}/../Results" ]; then
            logError "Could not create default results directory \"${TEST_ENV_DIR}/../Results\""
            fail
        fi
    fi
    RESULTS_DIR="${TEST_ENV_DIR}/../Results"
else
    if [ ! -d "${RESULTS_DIR}" ]; then
        logError "RESULTS_DIR is not set to a valid path"
        fail
    fi
fi

# = Load base functions #
loadFunctionsScript basefunctions.sh

# = Load the parsing function #
loadFunctionsScript parsing.sh

# === Read and run the campaign script ===
# Why is it a function? Because functions introduce scope for local variables
function run_campaign() {
    # Check whether campaign file exists
    local CAMPAIGN_FILE=$1
    if [ ! -f "${CAMPAIGN_FILE}" ]; then
        logError "Campaign file \"${CAMPAIGN_FILE}\" not found"
        fail
    fi

    # Set some local variables specific for the campaign
    local CAMPAIGN_ID=$(date +%Y.%m.%d-%H.%M.%S)
    local CAMPAIGN_NAME="`basename ${CAMPAIGN_FILE%\.*}`-$CAMPAIGN_ID" # Clean up campaign file to reduce it to the name and add the ID

    ## points to the local directory where results for the current campaign will be stored under; will be set to ${RESULTS_DIR}/${CAMPAIGN_NAME} for each campaign
    CAMPAIGN_RESULTS_DIR="${RESULTS_DIR}/${CAMPAIGN_NAME}"
    # check that it doesn't exist yet and create it
    if [ -e "${CAMPAIGN_RESULTS_DIR}" ]; then
        logError "Campaign results directory \"${CAMPAIGN_RESULTS_DIR}\" already exists?"
        fail
    fi
    mkdir "${CAMPAIGN_RESULTS_DIR}"
    if [ ! -d "${CAMPAIGN_RESULTS_DIR}" ]; then
        logError "Could not create campaign results directory \"${CAMPAIGN_RESULTS_DIR}\""
        fail
    fi

    ## points to a file that contains the error log for the current campaign; will be set to ${CAMPAIGN_RESULTS_DIR}/err.log
    CAMPAIGN_ERROR_LOG="${CAMPAIGN_RESULTS_DIR}/err.log"
    # create it
    touch "${CAMPAIGN_ERROR_LOG}"
    if [ ! -e "${CAMPAIGN_ERROR_LOG}" ]; then
        logError "Could not create campaign error log \"${CAMPAIGN_ERROR_LOG}\""
        fail
    fi

    ##
    # Log an error in the campaign error log.
    # This is just a convenience function for writing a line to ${CAMPAIGN_ERROR_LOG}
    #
    # @param    A string: the line to be logged
    ##
    function logError() {
        if [ $# -eq 0 ]; then
            return
        fi
        echo $1 >> "${CAMPAIGN_ERROR_LOG}"
    }

    echo "Reading campaign from campaign file ${CAMPAIGN_FILE}"
    echo "Results will be stored in ${CAMPAIGN_RESULTS_DIR}"

    # Compact campaign file
    # Do not throw away empty lines or comment lines: that would corrupt the line number count
    cat "${CAMPAIGN_FILE}" | sed -e"s/^[\t ]*//" | sed -e"s/[\t ]*$//" | sed -e"s/#.*//" > "${LOCAL_TEST_DIR}/campaign-file"
    if [ ! -f "${LOCAL_TEST_DIR}/campaign-file" ]; then
        logError "Could not compact the campaign file to ${LOCAL_TEST_DIR}/campaign-file"
        fail
    fi

    # = Parse scenarios and set them up =
    local LINE=""
    local scenarioName=""
    local scenarioFiles=( )
    LINE_NUMBER=1
    local scenarioLine=0
    SCENARIO_TIMELIMIT=300
    while IFS="" read LINE; do
        if [ "$LINE" = "" ]; then
            LINE_NUMBER=$((LINE_NUMBER + 1))
            continue
        fi
        if isSectionHeader "$LINE"; then
            # New section, extract section name and check that it's a scenario
            local sectionName=`getSectionName "$LINE"`
            checkFail
            if [ ! $sectionName = "scenario" ]; then
                logError "Unexpected section name $sectionName in campaign file. Only scenario sections are allowed in campaign files."
                fail
            fi
            # New scenario, so check sanity of the old one, but not for the scenario before the first scenario
            if [ ! $scenarioLine -eq 0 ]; then
                if [ -z "$scenarioName" ]; then
                    logError "Scenario started on line $scenarioLine has no name parameter"
                    fail
                fi
                if [ ${#scenarioFiles[@]} -eq 0 ]; then
                    logError "Scenario $scenarioName does not specify any files that describe the scenario"
                    fail
                fi
            fi
            # New scenario is OK, let's initialize for the next one
            scenarioName=""
            scenarioFiles=( )
            scenarioLine=$LINE_NUMBER
            SCENARIO_TIMELIMIT=300
        else
            # Not a section, so should be a parameter
            local parameterName=`getParameterName "$LINE"`
            checkFail
            local parameterValue=`getParameterValue "$LINE"`
            if [ $scenarioLine -eq 0 ]; then
                logError "Did not expect parameters before any section header (line $LINE_NUMBER)"
                fail
            fi
            case $parameterName in
                name)
                    # The name of the scenario: check uniqueness, validity as directory name and create directory
                    if [ ! -z $scenarioName ]; then
                        logError "Scenario started on line $scenarioLine has two names: $scenarioName and $parameterValue; only one name is allowed (line $LINE_NUMBER)"
                        fail
                    fi
                    if ! isValidName "$parameterValue"; then
                        logError "\"$parameterValue\" is not a valid scenario name"
                        fail
                    fi
                    if [ -e "${CAMPAIGN_RESULTS_DIR}/$parameterValue" ]; then
                        logError "Scenario started at line $scenarioLine has the same name as a previous scenario: $parameterValue"
                        fail
                    fi
                    mkdir -p "${CAMPAIGN_RESULTS_DIR}/scenarios/$parameterValue"
                    if [ ! -e "${CAMPAIGN_RESULTS_DIR}/scenarios/$parameterValue" ]; then
                        logError "Could not create result directory \"${CAMPAIGN_RESULTS_DIR}/scenarios/$parameterValue\" for scenario $parameterValue"
                        fail
                    fi
                    scenarioName="$parameterValue"
                    ;;
                file)
                    # A file for the scenario: check existence and add to files array
                    local file="$parameterValue"
                    if [ "${file:0:1}" != "/" ]; then
                        file="${TEST_ENV_DIR}/../$parameterValue"
                    fi
                    if [ ! -f "$parameterValue" ]; then
                        logError "Scenario file \"$parameterValue\" does not exist"
                        fail
                    fi
                    scenarioFiles[${#scenarioFiles[@]}]="${file}"
                    ;;
                timelimit)
                    # Time limit for the execution of a scenario, in seconds
                    if echo "$parameterValue" | grep -E "[^[:digit:]]" >/dev/null; then
                        logError "The time limit for the scenario defined on line $scenarioLine should be given in seconds, which is a positive integer value, unlike \"$parameterValue\"."
                        fail
                    fi
                    if [ "$parameterValue" -eq 0 ]; then
                        logError "The time limit for the scenario defined on line $scenarioLine should be larger than 0."
                        fail
                    fi
                    SCENARIO_TIMELIMIT="$parameterValue"
                    ;;
                default)
                    logError "Unsupported parameter $parameterName found on line $LINE_NUMBER, ignoring"
                    ;;
            esac
        fi
        LINE_NUMBER=$((LINE_NUMBER + 1))
    done < "${LOCAL_TEST_DIR}/campaign-file"
    # Check sanity of the last scenario
    if [ -z "$scenarioName" ]; then
        logError "Scenario started on line $scenarioLine has no name parameter"
        fail
    fi
    if [ ${#scenarioFiles[@]} -eq 0 ]; then
        logError "Scenario $scenarioName does not specify any files that describe the scenario"
        fail
    fi

    # = Reparse and run scenarios =
    echo "Reading scenario"
    # Prepare scenario-file
    rm -f "${LOCAL_TEST_DIR}/scenario-file"
    touch "${LOCAL_TEST_DIR}/scenario-file"
    if [ ! -f "${LOCAL_TEST_DIR}/scenario-file" ]; then
        logError "Scenario file \"${LOCAL_TEST_DIR}/scenario-file\" could not be created"
        fail
    fi
    # Reread the campaign file
    local firstScenario=1
    while IFS="" read LINE; do
        if [ "$LINE" = "" ]; then
            continue
        fi
        if isSectionHeader "$LINE"; then
            # New section, it is already checked, so this is a new scenario: run the one just read
            if [ $firstScenario -eq 1 ]; then
                firstScenario=0
            else
                echo "Running scenario $scenarioName"
                local CWD=`pwd`
                . "${TEST_ENV_DIR}/run_scenario.sh" "$scenarioName" "${LOCAL_TEST_DIR}/scenario-file"
                cd "${CWD}"
                echo "Reading scenario"
            fi
            # Initialize for the next scenario
            # Prepare scenario file
            rm -f "${LOCAL_TEST_DIR}/scenario-file"
            touch "${LOCAL_TEST_DIR}/scenario-file"
            if [ ! -f "${LOCAL_TEST_DIR}/scenario-file" ]; then
                logError "Scenario file \"${LOCAL_TEST_DIR}/scenario-file\" could not be created"
                fail
            fi
        else
            # Not a section, so should be a parameter
            local parameterName=`getParameterName "$LINE"`
            checkFail
            local parameterValue=`getParameterValue "$LINE"`
            case $parameterName in
                name)
                    # The name of the scenario: already checked, just use
                    scenarioName="$parameterValue"
                    ;;
                file)
                    # A file for the scenario: already checked, just use
                    local file="$parameterValue"
                    if [ "${file:0:1}" != "/" ]; then
                        file="${TEST_ENV_DIR}/../$parameterValue"
                    fi
                    echo "# ${file}" >> "${LOCAL_TEST_DIR}/scenario-file"
                    cat ${file} | sed -e"s/^[\t ]*//" | sed -e"s/[\t ]*$//" | sed -e"s/#.*//" >> "${LOCAL_TEST_DIR}/scenario-file"
                    ;;
                *)
                    # Already logged, just ignore
                    ;;
            esac
        fi
    done < "${LOCAL_TEST_DIR}/campaign-file"
    # Run the last read scenario
    echo "Running scenario $scenarioName"
    local CWD=`pwd`
    . "${TEST_ENV_DIR}/run_scenario.sh" "$scenarioName" "${LOCAL_TEST_DIR}/scenario-file"
    cd "${CWD}"

    # Reset the logError function
    loadFunctionsScript stderrlogging.sh
}

run_campaign $1

cleanup

# Just an empty line; increases readability when running
echo

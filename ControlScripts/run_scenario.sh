#!/bin/bash
echo "Running scenario $1 with file $2"

# Steps in running a scenario:
# 1. Check sanity of arguments
# 2. Parse and validate the whole scenario
# 3. Find out which hosts/clients/files are used and in which combinations; prepare them
# 4. Start all executions
# 5. Monitor executions until all have finished or time is up
# 6. End all executions
# 7. Retrieve and parse all log files
# 8. Process the raw and parsed log files
# 9. Create views for the data
# 10. Clean up

# === Check arguments ===
if [ ! $# -eq 3 ]; then
    echo "Do not call run_scenario directly" 1>&2
    exit -1
fi
if [ -z "${CAMPAIGN_RESULTS_DIR}" ]; then
    echo "Do not call run_scenario directly" 1>&2
    exit -1
fi
if [ ! -f $2 ]; then
    echo "Do not call run_scenario directly" 1>&2
    exit -1
fi
# Environment should be sane at this point: we have 2 arguments and a campaign seems to have been loaded in the environment.
# For those wishing to hack: PLEASE don't try and run this script directly on a scenario file by faking stuff; just create a campaign file of 3 lines

##
# Fails but only after attempting to back up the complete scenario file.
# This function will never return.
#
# @param    The scenario file to backup.
# @param    Optionally the argument to pass on to fail.
##
function failScenarioFile() {
    if [ -e "${CAMPAIGN_RESULTS_DIR}/failed_scenario_file.log" ]; then
        logError "Could not copy the failing scenario file to ${CAMPAIGN_RESULTS_DIR}/failed_scenario_file.log : file already exists"
        fail $2
    fi
    local res=`cp "$1" "${CAMPAIGN_RESULTS_DIR}/failed_scenario_file.log" 2>&1`
    logError $res
    if [ ! -f "${CAMPAIGN_RESULTS_DIR}/failed_scenario_file.log" ]; then
        logError "Could not copy the failing scenario file to ${CAMPAIGN_RESULTS_DIR}/failed_scenario_file.log : file did not copy"
        fail $2
    fi
    logError "Failing scenario file was backed up to ${CAMPAIGN_RESULTS_DIR}/failed_scenario_file.log"
    fail $2
}

##
# Checks whether failure is required, like checkFail, but fails using failScenarioFile instead of just fail.
#
# Usage is equal to checkFail.
#
# @param    The scenario file to backup.
# @param    Optionally the argument to pass on to fail.
##
function checkFailScenarioFile() {
    if checkFailReturn; then
        cleanFailSignal
        failScenarioFile "$1" "$2"
    fi
}

##
# Loads the module specified in the first argument.
# The module is expected to be found in ${TEST_ENV_DIR}/modules/$1.
# If the module can't be loaded this function fails.
#
# @param    The name of the module. May contain / for submodules.
##
function loadModule() {
    if ! existsModule "$1"; then  
        logError "Module \"${TEST_ENV_DIR}/modules/$1\" does not exist, but needs to be loaded"
        fail
    fi
    . "${TEST_ENV_DIR}/modules/$1"
}

##
# Returns whether the specified module exists.
# The module is expected to be found in ${TEST_ENV_DIR}/modules/$1.
#
# @param    The name of the module. May contain / for submodules.
#
# @return   True (0) iff the module exists.
##
function existsModule() {
    if [ -f "${TEST_ENV_DIR}/modules/$1" ]; then
        return 0
    fi
    return 1
}

##
# === Parse and run the scenario file ===
# The scenario file has already been concatenated and cleaned, so no need to compact/clean anymore
# Why is it a function? Because functions introduce scope for local variables
#
# @param    Scenario name
# @param    Path to a local file containing the full scenario description
# @param    1 if only a test run needs to be done (i.e. no actual running of clients, just do as much checks as possible before starting)
##
function runScenario() {
    SCENARIO_NAME=$1
    local scenarioFile=$2
    local testOnly=0
    if [ "$3" = "1" ]; then
        testOnly=1
    fi

    local APIVersion=`echo "1.0.2"`

    mkdir -p "${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/"
    cp "$scenarioFile" "${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/scenarioFile"

    local LINE=""
    LINE_NUMBER=1
    local objectLine=0
    local objectParameters=( )
    local moduleType=""
    local moduleSubType=""
    local sectionName=""
    local currLineNumer=0
    EXECUTION_COUNT=0
    PROCESSOR_COUNT=0
    VIEWER_COUNT=0
    HOSTS=""
    CLIENTS=""
    FILES=""
    while IFS="" read LINE; do
        echo "Parsing $LINE" 1>&2
        if [ "${LINE:0:1}" = "#" ]; then
            # Injected comments of which file is being written: these should be removed
            LINE=""
        fi
        if isSectionHeader "$LINE"; then
            # Fire off setting parser for specified object
            if [ ! $objectLine -eq 0 ]; then
                rm -f "${LOCAL_TEST_DIR}/object-settings"
                if [ -e "${LOCAL_TEST_DIR}/object-settings" ]; then
                    logError "Could not create new object settings file ${LOCAL_TEST_DIR}/object-settings : already exists and can't remove"
                    fail
                fi
                touch "${LOCAL_TEST_DIR}/object-settings"
                if [ ! -f "${LOCAL_TEST_DIR}/object-settings" ]; then
                    logError "Could not create new object settings file ${LOCAL_TEST_DIR}/object-settings : can't touch"
                    fail
                fi
                for index in `seq 0 $((${#objectParameters[@]} - 1))`; do
                    echo "${objectParameters[index]}" >> "${LOCAL_TEST_DIR}/object-settings"
                done
                eval "function ${moduleType}APIVersion__default() { echo "wrong"; }"
                function parseAPIVersion() {
                    echo "wrong"
                }
                loadModule "$moduleType/_defaults_"
                if [ "`${moduleType}APIVersion__default`" != $APIVersion ]; then
                    logError "API version mismatch: the core expects API version $APIVersion, but module $moduleType seems to have defaults for version `${moduleType}APIVersion__default`."
                    fail
                fi
                loadModule "$moduleType/_parser_.sh"
                if [ "`parseAPIVersion`" != $APIVersion ]; then
                    logError "API version mismatch: the core expects API version $APIVersion, but module $moduleType seems to have a parser for version `parseAPIVersion`."
                    fail
                fi
                currLineNumber=$LINE_NUMBER
                local LINESAVER="$LINE" # Needed since local is apparently not local enough. LINE will be destroyed after calling parseSettings.
                parseSettings "$moduleType" "$moduleSubType" "$objectLine" "${LOCAL_TEST_DIR}/object-settings" $SCENARIO_NAME $scenarioFile
                LINE=$LINESAVER
                LINE_NUMBER=$currLineNumber
            fi

            # Parse header for next object
            sectionName=`getSectionName $LINE`
            checkFailScenarioFile "$scenarioFile"
            moduleType=`getModuleType $sectionName`
            moduleSubType=`getModuleSubType $sectionName`
            objectLine=$LINE_NUMBER
            objectParameters=( )
            case $moduleType in
                host|client|file|parser|processor|viewer)
                    if [ -z $moduleSubType ]; then
                        logError "A $moduleType module must have a sub type (line $LINE_NUMBER)"
                        failScenarioFile "$scenarioFile"
                    fi
                    ;;
                execution)
                    ;;
                *)
                    logError "Unknown object type found: \"$moduleType\" (subtype: \"$moduleSubType\", full section name: \"$sectionName\") on line $LINE_NUMBER of scenario $SCENARIO_NAME"
                    failScenarioFile "$scenarioFile"
                    ;;
            esac
        else
            objectParameters[${#objectParameters[@]}]="$LINE"
        fi
        LINE_NUMBER=$((LINE_NUMBER + 1))
    done < $scenarioFile;
    if [ $objectLine -eq 0 ]; then
        logError "No objects found in scenario $SCENARIO_NAME"
        failScenarioFile "$scenarioFile"
    fi
    # Fire off setting parser for last specified object
    rm -f "${LOCAL_TEST_DIR}/object-settings"
    if [ -e "${LOCAL_TEST_DIR}/object-settings" ]; then
        logError "Could not create new object settings file ${LOCAL_TEST_DIR}/object-settings : already exists and can't remove"
        fail
    fi
    touch "${LOCAL_TEST_DIR}/object-settings"
    if [ ! -f "${LOCAL_TEST_DIR}/object-settings" ]; then
        logError "Could not create new object settings file ${LOCAL_TEST_DIR}/object-settings : can't touch"
        fail
    fi
    for index in `seq 0 $((${#objectParameters[@]} - 1))`; do
        echo "${objectParameters[index]}" >> "${LOCAL_TEST_DIR}/object-settings"
    done
    eval "function ${moduleType}APIVersion__default() { echo "wrong"; }"
    function parseAPIVersion() {
        echo "wrong"
    }
    loadModule "$moduleType/_defaults_"
    if [ "`${moduleType}APIVersion__default`" != $APIVersion ]; then
        logError "API version mismatch: the core expects API version $APIVersion, but module $moduleType seems to have defaults for version `${moduleType}APIVersion__default`."
        fail
    fi
    loadModule "$moduleType/_parser_.sh"
    if [ "`parseAPIVersion`" != $APIVersion ]; then
        logError "API version mismatch: the core expects API version $APIVersion, but module $moduleType seems to have a parser for version `parseAPIVersion`."
        fail
    fi
    currLineNumber=$LINE_NUMBER
    parseSettings "$moduleType" "$moduleSubType" "$objectLine" "${LOCAL_TEST_DIR}/object-settings" $SCENARIO_NAME $scenarioFile
    LINE_NUMBER=$currLineNumber
    echo "Parsing done"

    if [ $EXECUTION_COUNT -lt 1 ]; then
        logError "No executions defined for scenario $SCENARIO_NAME."
        failScenarioFile "$scenarioFile"
    fi
    function executionAPIVersion() {
        echo "wrong"
    }
    loadModule "execution/execution"
    if [ "`executionAPIVersion__default`" != $APIVersion ]; then
        logError "API version mismatch: the core expects API version $APIVersion, but module execution seems to have defaults for version `executionAPIVersion__default`."
        fail
    fi

    local currExec=0

    mkdir -p "${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/executions/"

    echo "Preparing all objects for execution"

    # Collect all hosts from the executions
    local executionhosts=( )
    local found=0
    for currExec in `seq 0 $(($EXECUTION_COUNT - 1))`; do
        local currExec__internal__saved=$currExec
        executionLoadSettings $currExec
        currExec=$currExec__internal__saved

        found=0
        if [ ${#executionhosts[@]} -gt 0 ]; then
            for index in `seq 0 $((${#executionhosts[@]} - 1))`; do
                if [ "$EXECUTION_HOST" = "${executionhosts[index]}" ]; then
                    found=1
                    break
                fi
            done
        fi
        if [ $found -eq 0 ]; then
            executionhosts[${#executionhosts[@]}]="$EXECUTION_HOST"
        fi
    done

    # Prepare all hosts
    for index in `seq 0 $((${#executionhosts[@]} - 1))`; do
        local index__internal__saved=$index
        hostLoadSettings ${executionhosts[index]}
        hostPrepare
        index=$index__internal__saved
    done

    # Executions list may be altered by the hostPrepare calls, build the executionhosts list again
    # All executions should refer to prepared hosts, which means that a hostPrepare that alters the executions
    # must take precautions to ensure this.
    executionhosts=( )
    for currExec in `seq 0 $(($EXECUTION_COUNT - 1))`; do
        local currExec__internal__saved=$currExec
        executionLoadSettings $currExec
        currExec=$currExec__internal__saved

        found=0
        if [ ${#executionhosts[@]} -gt 0 ]; then
            for index in `seq 0 $((${#executionhosts[@]} - 1))`; do
                if [ "$EXECUTION_HOST" = "${executionhosts[index]}" ]; then
                    found=1
                    break
                fi
            done
        fi
        if [ $found -eq 0 ]; then
            executionhosts[${#executionhosts[@]}]="$EXECUTION_HOST"
        fi
    done

    # Prepare all clients
    local client
    for client in $CLIENTS; do
        clientLoadSettings "$client"
        clientPrepare
    done

    # Collect all used hostnames (for traffic control purposes)
    local hostnames=( )
    for host in $HOSTS; do
        hostLoadSettings $host
        local found=0
        local myhostname=`hostGetSubnet`
        for index2 in `seq 0 $((${#hostnames[@]} - 1))`; do
            if [ "${hostnames[index2]}" = "$myhostname" ]; then
                found=1
                break
            fi
        done
        if [ $found -eq 0 ]; then
            hostnames[${#hostnames[@]}]="$myhostname"
        fi
    done

    # Prepare the hosts and files
    for index in `seq 0 $((${#executionhosts[@]} - 1))`; do
        local index__internal__saved=$index
        hostLoadSettings ${executionhosts[index]}
        # hostPrepare has already been called, or the host has been prepared otherwise
        index=$index__internal__saved

        # Collect all files and clients to be used on this host from the executions
        local files=( )
        local seedingFiles=( )
        local hostclients=( )
        for currExec in `seq 0 $(($EXECUTION_COUNT - 1))`; do
            local currExec__internal__saved=$currExec
            executionLoadSettings $currExec
            currExec=$currExec__internal__saved
            if [ "$EXECUTION_HOST" != "${executionhosts[index]}" ]; then
                continue
            fi

            if executionIsSeeder; then
                found=0
                if [ ${#seedingFiles[@]} -gt 0 ]; then
                    for index2 in `seq 0 $((${#seedingFiles[@]} - 1))`; do
                        if [ "$EXECUTION_FILE" = "${seedingFiles[index2]}" ]; then
                            found=1
                            break
                        fi
                    done
                fi
                if [ $found -eq 0 ]; then
                    seedingFiles[${#seedingFiles[@]}]="$EXECUTION_FILE"
                fi
            fi

            found=0
            if [ ${#files[@]} -gt 0 ]; then
                for index2 in `seq 0 $((${#files[@]} - 1))`; do
                    if [ "$EXECUTION_FILE" = "${files[index2]}" ]; then
                        found=1
                        break
                    fi
                done
            fi
            if [ $found -eq 0 ]; then
                files[${#files[@]}]="$EXECUTION_FILE"
            fi

            found=0
            if [ ${#hostclients[@]} -gt 0 ]; then
                for index2 in `seq 0 $((${#hostclients[@]} - 1))`; do
                    if [ "$EXECUTION_CLIENT" = "${hostclients[index2]}" ]; then
                        found=1
                        break;
                    fi
                done
            fi
            if [ $found -eq 0 ]; then
                hostclients[${#hostclients[@]}]="$EXECUTION_CLIENT"
            fi
        done

        # Build traffic control instructions for each host, based on how the clients can be controlled
        if [ ! -z "$HOST_TC" ]; then
            # Sanity check: refuse to enable traffic control on the commanding host
            if [ "`hostGetSubnet`" = "127.0.0.1" ]; then
                logError "Refusing to enable traffic control on local host $HOST_NAME. This would be a very, very bad idea. Please only use traffic control when commanding a number of remote hosts not including the commanding host."
                fail
            fi

            local tcinbound=1
            local tcoutbound=1
            local tcprotocol=""
            # For tcinbound and tcoutbound: 0 = none, 1 = restricted, 2 = full
            if [ -z "$HOST_TC_DOWN" -a "$HOST_TC_LOSS" = "0.0" -a "$HOST_TC_CORRUPTION" = "0.0" -a "$HOST_TC_DUPLICATION" = "0.0" ]; then
                # If download speed is not restricted and no loss, corruption or duplication, then no inbound traffic control is needed
                tcinbound=0
            fi
            if [ -z "$HOST_TC_UP" -a "$HOST_TC_DELAY" = "0" ]; then
                # If upload speed is not restricted and no delay is introduced, then no outbound traffic control is needed
                tcoutbound=0
            fi
            local inboundrestrictedlist=""
            local outboundrestrictedlist=""
            for index2 in `seq 0 $((${#hostclients[@]} - 1))`; do
                # Go over all clients to see how they think they should be restricted. Aggregate data to be saved in the host.
                local index2__internal__saved=$index2
                clientLoadSettings ${hostclients[index2]}
                if [ -z "$tcprotocol" ]; then
                    tcprotocol="`clientTrafficProtocol`"
                else
                    if [ "$tcprotocol" != "`clientTrafficProtocol`" ]; then
                        # TC at this point only supports restricted control on one protocol
                        logError "Restricted traffic control using multiple protocols is not supported. Falling back to unrestricted traffic control on host $HOST_NAME."
                        if [ $tcinbound -eq 1 ]; then
                            tcinbound=2
                        fi
                        if [ $tcoutbound -eq 1 ]; then
                            tcoutbound=2
                        fi
                        break
                        tcprotocol=""
                    fi
                fi
                if [ $tcinbound -eq 1 ]; then
                    local list=`clientTrafficInboundPorts`
                    if [ "$list" == "" ]; then
                        # If this client can't have restricted inbound traffic control, then go for full inbound
                        logError "Client $CLIENT_NAME can't have restricted inbound traffic control. Falling back to unrestricted inbound traffic control on host $HOST_NAME."
                        tcinbound=2
                        if [ $tcoutbound -ne 1 ]; then
                            break
                        fi
                    else
                        inboundrestrictedlist="$inboundrestrictedlist $list"
                    fi
                fi
                if [ $tcoutbound -eq 1 ]; then
                    local list=`clientTrafficOutboundPorts`
                    if [ "$list" == "" ]; then
                        # If this client can't have restricyed outbound traffic control, the go for full outbound
                        logError "Client $CLIENT_NAME can't have restricted outbound traffic control. Falling back to unrestricted outbound traffic control on host $HOST_NAME."
                        tcoutbound=2
                        if [ $tcinbound -ne 1 ]; then
                            break
                        fi
                    else
                        outboundrestrictedlist="$outboundrestrictedlist $list"
                    fi
                fi
            done
            # Save the data in the host
            case $tcinbound in
                0)
                    hostTCSaveInboundPortList ""
                    ;;
                2)
                    logError "Warning: using unrestricted traffic control for incoming traffic on host $HOST_NAME. If the commanding host (i.e. your terminal) is also part of the nodes you configured for testing, then this WILL cause trouble."
                    hostTCSaveInboundPortList "-1"
                    ;;
                1)
                    hostTCSaveInboundPortList "$inboundrestrictedlist"
                    ;;
            esac
            case $tcoutbound in
                0)
                    hostTCSaveOutboundPortList ""
                    ;;
                2)
                    logError "Warning: using unrestricted traffic control for outgoing traffic on host $HOST_NAME. If the commanding host (i.e. your terminal) is also part of the nodes you configured for testing, then this WILL cause trouble."
                    hostTCSaveOutboundPortList "-1"
                    ;;
                1)
                    hostTCSaveOutboundPortList "$outboundrestrictedlist"
                    ;;
            esac
            hostTCSaveProtocol "$tcprotocol"
            # Check whether the currently configured traffic control is possible
            loadModule "tc/$HOST_TC"
            if ! tcCheck; then
                # Try to fall back to full control and see if that works
                if [ "$HOST_TC_INBOUNDPORTS" != "-1" -a "$HOST_TC_INBOUNDPORTS" != "" ]; then
                    local __host_tc_inboundports_cache="$HOST_TC_INBOUNDPORTS"
                    hostTCSaveInboundPortList "-1"
                    if tcCheck; then
                        logError "Host $HOST_NAME could not initiate restricted inbound traffic control, falling back to unrestricted traffic control."
                        logError "Warning: using unrestricted traffic control for incoming traffic on host $HOST_NAME. If the commanding host (i.e. your terminal) is also part of the nodes you configured for testing, then this WILL cause trouble."
                    else
                        if [ "$HOST_TC_OUTBOUNDPORTS" != "-1" -a "$HOST_TC_OUTBOUNDPORTS" != "" ]; then
                            hostTCSaveInboundPortList "$__host_tc_inboundports_cache"
                            hostTCSaveOutboundPortList "-1"
                            if tcCheck; then
                                logError "Host $HOST_NAME could not initiate restricted outbound traffic control, falling back to unrestricted traffic control."
                                logError "Warning: using unrestricted traffic control for outgoing traffic on host $HOST_NAME. If the commanding host (i.e. your terminal) is also part of the nodes you configured for testing, then this WILL cause trouble."
                            else
                                hostTCSaveInboundPortList "-1"
                                if tcCheck; then
                                    logError "Host $HOST_NAME could not initiate restricted inbound or outbound traffic control, falling back to unrestricted traffic control."
                                    logError "Warning: using unrestricted traffic control for incoming traffic on host $HOST_NAME. If the commanding host (i.e. your terminal) is also part of the nodes you configured for testing, then this WILL cause trouble."
                                    logError "Warning: using unrestricted traffic control for outgoing traffic on host $HOST_NAME. If the commanding host (i.e. your terminal) is also part of the nodes you configured for testing, then this WILL cause trouble."
                                else
                                    logError "Host $HOST_NAME could not initiate restricted or unrestricted traffic control, but traffic control was requested."
                                    fail
                                fi
                            fi
                        else
                            logError "Host $HOST_NAME could not inititate restricted or unrestricted inbound traffic control, but traffic control was requested."
                            fail
                        fi
                    fi
                else
                    if [ "$HOST_TC_OUTBOUNDPORTS" != "-1" -a "$HOST_TC_OUTBOUNDPORTS" != "" ]; then
                        hostTCSaveOutboundPortList "-1"
                        if tcCheck; then
                            logError "Host $HOST_NAME could not initiate restricted outbound traffic control, falling back to unrestricted traffic control."
                            logError "Warning: using unrestricted traffic control for outgoing traffic on host $HOST_NAME. If the commanding host (i.e. your terminal) is also part of the nodes you configured for testing, then this WILL cause trouble."
                        else
                            logError "Host $HOST_NAME could not initiate restricted or unrestricted outbound traffic control, but traffic control was requested."
                            fail
                        fi
                    else
                        logError "Host $HOST_NAME could not initiate the requested traffic control."
                        fail
                    fi
                fi
            fi
            # At this point, either tcCheck passes and the right settings have thus been saved, or we have already failed (and hence never reached this point)
        fi

        # Everything after this point is for the actual execution only
        if [ $testOnly -eq 0 ]; then
            # Prepare all files for this host
            for index2 in `seq 0 $((${#files[@]} - 1))`; do
                local index2__internal__saved=$index2
                fileLoadSettings ${files[index2]}
                fileSendToHost
                index2=$index2__internal__saved
            done

            # Prepare all files for this host, if seeding is needed
            if [ ${#seedingFiles[@]} -gt 0 ]; then
                for index2 in `seq 0 $((${#seedingFiles[@]} - 1))`; do
                    local index2__internal__saved=$index2
                    fileLoadSettings ${seedingFiles[index2]}
                    fileSendToSeedingHost
                    index2=$index2__internal__saved
                done
            fi

            # Prepare all clients for this host
            for index2 in `seq 0 $((${#hostclients[@]} - 1))`; do
                local index2__internal__saved=$index2
                clientLoadSettings ${hostclients[index2]}
                clientPrepareHost
                index2=$index2__internal__saved
            done
        fi
    done

    # When we're just testing, we're about done now
    if [ $testOnly -eq 1 ]; then
        echo "Cleaning up hosts"

        # Clean up the hosts
        for index in `seq $((${#executionhosts[@]} - 1)) -1 0`; do
            local index__internal__saved=$index
            hostLoadSettings ${executionhosts[index]}
            hostCleanup
            index=$index__internal__saved
        done

        echo "Cleaning up client objects"

        # Final cleanup of all clients
        for client in $CLIENTS; do
            clientLoadSettings "$client"
            clientCleanupFinal
        done

        echo "Cleaning up scenario"
        
        # Clean temporary data for scenario
        rm -rf "${LOCAL_TEST_DIR}/clients/"
        rm -rf "${LOCAL_TEST_DIR}/executions/"
        rm -rf "${LOCAL_TEST_DIR}/files/"
        rm -rf "${LOCAL_TEST_DIR}/hosts/"
        rm -rf "${LOCAL_TEST_DIR}/parsers/"
        rm -rf "${LOCAL_TEST_DIR}/processors/"
        rm -rf "${LOCAL_TEST_DIR}/viewers/"

        # Since we were only testing: clean results as well
        rm -rf "${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/"
        
        echo "Scenario \"$SCENARIO_NAME\" checked"
        return
    fi

    # Prepare all clients
    for currExec in `seq 0 $(($EXECUTION_COUNT - 1))`; do
        local currExec__internal__saved=$currExec
        executionLoadSettings $currExec
        executionLoadHost
        executionLoadFile
        executionLoadClient

        clientPrepareExecution
        currExec=$currExec__internal__saved
    done

    echo "Setting up traffic control where requested"

    addCleanupScript
    local scenario_cleanup_tc_script_idx=$?
    # Since traffic control is rather invasive, don't try and load it before all hosts have been checked.
    for index in `seq 0 $((${#executionhosts[@]} - 1))`; do
        local index__internal__saved=$index
        hostLoadSettings ${executionhosts[index]}
        index=$index__internal__saved

        if [ -z "$HOST_TC" ]; then
            # No traffic control requested for this host: skip
            continue
        fi

        local otherhostnames=""
        local myhostname="`hostGetSubnet`"
        for index2 in `seq 0 $((${#hostnames[@]} - 1))`; do
            if [ "${hostnames[index2]}" = "$myhostname" ]; then
                continue
            fi
            if [ "${hostnames[index2]}" = "127.0.0.1" ]; then
                logError "Refusing to set up traffic control to 127.0.0.1 on host $HOST_NAME. This would be a very, very bad idea."
                fail
            fi
            otherhostnames="$otherhostnames ${hostnames[index2]}"
        done

        loadModule "tc/$HOST_TC"
        addCleanupCommand "hostLoadSettings \"${executionhosts[index]}\"" $scenario_cleanup_tc_script_idx
        addCleanupCommand "loadModule \"tc/$HOST_TC\"" $scenario_cleanup_tc_script_idx
        addCleanupCommand "(tcRemove)" $scenario_cleanup_tc_script_idx
        (tcInstall $otherhostnames)
    done

    echo "Starting all clients"

    # For each execution: fork off a process that will run the client
    for currExec in `seq 0 $(($EXECUTION_COUNT - 1))`; do
        local currExec__internal__saved=$currExec
        executionLoadSettings $currExec
        executionLoadHost
        executionLoadClient
        executionLoadFile

        clientStart &
        currExec=$currExec__internal__saved
    done

    echo "Running..."

    # While the time limit has not passed yet, keep checking whether all clients have ended, sleeping up to 5 seconds in between each check (note that a check takes time as well)
    local endTime=$(($SCENARIO_TIMELIMIT + `date +%s`))
    local sleepTime=$(($endTime - `date +%s`))
    local clientsDone=0
    while [ $sleepTime -gt 0 ]; do
        if [ $sleepTime -gt 5 ]; then
            sleepTime=5
        fi
        sleep $sleepTime
        clientsDone=1
        for currExec in `seq 0 $(($EXECUTION_COUNT - 1))`; do
            local currExec__internal__saved=$currExec
            executionLoadSettings $currExec
            executionLoadHost
            executionLoadClient

            if clientRunning; then
                clientsDone=0
                break
            fi
            currExec=$currExec__internal__saved
        done
        if [ $clientsDone -eq 1 ]; then
            echo "All clients have finished before time was up"
            break
        fi
        sleepTime=$(($endTime - `date +%s`))
    done

    echo "All clients should be done now, checking and killing if needed."

    # Either all clients are done, or clients should be killed because the time limit passed
    for currExec in `seq 0 $(($EXECUTION_COUNT - 1))`; do
        local currExec__internal__saved=$currExec
        executionLoadSettings $currExec
        executionLoadHost
        executionLoadClient

        if clientRunning; then
            clientKill
        fi
        currExec=$currExec__internal__saved
    done
    
    # Wait for all child processes, i.e. the clients, to finish
    wait

    echo "Removing any traffic control from hosts"
    # Immediately after all running has been done, not a step later
    for index in `seq 0 $((${#executionhosts[@]} - 1))`; do
        local index__internal__saved=$index
        hostLoadSettings ${executionhosts[index]}
        index=$index__internal__saved

        if [ -z "$HOST_TC" ]; then
            # No traffic control requested for this host: skip
            continue
        fi

        loadModule "tc/$HOST_TC"
        (tcRemove)
    done
    removeCleanupScript $scenario_cleanup_tc_script_idx

    echo "Retrieving logs and parsing them"

    # Retrieve logs for all executions and have them parsed
    for currExec in `seq 0 $(($EXECUTION_COUNT - 1))`; do
        local currExec__internal__saved=$currExec
        executionLoadSettings $currExec
        executionLoadHost
        executionLoadClient

        local execdir="${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/executions/exec_`executionNumber`"
        mkdir -p "$execdir/"

        mkdir -p "$execdir/logs/"
        clientRetrieveLogs "$execdir/logs/"

        mkdir -p "$execdir/parsedLogs/"
        executionRunParsers "$execdir/logs/" "$execdir/parsedLogs"
        currExec=$currExec__internal__saved
    done

    echo "Cleaning up executions"
    
    # Clean up all clients for executions, immediately build list with clients
    local allClients=( )
    for currExec in `seq 0 $(($EXECUTION_COUNT - 1))`; do
        local currExec__internal__saved=$currExec
        executionLoadSettings $currExec
        executionLoadHost
        executionLoadClient
        executionLoadFile

        clientCleanupExecution

        currExec=$currExec__internal__saved
    done

    # Clean up the hosts
    for index in `seq $((${#executionhosts[@]} - 1)) -1 0`; do
        local index__internal__saved=$index
        hostLoadSettings ${executionhosts[index]}

        # Collect all clients to be used on this host from the executions
        local hostclients=( )
        for currExec in `seq 0 $(($EXECUTION_COUNT - 1))`; do
            local currExec__internal__saved=$currExec
            executionLoadSettings $currExec
            currExec=$currExec__internal__saved
            if [ "$EXECUTION_HOST" != "${executionhosts[index]}" ]; then
                continue
            fi

            found=0
            if [ ${#hostclients[@]} -gt 0 ]; then
                for index2 in `seq 0 $((${#hostclients[@]} - 1))`; do
                    if [ "$EXECUTION_CLIENT" = "${hostclients[index2]}" ]; then
                        found=1
                        break;
                    fi
                done
            fi
            if [ $found -eq 0 ]; then
                hostclients[${#hostclients[@]}]="$EXECUTION_CLIENT"
            fi
        done

        # Cleanup all clients for this host
        for index2 in `seq 0 $((${#hostclients[@]} - 1))`; do
            local index2__internal__save=$index2
            clientLoadSettings ${hostclients[index2]}
            clientCleanupHost
            index2=$index2__internal__save
        done

        hostCleanup
        index=$index__internal__saved
    done

    # Final cleanup of all clients
    for client in $CLIENTS; do
        clientLoadSettings "$client"
        clientCleanupFinal
    done

    echo "Processing logs"

    # Run all processors over the logs
    mkdir -p "${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/processed/"
    if [ $PROCESSOR_COUNT -gt 0 ]; then
        for currProc in `seq 0 $(($PROCESSOR_COUNT - 1))`; do
            local currProc__internal__saved=$currProc
            processorLoadSettings $currProc
            processorProcessLogs "${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/executions/" "${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/processed/"
            currProc=$currProc__internal__saved
        done
    fi

    echo "Running viewers"

    # Run all viewers after all data has been processed
    mkdir "${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/views/"
    if [ $VIEWER_COUNT -gt 0 ]; then
        for currView in `seq 0 $(($VIEWER_COUNT - 1))`; do
            local currView__internal__saved=$currView
            viewerLoadSettings $currView
            viewerCreateView "${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/processed/" "${CAMPAIGN_RESULTS_DIR}/scenarios/$SCENARIO_NAME/views/"
            currView=$currView__internal__saved
        done
    fi

    echo "Cleaning up scenario"
    
    # Clean temporary data for scenario
    rm -rf "${LOCAL_TEST_DIR}/clients/"
    rm -rf "${LOCAL_TEST_DIR}/executions/"
    rm -rf "${LOCAL_TEST_DIR}/files/"
    rm -rf "${LOCAL_TEST_DIR}/hosts/"
    rm -rf "${LOCAL_TEST_DIR}/parsers/"
    rm -rf "${LOCAL_TEST_DIR}/processors/"
    rm -rf "${LOCAL_TEST_DIR}/viewers/"

    echo "Scenario \"$SCENARIO_NAME\" has completed"
}

runScenario "$1" "$2" "$3"

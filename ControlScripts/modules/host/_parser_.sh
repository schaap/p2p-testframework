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
        logError "host:_parser_.sh :: parseSettings called with invalid file argument"
        fail
    fi
    
    # Make sure the temp dir for host settings exists
    mkdir -p "${LOCAL_TEST_DIR}/hosts"

    # = Parse generic host options =
    LINE_NUMBER=$(($3 + 1))
    local parameterName=""
    local parameterValue=""
    HOST_NAME=""
    HOST_PREPARATION=""
    HOST_CLEANUP=""
    HOST_REMOTEFOLDER=""
    HOST_SUBTYPE="$2"
    HOST_TC_IFACE=""
    HOST_TC_DOWN=""
    HOST_TC_DOWN_BURST=""
    HOST_TC_UP=""
    HOST_TC_UP_BURST=""
    HOST_TC=""
    HOST_TC_DELAY="0"
    HOST_TC_JITTER="0"
    HOST_TC_LOSS="0.0"
    HOST_TC_DUPLICATION="0.0"
    HOST_TC_CORRUPTION="0.0"
    HOST_TC_INBOUNDPORTS=""
    HOST_TC_OUTBOUNDPORTS=""
    HOST_TC_PROTOCOL=""
    local TCparams=""
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
                if [ ! -z "$HOST_NAME" ]; then
                    logError "host:_parser_.sh :: The host started at line $3 in scenario $5 has multiple names, only one allowed (line $LINE_NUMBER)"
                    failScenarioFile "$6"
                fi
                HOST_NAME=$parameterValue
                if ! isValidName $HOST_NAME; then
                    logError "host:_parser_.sh :: \"$HOST_NAME\" is not a valid name for the host started at line $3 scenario $5 (line $LINE_NUMBER)"
                    failScenarioFile "$6"
                fi
                if [ -e "${LOCAL_TEST_DIR}/hosts/$HOST_NAME" ]; then
                    logError "host:_parser_.sh :: Host $HOST_NAME already exists in scenario $5, defined again at line $3 (line ${LINE_NUMBER})"
                    failScenarioFile "$6"
                fi
                ;;
            preparation)
                if [ ! -z "$HOST_PREPARATION" ]; then
                    logError "host:_parser_.sh :: A host can only have one preparation script (scenario $5, line $LINE_NUMBER)"
                    failScenarioFile "$6"
                fi
                HOST_PREPARATION="$parameterValue"
                ;;
            cleanup)
                if [ ! -z "$HOST_CLEANUP" ]; then
                    logError "host:_parser_.sh :: A host can only have one cleanup script (scenario $5, line $LINE_NUMBER)"
                    failScenarioFile "$6"
                fi
                HOST_CLEANUP="$parameterValue"
                ;;
            remoteFolder)
                if [ ! -z "$HOST_REMOTEFOLDER" ]; then
                    logError "host:_parser_.sh :: A host can only have one remote folder (scenario $5, line $LINE_NUMBER)"
                    failScenarioFile "$6"
                fi
                ;;
            tc_iface)
                if [ -z "$parameterValue" ]; then
                    logError "host:_parser_.sh :: Empty interface for traffic control found in the host defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$HOST_TC_IFACE" ]; then
                    logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 can only have one interface for traffic control. Interface \"$HOST_TC_IFACE\" was already declared and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                HOST_TC_IFACE="$parameterValue"
                ;;
            tc_down)
                if [ -z "$parameterValue" ]; then
                    logError "host:_parser_.sh :: Empty maximum download speed for traffic control found in the host defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$HOST_TC_DOWN" ]; then
                    logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 can only have one maximum download speed for traffic control. \"$HOST_TC_DOWN\" was already declared as maximum download speed and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)?$" > /dev/null; then
                    logError "host:_parser_.sh :: Maximum speeds are to be given as integer, optionally postfixed with 'kbit' or 'mbit' (no postfix for mbit), e.g. 8192kbit or 8mbit. Found \"$parameterValue\" in the host defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)$" > /dev/null; then
                    $parameterValue = "${parameterValue}mbit"
                fi
                TCparams="YES"
                HOST_TC_DOWN="$parameterValue"
                ;;
            tc_down_burst)
                if [ -z "$parameterValue" ]; then
                    logError "host:_parser_.sh :: Empty maximum download burst for traffic control found in the host defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$HOST_TC_DOWN_BURST" ]; then
                    logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 can only have one maximum download burst for traffic control. \"$HOST_TC_DOWN_BURST\" was already declared as maximum download burst and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)?$" > /dev/null; then
                    logError "host:_parser_.sh :: Maximum speeds are to be given as integer, optionally postfixed with 'kbit' or 'mbit' (no postfix for mbit), e.g. 8192kbit or 8mbit. Found \"$parameterValue\" in the host defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)$" > /dev/null; then
                    $parameterValue = "${parameterValue}mbit"
                fi
                HOST_TC_DOWN_BURST="$parameterValue"
                ;;
            tc_up)
                if [ -z "$parameterValue" ]; then
                    logError "host:_parser_.sh :: Empty maximum upload speed for traffic control found in the host defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$HOST_TC_UP" ]; then
                    logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 can only have one maximum upload speed for traffic control. \"$HOST_TC_UP\" was already declared as maximum upload speed and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)?$" > /dev/null; then
                    logError "host:_parser_.sh :: Maximum speeds are to be given as integer, optionally postfixed with 'kbit' or 'mbit' (no postfix for mbit), e.g. 8192kbit or 8mbit. Found \"$parameterValue\" in the host defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)$" > /dev/null; then
                    $parameterValue = "${parameterValue}mbit"
                fi
                TCparams="YES"
                HOST_TC_UP="$parameterValue"
                ;;
            tc_up_burst)
                if [ -z "$parameterValue" ]; then
                    logError "host:_parser_.sh :: Empty maximum upload burst for traffic control found in the host defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$HOST_TC_UP_BURST" ]; then
                    logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 can only have one maximum upload burst for traffic control. \"$HOST_TC_UP_BURST\" was already declared as maximum upload burst and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)?$" > /dev/null; then
                    logError "host:_parser_.sh :: Maximum speeds are to be given as integer, optionally postfixed with 'kbit' or 'mbit' (no postfix for mbit), e.g. 8192kbit or 8mbit. Found \"$parameterValue\" in the host defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)$" > /dev/null; then
                    $parameterValue = "${parameterValue}mbit"
                fi
                HOST_TC_UP_BURST="$parameterValue"
                ;;
            tc)
                if [ ! -z "$HOST_TC"]; then
                    logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 can only have one TC module enabled. tc:$HOST_TC was already enabled and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$parameterValue" ]; then
                    if ! isValidName "$parameterValue"; then
                        logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 was given \"$parameterValue\" as TC module, but that is not a valid module name (line $LINE_NUMBER)."
                        failScenarioFile "$6"
                    fi
                    if ! existsModule "tc:$parameterValue"; then
                        logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 has traffic control enabled with module tc:$parameterValue, but that module does not exist (line $LINE_NUMBER)."
                        failScenarioFile "$6"
                    fi
                    HOST_TC="$parameterValue"
                fi
                ;;
            tc_loss)
                if [ "$parameterValue" != "$HOST_TC_LOSS" ]; then
                    if [ ! -z "$HOST_TC_LOSS" ]; then
                        logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 already has a loss percentage defined (line $LINE_NUMBER)."
                        failScenarioFile "$6"
                    fi
                    if ! echo -n "$parameterValue" | grep -E "^(0|[1-9][0-9]*)\.[0-9][0-9]*$" > /dev/null; then
                        logError "host:_parser_.sh :: The loss percentage for the host defined on line $3 of scenario $5 was given as \"$parameterValue\", but that is not a valid floating point value."
                        failScenarioFile "$6"
                    fi
                    HOST_TC_LOSS="$parameterValue"
                fi
                ;;
            tc_corruption)
                if [ "$parameterValue" != "$HOST_TC_CORRUPTION" ]; then
                    if [ ! -z "$HOST_TC_CORRUPTION" ]; then
                        logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 already has a corruption percentage defined (line $LINE_NUMBER)."
                        failScenarioFile "$6"
                    fi
                    if ! echo -n "$parameterValue" | grep -E "^(0|[1-9][0-9]*)\.[0-9][0-9]*$" > /dev/null; then
                        logError "host:_parser_.sh :: The corruption percentage for the host defined on line $3 of scenario $5 was given as \"$parameterValue\", but that is not a valid floating point value."
                        failScenarioFile "$6"
                    fi
                    HOST_TC_CORRUPTION="$parameterValue"
                fi
                ;;
            tc_duplication)
                if [ "$parameterValue" != "$HOST_TC_DUPLICATION" ]; then
                    if [ ! -z "$HOST_TC_DUPLICATION" ]; then
                        logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 already has a duplication percentage defined (line $LINE_NUMBER)."
                        failScenarioFile "$6"
                    fi
                    if ! echo -n "$parameterValue" | grep -E "^(0|[1-9][0-9]*)\.[0-9][0-9]*$" > /dev/null; then
                        logError "host:_parser_.sh :: The duplication percentage for the host defined on line $3 of scenario $5 was given as \"$parameterValue\", but that is not a valid floating point value."
                        failScenarioFile "$6"
                    fi
                    HOST_TC_DUPLICATION="$parameterValue"
                fi
                ;;
            tc_delay)
                if [ "$parameterValue" != "$HOST_TC_DELAY" ]; then
                    if [ ! -z "$HOST_TC_DELAY" ]; then
                        logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 already has a delay defined (line $LINE_NUMBER)."
                        failScenarioFile "$6"
                    fi
                    if ! echo -n "$parameterValue" | grep -E "^(0|[1-9][0-9]*)$" > /dev/null; then
                        logError "host:_parser_.sh :: The delay for the host defined on line $3 of scenario $5 was given as \"$parameterValue\", but that is not a valid integer value."
                        failScenarioFile "$6"
                    fi
                    HOST_TC_DELAY="$parameterValue"
                fi
                ;;
            tc_jitter)
                if [ "$parameterValue" != "$HOST_TC_JITTER" ]; then
                    if [ ! -z "$HOST_TC_JITTER" ]; then
                        logError "host:_parser_.sh :: The host defined on line $3 of scenario $5 already has a jitter defined (line $LINE_NUMBER)."
                        failScenarioFile "$6"
                    fi
                    if ! echo -n "$parameterValue" | grep -E "^(0|[1-9][0-9]*)$" > /dev/null; then
                        logError "host:_parser_.sh :: The jitter for the host defined on line $3 of scenario $5 was given as \"$parameterValue\", but that is not a valid integer value."
                        failScenarioFile "$6"
                    fi
                    HOST_TC_JITTER="$parameterValue"
                fi
                ;;
            *)
                ;;
        esac
        LINE_NUMBER=$(($LINE_NUMBER + 1))
    done < "$4";

    if [ -z "$HOST_TC_IFACE" ]; then
        HOST_TC_IFACE="eth0"
    fi

    # Check whether TC parameters are valid
    if [ -z "$HOST_TC" ]; then
        if [ "$TCparams" = "YES" ]; then
            logError "host:_parser_.sh :: Some traffic control parameters were specified for the host defined on line $3 of scenario $5, but traffic control was not enabled. Ignoring."
        fi
    fi
    if [ ! -z "$HOST_TC" ]; then
        if [ -z "$TCparams" ]; then
            logError "host:_parser_.sh :: Traffic control was enabled for the host defined on line $3 of scenario $5, but no actual traffic control paramters were given."
            failScenarioFile "$6"
        fi
        if [ ! -z "$HOST_TC_DOWN_BURST" ]; then
            if [ -z "$HOST_TC_DOWN" ]; then
                logError "host:_parser_.sh :: A maximum download burst has been specified in the host defined on line $3 of scenario $5, but no maximum download speed has been specified."
                failScenarioFile "$6"
            else
                local RATE="$HOST_TC_DOWN"
                local BURST="$EXCEUTION_TC_DOWN_BURST"
                if echo "$RATE" | grep "kbit"; then
                    RATE=$((`echo "$RATE" | sed -e "s/kbit//"` * 1024))
                fi
                if echo "$RATE" | grep "mbit"; then
                    RATE=$((`echo "$RATE" | sed -e "s/mbit//"` * 1024 * 1024))
                fi
                if echo "$BURST" | grep "kbit"; then
                    BURST=$((`echo "$BURST" | sed -e "s/kbit//"` * 1024))
                fi
                if echo "$BURST" | grep "mbit"; then
                    BURST=$((`echo "$BURST" | sed -e "s/mbit//"` * 1024 * 1024))
                fi
                # minimum burst:
                # max down / 800
                # http://lartc.org/howto/lartc.qdisc.classless.html#AEN691
                # http://mailman.ds9a.nl/pipermail/lartc/2001q4/001972.html
                if [ $(($BURST * 800)) -lt $RATE ]; then
                    logError "host:_parser_.sh :: Warning: the advised minimum for maximum download burst is the maximum download / 8 * 10ms. This would be $(($RATE / 800)) in the host defined on line $3 of scenario $5, which is larger than $BURST. Ignoring."
                fi
            fi
        fi
        if [ ! -z "$HOST_TC_UP_BURST" ]; then
            if [ -z "$HOST_TC_UP" ]; then
                logError "host:_parser_.sh :: A maximum upload burst has been specified in the host defined on line $3 of scenario $5, but no maximum upload speed has been specified."
                failScenarioFile "$6"
            else
                local RATE="$HOST_TC_UP"
                local BURST="$EXCEUTION_TC_UP_BURST"
                if echo "$RATE" | grep "kbit"; then
                    RATE=$((`echo "$RATE" | sed -e "s/kbit//"` * 1024))
                fi
                if echo "$RATE" | grep "mbit"; then
                    RATE=$((`echo "$RATE" | sed -e "s/mbit//"` * 1024 * 1024))
                fi
                if echo "$BURST" | grep "kbit"; then
                    BURST=$((`echo "$BURST" | sed -e "s/kbit//"` * 1024))
                fi
                if echo "$BURST" | grep "mbit"; then
                    BURST=$((`echo "$BURST" | sed -e "s/mbit//"` * 1024 * 1024))
                fi
                # minimum burst:
                # max down / 800
                # http://lartc.org/howto/lartc.qdisc.classless.html#AEN691
                # http://mailman.ds9a.nl/pipermail/lartc/2001q4/001972.html
                if [ $(($BURST * 800)) -lt $RATE ]; then
                    logError "host:_parser_.sh :: Warning: the advised minimum for maximum upload burst is the maximum upload / 8 * 10ms. This would be $(($RATE / 800)) in the host defined on line $3 of scenario $5, which is larger than $BURST. Ignoring."
                fi
            fi
        fi
        if [ "$HOST_TC_JITTER" != "0" ]; then
            if [ "$HOST_TC_JITTER" -gt "$HOST_TC_DELAY" ]; then
                logError "host:_parser_.sh :: For the host defined at line $3 of scenario $5 tc_jitter has been set to \"$HOST_TC_JITTER\", which is greater than the delay \"$HOST_TC_DELAY\"."
                failScenarioFile "$6"
            fi
        fi
        function tcAPIVersion() {
            echo "wrong"
        }
        loadModule "tc/$HOST_TC"
        if [ "`tcAPIVersion`" != "`parseAPIVersion`" ]; then
            logError "host:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but module tc:$HOST_TC seems to have API version `tcAPIVersion`."
            failScenarioFile "$6"
        fi
    fi

    # = Load the subtype module =
    function hostAPIVersion() {
        echo "wrong"
    }
    loadModule "host/$HOST_SUBTYPE"
    if [ "`hostAPIVersion`" != `parseAPIVersion` ]; then
        logError "host:_parser_.sh :: API version mismatch: the core expects API version `parseAPIVersion` but module host:$HOST_SUBTYPE seems to have API version `hostAPIVersion`."
        failScenarioFile "$6"
    fi
    
    if ! hostReadSettings "$4" $3; then
        logError "host:_parser_.sh :: Error while reading host settings of host $HOST_NAME in scenario $5"
        failScenarioFile "$6"
    fi

    if [ -z "$HOST_NAME" ]; then
        logError "host:_parser_.sh :: Host defined at line $3 in scenario $5 does not have a name"
        failScenarioFile "$6"
    fi

    if [ ! -e "${LOCAL_TEST_DIR}/hosts/$HOST_NAME" ]; then
        logError "host:_parser_.sh :: Saving settings apparently failed somehow for host $HOST_NAME defined at line $3 in scenario $5"
        failScenarioFile "$6"
    fi
}

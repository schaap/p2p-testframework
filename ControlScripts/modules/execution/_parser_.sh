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
# Parses the settings for an execution.
# Note that this may have been *implemented* as a module, but it's not actually a module. There is just one implementation. THE implementation.
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
        logError "execution:_parser_.sh :: parseSettings called with invalid file argument"
        fail
    fi

    if [ ! -z "$2" ]; then
        logError "execution:_parser_.sh :: An execution can't have a subtype. There is only execution. Found subtype \"$2\"."
        failScenarioFile "$6"
    fi

    if [ -z "$EXECUTION_COUNT" ]; then
        EXECUTION_COUNT=0
    fi
    EXECUTION_NUMBER=$EXECUTION_COUNT
    EXECUTION_COUNT=$(($EXECUTION_COUNT + 1))

    LINE_NUMBER=$(($3 + 1))
    local parameterName=""
    local parameterValue=""
    EXECUTION_HOST=""
    EXECUTION_CLIENT=""
    EXECUTION_FILE=""
    EXECUTION_SEEDER=""
    EXECUTION_PARSER=( )
    EXECUTION_TC_IFACE=""
    EXECUTION_TC_DOWN=""
    EXECUTION_TC_DOWN_BURST=""
    EXECUTION_TC_UP=""
    EXECUTION_TC_UP_BURST=""
    EXECUTION_TC=""
    while IFS="" read LINE; do
        if [ "$LINE" = "" ]; then
            LINE_NUMBER=$(($LINE_NUMBER + 1))
            continue;
        fi
        parameterName=`getParameterName "$LINE"`
        checkFailScenarioFile "$6"
        parameterValue=`getParameterValue "$LINE"`
        case $parameterName in
            host)
                if ! isValidName "$parameterValue"; then
                    logError "execution:_parser_.sh :: \"$parameterValue\" is not the name of a host for the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$EXECUTION_HOST" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 can only have one host. Host \"$EXECUTION_HOST\" was already declared and host \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -e "${LOCAL_TEST_DIR}/hosts/$parameterValue" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 refers to host \"$parameterValue\", which does not exist (yet) (line $LINE_NUMBER). Maybe you declared the host after the execution?"
                    failScenarioFile "$6"
                fi
                EXECUTION_HOST="$parameterValue"
                ;;
            client)
                if ! isValidName "$parameterValue"; then
                    logError "execution:_parser_.sh :: \"$parameterValue\" is not the name of a client for the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$EXECUTION_CLIENT" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 can only have one client. Client \"$EXECUTION_CLIENT\" was already declared and client \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -e "${LOCAL_TEST_DIR}/clients/$parameterValue" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 refers to client \"$parameterValue\", which does not exist (yet) (line $LINE_NUMBER). Maybe you declared the client after the execution?"
                    failScenarioFile "$6"
                fi
                EXECUTION_CLIENT="$parameterValue"
                ;;
            file)
                if ! isValidName "$parameterValue"; then
                    logError "execution:_parser_.sh :: \"$parameterValue\" is not the name of a file for the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -z "$EXECUTION_FILE" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 can only have one file. File \"$EXECUTION_FILE\" was already declared and file \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -e "${LOCAL_TEST_DIR}/files/$parameterValue" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 refers to file \"$parameterValue\", which does not exist (yet) (line $LINE_NUMBER). Maybe you declared the file after the execution?"
                    failScenarioFile "$6"
                fi
                EXECUTION_FILE="$parameterValue"
                ;;
            parser)
                if ! isValidName "$parameterValue"; then
                    logError "execution:_parser_.sh :: \"$parameterValue\" is not the name of a parser for the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if [ ! -e "${LOCAL_TEST_DIR}/parsers/$parameterValue" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 refers to parser \"$parameterValue\", which does not exist (yet) (line $LINE_NUMBER). Maybe you declared the parser after the execution?"
                    failScenarioFile "$6"
                fi
                EXECUTION_PARSER[${#EXECUTION_PARSER[@]}]="$parameterValue"
                ;;
            seeder)
                if [ ! -z "$parameterValue" ]; then
                    EXECUTION_SEEDER="yes"
                fi
                ;;
            tc_iface)
                if [ -z "$parameterValue" ]; then
                    logError "execution:_parser_.sh :: Empty interface for traffic control found in the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                EXECUTION_TC="yes"
                if [ ! -z "$EXECUTION_TC_IFACE" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 can only have one interface for traffic control. Interface \"$EXECUTION_TC_IFACE\" was already declared and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                EXECUTION_TC_IFACE="$parameterValue"
                ;;
            tc_down)
                if [ -z "$parameterValue" ]; then
                    logError "execution:_parser_.sh :: Empty maximum download speed for traffic control found in the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                EXECUTION_TC="yes"
                if [ ! -z "$EXECUTION_TC_DOWN" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 can only have one maximum download speed for traffic control. \"$EXECUTION_TC_DOWN\" was already declared as maximum download speed and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)?$"; then
                    logError "execution:_parser_.sh :: Maximum speeds are to be given as integer, optionally postfixed with 'kbit' or 'mbit' (no postfix for mbit), e.g. 8192kbit or 8mbit. Found \"$parameterValue\" in the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)$"; then
                    $parameterValue = "${parameterValue}mbit"
                fi
                EXECUTION_TC_DOWN="$parameterValue"
                ;;
            tc_down_burst)
                if [ -z "$parameterValue" ]; then
                    logError "execution:_parser_.sh :: Empty maximum download burst for traffic control found in the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                EXECUTION_TC="yes"
                if [ ! -z "$EXECUTION_TC_DOWN_BURST" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 can only have one maximum download burst for traffic control. \"$EXECUTION_TC_DOWN_BURST\" was already declared as maximum download burst and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)?$"; then
                    logError "execution:_parser_.sh :: Maximum speeds are to be given as integer, optionally postfixed with 'kbit' or 'mbit' (no postfix for mbit), e.g. 8192kbit or 8mbit. Found \"$parameterValue\" in the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)$"; then
                    $parameterValue = "${parameterValue}mbit"
                fi
                EXECUTION_TC_DOWN_BURST="$parameterValue"
                ;;
            tc_up)
                if [ -z "$parameterValue" ]; then
                    logError "execution:_parser_.sh :: Empty maximum upload speed for traffic control found in the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                EXECUTION_TC="yes"
                if [ ! -z "$EXECUTION_TC_UP" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 can only have one maximum upload speed for traffic control. \"$EXECUTION_TC_UP\" was already declared as maximum upload speed and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)?$"; then
                    logError "execution:_parser_.sh :: Maximum speeds are to be given as integer, optionally postfixed with 'kbit' or 'mbit' (no postfix for mbit), e.g. 8192kbit or 8mbit. Found \"$parameterValue\" in the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)$"; then
                    $parameterValue = "${parameterValue}mbit"
                fi
                EXECUTION_TC_UP="$parameterValue"
                ;;
            tc_up_burst)
                if [ -z "$parameterValue" ]; then
                    logError "execution:_parser_.sh :: Empty maximum upload burst for traffic control found in the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                EXECUTION_TC="yes"
                if [ ! -z "$EXECUTION_TC_UP_BURST" ]; then
                    logError "execution:_parser_.sh :: The execution defined on line $3 of scenario $5 can only have one maximum upload burst for traffic control. \"$EXECUTION_TC_UP_BURST\" was already declared as maximum upload burst and \"$parameterValue\" was declared later on (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)?$"; then
                    logError "execution:_parser_.sh :: Maximum speeds are to be given as integer, optionally postfixed with 'kbit' or 'mbit' (no postfix for mbit), e.g. 8192kbit or 8mbit. Found \"$parameterValue\" in the execution defined on line $3 of scenario $5 (line $LINE_NUMBER)."
                    failScenarioFile "$6"
                fi
                if ! echo -n "$parameterValue" | grep -E "^[1-9][0-9]*((m|k)bit)$"; then
                    $parameterValue = "${parameterValue}mbit"
                fi
                EXECUTION_TC_UP_BURST="$parameterValue"
                ;;
            *)
                logError "execution:_parser_.sh :: Unknown parameter name ${parameterName} on line $LINE_NUMBER of scenario $5"
                failScenarioFile "$6"
                ;;
        esac
        LINE_NUMBER=$(($LINE_NUMBER + 1))
    done < "$4";

    # Fill in some more defaults
    if [ -z "$EXECUTION_TC_IFACE" ]; then
        EXECUTION_TC_IFACE="eth0"
    fi

    # Check if everything is there
    if [ -z "$EXECUTION_HOST" ]; then
        logError "execution:_parser_.sh :: The execution defined at line $3 of scenario $5 does not have a host specified."
        failScenarioFile "$6"
    fi
    if [ -z "$EXECUTION_CLIENT" ]; then
        logError "execution:_parser_.sh :: The execution defined at line $3 of scenario $5 does not have a client specified."
        failScenarioFile "$6"
    fi
    if [ -z "$EXECUTION_FILE" ]; then
        logError "execution:_parser_.sh :: The execution defined at line $3 of scenario $5 does not have a file specified."
        failScenarioFile "$6"
    fi
    if [ ! -z "$EXECUTION_TC" ]; then
        if [ -z "$EXECUTION_TC_DOWN" ]; then
            if [ -z "$EXECUTION_TC_UP" ]; then
                logError "execution:_parser_.sh :: Traffic control was enabled in the execution defined on line $3 of scenario $5, but no maximum speeds were given. Disabling traffic control again."
                EXECUTION_TC=""
            fi
        fi
    fi
    if [ ! -z "$EXECUTION_TC" ]; then
        if [ ! -z "$EXECUTION_TC_DOWN_BURST" ]; then
            if [ -z "$EXECUTION_TC_DOWN" ]; then
                logError "execution:_parser_.sh :: A maximum download burst has been specified in the execution defined on line $3 of scenario $5, but no maximum download speed has been specified."
                failScenarioFile "$6"
            else
                local RATE="$EXECUTION_TC_DOWN"
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
                    logError "execution:_parser_.sh :: Warning: the advised minimum for maximum download burst is the maximum download / 8 * 10ms. This would be $(($RATE / 800)) in the execution defined on line $3 of scenario $5, which is larger than $BURST. Ignoring."
                fi
            fi
        fi
        if [ ! -z "$EXECUTION_TC_UP_BURST" ]; then
            if [ -z "$EXECUTION_TC_UP" ]; then
                logError "execution:_parser_.sh :: A maximum upload burst has been specified in the execution defined on line $3 of scenario $5, but no maximum upload speed has been specified."
                failScenarioFile "$6"
            else
                local RATE="$EXECUTION_TC_UP"
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
                    logError "execution:_parser_.sh :: Warning: the advised minimum for maximum upload burst is the maximum upload / 8 * 10ms. This would be $(($RATE / 800)) in the execution defined on line $3 of scenario $5, which is larger than $BURST. Ignoring."
                fi
            fi
        fi
    fi

    # All settings have been parsed; these will now be saved
    mkdir -p "${LOCAL_TEST_DIR}/executions/"
    echo "#!/bin/bash" > "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_HOST=\"$EXECUTION_HOST\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_CLIENT=\"$EXECUTION_CLIENT\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_FILE=\"$EXECUTION_FILE\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_SEEDER=\"$EXECUTION_SEEDER\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_TC_IFACE=\"$EXECUTION_TC_IFACE\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_TC_DOWN=\"$EXECUTION_TC_DOWN\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_TC_DOWN_BURST=\"$EXECUTION_TC_DOWN_BURST\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_TC_UP=\"$EXECUTION_TC_UP\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_TC_UP_BURST=\"$EXECUTION_TC_UP_BURST\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_TC=\"$EXECUTION_TC\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_NUMBER=\"$EXECUTION_NUMBER\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    echo "EXECUTION_PARSER=( )" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
    if [ ${#EXECUTION_PARSER[@]} -gt 0 ]; then
        for index in `seq 0 $((${#EXECUTION_PARSER[@]} - 1))`; do
            echo "EXECUTION_PARSER[$index]=\"${EXECUTION_PARSER[index]}\"" >> "${LOCAL_TEST_DIR}/executions/exec_$EXECUTION_NUMBER"
        done
    fi
}

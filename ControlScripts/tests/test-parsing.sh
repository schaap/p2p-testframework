#!/bin/bash

# Set up a fake campaign environment
TEST_ENV_DIR=`dirname \`readlink -e "$0"\``/..
LOCAL_TEST_DIR=${TEST_ENV_DIR}/tests/testdir
rm -rf ${LOCAL_TEST_DIR}
mkdir -p ${LOCAL_TEST_DIR}/clients
RESULTS_DIR=${LOCAL_TEST_DIR}/Results/
mkdir -p ${RESULTS_DIR}
CAMPAIGN_RESULTS_DIR=${RESULTS_DIR}/campaign
mkdir -p ${CAMPAIGN_RESULTS_DIR}
CAMPAIGN_ERROR_LOG=${RESULTS_DIR}/err.log
. "${TEST_ENV_DIR}/functions/stderrlogging.sh"
. "${TEST_ENV_DIR}/functions/cleanup.sh"

echo ""
echo "Testing parsing functions (you'll be seeing some errors come by)"
echo ""

. "${TEST_ENV_DIR}/functions/parsing.sh"

if isSectionHeader "bla"; then
    echo "ERROR: bla is not a section header."
    exit -1
fi

if isSectionHeader ""; then
    echo "ERROR: \"\" is not a section header."
    exit -1
fi

if ! isSectionHeader "[bla]"; then
    echo "ERROR: [bla] is a section header."
    exit -1
fi

if ! isSectionHeader "[bla:bliep]"; then
    echo "ERROR: [bla:bliep] is a section header."
    exit -1
fi

A=`getSectionName "[bla:bliep]garbage"`
if ! checkFailReturn; then
    echo "ERROR: [bla:bliep]garbage contains garbage."
    exit -1
fi
cleanFailSignal

A=`getSectionName "[bla bliep]"`
if ! checkFailReturn; then
    echo "ERROR: [bla bliep] contains space."
    exit -1
fi
cleanFailSignal

A=`getSectionName "[]"`
if ! checkFailReturn; then
    echo "ERROR: [] is an empty section."
    exit -1
fi
cleanFailSignal

A=`getSectionName "[bla]"`
if checkFailReturn; then
    echo "ERROR: [bla] is a valid section header."
    cleanFailSignal
    exit -1
fi
if [ "$A" != "bla" ]; then
    echo "ERROR: section name of [bla] is \"bla\", found \"$A\"."
    exit -1
fi

A=`getSectionName "[bla:bliep]"`
if checkFailReturn; then
    echo "ERROR: [bla:bliep] is a valid section header."
    cleanFailSignal
    exit -1
fi
if [ "$A" != "bla:bliep" ]; then
    echo "ERROR: section name of [bla:bliep] is \"bla:bliep\", found \"$A\"."
    exit -1
fi

A=`getParameterName "="`
if ! checkFailReturn; then
    echo "ERROR: \"=\" is not a valid parameter."
    exit -1
fi
cleanFailSignal

A=`getParameterName "=bliep"`
if ! checkFailReturn; then
    echo "ERROR: \"=bliep\" is not a valid parameter."
    exit -1
fi
cleanFailSignal

A=`getParameterName "bla="`
if ! checkFailReturn; then
    echo "ERROR: \"bla=\" is not a valid parameter."
    exit -1
fi
cleanFailSignal

A=`getParameterName "long name=value"`
if ! checkFailReturn; then
    echo "ERROR: \"long name=value\" contains space in the parameter name."
    exit -1
fi
cleanFailSignal

A=`getParameterName "bla=bliep"`
if checkFailReturn; then
    echo "ERROR: bla=bliep is a valid parameter."
    cleanFailSignal
    exit -1
fi
if [ "$A" != "bla" ]; then
    echo "ERROR: parameter name of bla=bliep is \"bla\", found \"$A\"."
    exit -1
fi

A=`getParameterValue "bla=bliep"`
if [ "$A" != "bliep" ]; then
    echo "ERROR: parameter value of bla=bliep is \"bliep\", found \"$A\"."
    exit -1
fi

if hasModuleSubType "bla"; then
    echo "ERROR: \"bla\" has no module subtype."
    exit -1
fi

if ! hasModuleSubType "bla:bliep"; then
    echo "ERROR: \"bla:bliep\" has a module subtype."
    exit -1
fi

A=`getModuleType "bla"`
if [ "$A" != "bla" ]; then
    echo "ERROR: module type of bla is \"bla\", found \"$A\"."
    exit -1
fi

A=`getModuleType "bla:bliep"`
if [ "$A" != "bla" ]; then
    echo "ERROR: module type of bla:bliep is \"bla\", found \"$A\"."
    exit -1
fi

A=`getModuleSubType "bla"`
if [ "$A" != "" ]; then
    echo "ERROR: module subtype of bla is \"\", found \"$A\"."
    exit -1
fi

A=`getModuleSubType "bla:bliep"`
if [ "$A" != "bliep" ]; then
    echo "ERROR: module subtype of bla:bliep is \"bliep\", found \"$A\"."
    exit -1
fi

# Invalid names
names=( "_" "_a" "-" "-a" "/a" "0" "0a" "123" "5a" "5" "ab+aa" )

for index in `seq 0 $((${#names[@]} - 1))`; do
    if isValidName "${names[index]}"; then
        echo "ERROR: ${names[index]} is not a valid name."
        exit -1
    fi
done

# Valid names
names=( "abc" "a" "A" "ABC" "A5" "a5" "a_" "A_" "a-" "A-" "ab5-_" "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" )

for index in `seq 0 $((${#names[@]} - 1))`; do
    if ! isValidName "${names[index]}"; then
        echo "ERROR: ${names[index]} is a valid name."
        exit -1
    fi
done

echo ""
echo "Everything seems to be fine with the parsing."
echo ""

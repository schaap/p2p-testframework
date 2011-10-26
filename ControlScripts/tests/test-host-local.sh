#!/bin/bash

echo ""

# Set up a fake campaign environment
TEST_ENV_DIR=`dirname \`readlink -e "$0"\``/..
LOCAL_TEST_DIR=${TEST_ENV_DIR}/tests/testdir
rm -rf ${LOCAL_TEST_DIR}
mkdir -p ${LOCAL_TEST_DIR}/hosts
RESULTS_DIR=${LOCAL_TEST_DIR}/Results/
mkdir -p ${RESULTS_DIR}
CAMPAIGN_RESULTS_DIR=${RESULTS_DIR}/campaign
mkdir -p ${CAMPAIGN_RESULTS_DIR}
CAMPAIGN_ERROR_LOG=${RESULTS_DIR}/err.log
. ./ControlScripts/functions/stderrlogging.sh
. ./ControlScripts/functions/cleanup.sh
. ./ControlScripts/functions/parsing.sh

# Build a fake host as would be parsed by host:_parser_.sh
HOST_NAME=""
HOST_PREPARATION=""
HOST_CLEANUP=""
HOST_REMOTEFOLDER=""
HOST_SUBTYPE="local"

# Get the host:local module
. ./ControlScripts/modules/host/local

# Build fake settings file
touch "${LOCAL_TEST_DIR}/settings"

# Run some tests
A=`reinitializeCleanup; hostReadSettings "${LOCAL_TEST_DIR}/settings" 10; removeCleanupScript \$HOST_CLEANUPIDX; echo \$HOST_NAME`
if [ "$A" != "local" ]; then
    echo "Call with no hostname returns wrong host name: $A"
    exit -1
fi
if [ ! -e "${LOCAL_TEST_DIR}/hosts/local" ]; then
    echo "Settings file not created: failure"
    exit -1
fi
rm -rf "${LOCAL_TEST_DIR}/hosts/local"

echo "An error should occur on line 12, but it shouldn't fail"
echo "" >> "${LOCAL_TEST_DIR}/settings"
echo "bla=failure" >> "${LOCAL_TEST_DIR}/settings"
`reinitializeCleanup; hostReadSettings "${LOCAL_TEST_DIR}/settings" 10; removeCleanupScript \$HOST_CLEANUPIDX`
if [ ! -e "${LOCAL_TEST_DIR}/hosts/local" ]; then
    echo "Settings file not created: failure"
    exit -1
fi
rm "${LOCAL_TEST_DIR}/settings"
touch "${LOCAL_TEST_DIR}/settings"

rm -rf "${LOCAL_TEST_DIR}/hosts/local"
touch "${LOCAL_TEST_DIR}/hosts/local"
echo "An error should occur that local is already in use"
`reinitializeCleanup; hostReadSettings "${LOCAL_TEST_DIR}/settings" 10; removeCleanupScript \$HOST_CLEANUPIDX`
A=`cat "${LOCAL_TEST_DIR}/hosts/local"`
if [ "$A" != "" ]; then
    echo "A=$A"
    echo "Saved after all?"
    exit -1
fi

rm -rf "${LOCAL_TEST_DIR}/hosts/local"
echo "An error should occur"
`reinitializeCleanup; hostLoadSettings "local"`
echo "/Should give error"

HOST_PREPARATION="bla"
`reinitializeCleanup; hostReadSettings "${LOCAL_TEST_DIR}/settings" 10; removeCleanupScript \$HOST_CLEANUPIDX`
HOST_PREPARATION=""
A=`echo -n "X\${HOST_PREPARATION}X"; hostLoadSettings "local"; echo -n "X\${HOST_PREPARATION}X"`
if [ "$A" != "XXXblaX" ]; then
    echo "Load incorrect? A=$A"
    exit -1
fi

rm -f "${LOCAL_TEST_DIR}/test_file"
`reinitializeCleanup; hostSendCommand "touch ${LOCAL_TEST_DIR}/test_file"`
if [ ! -f "${LOCAL_TEST_DIR}/test_file" ]; then
    echo "Command not executed?"
    exit -1
fi

rm -f "${LOCAL_TEST_DIR}/test_file2"
`reinitializeCleanup; hostSendFile "${LOCAL_TEST_DIR}/test_file" "${LOCAL_TEST_DIR}/test_file2"`
if [ ! -f "${LOCAL_TEST_DIR}/test_file2" ]; then
    echo "File not sent?"
    exit -1
fi

echo "Should give an error and refuse"
echo "bla" > "${LOCAL_TEST_DIR}/test_file2"
`reinitializeCleanup; hostGetFile "${LOCAL_TEST_DIR}/test_file" "${LOCAL_TEST_DIR}/test_file2"`
echo "/Should give error"
A=`cat "${LOCAL_TEST_DIR}/test_file2"`
if [ "$A" != "bla" ]; then
    echo "Seems it got overwritten anyway: $A"
    exit -1;
fi

rm "${LOCAL_TEST_DIR}/test_file2"
echo "bli" > "${LOCAL_TEST_DIR}/test_file"
`reinitializeCleanup; hostGetFile "${LOCAL_TEST_DIR}/test_file" "${LOCAL_TEST_DIR}/test_file2"`
A=`cat "${LOCAL_TEST_DIR}/test_file2"`
if [ "$A" != "bli" ]; then
    echo "File not received? $A"
    exit -1;
fi

HOST_PREPARATION=""
HOST_NAME="local2"
HOST_REMOTEFOLDER=""
rm -rf "${LOCAL_TEST_DIR}/hosts/local2"
A=`reinitializeCleanup; hostReadSettings "${LOCAL_TEST_DIR}/settings" 10; hostPrepare; echo \$HOST_TEMPFOLDER`
if [ -z "$A" ]; then
    echo "No temp folder?"
    exit -1
fi
if [ ! -d "$A" ]; then
    echo "What is this? $A"
    exit -1
fi
rm -rf "$A"
if [ "$HOST_TEMPFOLDER" != "" ]; then
    echo "Temp folder in test env?"
    exit -1
fi
B=`. "${LOCAL_TEST_DIR}/hosts/local2/conf"; echo $HOST_TEMPFOLDER`
if [ "$A" != "$B" ]; then
    echo "Save went wrong, apparently"
    exit -1
fi
rm -rf "${LOCAL_TEST_DIR}/hosts/local2"

HOST_REMOTEFOLDER="${LOCAL_TEST_DIR}"
A=`reinitializeCleanup; hostReadSettings "${LOCAL_TEST_DIR}/settings" 10; hostPrepare; echo \$HOST_TEMPFOLDER; cleanup`
if [ "$A" != "" ]; then
    echo "Temp folder?"
    exit -1
fi

HOST_REMOTEFOLDER=""
rm -rf "${LOCAL_TEST_DIR}/hosts/local2"
A=`reinitializeCleanup; hostReadSettings "${LOCAL_TEST_DIR}/settings" 10; hostPrepare; echo \$HOST_TEMPFOLDER; cleanup`
if [ -e "$A" ]; then
    echo "Temp folder $A still exists?"
    exit -1
fi
if [ "$A" = "" ]; then
    echo "No temp folder? Again?"
    exit -1
fi

# Clean up
rm -rf "${LOCAL_TEST_DIR}"

echo ""
echo "You should check the lines above, but it looks like you're clear!"

#!/bin/bash

echo ""

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
. "${TEST_ENV_DIR}/functions/parsing.sh"

HOST_NAME="FAKE"
HOST_PREPARATION=""
HOST_CLEANUP=""
HOST_SUBTYPE="FAKE"
HOST_CLEANUPIDX=""
HOST_REMOTEFOLDER="${LOCAL_TEST_DIR}/remote"
function hostReadSettings() {
    echo -n ""
}
function hostLoadSettings() {
    echo -n ""
}
function hostSendCommand() {
    echo "    $1"
}
function hostSendFile() {
    echo "    cp \"$1\" \"$2\""
}
function hostGetFile() {
    echo "    cp \"$1\" \"$2\""
}
function hostPrepare() {
    echo -n ""
}
function hostCleanup() {
    echo -n ""
}
function hostGetTestDir() {
    echo "${HOST_REMOTEFOLDER}"
}

function fileReadSettings() {
    echo -n ""
}
function fileLoadSettings() {
    echo -n ""
}
function fileSendToHost() {
    hostSendFile "FAKEFILE" "`hostGetTestDir`/FAKEFILE"
}
function fileGetName() {
    echo "FAKEFILE"
}
function fileGetMetaName() {
    echo "FAKEFILE.torrent"
}
function fileGetRootHash() {
    echo "1234123412341234123412341234123412342134"
}

function executionIsSeeder() {
    return 1
}
function executionNumber() {
    echo "48"
}

CLIENT_NAME="swift"
CLIENT_PARAMS="--test-param1 --test-param2"
CLIENT_DIRECTORY="${LOCAL_TEST_DIR}/swift-client"
CLIENT_SUBTYPE="swift"

. ${TEST_ENV_DIR}/modules/client/swift

rm -rf ${LOCAL_TEST_DIR}/settings
touch ${LOCAL_TEST_DIR}/settings
A=`reinitializeCleanup; clientReadSettings "${LOCAL_TEST_DIR}/settings" 10; cleanup`
if [ ! -z "$A" ]; then
    echo "Apparently an error? $A"
    exit -1
fi

echo "" >> ${LOCAL_TEST_DIR}/settings
echo "listen=a b" >> ${LOCAL_TEST_DIR}/settings
echo "Should give an error on line 12"
`reinitializeCleanup; clientReadSettings "${LOCAL_TEST_DIR}/settings" 10`
echo "/Should give error"

rm -rf ${LOCAL_TEST_DIR}/settings
echo "listen=listenPort" >> ${LOCAL_TEST_DIR}/settings
echo "tracker=aTracker" >> ${LOCAL_TEST_DIR}/settings
echo "wait=123" >> ${LOCAL_TEST_DIR}/settings
A=`reinitializeCleanup; clientReadSettings "${LOCAL_TEST_DIR}/settings" 10; cleanup`
if [ ! -z "$A" ]; then
    echo "Should not have given an error: $A"
    exit -1
fi

echo "Please verify the below commands for sanity. The client should listen on listenPort, listen to aTracker amd wait 123. It should also have --testparam1 --testparam2"
clientReadSettings "${LOCAL_TEST_DIR}/settings" 10
clientPrepare
clientStart
clientRetrieveLogs "${CAMPAIGN_RESULTS_DIR}/logs"
clientCleanup
cleanup
echo "/End of commands"

echo "If everything above looks OK, then you're good"

echo ""

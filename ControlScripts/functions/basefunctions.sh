#!/bin/bash

#
#
# Requires:
# Provides: createTempFile
#

##
# Create a temporary file on the local system.
# This file will be created such that it will be cleaned by cleanup automatically, relieving the user from the burden of taking signals into account.
# Do clean up your temporary file after you're done: it's good practice.
#
# @output   The full filename of the temporary file on the local system.
##
function createTempFile() {
    if mktemp --version 2>/dev/null | grep \"GNU coreutils\" > /dev/null 2>/dev/null; then
        mktemp --tmpdir="${LOCAL_TEST_DIR}/tmp"
    else
        mktemp -p "${LOCAL_TEST_DIR}/tmp"
    fi
}

##
# Create a temporary directory on the local system.
# This directory will be created such that it will be cleaned by cleanup automatically, relieving the user from the burder of taking signals into account.
# Do clean up your temporary directory after you're done, though: it's good practice.
#
# @output   The full path to the directory on the local system.
##
function createTempDir() {
    if mktemp --version 2>/dev/null | grep \"GNU coreutils\" > /dev/null 2>/dev/null; then
        mktemp -d --tmpdir="${LOCAL_TEST_DIR}/tmp"
    else
        mktemp -d -p "${LOCAL_TEST_DIR}/tmp"
    fi
}

##
# Creates a temporary file on the currently loaded remote system.
# This file will NOT be cleaned up automatically: it is up to the caller to ensure this.
#
# @param    The basepath of the temporary file, if any.
#
# @output   The full path to the file on the remote host.
##
function createRemoteTempFile() {
    if [ ! -z "$1" ]; then
        hostSendCommand "if mktemp --version 2>/dev/null | grep \\\"GNU coreutils\\\" >/dev/null 2>/dev/null; then mktemp --tmpdir=\\\"$1\\\"; else mktemp -p \\\"$1\\\"; fi"
    else
        hostSendCommand "mktemp"
    fi
}

##
# Creates a temporary directory on the currently loaded remote system.
# This directory will NOT be cleaned up automatically: it is up to the caller to ensure this.
#
# @param    The basepath of the temporary directory, if any.
#
# @output   The full path to the directory on the remote host.
##
function createRemoteTempDir() {
    if [ ! -z "$1" ]; then
        hostSendCommand "if mktemp --version 2>/dev/null | grep \\\"GNU coreutils\\\" >/dev/null 2>/dev/null; then mktemp -d --tmpdir=\\\"$1\\\"; else mktemp -d -p \\\"$1\\\"; fi"
    else
        hostSendCommand "mktemp -d"
    fi
}

##
# Quotes a string by adding slashes in front of `, $, \ and "
#
# @param    The string to be quoted
#
# @output   The quoted string
##
function quote() {
    local s="${1//\\/\\\\}"
    s="${s//\`/\\\`}"
    s="${s//\"/\\\"}"
    s="${s//\$/\\\$}"
    echo "$s"
}

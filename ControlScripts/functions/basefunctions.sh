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
    mktemp --tmpdir="${LOCAL_TEST_DIR}/tmp"
}

##
# Create a temporary directory on the local system.
# This directory will be created such that it will be cleaned by cleanup automatically, relieving the user from the burder of taking signals into account.
# Do clean up your temporary directory after you're done, though: it's good practice.
#
# @output   The full path to the directory on the local system.
##
function createTempDir() {
    mktemp -d --tmpdir="${LOCAL_TEST_DIR}/tmp"
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

#!/bin/bash

#
#
# Requires:
# Provides: logError
#

##
# Log an error to stderr.
# This is just a convenience function for writing a line to stderr.
# Note that this is the default error logging function that will be overwritten by e.g. campaign-specific logging.
#
# @param    A string: the line to be logged
##
function logError() {
    if [ $# -eq 0 ]; then
        return
    fi
    echo $1 1>&2
}

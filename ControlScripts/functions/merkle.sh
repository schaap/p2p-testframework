#!/bin/bash

#
# Provides functions for on-the-fly calculation of Merkle root hashes.
# Requires: createTempFile
# Provides: merkleCanCalculate, merkleCalculateRootHashFromSingleFile
#

##
# Returns whether it is possible to calculate Merkle hashes.
# This basically checks for the dependencies to calculate Merkle hashes.
# Currently this is the openssl executable, needed for binary sha1 checksums, and xxd, needed for binary zeroes.
# Also required are mktemp and diff, which are used for checking how openssl works.
#
# @return   True (0) iff the dependencies for calculating merkle root hashes seem available.
##
function merkleCanCalculate() {
    local OPENSSL="`which openssl`"
    if [ -z "$OPENSSL" ]; then
        # No openssl? No Merkle hashes.
        return 1;
    fi
    if [ ! -f "$OPENSSL" ]; then
        # Does not exist? Strange, but okay. No Merkle hashes.
        return 2;
    fi
    if [ ! -x "$OPENSSL" ]; then
        # Does not exexcute? Strange, but okay. No Merkle hashes.
        return 3;
    fi

    XXD="`which xxd`"
    if [ -z "$XXD" ]; then
        # No xxd? No Merkle hashes.
        return 15;
    fi
    if [ ! -f "$XXD" ]; then
        # Does not exist? Strange, but okay. No Merkle hashes.
        return 16;
    fi
    if [ ! -x "$XXD" ]; then
        # Does not execute? Strange, but okay. No Merkle hashes.
        return 17;
    fi

    # Do a small testrun to see if openssl works as we expect
    local tmpFile1=`createTempFile`
    local tmpFile2=`createTempFile`
    echo "blabla" > "$tmpFile1"
    "$OPENSSL" sha1 -binary "$tmpFile1" > "$tmpFile2"
    # The terrible string below is the SHA1 of "blabla"
    echo -n $'\xe1\xa9\xde\x5d\xc7\xf9\x7c\xc1\x8c\xad\xe5\x5d\x04\xea\x0b\x3d\xd5\x2a\xc4\xf0' > "$tmpFile1"
    local ans=10
    if `which diff` "$tmpFile1" "$tmpFile2" > /dev/null; then
        ans=0
    fi
    if [ $ans -ne 0 ]; then
        rm -f $tmpFile1 $tmpFile2
        return $ans
    fi

    # Do a small testrun to see if xxd works as we expect, in both ways
    # These are the hexadecimal values of the string "blabla"
    echo -n "626c61626c61" | "$XXD" -r -p > "$tmpFile1"
    echo -n "blabla" > "$tmpFile2"
    ans=18
    if `which diff` "$tmpFile1" "$tmpFile2" > /dev/null; then
        ans=0
    fi
    if [ $ans -ne 0 ]; then
        rm -f $tmpFile1 $tmpFile2
        return $ans
    fi
    echo -n "626c61626c61" > "$tmpFile1"
    echo -n "blabla" | "$XXD" -p | head -c 12 > "$tmpFile2"
    ans=19
    if `which diff` "$tmpFile1" "$tmpFile2" > /dev/null; then
        ans=0
    fi
    if [ $ans -ne 0 ]; then
        rm -f $tmpFile1 $tmpFile2
        return $ans
    fi

    rm -f $tmpFile1 $tmpFile2
    return $ans
}

##
# Calculate a Merkle root hash from a single file on the local machine and output that.
# This function will not work if the file does not exist or merkleCanCalculate return false.
#
# On manual calculation (compiled calculation not supported, yet) files larger than 5M are refused: it takes excruciatingly long to calculate them.
#
# @param    The path to the file to calculate the Merkle root hash from.
#
# @output   The Merkle root hash of the file, or "" if it could not be calculated.
# @return   True (0) iff the hash was calculated.
##
function merkleCalculateRootHashFromSingleFile() {
    #
    # Root hashes are not (as assumed) the smallest bin covering all of the file, but bin (63,0).
    # Exact calculation needs to be checked.
    #

    if ! merkleCanCalculate; then
        return 1
    fi

    if [ -z "$1" ]; then
        return 1
    fi
    if [ ! -f "$1" ]; then
        return 1
    fi
    if [ ! -r "$1" ]; then
        return 1
    fi

    if [ `stat -c %s "$1"` -gt $((5 * 1024 * 1024)) ]; then
        # Optimistically try and use logError; if it isn't there, it isn't there.
        ( logError "merkleCalculateRootHashFromSingleFile refuses to manually calculate the root hash for files larger than 5M. It takes too much time." ) &
        return 1
    fi

    local hashes=( )
    local tmphash1=""
    local tmphash2=""
    local hashcount=0
    local MAXBLOCKS=$(((`stat -c %s "$1"` + 1023) / 1024))
    local BLOCKCOUNTER=0
    local OPENSSL=`which openssl`
    while [ $BLOCKCOUNTER -lt $MAXBLOCKS ]; do
        # Read block 1
        tmphash1="`dd if="$1" bs=1024 count=1 skip=$BLOCKCOUNTER 2> /dev/null | $OPENSSL sha1 -binary | xxd -p`"
        BLOCKCOUNTER=$(($BLOCKCOUNTER + 1))
        # Read block 2 (or set ZERO if no block available)
        if [ $BLOCKCOUNTER -lt $MAXBLOCKS ]; then
            tmphash2="`dd if="$1" bs=1024 count=1 skip=$BLOCKCOUNTER 2> /dev/null | $OPENSSL sha1 -binary | xxd -p`"
            BLOCKCOUNTER=$(($BLOCKCOUNTER + 1))
        else
            tmphash2="0000000000000000000000000000000000000000"
        fi
        # Hash together
        tmphash1="`echo -n "${tmphash1}${tmphash2}" | xxd -r -p | $OPENSSL sha1 -binary | xxd -p`"
        # Put in tree
        hashcount=0
        while true; do
            if [ "${hashes[hashcount]}" == "" ]; then
                # No left subtree present: this was left subtree, store and done
                hashes[$hashcount]=$tmphash1
                break
            else
                # Left subtree present: this was right subtree, hash together and continue to parent
                tmphash1="`echo -n "${hashes[hashcount]}${tmphash1}" | xxd -r -p | $OPENSSL sha1 -binary | xxd -p`"
                # Remove left subtree, since it is consumed into parent
                hashes[$hashcount]=""
            fi
            hashcount=$(($hashcount + 1))
        done
    done

    hashcount=0
    tmphash1="0000000000000000000000000000000000000000"
    # Seek first filled in hash in 'tree'
    while [ $hashcount -lt 62 ]; do         # 62, since we want layer 63 zero-based, but we're off by -1 since we don't store layer 0
        if [ "${hashes[hashcount]}" != "" ]; then
            break
        fi
        hashcount=$(($hashcount + 1))
    done
    # Keep hashing data, filing in ZERO hashes where needed, until we've found root hash
    while [ $hashcount -lt 62 ]; do
        if [ "${hashes[hashcount]}" == "" ]; then
            # No left subtree present: this was left subtree, hash together with ZERO and continue to parent
            tmphash1="`echo -n "${tmphash1}0000000000000000000000000000000000000000" | xxd -r -p | $OPENSSL sha1 -binary | xxd -p`"
        else
            # Left subtree present: this was right subtree, hash together and continue to parent
            tmphash1="`echo -n "${hashes[hashcount]}${tmphash1}" | xxd -r -p | $OPENSSL sha1 -binary | xxd -p`"
        fi
        hashcount=$(($hashcount + 1))
    done
    echo -n "$tmphash1"
    return 0
}

#!/bin/bash

#
# Provides functions for on-the-fly creation of torrent files.
# Requires:
# Provides: torrentCanCreate, torrentCreateFromSingleFile
#

##
# Returns whether it is possible to create torrent files.
# This basically checks for the dependencies to create torrent files.
# Currently this is the openssl executable, needed for binary sha1 checksums.
# Also required are mktemp and diff, which are used for checking how openssl works.
#
# @return   True (0) iff the dependencies for creating torrent files seem available.
##
function torrentCanCreate() {
    local OPENSSL="`which openssl`"
    if [ -z "$OPENSSL" ]; then
        # No openssl? No torrents.
        return 1;
    fi
    if [ ! -f "$OPENSSL" ]; then
        # Does not exist? Strange, but okay. No torrents.
        return 2;
    fi
    if [ ! -x "$OPENSSL" ]; then
        # Does not exexcute? Strange, but okay. No torrents.
        return 3;
    fi

    MKTEMP="`which mktemp`"
    if [ -z "$MKTEMP" ]; then
        # No mktemp? No checking of openssl. No torrents.
        return 4;
    fi
    if [ ! -f "$MKTEMP" ]; then
        # Does not exist? Strange, but okay. No torrents.
        return 5;
    fi
    if [ ! -x "$MKTEMP" ]; then
        # Does not execute? Strange, but okay. No torrents.
        return 6;
    fi

    DIFF="`which diff`"
    if [ -z "$DIFF" ]; then
        # No diff? No checking of openssl. No torrents.
        return 7;
    fi
    if [ ! -f "$DIFF" ]; then
        # Does not exist? Strange, but okay. No torrents.
        return 8;
    fi
    if [ ! -x "$DIFF" ]; then
        # Does not execute? Strange, but okay. No torrents.
        return 9;
    fi

    # Do a small testrun to see if openssl works as we expect
    local tmpFile1=`$MKTEMP`
    local tmpFile2=`$MKTEMP`
    # The terrible string below is the SHA1 of "blabla"
    echo -n $'\xe1\xa9\xde\x5d\xc7\xf9\x7c\xc1\x8c\xad\xe5\x5d\x04\xea\x0b\x3d\xd5\x2a\xc4\xf0' > "$tmpFile1"
    echo "blabla" | "$OPENSSL" sha1 -binary > "$tmpFile2"
    local ans=10
    if diff "$tmpFile1" "$tmpFile2" > /dev/null; then
        ans=0
    fi
    rm -f $tmpFile1 $tmpFile2

    return $ans
}

##
# Create a torrent file from a single file on the local machine.
# This function will not work if the file does not exist, the torrent file already exists, or torrentCanCreate return false.
# Note that this function will not attempt to create any directories in which the torrent file is to be placed: it will only create the torrent file.
# The created torrent will use piece sizes of 512 kB and will advise to call the file "outputFile".
#
# @param    The path to the file to create the torrent from.
# @param    The path to the torrent file to be created.
#
# @return   True (0) iff the torrent file was created.
##
function torrentCreateFromSingleFile() {
    if ! torrentCanCreate; then
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

    if [ -z "$2" ]; then
        return 1
    fi
    if [ -f "$2" ]; then
        return 1
    fi
    touch "$2"
    if [ ! -w "$2" ]; then
        return 1
    fi

    # start dictionary of torrent file
    echo -n "d" > "$2"

    # Note: the order of the fields is important. If you do first the encoding and then the announce, bittorrent will complain that the file is not correctly bencoded O_o

    # announce field
    echo -n "8:announce25:http://127.0.0.1/announce" >> "$2"

    # encoding field
    echo -n "8:encoding5:UTF-8" >> "$2"

    # start info dictionary
    echo -n "4:infod" >> "$2"
    
    # length field of info dict
    echo -n "6:lengthi" >> "$2"
    local FILE_SIZE=`stat -c %s "$1"`
    echo -n $FILE_SIZE >> "$2"
    echo -n "e" >> "$2"

    # name field of info dict
    echo -n "4:name10:outputFile" >> "$2"

    # piece length field of info dict
    echo -n "12:piece lengthi$((512 * 1024))e" >> "$2"

    # pieces field of info dict
    # this field contains one SHA1 for every 512 kB of the file
    # these SHA1 are byte strings that are concatenated
    local CEIL_FILE_SIZE=$(($FILE_SIZE / (512 * 1024) * (512 * 1024)))
    if [ $CEIL_FILE_SIZE -lt $FILE_SIZE ]; then
        CEIL_FILE_SIZE=$(($CEIL_FILE_SIZE + (512 * 1024)))
    fi
    echo -n "6:pieces$(($CEIL_FILE_SIZE / (512 * 1024) * 20)):" >> "$2"
    local FILE_OFFSET=0
    while [ $FILE_OFFSET -lt $FILE_SIZE ]; do
        # for each piece in the file: generate the binary sha1 hash and concatenate it into the file
        local CHUNK_SIZE=$((512 * 1024))
        if [ $(($FILE_OFFSET + $CHUNK_SIZE)) -gt $FILE_SIZE ]; then
            CHUNK_SIZE=$(($FILE_SIZE - $FILE_OFFSTE))
        fi
        head -c $(($FILE_OFFSET + $CHUNK_SIZE)) "$1" | tail -c $CHUNK_SIZE | `which openssl` sha1 -binary >> "$2"
        FILE_OFFSET=$(($FILE_OFFSET + $CHUNK_SIZE))
    done

    # end info dictionary
    echo -n "e" >> "$2"

    # end dictionary of torrent file
    echo -n "e" >> "$2"

    return 0
}

#!/bin/bash

# This script will go over all directories in the current directory (unless they start with a .) and make tarballs
# of them. E.g.:
#
#   bash$ pwd
#   /your/path/to/p2p-testframework/Results
#   bash$ ls --example
#   drwx------ one_dir
#   drwxr-xr-x two_dir
#   -rw-rw-rw- a_file
#   drwxrwx--- three_dir
#   bash$ ../Utils/compact_results.sh
#   bash$ ls --example
#   -rw-r--r-- one_dir.tar.bz2
#   -rw-r--r-- two_dir.tar.bz2
#   -rw-rw-rw- a_file
#   -rw-r--r-- three_dir.tar.bz2
#   bash$
#
# This also shows a weakness in this script: all resulting files will have mode 644, or whatever your default
# mask is. The ls --example is of a simplified version of ls -l, invented for my typing comfort.

# You should run this script inside your Results directory.
# If you're really sure about what you're doing you may give the argument --really to have it run in the current
# directory anyway.

if [ "$1" != "--really" ]; then
    if [ ! -f ../Utils/compact_results.sh ]; then
        echo "Please run this script from inside your Results directory."
        exit
    fi

    x=`basename \`pwd\``
    if [ "$x" != "Results" ]; then
        echo "Please run this script from inside your Results directory."
        exit
    fi

    if [ ! -d ../ControlScripts/ ]; then
        echo "Please run this script from inside your Results directory."
        exit
    fi
fi

for a in `ls`; do
    if [ ! -d $a ]; then
        continue
    fi
    tar cf $a.tar $a && bzip2 $a.tar && rm -rf $a
done

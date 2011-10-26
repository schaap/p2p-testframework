#!/bin/bash

#
# Provides a function for calculation relative paths.
# This is an adapted version of the code by Jens found at
# http://stackoverflow.com/questions/2564634/bash-convert-absolute-path-into-relative-path-given-a-current-directory/7023490#7023490
# (retrieved 05-10-2011)
# Adaptations: Inside the function a new environment is opened to prevent affecting the surrounding environment; terminal options and other functions are moved into that environment; results are not output instead of passed through a gloabl
# Requires:
# Provides: relativepath
#

##
# Find common parent directory path for a pair of paths.
# Call with two pathnames as args, e.g.
# commondirpart foo/bar foo/baz/bat -> result="foo/"
# The result is either empty or ends with "/".
# Call with FROM TO args.
#
# @param    The canonical path from where the relative path is to be calculated.
# @param    The canonical path to where the relative path is to be calculated.
#
# @output   The relative path from $1 to $2.
##
relativepath () {
(
   function commondirpart () {
      result=""
      while test ${#1} -gt 0 -a ${#2} -gt 0; do
         if test "${1%${1#?}}" != "${2%${2#?}}"; then   # First characters the same?
            break                                       # No, we're done comparing.
         fi
         result="$result${1%${1#?}}"                    # Yes, append to result.
         set -- "${1#?}" "${2#?}"                       # Chop first char off both strings.
      done
      case "$result" in
      (""|*/) ;;
      (*)     result="${result%/*}/";;
      esac
   }

   # Turn foo/bar/baz into ../../..
   #
   function dir2dotdot () {
      OLDIFS="$IFS" IFS="/" result=""
      for dir in $1; do
         result="$result../"
      done
      result="${result%/}"
      IFS="$OLDIFS"
   }

   set -f # noglob

   case "$1" in
   (*//*|*/./*|*/../*|*?/|*/.|*/..)
      printf '%s\n' "'$1' not canonical"; exit 1;;
   (/*)
      from="${1#?}";;
   (*)
      printf '%s\n' "'$1' not absolute"; exit 1;;
   esac
   case "$2" in
   (*//*|*/./*|*/../*|*?/|*/.|*/..)
      printf '%s\n' "'$2' not canonical"; exit 1;;
   (/*)
      to="${2#?}";;
   (*)
      printf '%s\n' "'$2' not absolute"; exit 1;;
   esac

   case "$to" in
   ("$from")   # Identical directories.
      echo ".";;
   ("$from"/*) # From /x to /x/foo/bar -> foo/bar
      echo "${to##$from/}";;
   ("")        # From /foo/bar to / -> ../..
      dir2dotdot "$from"
      echo $result
      ;;
   (*)
      case "$from" in
      ("$to"/*)       # From /x/foo/bar to /x -> ../..
         dir2dotdot "${from##$to/}"
         echo $result
         ;;
      (*)             # Everything else.
         commondirpart "$from" "$to"
         common="$result"
         dir2dotdot "${from#$common}"
         echo "$result/${to#$common}"
      esac
      ;;
   esac
)
}

# Uncomment all of the following for a small testsuite for the above function
#set -f # noglob

#set -x
#cat <<EOF |
#/ / .
#/- /- .
#/? /? .
#/?? /?? .
#/??? /??? .
#/?* /?* .
#/* /* .
#/* /** ../**
#/* /*** ../***
#/*.* /*.** ../*.**
#/*.??? /*.?? ../*.??
#/[] /[] .
#/[a-z]* /[0-9]* ../[0-9]*
#/foo /foo .
#/foo / ..
#/foo/bar / ../..
#/foo/bar /foo ..
#/foo/bar /foo/baz ../baz
#/foo/bar /bar/foo  ../../bar/foo
#/foo/bar/baz /gnarf/blurfl/blubb ../../../gnarf/blurfl/blubb
#/foo/bar/baz /gnarf ../../../gnarf
#/foo/bar/baz /foo/baz ../../baz
#/foo. /bar. ../bar.
#/foo/barr/baz /foo/bar/baz ../../bar/baz
#EOF
#while read FROM TO VIA; do
#   result=`relativepath "$FROM" "$TO"`
#   printf '%s\n' "FROM: $FROM" "TO:   $TO" "VIA:  $result"
#   if test "$result" != "$VIA"; then
#      printf '%s\n' "OOOPS! Expected '$VIA' but got '$result'"
#   fi
#done

#!/bin/bash

# $Id: $
# Herve Saint-Amand
# Edinburgh

#------------------------------------------------------------------------------

cd $(dirname $0)

supported_versions=(2.7 3.3 3.4 3.5 3.6)
tested_versions=()

for v in ${supported_versions[@]}; do
    cmd="python$v"
    if [ $(which $cmd) ]; then
        full_version=$($cmd --version 2>&1 | sed 's/Python //')
        $cmd -m tests.run $* || exit $?
        echo "tests passed for Python $full_version"
        echo
        tested_versions+=($full_version)
    fi
done

echo "Successfully ran all tests for these Python versions:"
for full_version in ${tested_versions[@]}; do
    echo "    $full_version"
done

find -name '*.pyc' -delete
find -name '__pycache__' -delete

#------------------------------------------------------------------------------

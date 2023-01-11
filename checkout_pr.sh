#!/bin/bash -e

if ! which jq > /dev/null; then exit $?; fi

ME=$0
usage() {
    echo Usage: $ME "<pull request id>"
    echo
    exit 1
}

[ -z "$PRID" ] && PRID=$1
[ -z "$PRID" ] && usage

echo Fetching info for "PR#$PRID"...
JSON=$(curl -s https://api.github.com/repos/arskom/spyne/pulls/$PRID)
#JSON=$(cat pull.json)
BRANCH=$(jq -r .head.ref <<< "$JSON")
UPSTREAM=$(jq -r .head.repo.ssh_url <<< "$JSON")
NAME=$(jq -r .head.user.login <<< "$JSON")

# add remote
if ! git remote get-url $NAME > /dev/null; then
    echo Add remote $NAME url: $UPSTREAM
    git remote add $NAME $UPSTREAM
fi

set -x
git fetch -u $NAME $BRANCH:pr/$PRID
git checkout pr/$PRID
git branch -u $NAME/$BRANCH

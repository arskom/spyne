#!/bin/sh -x

make clean -C doc || exit 1
make html -C doc || exit 1

git checkout gh-pages || exit 1
mv .git ..
rsync -aP doc/build/html/ ./ --delete-after
mv ../.git .

#!/bin/sh

make clean -C doc
make html -C doc

git checkout gh-pages
mv .git ..
rsync -aP doc/build/html/ ./ --delete-after
mv ../.git .

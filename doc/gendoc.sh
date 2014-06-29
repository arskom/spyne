#!/bin/sh -x

git branch
rm -rf docs;
declare -A docs=( [2.10]=2_10 [2.11]=2_11 [2.12]=master );

for i in ${!docs[@]}; do
    git checkout ${docs[$i]} || exit 1;

    rm -rf $i;
    make clean;
    make html || exit 1;
    mv build/html $i;
done;

mkdir docs;
mv ${!docs[@]} docs
make clean;

#!/bin/sh -x

rm -rf docs;
declare -A docs=( [2.9]=2_9 [2.10]=master);
stable=2.9

for i in ${!docs[@]}; do
    git checkout ${docs[$i]} || exit 1;

    rm -rf $i;
    make clean;
    make html || exit 1;
    mv build/html $i;
done;

mkdir docs;
mv ${!docs[@]} docs
rsync -aP docs/$stable/ docs/

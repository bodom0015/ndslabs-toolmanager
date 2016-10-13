#!/bin/bash

#
# Download a zip file using the Clowder API
# Unzip the contents locally and copy to the analysis container
#

echo $*

# $1 dataset download URL
# $2 dataset ID
# $3 clowder access key
# $4 destination directory path
# $5 container ID

tmpdir=`mktemp -d` && cd $dir
mkdir -p $tmpdir/data
echo curl --connect-timeout 10 -k -o $tmpdir/dataset.zip -L $1?key=$3
curl --connect-timeout 10 -k -o $tmpdir/dataset.zip -L $1?key=$3 > $tmpdir/data/transfer-log_$2 2>&1
chmod -R 777 $tmpdir/data
unzip -o $tmpdir/dataset.zip -d $tmpdir/data/$2
rm $tmpdir/dataset.zip
docker cp $tmpdir/data $5:$4
rm -rf $tmpdir

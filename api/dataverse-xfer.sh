#!/bin/bash

#
# Download a data file using the Dataverse API
# Unzip the contents locally and copy to the analysis container
#

echo $*

# $1 datafile download URL
# $2 datafile ID
# $3 API key
# $4 destination directory path
# $5 container ID

tmpdir=`mktemp -d` && cd $dir
echo "Created temp dir $tmpdir"
mkdir -p $tmpdir/data
cd $tmpdir/data
echo curl --connect-timeout 10 -s -k -J -O -L "https://$1?key=$3&format=original"
curl --connect-timeout 10 -s -k -J -O -L "https://$1?key=$3&format=original" > $tmpdir/data/transfer-log_$2 2>&1
chmod -R 777 $tmpdir/data
docker cp $tmpdir/data $5:$4
cd /tmp
rm -rf $tmpdir

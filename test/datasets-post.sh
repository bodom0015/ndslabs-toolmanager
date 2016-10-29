#!/bin/bash
#
# Usage:
#    POST a test object to /datasets: ./datasets-post.sh
#    POST a test array  to /datasets: ./datasets-post.sh -a
#

postBodyType="object"
if [[ "$1" == "-a" ]]; then
    postBodyType="array"
fi

curl -X POST -d @datasets-post-${postBodyType}.json http://localhost:8083/datasets --header "Content-Type:application/json"
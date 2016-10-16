#!/bin/bash
set -e

if [ "$1" = "toolserver" ]; then

   $(which dind) docker daemon \
        --host=unix:///var/run/docker.sock \
        --host=tcp://0.0.0.0:2375 \
        --registry-mirror=http://docker-cache.default:5001 \
        --storage-driver=overlay  > dind.log 2>&1 &

   nginx &

   toolserver.py & 
   sleep infinity
else
   exec "$@"
fi

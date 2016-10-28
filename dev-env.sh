#!/bin/bash

docker build -t cloud9-python -f Dockerfile.devenv . && docker run -it -d --name=cloud9 -v `pwd`:/workspace -w /workspace -p 8080:80 cloud9-python

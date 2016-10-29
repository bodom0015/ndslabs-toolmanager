#!/usr/bin/python

import os, json
import arrow
import logging
import subprocess
import flask_restful as restful
from flask import Flask, request
#from flask.ext import restful
from flask_restful import reqparse, abort, Api, Resource
from jinja2 import Template

app = Flask(__name__) 
api = restful.Api(app)

PORTNUM = os.getenv('TOOLSERVER_PORT', "8083")
metadataPath = "./data/metadata.json"
metadata = {}

class Metadata(restful.Resource):
    def get(self):
        logging.debug("Datasets.get")
        metadata = readMetadata()
        
        id = request.args.get('id')
        
        if id is not None:
            return metadata[str(id)], 200
        else:
            return metadata, 200
    
    def post(self):
        logging.debug("Datasets.post")

        # Read known metadata into memory
        metadata = readMetadata()

        # Parse POST body into JSON
        json_data = request.get_json(force=True)
        logging.debug(metadata)
        
        if type(json_data) is dict:
            addDataset(json_data['id'], json_data['metadata'])
        elif type(json_data) is list:
            for dataset in json_data:
                addDataset(dataset['id'], dataset['metadata'])
        else:
            logging.error("Unexpected POST body encountered: " + type(json_data))
            return

        # Export new metadata store back out to disk
        writeMetadata()

        return json_data, 201
    
    def put(self):
        logging.debug("Datasets.put")
        return "Operation not supported - use POST instead", 501
        
        
    def delete(self):
        logging.debug("Datasets.delete")
        return "Operation not supported", 501
        
        
class Resolver(restful.Resource):
    def get(self, id):
        logging.debug("Resolver.get")
        metadata = readMetadata()
        
        val = metadata[str(id)]
        
        if val is not None:
            return val, 200
        else:
            return "Key not found", 404
        
def addDataset(id, dataset): 
    # Check for existing metadata for this id
    # Merge new data with previous, if any existed
    metadata[str(id)] = dataset
    
    return metadata[str(id)] 

# Read metadata from file
def readMetadata(path=metadataPath):
    logging.debug("readMetadata " + path)
    mdFile = open(path)
    metadataJson = mdFile.read()
    mdFile.close()
    return json.loads(metadataJson)

# Write current metadata store to file
def writeMetadata(path=metadataPath):
    logging.debug("writeMetadata " + path)
    mdFile = open(path, 'w')
    mdFile.write(json.dumps(metadata))
    mdFile.close()
    return

metadata = readMetadata()

# /datasets is for querying and updating dataset metadata from other sites
api.add_resource(Metadata, '/datasets')

# Same as /datasets?id=<string>, resolves an ID to the set of associated metadata
api.add_resource(Resolver, '/resolve/<string:id>')

# ----------------------------

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(PORTNUM), debug=True)

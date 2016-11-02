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

import requests
from requests.auth import HTTPBasicAuth

# TODO: Comment this out to remove toolserver dependency
from toolserver import *

app = Flask(__name__) 
api = restful.Api(app)

logging.basicConfig(level=logging.DEBUG)

PORTNUM = os.getenv('TOOLSERVER_PORT', "8083")
basePath = '/usr/local'
metadataPath = basePath + "/data/metadata.json"
metadata = {}
dataset_list = []
        
"""Allow remote user to lookup metadata about a particular dataset identifier"""
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
        
"""Allow remote user to launch tools next to a given dataset using its associated metadata"""
class Resolver(restful.Resource):
    def get(self, id):
        logging.debug("Resolver.get")
        
        metadata = readMetadata()
        
        dataset_metadata = metadata[str(id)]
        
        if dataset_metadata is None:
            return "Key not found", 404
            
        girder_metadata = dataset_metadata['girder'];
        
        # TODO: Retrieve this from the site metadata
        girder_api_protocol = girder_metadata['api_protocol']
        girder_api_host = girder_metadata['api_host']
        girder_api_port = girder_metadata['api_port']
        girder_api_suffix = girder_metadata['api_suffix']
        girder_api_uri = girder_api_protocol + girder_api_host + girder_api_port + girder_api_suffix
        
        girder_proxy_port = girder_metadata['tmpnb_proxy_port']
        girder_proxy_uri = girder_api_protocol + girder_api_host + girder_proxy_port + '/'
        
        girder_folder_id = girder_metadata['folder_id']
        
        # This shared note environment is bad long-term
        # TODO: needs federated auth somehow
        girder_guest_user = girder_metadata['guest_user']
        girder_guest_pass = girder_metadata['guest_pass']
        
        # TODO: Authenticate
        auth = requests.get(girder_api_uri + '/user/authentication', auth=HTTPBasicAuth(girder_guest_user, girder_guest_pass)).content
        logging.debug(auth)
        
        # Example response:
        # {
        #   "authToken": {
        #     "expires": "2017-04-24T21:48:48.070000+00:00",
        #     "scope": [
        #       "core.user_auth"
        #     ],
        #     "token": "fai4BDAjN5Ba5S9fFRLNKK69gdkhfd4YOchc1mC64gkQMptcV0lV6nFPBRu0jzga"
        #   },
        #   "message": "Login succeeded.",
        #   "user": {
        #     "_accessLevel": 2,
        #     "_id": "581124c0bd2af000015c7e44",
        #     "_modelType": "user",
        #     "admin": true,
        #     "created": "2016-10-26T21:48:47.634000+00:00",
        #     "email": "lambert8@illinois.edu",
        #     "emailVerified": true,
        #     "firstName": "Mike",
        #     "groupInvites": [],
        #     "groups": [],
        #     "lastName": "Lambert",
        #     "login": "admin",
        #     "public": true,
        #     "size": 0,
        #     "status": "enabled"
        #   } 
        # }
        intermediate_url=girder_api_uri + '/notebook/' + girder_folder_id
        logging.debug(intermediate_url)
        
        # Parse the string response into JSON
        auth = json.loads(auth)
        logging.debug(auth)
        
        logging.debug("Token: " +  auth['authToken']['token'])
        
        # TODO: Build up proper headers
        data = { 'id': girder_folder_id }
        postData = json.dumps(data)
        headers = {
            'Content-Length': str(len(postData)), 
            'Content-Type': 'application/json', 
            'Girder-Token': auth['authToken']['token']
        }
        
        # TODO: Send proper POST body?
        notebook = requests.post(intermediate_url, data=data, headers=headers).text
        
        # Parse the string response into JSON
        notebook = json.loads(notebook)
        logging.debug(notebook)
        
        # Example response:
        # {
        #   "_accessLevel": 2,
        #   "_id": "58142ff5bd2af0000156de87",
        #   "_modelType": "notebook",
        #   "containerId": "89a08c97cbe31f484ca1545d4467024feefc881ea8c4af0e4ab8a9dc05fd4a16",
        #   "containerPath": "user/fXJxgykVoLJg",
        #   "created": "2016-10-29T05:13:14.142929+00:00",
        #   "folderId": "5813c451bd2af0000156de85",
        #   "lastActivity": "2016-10-29T05:13:14.142929+00:00",
        #   "mountPoint": "/var/lib/docker/volumes/5813c451bd2af0000156de85_admin/_data",
        #   "status": 0,
        #   "userId": "581124c0bd2af000015c7e44",
        #   "when": "2016-10-29T05:13:14.142929+00:00"
        # }
        #
        
        if 'containerPath' not in notebook:
            return notebook, 500
        
        # TODO: Retrieve and return notebook URL
        #return notebook, 201
        return { 
            "notebook": notebook, 
            "url": girder_proxy_uri + notebook['containerPath'] 
        }, 302
        
def getKnownIds():
    id_list = []
    
    for dataset in dataset_list:
        id_list.append(dataset.id)
    
    return id_list
        
def addDataset(id, dataset): 
    # TODO: Merge new data with previous, if any existed?
    metadata[str(id)] = dataset
    
    #id_list=
    
    dataset_list.append
    
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
    mdFile.write(json.dumps(metadata, indent=2, sort_keys=True))
    mdFile.close()
    return

metadata = readMetadata()

# /datasets is for querying and updating dataset metadata from other sites
api.add_resource(Metadata, '/datasets')

# Same as /datasets?id=<string>, resolves an ID to the set of associated metadata
api.add_resource(Resolver, '/resolve/<string:id>')

# ----------------------------

if __name__ == '__main__':
    writeNginxConf()
    app.run(host="0.0.0.0", port=int(PORTNUM), debug=True)

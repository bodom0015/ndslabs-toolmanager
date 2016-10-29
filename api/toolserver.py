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

id_parser = reqparse.RequestParser()
id_parser.add_argument('id')

post_parser = reqparse.RequestParser()
post_parser.add_argument('name')        # human-readable name to refer to instance for displaying running list
post_parser.add_argument('dataset')     # Dataset download URL e.g. "http://0.0.0.0:9000/clowder/api/datasets/<ds_id>/download"
post_parser.add_argument('datasetId')   # Dataset ID separate from full path, for generating upload history
post_parser.add_argument('datasetName') # Dataset name for generating upload history
post_parser.add_argument('key')         # API key
post_parser.add_argument('ownerId')     # UUID of user who is creating this instance
post_parser.add_argument('source')      # Source application

put_parser = reqparse.RequestParser()
put_parser.add_argument('id')           # tool containerID to upload dataset into
put_parser.add_argument('dataset')      # Dataset download URL e.g. "http://0.0.0.0:9000/clowder/api/datasets/<ds_id>/download"
put_parser.add_argument('datasetId')    # Dataset ID separate from full path, for generating upload history
put_parser.add_argument('datasetName')  # Dataset name for generating upload history
put_parser.add_argument('key')          # API key
put_parser.add_argument('uploaderId')   # UUID of user who is uploading this dataset
put_parser.add_argument('source')       # Source application

get_parser = reqparse.RequestParser()
get_parser.add_argument('id')
get_parser.add_argument('ownerId')      # UUID of user who created the instance
get_parser.add_argument('source')       # Source application

logging.basicConfig(level=logging.DEBUG)
# TODO: Move these parameters somewhere else?
PORTNUM = os.getenv('TOOLSERVER_PORT', "8083")
configPath = "./data/toolconfig.json"
instancesPath = "./data/instances.json"
templatesPath = "./data/templates/"


"""Allow remote user to get contents of logs for container"""
class DockerLog(restful.Resource):

    def get(self, id):
        logging.debug("DockerLog.log " + id)
        p = subprocess.Popen(['docker', 'logs', id], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, err = p.communicate()
        return out, 200


class Instances(restful.Resource):
    # Returns all running tool instances, optionally filtered by owner and/or source
    def get(self):

        args = get_parser.parse_args()
        if args['ownerId']:
           ownerId = str(args['ownerId'])
        else:
           ownerId = ""

        if args['source']:
           source = str(args['source'])
        else:
           source = ""

        logging.debug("get_instances" + " ownerId=" + ownerId + "source=" + source)
        instances = {}
        for containerID in instanceAttrs:
            if len(ownerId) > 0 and instanceAttrs[containerID]['ownerId'] != ownerId:
               continue 

            if len(source) > 0 and instanceAttrs[containerID]['source'] != source:
               continue 

            instances[containerID] = instanceAttrs[containerID]

            # Add some additional tool info from the config data before returning
            cfg = config[instances[containerID]["toolPath"]]
            instances[containerID]["toolName"] = cfg["toolName"]
            instances[containerID]["description"] = cfg["description"]

        return instances, 200

# Main class for instances of tools
class Instance(restful.Resource):

    # Get details of running instance
    def get(self, id):
        args = id_parser.parse_args()

        # Backwards compatibility - v1 used /instances/:toolPath?id= v2 uses /instances/:id
        if args['id']:
           containerID = str(args['id'])
           toolPath = id
        else: 
           containerID = id
           toolPath = instanceAttrs[containerID]["toolPath"]

        logging.debug("Instance.get toolPath=" + toolPath + ", containerID=" + containerID) 

        if containerID in instanceAttrs:
            toolPath = instanceAttrs[containerID]['toolPath']
            cfg = config[toolPath]
            return {
                "toolPath": toolPath,
                "name": instanceAttrs[containerID]["name"],
                "url": instanceAttrs[containerID]["url"],
                "created": instanceAttrs[containerID]["created"],
                "ownerId": instanceAttrs[containerID]["ownerId"],
                "source": instanceAttrs[containerID]["source"],
                "uploadHistory": instanceAttrs[containerID]["uploadHistory"],
                "toolName": cfg["toolName"],
                "description": cfg["description"]
            }, 200
        else:
            return "Container not found", 404

    # Delete an instance
    def delete(self, id):
        args = id_parser.parse_args()

        # Backwards compatibility - v1 used /instances/:toolPath?id= v2 uses /instances/:id
        if args['id']:
           containerID = str(args['id'])
           toolPath = id
        else: 
           containerID = id
           toolPath = instanceAttrs[containerID]["toolPath"]

        logging.debug("Instance.delete toolPath=" + toolPath + ", containerID=" + containerID) 

        # Remove container
        cmd = 'docker rm -f -v '+containerID
        os.popen(cmd).read().rstrip()
        # Remove from list
        del instanceAttrs[containerID]

        writeInstanceAttrsToFile()

        return containerID+" removed", 200

    # Create a new instance of a tool
    def post(self, id):

        args = post_parser.parse_args()
        # Backwards compatibility - v1 used /instances/:toolPath?id= v2 uses /instances/:id
        if config[id]:
           toolPath = id
        else: 
           toolPath = str(args['toolPath'])

        cfg = config[toolPath]
        host = os.environ["NDSLABS_HOSTNAME"]
        if args['source']:
           source = str(args['source'])
        else:
           source = "clowder"

        logging.debug("Instance.post toolPath=" + toolPath + 
             "\n\t dataset=" + str(args['dataset']) + 
             "\n\t datasetId=" + str(args['datasetId']) + 
             "\n\t source=" + source + 
             "\n\t key=" + str(args['key']) )

        # Create the tool container -P Publish all exposed ports
        try:
           toolCmd = "docker create -P -v "+cfg['dataPath']+"/data "+cfg['dockerSrc']
           logging.debug("Creating container: " + toolCmd)
           containerID = os.popen(toolCmd).read().rstrip()
           logging.debug("ContainerID: " + containerID)
        except OSError as e:
           return 500 

        # Do data transfer to container
        try:
            xferCmd = '/usr/local/bin/'+ source +'-xfer.sh '+str(args['dataset'])+' '+str(args['datasetId'])+' '+str(args['key'])+' '+cfg['dataPath']+' '+containerID
            logging.debug("Transfering data: " + xferCmd)
            os.popen(xferCmd).read().rstrip()
        except OSError as e:
           return 500 

        # Start the requested tool container
        try:
            startCmd = 'docker start '+containerID
            logging.debug("Starting container: " + startCmd)
            os.popen(startCmd).read().rstrip()
        except OSError as e:
           return 500 

        # Get and remap port for tool
        try:
            portCmd = "docker inspect --format '{{(index (index .NetworkSettings.Ports \""+cfg['mappedPort']+"\") 0).HostPort}}' "+containerID
            logging.debug("Getting container port " + portCmd)
            port = os.popen(portCmd).read().rstrip()
        except OSError as e:
           return 500 

        # Make a record of this container's URL for later reference
        currTime = arrow.now().isoformat()
        instanceAttrs[containerID] = {
            "toolPath": toolPath,
            "name": str(args['name']),
            "url": "https://" + host+"/"+containerID[0:10]+"/",
            "port": port,
            "created": currTime,
            "ownerId": str(args['ownerId']),
            "source": source,
            "uploadHistory": [{
                "url":str(args['dataset']),
                "time": currTime,
                "uploaderId": str(args['ownerId']),
                "datasetName": str(args['datasetName']),
                "datasetId": str(args['datasetId'])
            }]
        }
        logging.debug(instanceAttrs[containerID])

        writeInstanceAttrsToFile()

        # TODO: initial notebook has code or script or help file to assist in transfer of files back to clowder

        return {
           'id': containerID,
           'URL': "https://" + host+"/"+containerID[0:10]+"/"
        }, 201

    def put(self, id):

        args = put_parser.parse_args()
        # Backwards compatibility - v1 used /instances/:toolPath?id= v2 uses /instances/:id
        if args['id']:
           containerID = str(args['id'])
           toolPath = id
        else: 
           containerID = id
           toolPath = instanceAttrs[containerID]["toolPath"]

        if args['source']:
           source = str(args['source'])
        else:
           source = "clowder"

        logging.debug("Instance.put containerID=" + containerID + 
             "\n\ttoolPath=" + toolPath + 
             "\n\t dataset=" + str(args['dataset']) + 
             "\n\t datasetId=" + str(args['datasetId']) + 
             "\n\t key=" + str(args['key']) )

        # Do data transfer container in another container
        xferCmd = '/usr/local/bin/' + source + '-xfer.sh '+str(args['dataset'])+' '+str(args['datasetId'])+' '+str(args['key'])+' '+config[toolPath]['dataPath'] +  ' ' + containerID
        logging.debug("xferCmd " + xferCmd)
        os.popen(xferCmd).read().rstrip()


        instanceAttrs[containerID]["uploadHistory"].append({
            "url": str(args["dataset"]),
            "time": arrow.now().isoformat(),
            "uploaderId": str(args['uploaderId']),
            "source": str(args['source']),
            "datasetName": str(args['datasetName']),
            "datasetId": str(args['datasetId'])
        })

        writeInstanceAttrsToFile()

        return 204

# Main class for tool definitions, pulling necessary config vars from toolconfig.json
class Toolbox(restful.Resource):

    # Return a list of tools that can be instantiated.
    def get(self):
        logging.debug("Toolbox.get")
        tools = {}
        for toolPath in config.keys():
          tools[toolPath] = {
            "name": config[toolPath]["toolName"],
            "description": config[toolPath]["description"]
          }

        return tools, 200

    # Delete tool endpoint from config file 
    def delete(self):
        logging.debug("Toolbox.delete")
        return 200

    # Add new tool endpoint to config file 
    def post(self):
        logging.debug("Toolbox.post")
        return 201

    # Update existing tool endpoint in config file
    def put(self):
        logging.debug("Toolbox.put")
        return 200
        

# Get configured tools from json file
def getConfig(path=configPath):
    """config file should be a set of definition objects like so:
        {"toolPath": {
                "toolName"      Human-readable name of the tool, e.g. to display in selection menus.
                "description"   Brief description of tool for users.
                "dockerSrc"     Container source on dockerhub.
                "dataPath"      Path where uploaded datasets will be downloaded.
                "mappedPort"    This is used to map ports for containers of this type using docker inspect.
            },
            {...},
            {...}}
    """
    confFile = open(path)
    config = json.load(confFile)
    confFile.close()
    return config

# Get previously written instance attributes from json file, creating file if it doesn't exist
def getInstanceAttrsFromFile(path=instancesPath):
    """instances file stores attributes of running instances so metadata is available after service restart:
        {"containerID": {
                "toolPath"      Reference to which type of tool this instance is (i.e. key in config)
                "name"          Human-readable name to be displayed in Clowder user interface
                "url"           URL for reaching instance from outside
                "created"       Timestamp when container was created
                "ownerId"       UUID of owner in Clowder,
                "uploadHistory" List of objects tracking {url, time, uploaderId, datasetName, datasetId} for each file uploaded to instance
            },
            {...},
            {...}}
    """
    if not os.path.exists(path):
        # Create an empty file if it doesn't exist already
        instFile = open(path, 'w')
        instFile.write("{}")
        instFile.close()

    # TODO: remove entries from this object if there are no matching docker containers
    instFile = open(path)
    attrs = json.load(instFile)
    instFile.close()
    return attrs

# Write current instanceAttrs object to file
def writeInstanceAttrsToFile(path=instancesPath):
    # We don't care what the current contents are; they should either already be loaded or are outdated. Overwrite 'em.
    instFile = open(path, 'w')
    instFile.write(json.dumps(instanceAttrs))
    instFile.close()
    writeNginxConf()

# Read template
def readTemplate(path):
    logging.debug("readTemplate " + path)
    templFile = open(path)
    template = templFile.read()
    templFile.close()
    return template

# Write nginx conf
def writeNginxConf():
    logging.debug("writeNginxConf")
    nginxTmpl = Template(readTemplate(templatesPath + "nginx.tmpl"))

    locations = ""
    for instanceID in instanceAttrs:
        shortID = instanceID[0:10]
        toolPath = instanceAttrs[instanceID]["toolPath"]
        port = instanceAttrs[instanceID]["port"]
        templ = Template(readTemplate(templatesPath + toolPath + ".tmpl"))
        locations += "\n\n" + templ.render(id=shortID, port=port)

    nginxConf = open("/etc/nginx/nginx.conf", 'w')
    nginxConf.write(nginxTmpl.render(locations=locations))
    nginxConf.close()
    reloadNginx()

def reloadNginx():
    logging.debug("reloadNginx")
    cmd = 'nginx -s reload'
    os.popen(cmd).read().rstrip()

# Initialize tool configuration and load any instance data from previous runs
config = getConfig()
instanceAttrs = getInstanceAttrsFromFile()

# ENDPOINTS ----------------
# /tools will fetch summary of available tools that can be launched
api.add_resource(Toolbox, '/tools') 

# /instances will fetch the list of instances that are running on the server
api.add_resource(Instances, '/instances')

# /instances/id fetches details of a particular instance, including URL, owner, history, etc.
# /instances/toolPath 
api.add_resource(Instance, '/instances/<string:id>')


# /logs should return docker logs for the requested container
api.add_resource(DockerLog, '/logs/<string:id>')
# ----------------------------

if __name__ == '__main__':
    writeNginxConf()
    app.run(host="0.0.0.0", port=int(PORTNUM), debug=True)

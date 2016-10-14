#!/usr/bin/python

import os, json
import arrow
import logging
from flask import Flask, request
from flask.ext import restful
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

logging.basicConfig(level=logging.DEBUG)
# TODO: Move these parameters somewhere else?
PORTNUM = os.getenv('TOOLSERVER_PORT', "8083")
configPath = "/usr/local/data/toolconfig.json"
instancesPath = "/usr/local/data/instances.json"
templatesPath = "/usr/local/data/templates/"

"""Allow remote user to get contents of toolserver logs"""
class DockerLog(restful.Resource):

    def get(self):
        cmd = 'docker logs toolserver'
        logtext = os.popen(cmd).read().rstrip()
        return logtext, 200

"""Main class for instances of tools"""
class ToolInstance(restful.Resource):

    def get(self, toolPath):
        """ Get details of running instance """
        args = id_parser.parse_args()
        cfg = config[toolPath]
        containerID = str(args['id'])
        logging.debug("ToolInstance GET toolPath=" + toolPath + ", containerID=" + containerID) 

        if containerID in instanceAttrs:
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

    def delete(self, toolPath):
        """ Delete a tool instance """
        args = id_parser.parse_args()
        containerID = str(args['id'])
        logging.debug("ToolInstance DELETE toolPath=" + toolPath + ", containerID=" + containerID) 

        # Remove container
        cmd = 'docker rm -f -v '+containerID
        os.popen(cmd).read().rstrip()
        # Remove from list
        del instanceAttrs[containerID]

        writeInstanceAttrsToFile()

        return containerID+" removed", 200

    def post(self, toolPath):
        """ Create a new instance of requested tool container """
        args = post_parser.parse_args()
        cfg = config[toolPath]
        #host = request.url_root[:request.url_root.find(":"+PORTNUM)]
        host = os.environ["NDSLABS_HOSTNAME"]
        logging.debug("ToolInstance POST toolPath=" + toolPath + 
             "\n\t dataset=" + str(args['dataset']) + 
             "\n\t datasetId=" + str(args['datasetId']) + 
             "\n\t source=" + str(args['source']) + 
             "\n\t key=" + str(args['key']) )

        # Create the tool container -P Publish all exposed ports
        toolCmd = "docker create -P -v "+cfg['dataPath']+"/data "+cfg['dockerSrc']
        logging.debug(toolCmd)
        containerID = os.popen(toolCmd).read().rstrip()
        logging.debug("CONTAINER ID: " + containerID)

        # Do data transfer to container
        if source  == "dataverse":
            xferCmd = '/usr/local/bin/dataverse-xfer.sh '+str(args['dataset'])+' '+str(args['datasetId'])+' '+str(args['key'])+' '+cfg['dataPath']+' '+containerID
        else :
            xferCmd = '/usr/local/bin/clowder-xfer.sh '+str(args['dataset'])+' '+str(args['datasetId'])+' '+str(args['key'])+' '+cfg['dataPath']+' '+containerID
        logging.debug("xferCmd " + xferCmd)
        os.popen(xferCmd).read().rstrip()

        # Start the requested tool container
        startCmd = 'docker start '+containerID
        logging.debug("startCmd " + startCmd)
        os.popen(startCmd).read().rstrip()

        # Get and remap port for tool
        portCmd = "docker inspect --format '{{(index (index .NetworkSettings.Ports \""+cfg['mappedPort']+"\") 0).HostPort}}' "+containerID
        logging.debug("portCmd " + portCmd)
        port = os.popen(portCmd).read().rstrip()

        # Make a record of this container's URL for later reference
        currTime = arrow.now().isoformat()
        instanceAttrs[containerID] = {
            "toolPath": toolPath,
            "name": str(args['name']),
            "url": "https://" + host+"/"+containerID[0:10]+"/",
            "port": port,
            "created": currTime,
            "ownerId": str(args['ownerId']),
            "source": str(args['source']),
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

    def put(self, toolPath):
        """ Download another dataset into container """
        args = put_parser.parse_args()
        containerID = str(args['id'])
        logging.debug("ToolInstance PUT toolPath=" + toolPath + 
             "\n\t dataset=" + str(args['dataset']) + 
             "\n\t datasetId=" + str(args['datasetId']) + 
             "\n\t key=" + str(args['key']) )

        # Do data transfer container in another container
        if source  == "dataverse":
            xferCmd = '/usr/local/bin/dataverse-xfer.sh '+str(args['dataset'])+' '+str(args['datasetId'])+' '+str(args['key'])+' '+config[toolPath]['dataPath'] +  ' ' + containerID
        else :
            xferCmd = '/usr/local/bin/clowder-xfer.sh '+str(args['dataset'])+' '+str(args['datasetId'])+' '+str(args['key'])+' '+config[toolPath]['dataPath'] +  ' ' + containerID
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

"""Main class for tool definitions, pulling necessary config vars from toolconfig.json"""
class Toolbox(restful.Resource):

    def get(self):
        """ Get a list of eligible tool endpoints that can be called. If toolPath given, return details of specific tool """

        logging.debug("Toolbox GET")
        tools = {}
        for toolPath in config.keys():
          tools[toolPath] = {
            "name": config[toolPath]["toolName"],
            "description": config[toolPath]["description"]
          }

        return tools, 200

    def delete(self):
        """ Delete tool endpoint from config file """
        return 200

    def post(self):
        """ Add new tool endpoint to config file """
        return 201

    def put(self):
        """ Update existing tool endpoint in config file """
        return 200

"""Used to fetch entire set of running instances for populating manager list"""
class Instances(restful.Resource):

    def get(self):
        """ Return attributes of all running tool instances """
        logging.debug("Instances GET")
        instances = {}
        for containerID in instanceAttrs:
            instances[containerID] = instanceAttrs[containerID]

            # Add some additional tool info from the config data before returning
            cfg = config[instances[containerID]["toolPath"]]
            instances[containerID]["toolName"] = cfg["toolName"]
            instances[containerID]["description"] = cfg["description"]

        return instances, 200


"""Get configured tools from json file"""
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

"""Get previously written instance attributes from json file, creating file if it doesn't exist"""
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

"""Write current instanceAttrs object to file"""
def writeInstanceAttrsToFile(path=instancesPath):
    # We don't care what the current contents are; they should either already be loaded or are outdated. Overwrite 'em.
    instFile = open(path, 'w')
    instFile.write(json.dumps(instanceAttrs))
    instFile.close()
    writeNginxConf()
    reloadNginx()

"""Read template"""
def readTemplate(path):
    templFile = open(path)
    template = templFile.read()
    templFile.close()
    return template

""" Write nginx conf"""
def writeNginxConf():
    print "Writing nginx conf"
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
    print "Reloading nginx"
    cmd = 'nginx -s reload'
    os.popen(cmd).read().rstrip()

# Initialize tool configuration and load any instance data from previous runs
config = getConfig()
instanceAttrs = getInstanceAttrsFromFile()

# ENDPOINTS ----------------
# /tools will fetch summary of available tools that can be launched
api.add_resource(Toolbox, '/tools') # TODO: Allo /tools/<toolPath> to get more details about specific tool

# /instances will fetch the list of instances that are running on the server
api.add_resource(Instances, '/instances')

# /instances/toolPath fetches details of a particular instance, including URL, owner, history, etc.
api.add_resource(ToolInstance, '/instances/<string:toolPath>')

# /logs should return docker logs for the requested toolPath TODO: remove?
api.add_resource(DockerLog, '/logs')
# ----------------------------

if __name__ == '__main__':
    writeNginxConf()
    app.run(host="0.0.0.0", port=int(PORTNUM), debug=True)

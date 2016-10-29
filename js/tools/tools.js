/* global angular */

'use strict';

angular.module('toolmgr.tools', ['ngRoute', 'ngResource', /*'toolmgr.instances'*/ ])

/** 
 * Use mock REST API?
 */
.constant('MOCK', false)

/**
 * Inject lodash as an angular service
 */
.constant('_', window._)

/**
 * Configure "ToolInstance" REST API Client
 */
.factory('ToolInstance', [ '$resource', function($resource) {
  // TODO: How to handle "maps" with $resource?
  return $resource('/api/instances/:id', { id:'@toolPath' });
}])

/**
 * Configure "Toolbox" REST API Client
 */
.factory('Tool', [ '$resource', function($resource) {
  return $resource('/api/tools', {});
}])

/**
 * Configure "Launch" REST API Client
 * 
 * GET /resolve/<string:id> => lookup metadata about a given id, then use this metadata to launch a notebook next to the data
 */
.factory('Resolve', [ '$resource', function($resource) {
  return $resource('/api/resolve/:id', {});
}])

/**
 * Configure "Datasets" REST API Client
 * 
 * DELETE /datasets                 => Not implemented - returns 501
 * PUT /datasets                    => Not implemented - returns 501
 * GET /datasets                    => lookup all metadata records
 * GET /datasets?id=<string:id>     => lookup metadata about a given id (this is the same as GET /resolve/<string:id>)
 * POST /datasets                   => Import dataset or datasets ids/metadata provided in the POST body
 *    Expected Body: object or array of objects containing only the following two fields:
 *        -id: the string identifier of a metadata record
 *        -metadata: a JSON object containing any necessary information needed to launch the record
 *              (i.e. capabilities, urls, guest user credentials, etc.)
 * 
 * NOTE: all other fields on POST body will be ignored
 */
.factory('Datasets', [ '$resource', function($resource) {
  return $resource('/api/datasets', {});
}])

/**
 * Configure up a route to the "Toolbox" view
 */
.config(['$routeProvider', function($routeProvider) {
  $routeProvider.when('/tools', {
    templateUrl: 'tools/tools.html',
    controller: 'ToolCtrl'
  });
}])

.factory('Instances', [function() {
  return {
    list: {}
  };
}])

.factory('Tools', [function() {
  return {
    list: {}
  };
}])

/**
 * The controller for our "Toolbox" view
 */
.controller('ToolCtrl', [ '$log', '$scope', '$window', '$routeParams', '$http', 'MOCK', 'Tools', 'Instances', 'ToolInstance', 'Tool', 'Datasets', 'Resolve',
      function($log, $scope, $window, $routeParams, $http, MOCK, Tools, Instances, ToolInstance, Tool, Datasets, Resolve) {
    $scope.instances = {};
    
    ($scope.resetForm = function() {
      /* Tool parameters */
      $scope.instances.template = {}; //new ToolInstance();
      $scope.instances.template.name = $routeParams['name'] || '';
      
      /* API parameters */
      $scope.instances.template.key = $routeParams['key'] || '';
      $scope.instances.template.ownerId = $routeParams['ownerId'] || '';
      $scope.instances.template.source = $routeParams['source'] || '';
      
      /* Dataset parameters */
      $scope.instances.template.datasetName = $routeParams['datasetName'] || '';
      $scope.instances.template.datasetId = $routeParams['datasetId'] || '';
      $scope.instances.template.dataset = $routeParams['dataset'] || '';
      
      angular.forEach(['name', 'key', 'ownerId', 'source', 'dataset', 'datasetName', 'datasetId' ], function(key) {
        delete $routeParams[key];
      });
    })();
    
    Datasets.get({ /* request parameters go here */ }, function(datasets) {
      $scope.datasets = datasets;
      $log.debug("Successful GET from /datasets!");
    }, function(response) {
      $log.debug("Failed GET from /datasets:");
      $log.debug(response);
      console.debug(response);
    });
    
    $scope.resolve = function(id, dataset) {
      Resolve.save({ id:id }, { /* POST body goes here */ }, function(tool) {
        $scope.tool = tool;
        $log.debug("Successful POST to /resolve!");
      }, function(response) {
        $scope.tool = response.data;
        
        if (response.status == 302 && response.data.url) {
          $window.open(response.data.url, '_blank');
          return;
        }
        
        $log.debug("Failed POST to /resolve:");
        console.debug(response);
      });
    };
    
    var nextId = 1;
    
    /* Creates a new ToolInstance from the template */
    $scope.createInstance = function(toolKey, tool, template) {
      $log.debug('Creating new instance of ' + toolKey);
      
      var newInstance = new ToolInstance($scope.instances.template);
      newInstance.toolPath = toolKey;
      
      if (MOCK) {
        var id = nextId++;
        $scope.instances.list[id] = Instances.list[id] = newInstance;
        return;
      }
      
      newInstance.$save(function() {
        $log.debug('Successfully created ToolInstance:' + template.name);
        $scope.retrieveInstances();
        $scope.resetForm();
      }, function() {
        $log.error('Failed creating ToolInstance:' + template.name);
      });
      
      $scope.resetForm();
    };
    
    /* Retrieves the list of existing ToolInstances */
    ($scope.retrieveInstances = function() {
      $log.debug('Grabbing instances');
      
      if (MOCK) {
        $scope.instances.list = Tools.list = {
          '123456789': { name:'Test User\' instance' }  
        };
        return;
      }
      
      $scope.instances.list = Instances.list = ToolInstance.get({ /*ownerId: $routeParams['ownerId'] || ''*/ }, function() {
        $log.debug('Successfully populated ToolInstances!');
      }, function() {
        $log.error('Failed populating ToolInstances!');
      });
    })();
    
    /* Attach a new dataset to an existing ToolInstance */
    $scope.updateInstance = function(id, instance, template) {
      if (!id) {
        $log.error("Bad id: " + id + " on instance " + instance);
        return;
      }
      
      $log.debug('Updating instance: '+ id);
      
      if (MOCK) {
        $scope.instances.list[id].uploadHistory.push({
          url: template.dataset,
          time: new Date(),
          uploaderId: "",
          source: "None",
          datasetName: template.datasetName,
          datasetId: template.datasetId
        });
        return;
      }
      
      $http.put('/api/instances/' + id, template).then(function(data) {
        $log.debug('Successfully saved ToolInstance:' + instance.name);
        $scope.resetForm();
        $scope.retrieveInstances();
      }, function(response) {
        $log.error('Failed saving ToolInstance:' + instance.name);
      });
    };
    
    /* Deletes an existing ToolInstance */
    $scope.deleteInstance = function(id, instance) {
      if (!id) {
        $log.error("Bad id: " + id + " on instance " + instance);
        return;
      }
      
      $log.debug('Deleting instance: '+ id);
      
      if (MOCK) {
        delete $scope.instances.list[id];
        return;
      }
      
      $http.delete('/api/instances/' + id).then(function(data) {
        $log.debug('Successfully deleted ToolInstance:' + id);
        $scope.retrieveInstances();
      }, function(response) {
        $log.error('Failed deleting ToolInstance:' + id);
      });
    };
    
    /* Retrieve the list of Tools */
    ($scope.retrieveTools = function() {
      if (MOCK) {
        $scope.tools = {
          'jupyterlab': {
            name: 'JupyterLab',
            description: 'JupyterLab environment'
          },
          'rstudio': {
            name: 'RStudio',
            description: 'RStudio analysis environment'
          }
        };
        return;  
      }
      
      $scope.tools = Tools.list = Tool.get({}, function() {
        $log.debug('Successfully populated Tools!');
      }, function() {
        $log.error('Failed populating Tools!');
      });
    })();
}]);

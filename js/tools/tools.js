/* global angular */

'use strict';

angular.module('toolmgr.tools', ['ngRoute', 'ngResource', /*'toolmgr.instances'*/ ])

/**
 * Configure "ToolInstance" REST API Client
 */
.factory('ToolInstance', [ '$resource', function($resource) {
  // TODO: How to handle "maps" with $resource?
  return $resource('/api/instances/:id', { id:'@id' });
}])

/**
 * Configure "Toolbox" REST API Client
 */
.factory('Tool', [ '$resource', function($resource) {
  return $resource('/api/tools', {});
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

.factory('Tools', [function() {
  return {
    list: []
  };
}])

/**
 * The controller for our "Toolbox" view
 */
.controller('ToolCtrl', [ '$log', '$scope', '$routeParams', 'Tools', 'ToolInstance', 'Tool', function($log, $scope, $routeParams, Tools, ToolInstance, Tool) {
    $scope.instances = {};
    
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
    
    /* Creates a new ToolInstance from the template */
    $scope.instances.createInstance = function(tool, template) {
      var newInstance = new ToolInstance($scope.instances.template);
      newInstance.toolPath = Tools.selected;
      
      newInstance.$save(function() {
        $log.debug('Successfully created ToolInstance:' + template.name);
      }, function() {
        $log.error('Failed creating ToolInstance:' + template.name);
      });
    };
    
    /* Retrieves the list of existing ToolInstances */
    ($scope.retrieveInstances = function() {
      /*$scope.instances.list = ToolInstance.get({ ownerId: $routeParams['ownerId'] || '' }, function() {
        $log.debug('Successfully populated ToolInstances!');
      }, function() {
        $log.error('Failed populating ToolInstances!');
      });*/
      $scope.instances.list = {
        '123456789': { name:'Test User\' instance' }  
      };
    })();
    
    /* Add a new dataset to an existing ToolInstance */
    $scope.updateInstance = function(id, instance, template) {
      debugger;
      instance.$save(function() {
        $log.debug('Successfully saved ToolInstance:' + instance.name);
      }, function() {
        $log.error('Failed saving ToolInstance:' + instance.name);
      });
    };
    
    /* Deletes an existing ToolInstance */
    $scope.deleteInstance = function(id, instance) {
      if (!id) {
        $log.error("Bad id: " + id + " on instance " + instance);
        return;
      }
      
      delete instance[id];
      
      instance.$save(function() {
        $log.debug('Successfully deleted ToolInstance:' + id);
      }, function() {
        $log.error('Failed deleting ToolInstance:' + id);
      });
    };
    
    /* Retrieve the list of Tools */
    ($scope.retrieveTools = function() {
      $scope.tools = Tools.list = Tool.get({}, function() {
        $log.debug('Successfully populated Tools!');
      }, function() {
        $log.error('Failed populating Tools!');
      });
    })();
}]);

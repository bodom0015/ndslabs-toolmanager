/* global angular */

'use strict';

angular.module('toolmgr.instances', ['ngRoute', 'ngResource'])

/**
 * Configure "ToolInstance" REST API Client
 */
.factory('ToolInstance', [ '$resource', function($resource) {
  // TODO: How to handle "maps" with $resource?
  return $resource('/api/instances/:id', { id:'@id' });
}])

/**
 * Configure up a route to the "ToolInstances" view
 */
.config(['$routeProvider', function($routeProvider) {
  $routeProvider.when('/instances', {
    templateUrl: 'instances/instances.html',
    controller: 'ToolInstancesCtrl',
    controllerAs: 'instances'
  });
}])

/**
 * The controller for our "ToolInstances" view
 */
.controller('ToolInstancesCtrl', [ '$log', '$location', '$routeParams', 'ToolInstance', 'Tools',
        function($log, $location, $routeParams, ToolInstance, Tools) {
    var instances = this;
    
    /* Tool parameters */
    instances.template = {}; //new ToolInstance();
    instances.template.name = $routeParams['name'] || '';
    
    /* API parameters */
    instances.template.key = $routeParams['key'] || '';
    instances.template.ownerId = $routeParams['ownerId'] || '';
    instances.template.source = $routeParams['source'] || '';
    
    /* Dataset parameters */
    instances.template.datasetName = $routeParams['datasetName'] || '';
    instances.template.datasetId = $routeParams['datasetId'] || '';
    instances.template.dataset = $routeParams['dataset'] || '';
    
    /* Creates a new ToolInstance from the template */
    instances.createInstance = function(tool, template) {
      var newInstance = new ToolInstance(instances.template);
      newInstance.toolPath = Tools.selected;
      
      newInstance.$save(function() {
        $log.debug('Successfully created ToolInstance:' + template.name);
      }, function() {
        $log.error('Failed creating ToolInstance:' + template.name);
      });
    };
    
    /* Retrieves the list of existing ToolInstances */
    (instances.retrieveInstances = function() {
      instances.list = ToolInstance.get({ ownerId: $routeParams['ownerId'] || '' }, function() {
        $log.debug('Successfully populated ToolInstances!');
      }, function() {
        $log.error('Failed populating ToolInstances!');
      });
    })();
    
    /* Add a new dataset to an existing ToolInstance */
    instances.updateInstance = function(id, instance, template) {
      debugger;
      instance.$save(function() {
        $log.debug('Successfully saved ToolInstance:' + instance.name);
      }, function() {
        $log.error('Failed saving ToolInstance:' + instance.name);
      });
    };
    
    /* Deletes an existing ToolInstance */
    instances.deleteInstance = function(id, instance) {
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
}]);

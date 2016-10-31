/* global angular */

'use strict';

angular.module('toolmgr.datasets', ['ngRoute', 'ngResource' ])

/**
 * Inject lodash as an angular service
 */
.constant('_', window._)

/**
 * Configure "Resolve" REST API Client
 * 
 * GET /resolve/<string:id> => lookup metadata about a given id, then use this metadata to launch a notebook next to the data
 *      Returns: 200 => an object containing the notebook launched and a URL to access it
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


.factory('Logs', [ '$resource', function($resource) {
  return $resource('/api/logs/:containerId', {});
}])

/**
 * Configure up a route to the "Datasets" view
 */
.config(['$routeProvider', function($routeProvider) {
  $routeProvider.when('/datasets', {
    templateUrl: 'datasets/datasets.html',
    controller: 'DatasetsCtrl'
  });
}])

/**
 * The controller for our "Datasets" view
 */
.controller('DatasetsCtrl', [ '$log', '$scope', '$window', 'Datasets', 'Resolve', 'Logs',
      function($log, $scope, $window, Datasets, Resolve, Logs) {
    
    $scope.selectedMetadata = null;
    
    $scope.getLogs = function() {
      return $scope.logs = Logs.get();
    };
    
    $scope.viewMetadata = function(metadata) {
      $scope.selectedMetadata = metadata;
    };
    
    Datasets.get({ /* request parameters go here */ }, function(datasets) {
      $scope.datasets = datasets;
      $log.debug("Successful GET from /datasets!");
    }, function(response) {
      $log.debug("Failed GET from /datasets:");
      $log.debug(response);
      console.debug(response);
    });
    
    $scope.resolving = {};
    $scope.resolve = function(id, dataset) {
      $scope.resolving[id] = true;
      Resolve.get({ id:id }, { /* POST body goes here */ }, function(tool) {
       
        $scope.resolving[id] = false;
        $scope.tool = tool;
        
        $log.debug("Successful GET to /resolve!");
      }, function(response) {
        $scope.resolving[id] = false;
        $scope.tool = response.data;
        
        if (response.status == 302 && response.data.url) {
          // Attach URL to target dataset
          angular.forEach($scope.datasets, function(dataset, datasetId) {
            if (datasetId === id) {
              dataset.tool_url = response.data.url;
            }
          });
          
          // Open a new tab to the tool
          // NOTE: Pop-up blocker may prevent this from showing
          $window.open(response.data.url, '_blank');
          return;
        }
        
        $log.debug("Failed GET to /resolve:");
        console.debug(response);
      });
    };
}]);

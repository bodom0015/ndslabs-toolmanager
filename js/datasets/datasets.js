/* global angular */

'use strict';

angular.module('toolmgr.datasets', ['ngRoute', 'ngResource' ])

/**
 * Inject lodash as an angular service
 */
.constant('_', window._)

/**
 * Mock calls to API?
 */
.constant('MOCK', true)

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
.controller('DatasetsCtrl', [ '$log', '$scope', '$window', 'Datasets', 'Resolve', 'MOCK',
      function($log, $scope, $window, Datasets, Resolve, MOCK) {
    
    $scope.selectedMetadata = null;
    
    // TODO: This is ugly and I hate it... should be a filter
    $scope.viewCitation = function(id, metadata) {
      $scope.viewJson = false;
      var citation = '';
      
      if (metadata.dataset) {
        // Loop over authors and append them
        if (metadata.dataset.authors) {
          citation += 'Authors: ';
          angular.forEach(metadata.dataset.authors, function(author) {
            if (author !== metadata.dataset.authors[0]) {
              citation += ', '
            }
            citation += author.lastName + ', ' + author.firstName + ' (' + author.email + '), ';
          });
        }
        
        // Append dataset label
        if (metadata.dataset.label) {
          citation += '"' + metadata.dataset.label + '", ';
        }
      }
      
      // Append ID / DOI link
      citation += id;
      
      $scope.selectedMetadata = citation;
    };
    
    $scope.viewMetadata = function(metadata) {
      $scope.selectedMetadata = metadata;
      $scope.viewJson = true;
    };
    
    
      $scope.datasets = {
        "test1": {
          "girder_api_host": "141.142.208.142",
          "girder_api_port": ":8080",
          "girder_api_protocol": "http://",
          "girder_api_suffix": "/api/v1",
          "girder_folder_id": "5813c451bd2af0000156de85",
          "girder_guest_pass": "123456",
          "girder_guest_user": "admin",
          "girder_proxy_port": ""
        },
        "test2": {
          "dataset": {
            "label": "Test Dataset 2",
            "landing_url": "http://landing.page.com/2/",
            "authors": [
              { "email": "test2@author.com", "name": "Test Author 2" }
            ]
          },
          "girder": {
            "api_protocol": "http://",
            "api_host": "141.142.208.127",
            "api_port": ":8080",
            "api_suffix": "\/api\/v1",
            "tmpnb_proxy_port": "",
            "folder_id": "5814ec2830c4eb000199d09a",
            "guest_user": "admin",
            "guest_pass": "123456"
          }
        }
      };
    
    if (!MOCK) {
      Datasets.get({ /* request parameters go here */ }, function(datasets) {
        $scope.datasets = datasets;
        $log.debug("Successful GET from /datasets!");
      }, function(response) {
        $log.debug("Failed GET from /datasets:");
        $log.debug(response);
        console.debug(response);
      });
    }
    
    $scope.resolving = {};
    $scope.resolve = function(id, dataset) {
      $scope.resolving[id] = true;
      
      if (!MOCK) {
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
                dataset.girder.tool_url = response.data.url;
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
    }
}]);

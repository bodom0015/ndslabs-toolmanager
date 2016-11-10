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
.constant('MOCK', false)

/**
 * Offer full metadata listing
 */
.constant('DEBUG', false)

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
 *        -label: the friendly name to give this dataset
 *        -authors: array of authors of this dataset
 *        -landing_url: url to the landing page for this dataset
 *        -metadata: a JSON object containing any necessary information needed to launch the record
 *              (i.e. capabilities, urls, guest user credentials, etc.)
 * 
 */
.factory('Datasets', [ '$resource', 'MOCK', function($resource, MOCK) {
  if (MOCK) {
    return $resource('./datasets/metadata.json', {});
  } else {
    return $resource('/api/datasets', {});
  }
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

.filter('authors', [ function() {
  return function(dataset) {
    // Loop over authors and append them
    if (!dataset.authors) {
      return "";
    }
    
    var authorsList = '';
    angular.forEach(dataset.authors, function(author) {
      if (author !== dataset.authors[0]) {
        authorsList += '; '
      }
      authorsList += author.lastName + ', ' + author.firstName + (author.email ? ' (' + author.email + ')' : '');
    });
    
    return authorsList;
  };
}])

.filter('citation', [ function() {
  return function(dataset) {
      var citation = '';
      // Append dataset label
      if (dataset.label) {
        citation += ', "' + dataset.label + '", ';
      }
      
      // Append ID / DOI link
      citation += dataset._id;
      
      return citation;
  };
}])

/**
 * The controller for our "Datasets" view
 */
.controller('DatasetsCtrl', [ '$log', '$scope', '$http', '$window', 'Datasets', 'Resolve', 'DEBUG',
      function($log, $scope, $http, $window, Datasets, Resolve, DEBUG) {
    $scope.DEBUG = DEBUG;
    $scope.searchQuery = '';
    
    $scope.datasets = [];
    
    Datasets.query({ /* request parameters go here */ }, function(datasets) {
      $scope.datasets = datasets;
      $log.debug("Successful GET from /datasets!");
      angular.forEach($scope.datasets, function(dataset) {
        angular.forEach(dataset.publications, function(publication) {
          var url = publication.url;
          $http({method: 'GET', url: url, headers: {'Accept' : 'text/x-bibliography; style=apa'} }).then(function successCallback(response) {
            publication.datacite = response.data;
          }, function errorCallback(response) {
            $log.error('Failed to retrieve trusted citation for: ' + url);
            console.debug(response);
          });
        });
      });
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
          angular.forEach($scope.datasets, function(dataset) {
            if (dataset._id === id) {
              dataset.girder.tool_url = response.data.url;
            }
          });
          
          // Open a new tab to the tool
          // FIXME: Pop-up blocker may prevent this from showing
          $window.open(response.data.url, '_blank');
          return;
        }
        
        $log.debug("Failed GET to /resolve:");
        console.debug(response);
      });
    }
}]);

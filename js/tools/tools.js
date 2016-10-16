/* global angular */

'use strict';

angular.module('toolmgr.tools', ['ngRoute', 'ngResource', 'toolmgr.instances' ])

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
    controller: 'ToolCtrl',
    controllerAs: 'tools'
  });
}])

.factory('Tools', [function() {
  return {
    list: [],
    selected: null
  };
}])

/**
 * The controller for our "Toolbox" view
 */
.controller('ToolCtrl', [ '$log', '$scope', '$routeParams', 'Tools', 'Tool', function($log, $scope, $routeParams, Tools, Tool) {
    var tools = this;
    
    /* Write back to shared store when value changes */
    $scope.$watch('tools.selected', function(newValue, oldValue) {
      Tools.selected = tools.selected;
    });
    
    /* Retrieve the list of Tools */
    (tools.retrieve = function() {
      tools.list = Tools.list = Tool.get({}, function() {
        $log.debug('Successfully populated Tools!');
      }, function() {
        $log.error('Failed populating Tools!');
      });
    })();
}]);

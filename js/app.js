/* global angular */

'use strict';

// Declare app level module which depends on views, and components
angular.module('toolmgr', [
  'ngRoute',
  /*'toolmgr.logs',*/
  'toolmgr.tools',
  /*'toolmgr.instances'*/
])

/**
 * Given a string, capitalize each term (separated by whitespace)
 */ 
.filter('capitalize', [ '_', function(_) {
  return function(input) {
    var ret = [];
    angular.forEach(_.split(input, /\s/), function(term) {
      ret.push(_.capitalize(term));
    });
    return _.join(ret, " ");
  };
}])

/**
 * Configure the overarching toolmgr module
 */ 
.config(['$locationProvider', '$logProvider', '$routeProvider', function($locationProvider, $logProvider, $routeProvider) {
  $locationProvider.hashPrefix('!');
  $logProvider.debugEnabled(true);
  $routeProvider.otherwise({redirectTo: '/tools'});
}]);
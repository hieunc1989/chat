var rtApp = angular.module('RabbitornadoApp', []);


rtApp.controller('RoomCtrl', ['$scope', '$element', function($scope, $element) {
    
    var elem = $element[0];
    $scope.sender = elem.sender || 'anonymous';
    $scope.message = elem.message || 'no message';
    $scope.room_name = elem.id;
    $scope.topic = $scope.room_name;
    $scope.lines = [];
        
    console.log("RoomCtrl being loaded ", $element[0].id);
    console.log("TRYING ws://localhost:8888/ws/" + $scope.room_name);
    var ws = new WebSocket("ws://localhost:8888/ws/" + $scope.room_name);
    $scope.ws = ws;
        
    ws.onopen = function() {
       //ws.send("Hello, world");
    };
    ws.onmessage = function (evt) {
        var data = {};
        try {
            data = JSON.parse(evt.data);
        } catch(err) {
            data = { command: 'raw', message: '/raw ' + evt.data };
        }

        var inner_html = null;
        if(data.message.indexOf('/') == 0) {
            var x = data.message.match(/\/(\w+)\s+(.+)/);
            switch(x[1].toLowerCase()) {
                case 'topic':
                    $scope.topic = x[2];
                    break;
                case 'me':
                    inner_html = '<span class="me">' + data.from + ' ' + x[2] + '</span>';
                    break;
                case 'raw':
                    inner_html = '<span class="raw">' + x[2] + '</span>';
                    break;
            }
        }
        else {
            inner_html = '<span class="sender">' + data.from + '</span>' + data.message;
        }

        if(inner_html) {
            var d = new Date(data.ts);
            var ts = d.toLocaleTimeString();
            inner_html = '<span class="ts">' + ts + '</span>' + inner_html;
            /*
            var li = document.createElement("li");
            li.innerHTML = inner_html;
        
            output_list.appendChild(li);
            */
            $scope.lines.push(inner_html);
            $scope.$apply();
            var ul = elem.getElementsByClassName('output_list');
            ul[0].scrollTop = ul[0].scrollHeight;
        }
        else {
            $scope.$apply();
        }
    }

	$scope.send = function() {
        var sender = $scope.sender;
        var message = $scope.message;
        if(sender && message) {
            $scope.ws.send(JSON.stringify({ts: Date.now(), from: sender, to: '*', topic: $scope.room_name, content_type: 'text/html', message: message}));
            $scope.message = '';
        }
    }
}]);


rtApp.directive('chatroom', [function() {
    console.log("chatroom directive being loaded");
	return {
    	restrict: 'E',
        replace: true,
        templateUrl: "/static/room.template.html",
        scope: {},
        controller: 'RoomCtrl',
    };
}]);
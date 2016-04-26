function setup(){
  var map = L.map('map', {
    center: [50.8749, -1.328],
    //odly this prevents map load event from being fired
    //zoom: 19
  });

  var googleSat = L.tileLayer('http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',{
    maxZoom: 20,
    subdomains:['mt0','mt1','mt2','mt3']
  });

  googleSat.addTo(map);

  var markers = L.layerGroup();
  markers.addTo(map);
  var bounds = new L.latLngBounds([]);
  var colScale = d3.scale.category10();

  var updateMap = function(d) {
    if (d.lat === 0) {
     //d.lat = 50.8749 + Math.random()/1000;
     //d.lon = -1.328 + Math.random()/1000;
     //d.yaw = Math.random();
     return;
    }
    var ll = L.latLng(d.lat, d.lon);
    bounds.extend(ll);

    var col = colScale(d.cls);
    //draw a circle for the detection
    var circle = L.circleMarker(ll, {
        radius: d.score/2.0,
        color: 'white',
        weight: 3,
        fillColor: col,
        fillOpacity: 1
    });

    // add a line pointing in the direction we are yawed
    var start = map.latLngToContainerPoint(ll);
    // translate
    var len = Math.max(15, d.score*5);
    // straight up
    var pt = L.point(start.x, start.y - len);
    // rotate
    pt = pt.subtract(start);
    a = d.yaw;
    pt.x = pt.x * Math.cos(a) - pt.y * Math.sin(a);
    pt.y = pt.x * Math.sin(a) + pt.y * Math.cos(a);
    pt = pt.add(start);

    var end = map.containerPointToLatLng(pt);

    var line = L.polyline([ll, end], {
      weight: 4,
      color: "white",
      lineCap: "round",
      fillColor: col,
      fillOpacity: 0.7
    });

    var fg = L.featureGroup([circle, line])
      .bindPopup(d.cls + " (" + d.score.toFixed(2) + "%)");

    if (d.score > 20){
        fg.bindLabel(d.cls, {noHide: true});
    }

    markers.addLayer(fg);

    map.fitBounds(bounds);
  };

  map.on("load", function(e) {
    map.setZoom(19);
    setupSocket(updateMap);
  });

  map.locate({setView: true});
}

function setupSocket(mapFun){
    var socket = io('http://' + document.domain + ':' + location.port);

    socket.on('disconnect', function() {
        console.log('disconnected');
    });

    socket.on('connect', function() {
        console.log('connected');
    });
    socket.on('meta', function(msg) {
          $("#fn").text(msg.fn);
          $("#class").text(msg.cls + " (" + msg.score.toFixed(2) + "%)");
          $("#lat").text(msg.lat.toFixed(5));
          $("#lon").text(msg.lon.toFixed(5));
          mapFun(msg);
    });

    socket.on('frame', function(msg) {
          $("#video").attr('src', 'data:image/jpeg;base64,' + msg)

          /*var arrayBuffer = msg.data;
          var bytes = new Uint8Array(arrayBuffer);
          var blob        = new Blob([bytes.buffer]);

          var image = document.getElementById('video');

          var reader = new FileReader();
          reader.onload = function(e) {
            image.src = e.target.result;
          };
          reader.readAsDataURL(blob); */
    });
}


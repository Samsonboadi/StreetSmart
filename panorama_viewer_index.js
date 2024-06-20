/*jshint esversion: 6 */

/**
 * Calls python to indicate that the browser is ready to receive commands
 */
function apiInitialized() {
    js_initialized();
    console.log('Api: init: success!');
    // Hide the loading screen and show the main content
    document.getElementById('loadingScreen').style.display = 'none';
    document.getElementById('streetsmartApi').style.display = 'block';
}

/*function loadError(oError) {
    //throw new URIError(`The script ${oError.target.src} didn't load correctly.`);
    console.log('Api: init: success!',oError.oError.target.src);
  }*/

  function loadError(oError) {
    console.log('Api: init: failed!', oError.target.src);
    // Optionally, display a different message or UI element to the user indicating the load failure
    document.getElementById('loadingScreen').innerHTML = "Failed to load resources. Please try again.";
}
/**
 * Initialize Street Smart API
 */
function initApi(userSettings, addressSettings, configSettings) {
    console.log("initApi");
    console.log(userSettings);
    console.log(addressSettings);
    console.log(configSettings);
    load_streetsmart_api();

    /**
     * Loads streetsmart API script
     * http://www.jspatterns.com/the-ridiculous-case-of-adding-a-script-element/
     */
    function load_streetsmart_api() {
        var js = document.createElement('script');
        js.onerror = loadError;
        js.async = false;
        js.src = configSettings.streetsmartApiUrl;
        js.onreadystatechange= initialize;
        js.onload = initialize;
        var first = document.getElementsByTagName('script')[0];
        first.parentNode.insertBefore(js, first);
        console.log(js);
    }
    

    /*
     * Initializes the streetsmart API once the script is loaded.
     */
    function initialize() {
        StreetSmartApi.init({
            targetElement: document.getElementById('streetsmartApi'),
            username: userSettings.username,
            password: userSettings.password,
            apiKey: userSettings.apiKey,
            srs: configSettings.srs,
            locale: configSettings.locale,
            configurationUrl: configSettings.configUrl,
            addressSettings:
                {
                locale: addressSettings.locale,
                database: addressSettings.database
                }
        }).then(
            apiInitialized,
            function(err) {
                console.log('Api: init: failed. Error: ', err);
                alert('Api Init Failed!');
            }
        );
    }
}

/**
 * Creates the cone string
 * @param {viewer} panoramaViewer Viewer for which the cone is calculated
 */
function coneString(panoramaViewer) {
        rotation = panoramaViewer.getOrientation().yaw;
        x = panoramaViewer.getRecording().xyz[0];
        y = panoramaViewer.getRecording().xyz[1];
        z = panoramaViewer.getRecording().xyz[2];
        id = panoramaViewer.getRecording().id;
        srs = panoramaViewer.getRecording().srs;
        r = panoramaViewer.getViewerColor()[0];
        g = panoramaViewer.getViewerColor()[1];
        b = panoramaViewer.getViewerColor()[2];
        a = panoramaViewer.getViewerColor()[3] * 255;

        return [id, x, y, z, srs, rotation, r, g, b, a].toString();
}

/**
 * Add eventhandlers to panoramaViewer
 */
function initEvents() {
    console.log("Set Measurement event");
    StreetSmartApi.on(StreetSmartApi.Events.measurement.MEASUREMENT_CHANGED, function(e){
        js_measure(JSON.stringify(e.detail.activeMeasurement));
    });
    window.panoramaViewer.on(StreetSmartApi.Events.panoramaViewer.IMAGE_CHANGE, function(e){
            console.log("Image Changed");
            console.log(e);
        }).on(StreetSmartApi.Events.panoramaViewer.VIEW_CHANGE, function(e){

            js_cone(coneString(window.panoramaViewer));

        }).on(StreetSmartApi.Events.panoramaViewer.VIEW_LOAD_END, function(e){

            js_cone(coneString(window.panoramaViewer));

        }).on(StreetSmartApi.Events.panoramaViewer.VIEW_LOAD_START, function(e){
            console.log("View load start Changed");
            console.log(e);
        }).on(StreetSmartApi.Events.panoramaViewer.TIME_TRAVEL_CHANGE, function(e){
            console.log("Time travel change");
            console.log(e);
        });
}

/**
 * Add window loaded eventhandler
 */
window.addEventListener('load', function() {
    console.log("it's loaded!");
    js_window_loaded();
});

/*
 * Get a measurement
 *
 * Function is called form QGIS (obsolete)
 */
function getMeasure() {
    console.log("getMeasure called");
    activeMeasure = StreetSmartApi.getActiveMeasurement(window.panoramaViewer);
    console.log(activeMeasure);
}

/*
 * Starts a measurement with the corresponding geometry type
 *
 * Function is called form QGIS
 */
function startMeasure(geometryType) {
    measurementtype = '';
    if (geometryType == 'point') {
        measurementtype = StreetSmartApi.MeasurementGeometryType.POINT;
    } else if (geometryType == 'polyline') {
        measurementtype = StreetSmartApi.MeasurementGeometryType.LINESTRING;
    } else if (geometryType == 'polygon') {
        measurementtype = StreetSmartApi.MeasurementGeometryType.POLYGON;
    }

    if (measurementtype == '') {
        StreetSmartApi.startMeasurementMode(window.panoramaViewer);
    } else {
        StreetSmartApi.startMeasurementMode(window.panoramaViewer,
            {geometry:measurementtype});
    }
}

/*
 * Stops a measurement
 *
 * Function is called form QGIS
 */
function stopMeasure() {
    StreetSmartApi.stopMeasurementMode();
}

/**
 * Opens an image in a panorama viewer
 * @param {string} point Point to open Cyclorama
 *
 * Function is called from QGIS
 */
function open(point) {
    point = JSON.parse(point);
    StreetSmartApi.open(point.point, {
        viewerType: [StreetSmartApi.ViewerType.PANORAMA],
        srs: point.crs,
        panoramaViewer: { replace: true, },
    }).then(
        function(result) {
            if (result && result[0]) {
                        for (let i =0; i < result.length; i++)
                        {
                console.log('Opened a panorama viewer through API!', result[0]);
                if(result[i].getType() === StreetSmartApi.ViewerType.PANORAMA) window.panoramaViewer = result[i];
                            initEvents();
                        }
            }
        }
    ).catch(
        function(reason) {
            console.log('Error opening panorama viewer: ' + reason);
            alert('Error opening panorama viewer: ' + reason);
        }
    );
}

// Overlay layers added to the viewer
window.overlayLayers = [];

/**
 * Remove overlays added to panorama viewer
 *
 * Function is called from QGIS
 */
function removeOverlay() {
    len = window.overlayLayers.length;
    for (i = 0; i < len; i++) {
        StreetSmartApi.removeOverlay(window.overlayLayers[i].id);
    }
}

/**
 * Add overlay to panorama viewer
 * @param {string} geojson Geometries to shown
 * @param {string} name Name of the layer
 * @param {string} srs Coordinate System Reference
 * @param {string} sldText SLD with which the geometries are shown
 * @param {string} color Color of the layer
 *
 * Function is called from QGIS
 */
function addOverlay(geojson, name, srs, sldText, color) {
    console.log("Try to add overlay");
    console.log(geojson);
    console.log(name);
    console.log(srs);
    console.log(sldText);
    console.log(color);

    options = {
        "geojson": JSON.parse(geojson),
        "visible": true,
        "id": '',
    };
    if (name !== undefined && name !== "") {
        options.name = name;
    }
    if (srs !== undefined && srs !== "") {
        options.sourceSrs = srs;
    }
    if (sldText !== undefined && sldText !== "") {
        options.sldXMLtext = sldText;
    }
    if (color !== undefined && color !== "") {
        options.color = color;
    }

    console.log(options);
    try {
        window.overlayLayers.push(StreetSmartApi.addOverlay(options));
    } catch (e) {
        alert(e);
    }
}


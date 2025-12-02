// static/js/main.js

let map;
let markers = [];
let directionsService = null;
let directionsRenderer = null;

function initMap() {
    console.log("initMap llamado");

    let center = { lat: -36.827, lng: -73.050 }; // Concepción

    if (typeof origen_coords !== "undefined" && origen_coords && origen_coords.lat && origen_coords.lng) {
        center = { lat: origen_coords.lat, lng: origen_coords.lng };
    } else if (Array.isArray(puntos_entrega_data) && puntos_entrega_data.length > 0) {
        center = {
            lat: puntos_entrega_data[0].latitud,
            lng: puntos_entrega_data[0].longitud
        };
    }

    map = new google.maps.Map(document.getElementById("map"), {
        center: center,
        zoom: 12
    });

    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({
        suppressMarkers: true
    });
    directionsRenderer.setMap(map);

    renderPuntosEntrega();
}

function renderPuntosEntrega() {
    clearMap();

    const bounds = new google.maps.LatLngBounds();
    const path = [];

    let originPos = null;
    let destPos = null;

    // ORIGEN
    if (typeof origen_coords !== "undefined" && origen_coords && origen_coords.lat && origen_coords.lng) {
        originPos = { lat: origen_coords.lat, lng: origen_coords.lng };

        const originMarker = new google.maps.Marker({
            position: originPos,
            map: map,
            label: "O",
            title: "Origen del recorrido"
        });

        markers.push(originMarker);
        path.push(originPos);
        bounds.extend(originPos);
    }

    // PUNTOS DE ENTREGA
    if (Array.isArray(puntos_entrega_data) && puntos_entrega_data.length > 0) {
        const anyOrden = puntos_entrega_data.some(
            (p) => p.orden_optimo !== null && p.orden_optimo !== undefined
        );

        const puntos = [...puntos_entrega_data];

        if (anyOrden) {
            puntos.sort((a, b) => {
                if (a.orden_optimo == null) return 1;
                if (b.orden_optimo == null) return -1;
                return a.orden_optimo - b.orden_optimo;
            });
        }

        puntos.forEach((p, index) => {
            const position = { lat: p.latitud, lng: p.longitud };

            const labelText = anyOrden && p.orden_optimo
                ? String(p.orden_optimo)
                : String(index + 1);

            const marker = new google.maps.Marker({
                position: position,
                map: map,
                label: labelText,
                title: `${p.nombre} - ${p.direccion}`
            });

            markers.push(marker);
            path.push(position);
            bounds.extend(position);
        });
    }

    // DESTINO
    if (typeof destino_coords !== "undefined" && destino_coords && destino_coords.lat && destino_coords.lng) {
        destPos = { lat: destino_coords.lat, lng: destino_coords.lng };

        const destMarker = new google.maps.Marker({
            position: destPos,
            map: map,
            label: "F",
            title: "Fin del recorrido"
        });

        markers.push(destMarker);
        path.push(destPos);
        bounds.extend(destPos);
    }

    if (!bounds.isEmpty()) {
        map.fitBounds(bounds);
    }

    if (path.length > 1) {
        drawRouteWithDirectionsAPI(path);
    }
}

function drawRouteWithDirectionsAPI(path) {
    if (!directionsService || !directionsRenderer) return;
    if (!Array.isArray(path) || path.length < 2) return;

    const origin = path[0];
    const destination = path[path.length - 1];

    const waypoints = path.slice(1, -1).map((pos) => ({
        location: pos,
        stopover: true
    }));

    const request = {
        origin: origin,
        destination: destination,
        waypoints: waypoints,
        travelMode: google.maps.TravelMode.DRIVING,
        optimizeWaypoints: false
    };

    directionsService.route(request, (result, status) => {
        console.log("Directions status:", status);
        if (status === "OK" || status === google.maps.DirectionsStatus.OK) {
            directionsRenderer.setDirections(result);
        } else {
            console.error("Error en Directions API:", status);
        }
    });
}

function clearMap() {
    if (markers.length > 0) {
        markers.forEach((m) => m.setMap(null));
        markers = [];
    }

    if (directionsRenderer) {
        directionsRenderer.set("directions", null);
    }
}

function toggleOrigenCustom() {
    const select = document.getElementById("origen_predefinido");
    const wrapper = document.getElementById("origen_custom_wrapper");

    if (!select || !wrapper) return;

    if (select.value === "custom") {
        wrapper.style.display = "block";
    } else {
        wrapper.style.display = "none";
    }
}

function toggleDestinoCustom() {
    const select = document.getElementById("destino_predefinido");
    const wrapper = document.getElementById("destino_custom_wrapper");

    if (!select || !wrapper) return;

    if (select.value === "custom") {
        wrapper.style.display = "block";
    } else {
        wrapper.style.display = "none";
    }
}

// --- BORRAR PUNTO INDIVIDUAL ---

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function eliminarPunto(url) {
    if (!confirm("¿Seguro que quieres eliminar este punto de entrega?")) {
        return;
    }

    const csrftoken = getCookie("csrftoken");

    fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrftoken,
            "X-Requested-With": "XMLHttpRequest",
        },
    })
    .then((response) => {
        if (!response.ok) {
            console.error("Error al borrar. Status:", response.status);
            throw new Error("Error al borrar el punto");
        }
        return response.json();
    })
    .then((data) => {
        if (data.ok) {
            // Se borró en backend; recargamos para refrescar lista + mapa
            location.reload();
        } else {
            alert("El servidor respondió, pero no confirmó el borrado.");
            console.error("Detalle error:", data.error);
        }
    })
    .catch((err) => {
        console.error(err);
        alert("No se pudo borrar el punto");
    });
}

window.initMap = initMap;
window.clearMap = clearMap;
window.toggleOrigenCustom = toggleOrigenCustom;
window.toggleDestinoCustom = toggleDestinoCustom;
window.eliminarPunto = eliminarPunto;

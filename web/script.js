// web/script.js
// checkpoint -> sample coords (you can adjust as needed)
const CHECKPOINT_COORDS = {
  1: [-29.867, 31.045],
  2: [-4.043, 39.668],
  3: [11.600, 43.167],
  4: [21.485, 39.192],
  5: [25.010, 55.060],
  6: [19.033, 73.100],
  7: [6.927, 79.861],
  8: [1.352, 103.820],
  9: [31.230, 121.473],
  10: [51.924, 4.480]
};

document.getElementById("checkpoint").addEventListener("change", (e) => {
  const cp = parseInt(e.target.value);
  const coords = CHECKPOINT_COORDS[cp];
  if (coords) {
    document.getElementById("lat").value = coords[0];
    document.getElementById("lon").value = coords[1];
  }
});

async function upload() {
  const fileEl = document.getElementById("fileInput");
  if (!fileEl.files.length) { alert("Select file"); return; }
  const file = fileEl.files[0];
  const cp = document.getElementById("checkpoint").value;
  const lat = document.getElementById("lat").value;
  const lon = document.getElementById("lon").value;

  const form = new FormData();
  form.append("file", file);
  form.append("checkpoint", cp);
  form.append("latitude", lat);
  form.append("longitude", lon);

  document.getElementById("result").innerText = "Uploading...";

  try {
      const res = await fetch("http://127.0.0.1:8000/upload", { method: "POST", body: form });
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch (e) {
        document.getElementById("result").innerText = "Server returned non-JSON:\n" + text;
        return;
      }
      document.getElementById("result").innerText = JSON.stringify(data, null, 2);
  } catch (e) {
      document.getElementById("result").innerText = "Upload failed: " + e;
  }
}

async function loadEntries(cp) {
  const res = await fetch(`http://127.0.0.1:8000/entries/${cp}`);
  const data = await res.json();
  document.getElementById("entries").innerText = JSON.stringify(data, null, 2);
}

/* -----------------------------------------
 MAP + ROUTE VIEWER (supports multi-point route)
----------------------------------------- */

// Init Leaflet map
let map = L.map('map').setView([20, 75], 5);

// Free OpenStreetMap tiles
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 20
}).addTo(map);

let markers = [];
let routeLine = null;

async function loadRoute() {
  const cid = document.getElementById("route_input").value.trim();
  if (!cid) return alert("Enter container ID");

  const res = await fetch(`http://127.0.0.1:8000/route/${encodeURIComponent(cid)}`);
  const data = await res.json();

  if (data.status !== "found") {
      alert("Container not found at two or more checkpoints!");
      return;
  }

  // Clear old markers
  markers.forEach(m => map.removeLayer(m));
  markers = [];

  if (routeLine) {
      map.removeLayer(routeLine);
      routeLine = null;
  }

  const route = data.route; // array of {checkpoint, lat, lon, timestamp}

  // Add markers and build latlngs
  const latlngs = [];
  for (const pt of route) {
    const m = L.marker([pt.lat, pt.lon]).addTo(map).bindPopup(`Checkpoint ${pt.checkpoint}<br>${pt.timestamp}`);
    markers.push(m);
    latlngs.push([pt.lat, pt.lon]);
  }

  // Draw polyline
  routeLine = L.polyline(latlngs, { color: 'blue', weight: 4 }).addTo(map);

  // Auto-zoom to fit route
  map.fitBounds(routeLine.getBounds());
}

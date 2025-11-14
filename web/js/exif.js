// Update selected checkpoint coordinates
document.getElementById("checkpoint").addEventListener("change", function () {
    const [lat, lon] = this.value.split(",");
    document.getElementById("selectedLoc").innerText =
      "Lat: " + lat + " , Lon: " + lon;
  });
  
  // SUBMIT DATA TO BACKEND
  async function submitData() {
    if (!imageFile) {
      alert("Upload an image first!");
      return;
    }
  
    const checkpointValue = document.getElementById("checkpoint").value;
    const [lat, lon] = checkpointValue.split(",");
  
    const location = document.getElementById("locSelect").value;
  
    let formData = new FormData();
    formData.append("file", imageFile);
    formData.append("location", location);
    formData.append("latitude", lat);
    formData.append("longitude", lon);
  
    const res = await fetch("http://127.0.0.1:8000/upload", {
      method: "POST",
      body: formData,
    });
  
    const data = await res.json();
    document.getElementById("result").innerText =
      JSON.stringify(data, null, 2);
  }
  
  // LOAD ENTRIES
  async function loadEntries() {
    const res = await fetch("http://127.0.0.1:8000/paths");
    const data = await res.json();
    document.getElementById("entries").innerText =
      JSON.stringify(data, null, 2);
  }
  
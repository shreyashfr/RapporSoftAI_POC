# backend/app.py
import os
import csv
import traceback
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.ocr.detector import extract_container_id, run_local_ocr_debug

# FastAPI init
app = FastAPI(title="Container Vision OCR (Experimental)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve UI
app.mount("/ui", StaticFiles(directory="web", html=True), name="ui")

# CSV paths (now 10 checkpoints)
CSV_DIR = "backend/data"
os.makedirs(CSV_DIR, exist_ok=True)

CSV_FILES = {i: os.path.join(CSV_DIR, f"checkpoint{i}.csv") for i in range(1, 11)}

HEADER = ["timestamp", "container_id", "latitude", "longitude", "image"]

# Ensure CSVs exist and fix old broken ones
for p in CSV_FILES.values():

    # Create file if missing
    if not os.path.exists(p):
        with open(p, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
        continue

    # Read file
    with open(p, "r") as f:
        rows = list(csv.reader(f))

    # Empty file → recreate
    if not rows:
        with open(p, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
        continue

    # If header incorrect → rewrite file (force consistent format)
    if rows[0] != HEADER:
        print(f"[FIX] Rewriting header in {p}")

        valid_rows = []
        for r in rows[1:]:
            if len(r) != 5:
                continue  # skip corrupted rows
            ts, cid, lat, lon, img = r
            valid_rows.append([ts, cid, lat, lon, img])

        with open(p, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)
            writer.writerows(valid_rows)


@app.get("/")
def home():
    return {"message": "Container Vision OCR API running. Open /ui/"}


@app.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    checkpoint: int = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    try:
        if checkpoint not in CSV_FILES:
            return JSONResponse({"error": "checkpoint must be 1..10"}, status_code=400)

        # save file
        save_path = os.path.join(CSV_DIR, file.filename)
        with open(save_path, "wb") as f:
            f.write(await file.read())

        # extract container id
        container_id = extract_container_id(save_path)

        # local OCR preview
        local_text = run_local_ocr_debug(save_path)

        # if no container_id from pattern, use local OCR raw text (cleaned)
        if container_id == "UNKNOWN" and local_text:
            container_id = local_text.replace(" ", "").strip().upper()

        # write csv row
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        with open(CSV_FILES[checkpoint], "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([ts, container_id, latitude, longitude, file.filename])

        return {
            "status": "ok",
            "container_id": container_id,
            "checkpoint": checkpoint,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": ts
        }

    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": "upload_failed", "details": str(e)}, status_code=500)


@app.get("/entries/{checkpoint}")
def get_entries(checkpoint: int):
    if checkpoint not in CSV_FILES:
        return JSONResponse({"error": "checkpoint must be 1..10"}, status_code=400)

    rows = []
    with open(CSV_FILES[checkpoint], "r", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    return {"checkpoint": checkpoint, "rows": rows}


@app.get("/route/{container_id}")
def get_route(container_id: str):
    container_id = container_id.strip().upper()
    points = {}

    for cp, path in CSV_FILES.items():
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get("container_id", "").strip().upper()
                if cid == container_id:
                    try:
                        lat = float(row.get("latitude", 0))
                        lon = float(row.get("longitude", 0))
                    except Exception:
                        lat = 0.0
                        lon = 0.0
                    points[cp] = {
                        "lat": lat,
                        "lon": lon,
                        "timestamp": row.get("timestamp", "")
                    }
                    break

    if len(points) >= 2:
        # sort by checkpoint number
        sorted_pts = sorted(points.items(), key=lambda x: x[0])
        route = [{"checkpoint": cp, **info} for cp, info in sorted_pts]
        return {
            "status": "found",
            "container_id": container_id,
            "route": route
        }

    return {"status": "not_found", "container_id": container_id}

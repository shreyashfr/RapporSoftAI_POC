import csv
import os
from datetime import datetime

DATA_DIR = "backend/data"


def save_entry(checkpoint, container_id, lat, lon, image_name):
    csv_path = f"{DATA_DIR}/checkpoint{checkpoint}.csv"

    exists = os.path.exists(csv_path)

    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)

        if not exists:
            writer.writerow(["timestamp", "container_id", "latitude", "longitude", "image"])

        writer.writerow([datetime.now(), container_id, lat, lon, image_name])


def read_entries(checkpoint):
    csv_path = f"{DATA_DIR}/checkpoint{checkpoint}.csv"

    if not os.path.exists(csv_path):
        return []

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)

import csv
import os

LABELS_PATH = "player_photos/labels.csv"
DUMMY_IMAGE_PATH = os.path.join("player_photos", "dummy_player.png")
DUMMY_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/b/be/Women%27s_basketball_%28429322%29_-_The_Noun_Project.svg"
DUMMY_LICENSE = "CC0"
DUMMY_CREDIT = "Damián Patrignani, CC0, via Wikimedia Commons"

rows = []
with open(LABELS_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        if not row.get("image_path"):
            row["image_path"] = DUMMY_IMAGE_PATH
            row["image_url"] = DUMMY_IMAGE_URL
            row["license"] = DUMMY_LICENSE
            row["credit"] = DUMMY_CREDIT
        rows.append(row)

with open(LABELS_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("labels.csv updated.")
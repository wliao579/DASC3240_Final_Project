import csv
import json
import os
import re
import time
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError


DATA_PATH = "basketball.csv"
OUTPUT_DIR = "player_photos"
LABELS_PATH = os.path.join(OUTPUT_DIR, "labels.csv")
DUMMY_IMAGE_PATH = os.path.join(OUTPUT_DIR, "dummy_player.png")
DUMMY_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/b/be/Women%27s_basketball_%28429322%29_-_The_Noun_Project.svg"
DUMMY_LICENSE = "CC0"
DUMMY_CREDIT = "Damián Patrignani, CC0, via Wikimedia Commons"

USER_AGENT = "DASC3240_Final_Project/1.0 (contact: local script)"
REQUEST_DELAY_SECONDS = 1.5
MIN_REQUEST_INTERVAL_SECONDS = 0.6
_LAST_REQUEST_TS = 0.0

# Only download images with a clear, permissive license.
ALLOWED_LICENSES = {
	"Public domain",
	"CC0",
	"CC BY",
	"CC BY 2.0",
	"CC BY 3.0",
	"CC BY 4.0",
	"CC BY-SA",
	"CC BY-SA 2.0",
	"CC BY-SA 3.0",
	"CC BY-SA 4.0",
}


def throttle_requests():
	global _LAST_REQUEST_TS
	now = time.monotonic()
	elapsed = now - _LAST_REQUEST_TS
	if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
		time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)
	_LAST_REQUEST_TS = time.monotonic()


def http_get(url, retries=5, backoff_seconds=5):
	req = Request(url, headers={"User-Agent": USER_AGENT})
	for attempt in range(retries):
		try:
			throttle_requests()
			with urlopen(req) as resp:
				return resp.read()
		except HTTPError as exc:
			if exc.code == 429 and attempt < retries - 1:
				retry_after = exc.headers.get("Retry-After")
				if retry_after and retry_after.isdigit():
					time.sleep(int(retry_after))
				else:
					time.sleep(backoff_seconds * (attempt + 1))
				continue
			raise
		except Exception:
			if attempt == retries - 1:
				raise
			time.sleep(backoff_seconds * (attempt + 1))


def safe_filename(name):
	cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
	return cleaned.strip("_") or "unknown"


def load_player_names(csv_path):
	names = []
	with open(csv_path, newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			name = (row.get("player_name") or "").strip()
			if name:
				names.append(name)
	return sorted(set(names))


def wikidata_search(name):
	query = quote(name)
	url = (
		"https://www.wikidata.org/w/api.php"
		f"?action=wbsearchentities&search={query}"
		"&language=en&format=json&limit=5"
	)
	data = json.loads(http_get(url).decode("utf-8"))
	return data.get("search", [])


def wikidata_entity(entity_id):
	url = (
		"https://www.wikidata.org/wiki/Special:EntityData/"
		f"{entity_id}.json"
	)
	data = json.loads(http_get(url).decode("utf-8"))
	return data.get("entities", {}).get(entity_id, {})


def get_commons_file_name(entity):
	# P18 is the image property
	claims = entity.get("claims", {})
	image_claims = claims.get("P18", [])
	if not image_claims:
		return None
	mainsnak = image_claims[0].get("mainsnak", {})
	datavalue = mainsnak.get("datavalue", {})
	value = datavalue.get("value")
	if isinstance(value, str) and value:
		return value
	return None


def get_commons_image_info(file_name):
	title = "File:" + file_name.replace(" ", "_")
	url = (
		"https://commons.wikimedia.org/w/api.php"
		f"?action=query&format=json&prop=imageinfo"
		"&iiprop=url|extmetadata"
		f"&titles={quote(title)}"
	)
	data = json.loads(http_get(url).decode("utf-8"))
	pages = data.get("query", {}).get("pages", {})
	if not pages:
		return None
	page = next(iter(pages.values()))
	imageinfo = page.get("imageinfo", [])
	if not imageinfo:
		return None
	return imageinfo[0]


def parse_extmetadata(extmetadata):
	def get_field(key):
		entry = extmetadata.get(key, {})
		return entry.get("value")

	return {
		"license": get_field("LicenseShortName"),
		"license_url": get_field("LicenseUrl"),
		"credit": get_field("Credit"),
		"artist": get_field("Artist"),
		"source_page": get_field("ImageDescription"),
	}


def download_image(url, dest_path, retries=5, backoff_seconds=5):
	req = Request(url, headers={"User-Agent": USER_AGENT})
	for attempt in range(retries):
		try:
			throttle_requests()
			with urlopen(req) as resp:
				content = resp.read()
			with open(dest_path, "wb") as f:
				f.write(content)
			return True
		except HTTPError as exc:
			if exc.code == 429 and attempt < retries - 1:
				retry_after = exc.headers.get("Retry-After")
				if retry_after and retry_after.isdigit():
					time.sleep(int(retry_after))
				else:
					time.sleep(backoff_seconds * (attempt + 1))
				continue
			return False
		except Exception:
			if attempt == retries - 1:
				return False
			time.sleep(backoff_seconds * (attempt + 1))
	return False


def main():
	os.makedirs(OUTPUT_DIR, exist_ok=True)
	names = load_player_names(DATA_PATH)

	if not os.path.exists(DUMMY_IMAGE_PATH):
		print(f"Warning: missing dummy image at {DUMMY_IMAGE_PATH}")

	with open(LABELS_PATH, "w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(
			f,
			fieldnames=[
				"player_name",
				"image_path",
				"image_url",
				"license",
				"license_url",
				"credit",
				"artist",
				"source_page",
			],
		)
		writer.writeheader()

		total = len(names)
		print(f"Processing {total} unique players...")

		for idx, name in enumerate(names, start=1):
			print(f"[{idx}/{total}] {name}")
			search_results = wikidata_search(name)
			entity_id = search_results[0]["id"] if search_results else None
			if not entity_id:
				print(f"  - Not found in Wikidata")
				writer.writerow({"player_name": name})
				continue

			entity = wikidata_entity(entity_id)
			file_name = get_commons_file_name(entity)
			if not file_name:
				print(f"  - No image on Wikidata")
				writer.writerow({"player_name": name})
				continue

			imageinfo = get_commons_image_info(file_name)
			if not imageinfo:
				print(f"  - No image info on Commons")
				writer.writerow({"player_name": name})
				continue

			image_url = imageinfo.get("url")
			extmetadata = imageinfo.get("extmetadata", {})
			meta = parse_extmetadata(extmetadata)

			file_ext = os.path.splitext(file_name)[1].lower() or ".jpg"
			filename = safe_filename(name) + file_ext
			image_path = os.path.join(OUTPUT_DIR, filename)

			license_name = (meta.get("license") or "").strip()
			if image_url and license_name in ALLOWED_LICENSES:
				if not os.path.exists(image_path):
					ok = download_image(image_url, image_path)
					if not ok:
						image_path = ""
						print("  - Download failed (rate limit or network)")
					else:
						print("  - Downloaded")
				else:
					print("  - Exists, skipped")
			elif image_url:
				image_path = ""
				print(f"  - Skipped (license: {license_name or 'unknown'})")

			using_dummy = not image_path
			final_image_path = image_path or DUMMY_IMAGE_PATH
			final_image_url = image_url or (DUMMY_IMAGE_URL if using_dummy else "")
			final_license = meta.get("license") or (DUMMY_LICENSE if using_dummy else "")
			final_credit = meta.get("credit") or (DUMMY_CREDIT if using_dummy else "")
			writer.writerow(
				{
					"player_name": name,
					"image_path": final_image_path,
					"image_url": final_image_url,
					"license": final_license,
					"license_url": meta.get("license_url") or "",
					"credit": final_credit,
					"artist": meta.get("artist") or "",
					"source_page": meta.get("source_page") or "",
				}
			)

			# Be polite to Wikimedia endpoints.
			time.sleep(REQUEST_DELAY_SECONDS)


if __name__ == "__main__":
	main()

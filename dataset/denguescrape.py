import csv
import os
import time
import urllib.parse
from io import BytesIO
from collections import defaultdict

import requests
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException

# =========================
# CONFIG
# =========================
PAST_QUERIES = [
    ("English", "dengue rash patient skin"),
    ("English", "dengue petechiae skin patient"),
    ("English", "dengue maculopapular rash human"),
    ("English", "dengue fever rash photograph"),
    ("English", "dengue eye pain rapid bleeding"),
    ("Thai", "ผู้ป่วยที่เป็นไข้เลือดออกใต้ผิวหนังอาจมีจุดเลือดออกเล็กๆ (petechiae)"),
    ("Thai", "ผื่นแดงจากไข้เลือดออกที่ลำตัว"),
    ("Vietnamese", "sốt xuất huyết"),
]

QUERIES = [
    ("Vietnamese", "Phát ban dát sẩn"),
    ("Vietnamese", "chấm xuất huyết dưới da"),
    ("Chinese", "登革热皮疹"),
    ("Portuguese", "imagens da erupção cutânea da dengue"),
    ("Portuguese", "dengue erupção cutânea paciente"),
]

MAX_IMAGES_PER_QUERY = 100
SCROLL_ROUNDS = 20
OUTPUT_DIR = "output"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
METADATA_CSV = os.path.join(OUTPUT_DIR, "metadata.csv")

os.makedirs(IMAGES_DIR, exist_ok=True)


# =========================
# BROWSER SETUP
# =========================
def make_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")
    options.add_argument("--lang=en-US")

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1400, 1000)

    return driver

def close_extra_tabs(driver: webdriver.Chrome, main_window: str) -> None:
    for handle in driver.window_handles:
        if handle != main_window:
            driver.switch_to.window(handle)
            driver.close()

    driver.switch_to.window(main_window)

# =========================
# NETWORK / FILE HELPERS
# =========================
def safe_get(url: str, timeout: int = 20) -> requests.Response:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.google.com/",
    }
    return requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)


def is_valid_image_response(resp: requests.Response) -> bool:
    content_type = resp.headers.get("Content-Type", "").lower()
    return resp.status_code == 200 and "image" in content_type


def download_image(url: str, out_path: str) -> tuple[bool, str]:
    try:
        resp = safe_get(url)
        content_type = resp.headers.get("Content-Type", "")
        print(f"Trying: {url}")
        print(f"Status: {resp.status_code}, Content-Type: {content_type}")

        if not is_valid_image_response(resp):
            return False, f"bad content-type/status: {resp.status_code}, {content_type}"

        image_bytes = resp.content

        img = Image.open(BytesIO(image_bytes))
        img.verify()

        with open(out_path, "wb") as f:
            f.write(image_bytes)

        return True, "ok"
    except Exception as e:
        return False, str(e)

# =========================
# GOOGLE IMAGES HELPERS
# =========================
def google_images_url(query: str) -> str:
    return (
        "https://www.google.com/search?"
        + urllib.parse.urlencode({
            "q": query,
            "tbm": "isch",
            "hl": "en",
            "ijn": "0"
        })
    )


def scroll_page(driver: webdriver.Chrome, rounds: int = 20, pause: float = 2.0) -> None:
    last_height = driver.execute_script("return document.body.scrollHeight")
    same_height_count = 0

    for _ in range(rounds):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

        try:
            more_button = driver.find_element(By.CSS_SELECTOR, ".mye4qd")
            driver.execute_script("arguments[0].click();", more_button)
            print("Clicked 'Show more results'")
            time.sleep(2)
        except Exception:
            pass

        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            same_height_count += 1
        else:
            same_height_count = 0

        if same_height_count >= 3:
            print("Reached bottom of page.")
            break

        last_height = new_height


def get_thumbnail_elements(driver: webdriver.Chrome):
    selectors = [
        "img.Q4LuWd",
        "img.YQ4gaf",
    ]

    for selector in selectors:
        thumbs = driver.find_elements(By.CSS_SELECTOR, selector)
        thumbs = [
            t for t in thumbs
            if (t.get_attribute("src") or t.get_attribute("data-src"))
        ]
        if thumbs:
            print(f"Using selector: {selector}")
            return thumbs

    print("No preferred thumbnail selector matched.")
    return []


def extract_large_image_candidates(driver: webdriver.Chrome) -> list[str]:
    """
    After clicking a thumbnail, collect visible HTTP image URLs from the page.
    Keep this moderately strict, not overly strict.
    """
    image_elements = driver.find_elements(By.CSS_SELECTOR, "img")
    urls = []
    seen = set()

    for img in image_elements:
        try:
            src = img.get_attribute("src")
            if not src or not src.startswith("http"):
                continue

            width = driver.execute_script("return arguments[0].naturalWidth || 0;", img)
            height = driver.execute_script("return arguments[0].naturalHeight || 0;", img)

            # Relaxed filter: Google preview images sometimes report smaller than expected
            if width < 120 or height < 120:
                continue

            lower = src.lower()

            # Skip obvious junk, but do NOT skip encrypted-tbn0 during collection
            if "googlelogo" in lower or "/logos/" in lower:
                continue
            if src in seen:
                continue

            seen.add(src)
            urls.append(src)
        except Exception:
            continue

    # Prefer larger-looking candidates first
    urls.sort(key=lambda u: len(u), reverse=True)
    return urls


# =========================
# METADATA HELPERS
# =========================
def write_metadata_header_if_needed(csv_path: str) -> None:
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["filename", "query", "language", "image_url", "page_url", "status"])


def append_metadata_row(csv_path: str, row: list[str]) -> None:
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row)

def load_existing_progress(csv_path: str):
    """
    Returns:
        next_index: next numeric image id to use
        seen_download_urls: set of already downloaded image URLs
        downloaded_per_query: dict mapping query -> count of successful downloads
    """
    seen_download_urls = set()
    downloaded_per_query = defaultdict(int)
    max_index = -1

    if not os.path.exists(csv_path):
        return 0, seen_download_urls, downloaded_per_query

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = (row.get("filename") or "").strip()
            query = (row.get("query") or "").strip()
            image_url = (row.get("image_url") or "").strip()
            status = (row.get("status") or "").strip().lower()

            if status == "downloaded":
                if image_url:
                    seen_download_urls.add(image_url)
                if query:
                    downloaded_per_query[query] += 1

                if filename.startswith("img_"):
                    try:
                        num = int(filename.replace("img_", "").replace(".jpg", ""))
                        if num > max_index:
                            max_index = num
                    except ValueError:
                        pass

    return max_index + 1, seen_download_urls, downloaded_per_query

def get_existing_file_indices(images_dir: str) -> set[int]:
    indices = set()
    if not os.path.exists(images_dir):
        return indices

    for name in os.listdir(images_dir):
        if name.startswith("img_") and name.lower().endswith(".jpg"):
            try:
                num = int(name.replace("img_", "").replace(".jpg", ""))
                indices.add(num)
            except ValueError:
                pass
    return indices

def get_next_available_index(start_index: int, used_indices: set[int]) -> int:
    idx = start_index
    while idx in used_indices:
        idx += 1
    return idx

# =========================
# SCRAPER
# =========================
def scrape_query(
    driver: webdriver.Chrome,
    language: str,
    query: str,
    start_index: int,
    seen_download_urls: set[str],
    downloaded_per_query: dict[str, int],
    used_file_indices: set[int],
    main_window: str,
) -> int:
    print(f"\n=== [{language}] Query: {query} ===")
    driver.get(google_images_url(query))

    try:
        WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img"))
        )
    except Exception:
        print("No images appeared on page.")
        print("Current URL:", driver.current_url)
        print("Page title:", driver.title)
        return start_index

    time.sleep(2)
    scroll_page(driver, rounds=SCROLL_ROUNDS, pause=2)

    thumbnails = get_thumbnail_elements(driver)
    print(f"Found {len(thumbnails)} image elements")

    if not thumbnails:
        print("No thumbnails found.")
        print("Current URL:", driver.current_url)
        print("Page title:", driver.title)
        print(driver.page_source[:2000])
        return start_index

    first_src = thumbnails[0].get_attribute("src") or thumbnails[0].get_attribute("data-src")
    print("Example src:", first_src)

    already_have = downloaded_per_query.get(query, 0)
    if already_have >= MAX_IMAGES_PER_QUERY:
        print(f"Skipping query, already has {already_have} images: {query}")
        return start_index

    saved_count = already_have
    new_downloads = 0
    file_index = get_next_available_index(start_index, used_file_indices)

    print(f"Already downloaded for this query: {already_have}")
    print(f"Starting file index at: {file_index}")
    thumb_index = 0

    while saved_count < MAX_IMAGES_PER_QUERY:
        thumbnails = get_thumbnail_elements(driver)

        if not thumbnails:
            print("No thumbnails available.")
            break

        if thumb_index >= len(thumbnails):
            print("Reached end of thumbnails.")
            break

        print(f"Processing thumbnail {thumb_index+1}/{len(thumbnails)}")

        try:
            thumb = thumbnails[thumb_index]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thumb)
            time.sleep(0.7)

            thumbnails = get_thumbnail_elements(driver)
            if thumb_index >= len(thumbnails):
                break

            thumb = thumbnails[thumb_index]
            try:
                thumb.click()
            except Exception:
                driver.execute_script("arguments[0].click();", thumb)
            time.sleep(1)
            close_extra_tabs(driver, main_window)
            time.sleep(1.5)

        except StaleElementReferenceException:
            print("Stale element, skipping...")
            thumb_index += 1
            continue
        except Exception as e:
            print("Click failed:", e)
            thumb_index += 1
            continue

        candidates = extract_large_image_candidates(driver)
        print(f"Candidates found: {len(candidates)}")

        if not candidates:
            append_metadata_row(
                METADATA_CSV,
                ["", query, language, "", driver.current_url, "no_candidates"]
            )
            thumb_index += 1
            continue

        downloaded = False

        for img_url in candidates[:20]:
            if img_url in seen_download_urls:
                print("Skipping duplicate:", img_url)
                continue

            file_index = get_next_available_index(file_index, used_file_indices)
            filename = f"img_{file_index:06d}.jpg"
            out_path = os.path.join(IMAGES_DIR, filename)

            ok, msg = download_image(img_url, out_path)
            print("Download result:", ok, msg)

            if ok:
                append_metadata_row(
                    METADATA_CSV,
                    [filename, query, language, img_url, driver.current_url, "downloaded"]
                )
                seen_download_urls.add(img_url)
                used_file_indices.add(file_index)
                downloaded_per_query[query] += 1
                print(f"[OK] {filename}")
                file_index += 1
                saved_count += 1
                downloaded = True
                new_downloads += 1
                break
            else:
                print(msg)

        if not downloaded:
            append_metadata_row(
                METADATA_CSV,
                ["", query, language, candidates[0], driver.current_url, "failed_download"]
            )

        thumb_index += 1

    print(f"New downloads this run for query '{query}': {new_downloads}")
    print(f"Total downloads for query '{query}': {saved_count}")
    return file_index

def main():
    write_metadata_header_if_needed(METADATA_CSV)

    next_index, seen_download_urls, downloaded_per_query = load_existing_progress(METADATA_CSV)
    used_file_indices = get_existing_file_indices(IMAGES_DIR)

    print(f"Resuming at index: {next_index}")
    print(f"Previously downloaded unique URLs: {len(seen_download_urls)}")
    print("Previously downloaded per query:")
    for lang, q in QUERIES:
        print(f"  [{lang}] {q}: {downloaded_per_query.get(q, 0)}")

    driver = make_driver(headless=False)
    main_window = driver.current_window_handle

    try:
        for lang, query in QUERIES:
            next_index = scrape_query(
                driver,
                lang,
                query,
                next_index,
                seen_download_urls,
                downloaded_per_query,
                used_file_indices,
                main_window
            )
    finally:
        driver.quit()

    print("\nDone.")
    print(f"Images saved to: {IMAGES_DIR}")
    print(f"Metadata saved to: {METADATA_CSV}")
    print(f"Unique downloaded URLs: {len(seen_download_urls)}")


if __name__ == "__main__":
    main()
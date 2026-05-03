from pathlib import Path
from urllib.parse import urljoin
import re
import requests
from playwright.sync_api import sync_playwright

PROFILE_URL = "https://public.tableau.com/app/profile/rob.taylor6175/vizzes"
SAVE_FOLDER = Path(r"C:\Users\rober\Documents\Tableau Portfolio\Viz Images")

SAVE_FOLDER.mkdir(parents=True, exist_ok=True)


def clean_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:120] or "tableau_image"


def download_image(url, filename):
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    file_path = SAVE_FOLDER / filename
    file_path.write_bytes(response.content)
    print(f"Saved: {file_path}")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(PROFILE_URL, wait_until="networkidle", timeout=60000)

    # Scroll to load more vizzes
    previous_height = 0
    for _ in range(30):
        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(1500)

        current_height = page.evaluate("document.body.scrollHeight")
        if current_height == previous_height:
            break
        previous_height = current_height

    images = page.locator("img").evaluate_all("""
        imgs => imgs.map(img => ({
            src: img.src,
            alt: img.alt || ""
        }))
    """)

    browser.close()

seen = set()
count = 0

for img in images:
    src = img["src"]
    alt = img["alt"]

    if not src:
        continue

    # Keep likely Tableau viz thumbnails only
    if "tableau" not in src.lower() and "public" not in src.lower():
        continue

    if src in seen:
        continue

    seen.add(src)
    count += 1

    ext = ".png"
    if ".jpg" in src.lower() or ".jpeg" in src.lower():
        ext = ".jpg"
    elif ".webp" in src.lower():
        ext = ".webp"

    filename = f"{count:03d}_{clean_filename(alt)}{ext}"

    try:
        download_image(src, filename)
    except Exception as e:
        print(f"Skipped image {count}: {e}")

print(f"\nDone. Downloaded {count} images.")    

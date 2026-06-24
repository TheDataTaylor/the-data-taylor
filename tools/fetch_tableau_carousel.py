#!/usr/bin/env python3
"""
Fetch Tableau Public workbook thumbnails, save them locally, and build a
carousel manifest for a static website.

Run from the project root:
    python tools/fetch_tableau_carousel.py
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote
from PIL import Image
from io import BytesIO
from datetime import datetime, timezone

import requests
from slugify import slugify

PROFILE_API_BASE = "https://public.tableau.com/profile/api/"
WORKBOOK_API_BASE = "https://public.tableau.com/public/apis/workbooks"
STATIC_IMAGE_BASE = "https://public.tableau.com/static/images/"
SINGLE_WORKBOOK_API_BASE = "https://public.tableau.com/profile/api/single_workbook/"

DEFAULT_AUTHORS = [
    {"authorDisplayName": "Rob Taylor", "authorProfileName": "rob.taylor6175"},
]


@dataclass(frozen=True)
class CarouselItem:
    title: str
    href: str
    image: str
    alt: str
    view_count: int
    favourites: int
    workbook_order: int
    published_at: str
    def to_manifest_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "href": self.href,
            "image": self.image,
            "alt": self.alt,
            "viewCount": self.view_count,
            "numberOfFavorites": self.favourites,
            "workbookOrder": self.workbook_order,
            "publishedAt": self.published_at,
        }


def get_json(session: requests.Session, url: str, *, timeout: int = 30) -> Any:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_visible_workbook_count(session: requests.Session, profile_name: str) -> int:
    profile = get_json(session, f"{PROFILE_API_BASE}{profile_name}")
    return int(profile.get("visibleWorkbookCount") or 0)


def get_workbooks_for_author(
    session: requests.Session,
    profile_name: str,
    total_workbooks: int,
    *,
    batch_size: int = 50,
    delay: float = 0.4,
) -> list[dict[str, Any]]:
    workbooks: list[dict[str, Any]] = []

    for start in range(0, total_workbooks, batch_size):
        count = min(batch_size, total_workbooks - start)
        url = (
            f"{WORKBOOK_API_BASE}?profileName={quote(profile_name)}"
            f"&start={start}&count={count}&visibility=NON_HIDDEN"
        )
        data = get_json(session, url)
        for workbook in data.get("contents", []):
            workbook["authorProfileName"] = profile_name
            workbooks.append(workbook)
        time.sleep(delay)

    return workbooks

def get_workbook_created_date(session: requests.Session, workbook_repo_url: str) -> str:
    url = f"{SINGLE_WORKBOOK_API_BASE}{workbook_repo_url}?"
    try:
        data = get_json(session, url)
        # Tableau returns timestamps in milliseconds, convert to readable date
        timestamp = data.get("firstPublishDate") or data.get("createdAt") or 0
        if timestamp:
            
            return datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        return ""
    except Exception as e:
        print(f"Could not fetch date for {workbook_repo_url}: {e}")
        return ""
    
def tableau_thumbnail_url(workbook_repo_url: str, default_view_repo_url: str) -> str:
    # Matches your notebook logic, but keeps it as explicit path manipulation.
    url = f"{STATIC_IMAGE_BASE}{workbook_repo_url[:2]}/{default_view_repo_url}/4_3.png"
    url = url.replace("/sheets/", "/")
    url = url.replace("//", "/_/")
    url = url.replace("https:/_/", "https://")
    return url


def tableau_viz_url(profile_name: str, default_view_repo_url: str) -> str:
    view_path = default_view_repo_url.replace("/sheets/", "/")
    return f"https://public.tableau.com/app/profile/{profile_name}/viz/{view_path}"


#def download_image(session: requests.Session, image_url: str, output_path: Path) -> None:
#    response = session.get(image_url, timeout=45)
#    response.raise_for_status()

#    content_type = response.headers.get("content-type", "")
#    if "image" not in content_type.lower():
#        raise ValueError(f"Expected an image from {image_url}, got content-type {content_type!r}")

#    output_path.parent.mkdir(parents=True, exist_ok=True)
#    output_path.write_bytes(response.content)

def download_image(
    session: requests.Session,
    image_url: str,
    output_path: Path,
    *,
    quality: int = 75,
) -> None:
    response = session.get(image_url, timeout=45)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "image" not in content_type.lower():
        raise ValueError(f"Expected an image from {image_url}, got content-type {content_type!r}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(BytesIO(response.content))
    img = img.convert("RGB")
    img.save(output_path, "JPEG", quality=quality, optimize=True)

def build_carousel(
    *,
    authors: list[dict[str, str]],
    output_dir: Path,
    manifest_path: Path,
    min_favourites: int,
    max_items: int | None,
    delay: float,
    dry_run: bool,
    jpg_quality: int,
) -> list[CarouselItem]:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 Tableau carousel builder"})
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    items: list[CarouselItem] = []

    for author in authors:
        profile_name = author["authorProfileName"]
        total = get_visible_workbook_count(session, profile_name)
        print(f"Found {total} visible workbooks for {profile_name}")

        workbooks = get_workbooks_for_author(session, profile_name, total, delay=delay)
        workbooks.sort(key=lambda wb: (wb.get("authorProfileName", ""), wb.get("workbookRepoUrl", "")))

        for order, workbook in enumerate(workbooks, start=1):
            favourites = int(workbook.get("numberOfFavorites") or 0)
            if favourites < min_favourites:
                continue

            title = str(workbook.get("title") or "Untitled Tableau workbook")

            workbook_repo_url = str(workbook.get("workbookRepoUrl") or "")
            default_view_repo_url = str(workbook.get("defaultViewRepoUrl") or "")
            if not workbook_repo_url or not default_view_repo_url:
                print(f"Skipping {title!r}: missing workbook/view URL")
                continue
            
            published_at = get_workbook_created_date(session, workbook_repo_url)

            image_url = tableau_thumbnail_url(workbook_repo_url, default_view_repo_url)
            href = tableau_viz_url(profile_name, default_view_repo_url)
            #filename = f"{order:03d}-{slugify(title) or 'tableau-viz'}.png"
            #filename = f"{order:03d}-{slugify(title) or 'tableau-viz'}.jpg"
            filename = f"{slugify(title) or 'tableau-viz'}.jpg"
            image_output_path = output_dir / filename

            #if not dry_run:
            #    try:
            #        #download_image(session, image_url, image_output_path)
            #        download_image(session, image_url, image_output_path, quality=jpg_quality)
            #    except Exception as exc:
            #        print(f"Skipping {title!r}: could not download thumbnail: {exc}")
            #        continue

            if not dry_run:
                if image_output_path.exists():
                    print(f"Skipping download (already exists): {filename}")
                else:
                    try:
                        download_image(session, image_url, image_output_path, quality=jpg_quality)
                    except Exception as exc:
                        print(f"Skipping {title!r}: could not download thumbnail: {exc}")
                        continue

            items.append(
                CarouselItem(
                    title=title,
                    href=href,
                    image=f"assets/Public Thumbnails/{filename}",
                    alt=f"Tableau Public thumbnail for {title}",
                    view_count=int(workbook.get("viewCount") or 0),
                    favourites=favourites,
                    workbook_order=order,
                    published_at=published_at,
                )
            )

            print(f"Added: {title}")

            if max_items and len(items) >= max_items:
                break
        if max_items and len(items) >= max_items:
            break

    manifest = [item.to_manifest_dict() for item in items]
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(items)} manifest entries to {manifest_path}")

    by_date = sorted(items, key=lambda x: x.published_at, reverse=True)
    by_favourites = sorted(items, key=lambda x: x.favourites, reverse=True)

    date_manifest_path = manifest_path.with_stem(manifest_path.stem + "-by-date")
    fav_manifest_path = manifest_path.with_stem(manifest_path.stem + "-by-favourites")

    date_manifest_path.write_text(json.dumps([i.to_manifest_dict() for i in by_date], indent=2, ensure_ascii=False), encoding="utf-8")
    fav_manifest_path.write_text(json.dumps([i.to_manifest_dict() for i in by_favourites], indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(by_date)} entries to {date_manifest_path}")
    print(f"Wrote {len(by_favourites)} entries to {fav_manifest_path}")
    print("\n--- By Date Published ---")
    for i in by_date:
        print(f"  {i.published_at}  |  {i.title}  |  ❤️ {i.favourites}")

    print("\n--- By Most Favourites ---")
    for i in by_favourites:
        print(f"  ❤️ {i.favourites}  |  {i.title}  |  {i.published_at}")


    return items


def load_authors(authors_file: Path | None) -> list[dict[str, str]]:
    if authors_file is None:
        return DEFAULT_AUTHORS
    return json.loads(authors_file.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a local Tableau Public carousel manifest.")
    parser.add_argument("--authors-file", type=Path, help="Optional JSON file of Tableau author profiles.")
    parser.add_argument("--output-dir", type=Path, default=Path("assets/Public Thumbnails"))
    parser.add_argument("--manifest", type=Path, default=Path("assets/js/carousel-manifest.json"))
    parser.add_argument("--min-favourites", type=int, default=1)
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--dry-run", action="store_true", help="Create manifest entries without downloading images.")
    parser.add_argument("--jpg-quality", type=int, default=75)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    authors = load_authors(args.authors_file)

    # 👇 ADD THIS BLOCK
    BASE_DIR = Path(__file__).resolve().parent.parent

    output_dir = (BASE_DIR / args.output_dir).resolve()
    manifest_path = (BASE_DIR / args.manifest).resolve()

    build_carousel(
        authors=authors,
        output_dir=output_dir,
        manifest_path=manifest_path,
        min_favourites=args.min_favourites,
        max_items=args.max_items,
        delay=args.delay,
        dry_run=args.dry_run,
        jpg_quality=args.jpg_quality,
    )


if __name__ == "__main__":
    main()

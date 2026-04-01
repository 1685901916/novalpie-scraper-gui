import argparse
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from novalpie_utils import create_driver, load_auth_token, load_cookies, load_local_storage, normalize_text


BASE_URL = "https://novalpie.cc"
DEFAULT_BOOK_ID = "353927"
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"


def _build_chapter_url(book_id: str, chapter_id: str) -> str:
    return f"{BASE_URL}/book/{book_id}/{chapter_id}"


def _load_chapters(input_path: str, book_id: str):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    chapters = []
    for idx, ch in enumerate(data):
        chapter_id = str(ch.get("id", "")).strip()
        if not chapter_id:
            continue
        title = (ch.get("title") or "").strip() or f"Chapter {chapter_id}"
        url = (ch.get("url") or "").strip() or _build_chapter_url(book_id, chapter_id)
        order = ch.get("order", idx)
        chapters.append({"id": chapter_id, "title": title, "url": url, "order": order})
    return chapters


def _load_progress(progress_file: Path):
    if not progress_file.exists():
        return set(), []
    with open(progress_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    completed = set(data.get("completed_ids", []))
    chapters_content = data.get("chapters_content", [])
    return completed, chapters_content


def _save_progress(progress_file: Path, completed_ids, chapters_content):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "completed_ids": sorted(completed_ids),
        "chapters_content": chapters_content,
    }
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _extract_chapter_content(html: str, chapter_id: str, chapter_title: str):
    soup = BeautifulSoup(html, "lxml")
    chapter_div = soup.select_one(f"div.chapter-item[data-chapter-id='{chapter_id}']")
    if chapter_div is None:
        chapter_div = soup.select_one("div.chapter-item")
    if chapter_div is None:
        return None

    for sel in ["div.chapter-comments", "div.chapter-navigation-toolbar", "div.chapter-separator"]:
        for node in chapter_div.select(sel):
            node.decompose()
    for tag in chapter_div.find_all(["h1", "h2", "h3"]):
        tag.decompose()

    for br in chapter_div.find_all("br"):
        br.replace_with("\n")

    title = chapter_div.get("data-chapter-title") or chapter_title
    images = []
    for idx, img in enumerate(chapter_div.find_all("img")):
        src = img.get("src") or ""
        if src:
            images.append(src)
            img.replace_with(f"\n[IMG_{idx}]\n")
        else:
            img.decompose()

    content = normalize_text(chapter_div.get_text())
    return {"id": chapter_id, "title": title, "content": content, "images": images}


_driver_lock = threading.Lock()
_drivers = []
_thread_local = threading.local()


def _get_driver(headless, cookies, auth_token):
    driver = getattr(_thread_local, "driver", None)
    if driver is not None:
        return driver
    driver = create_driver(
        headless=headless,
        base_url=BASE_URL,
        cookies=cookies,
        auth_token=auth_token,
        local_storage=load_local_storage(),
    )
    _thread_local.driver = driver
    with _driver_lock:
        _drivers.append(driver)
    return driver


def _fetch_one(chapter, headless, cookies, auth_token, delay):
    driver = _get_driver(headless, cookies, auth_token)
    try:
        driver.get(chapter["url"])
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.chapter-item")))
        time.sleep(delay)
        content = _extract_chapter_content(driver.page_source, chapter["id"], chapter["title"])
        if content:
            content["order"] = chapter.get("order", 0)
        return content
    except Exception:
        return None


def scrape(
    book_id: str,
    input_path: Path,
    output_path: Path,
    progress_file: Path,
    headless: bool = True,
    start: int = 0,
    limit: int = 0,
    workers: int = 4,
    delay: float = 0.6,
):
    chapters = _load_chapters(str(input_path), book_id)
    order_map = {ch["id"]: ch.get("order", 0) for ch in chapters}
    if start > 0 or limit > 0:
        end = (start + limit) if limit > 0 else None
        chapters = chapters[start:end]

    completed_ids, chapters_content = _load_progress(progress_file)
    # 补齐已完成章节的 order
    for item in chapters_content:
        if "order" not in item and item.get("id") in order_map:
            item["order"] = order_map[item["id"]]
    cookies = load_cookies()
    auth_token = load_auth_token()

    remaining = [ch for ch in chapters if ch["id"] not in completed_ids]
    if not remaining:
        print("No remaining chapters to scrape.")
    else:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = {
                executor.submit(_fetch_one, ch, headless, cookies, auth_token, delay): ch
                for ch in remaining
            }
            done = 0
            for fut in as_completed(futures):
                ch = futures[fut]
                result = fut.result()
                done += 1
                if result:
                    chapters_content.append(result)
                    completed_ids.add(ch["id"])
                    print(f"[{done}/{len(remaining)}] ok: {ch['title']}")
                else:
                    print(f"[{done}/{len(remaining)}] fail: {ch['title']}")

                if done % 10 == 0:
                    _save_progress(progress_file, completed_ids, chapters_content)

    for driver in _drivers:
        try:
            driver.quit()
        except Exception:
            pass

    _save_progress(progress_file, completed_ids, chapters_content)

    if chapters_content:
        chapters_content.sort(key=lambda x: x.get("order", 0))
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"Novalpie book {book_id}\n\n")
            for ch in chapters_content:
                f.write("=" * 50 + "\n")
                f.write(f"{ch['title']}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"{ch['content']}\n\n\n")
            f.write("=" * 50 + "\n")
            f.write(f"Total chapters: {len(chapters_content)}\n")
        print(f"Saved text to {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-id", default=DEFAULT_BOOK_ID)
    parser.add_argument("--input", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--progress", default="")
    parser.add_argument("--show", action="store_true", help="show browser")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--delay", type=float, default=0.6)
    args = parser.parse_args()

    book_id = args.book_id
    default_input = OUTPUT_DIR / f"novalpie_{book_id}_chapters_list.json"
    default_output = OUTPUT_DIR / f"novalpie_{book_id}.txt"
    default_progress = OUTPUT_DIR / f"novalpie_{book_id}_scrape_progress.json"
    input_path = Path(args.input) if args.input else default_input
    output_path = Path(args.output) if args.output else default_output
    progress_file = Path(args.progress) if args.progress else default_progress

    scrape(
        book_id=book_id,
        input_path=input_path,
        output_path=output_path,
        progress_file=progress_file,
        headless=not args.show,
        start=args.start,
        limit=args.limit,
        workers=args.workers,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()

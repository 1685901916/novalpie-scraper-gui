import json
import os
import re
import time
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from novalpie_utils import create_driver, load_auth_token, load_cookies, load_local_storage


BASE_URL = "https://novalpie.cc"
DEFAULT_BOOK_ID = "353927"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"


def _build_chapter_url(book_id: str, chapter_id: str) -> str:
    return f"{BASE_URL}/book/{book_id}/{chapter_id}"


def _click_expand_button(driver):
    js = """
    (function() {
        function findRoot() {
            const headers = Array.from(document.querySelectorAll('div,span,button,h3,h4'))
                .filter(el => (el.textContent || '').trim().includes('章目录'));
            if (headers.length) {
                let el = headers[0];
                while (el) {
                    if (el.querySelector && el.querySelector('button, a, span, div')) {
                        return el;
                    }
                    el = el.parentElement;
                }
            }
            return document.body;
        }
        const root = findRoot();
        const candidates = root.querySelectorAll('button, a, span, div');
        for (const el of candidates) {
            const text = (el.textContent || '').trim();
            if (text === '更多' || text === 'More' || text.includes('展开')) {
                el.click();
                return text;
            }
        }
        return '';
    })();
    """
    try:
        clicked = driver.execute_script(js)
        return bool(clicked)
    except Exception:
        return False


def _click_catalog_tab(driver):
    candidates = driver.find_elements(By.TAG_NAME, "button")
    for el in candidates:
        text = (el.text or "").strip()
        if text.startswith("目录") or "绔犵洰" in text:
            try:
                driver.execute_script("arguments[0].click();", el)
                return True
            except Exception:
                try:
                    el.click()
                    return True
                except Exception:
                    continue
    return False


def _find_scroll_container(driver):
    scrollers = driver.find_elements(By.CSS_SELECTOR, ".vue-recycle-scroller")
    best = None
    best_height = 0
    for sc in scrollers:
        try:
            buttons = sc.find_elements(By.CSS_SELECTOR, "button[data-chapter-id]")
            if not buttons:
                continue
            height = driver.execute_script("return arguments[0].scrollHeight || 0;", sc)
            if height > best_height:
                best = sc
                best_height = height
        except Exception:
            continue
    if best is not None:
        return best

    buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-chapter-id]")
    if not buttons:
        return None

    js = """
    const btn = arguments[0];
    let el = btn.parentElement;
    while (el) {
        const style = window.getComputedStyle(el);
        if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
            el.scrollHeight > el.clientHeight) {
            return el;
        }
        el = el.parentElement;
    }
    return null;
    """
    try:
        return driver.execute_script(js, buttons[0])
    except Exception:
        return None


def _scroll_chapter_list(driver, scroll_el=None, step=600):
    if scroll_el is None:
        scroll_el = _find_scroll_container(driver)
    if scroll_el is None:
        try:
            driver.execute_script("window.scrollBy(0, arguments[0]);", step)
        except Exception:
            pass
        return

    try:
        driver.execute_script(
            """
            const el = arguments[0];
            const step = arguments[1];
            el.scrollTop = el.scrollTop + step;
            el.dispatchEvent(new Event('scroll', {bubbles: true}));
            const evt = new WheelEvent('wheel', {deltaY: step, bubbles: true});
            el.dispatchEvent(evt);
            """,
            scroll_el,
            step,
        )
    except Exception:
        try:
            driver.execute_script("arguments[0].scrollTop += arguments[1];", scroll_el, step)
        except Exception:
            pass


def _extract_title_from_button(btn, fallback_index: int) -> str:
    try:
        title_el = btn.find_element(By.CSS_SELECTOR, ".font-medium")
        title = (title_el.text or "").strip()
        if title:
            return title
    except Exception:
        pass
    text = (btn.text or "").strip().splitlines()
    if len(text) >= 2 and text[0].strip().startswith("第"):
        title = text[1].strip()
        if title:
            return title
    if text:
        return text[0].strip()
    return f"Chapter {fallback_index}"


def collect_chapters(book_id: str, headless: bool = True):
    cookies = load_cookies()
    auth_token = load_auth_token()
    driver = create_driver(
        headless=headless,
        base_url=BASE_URL,
        cookies=cookies,
        auth_token=auth_token,
        local_storage=load_local_storage(),
    )

    chapters = []
    all_chapters = {}
    order = 0
    detail_url = f"{BASE_URL}/book/{book_id}/"
    output_json = OUTPUT_DIR / f"novalpie_{book_id}_chapters_list.json"

    try:
        driver.get(detail_url)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)

        _click_catalog_tab(driver)
        time.sleep(1.5)

        _click_expand_button(driver)
        time.sleep(1.5)

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-chapter-id]")))
        except Exception:
            pass

        scroll_el = _find_scroll_container(driver)
        if scroll_el is not None:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", scroll_el)
            except Exception:
                pass

        no_change = 0
        last_count = 0

        for i in range(800):
            buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-chapter-id]")

            for btn in buttons:
                chapter_id = btn.get_attribute("data-chapter-id")
                if not chapter_id:
                    continue
                title = _extract_title_from_button(btn, order + 1)
                existing = all_chapters.get(chapter_id)
                if existing is None:
                    all_chapters[chapter_id] = {
                        "id": chapter_id,
                        "title": title,
                        "order": order,
                        "url": _build_chapter_url(book_id, chapter_id),
                    }
                    order += 1
                    continue

                if (
                    existing["title"].startswith("Chapter ")
                    or not existing["title"].strip()
                ) and title and not title.startswith("Chapter "):
                    existing["title"] = title

            current_count = len(all_chapters)
            if current_count == last_count:
                no_change += 1
            else:
                no_change = 0
                last_count = current_count

            if i % 10 == 0:
                print(f"[{i:3d}] chapters={current_count} no_change={no_change}")

            if no_change >= 60:
                break

            _scroll_chapter_list(driver, scroll_el=scroll_el, step=700)
            time.sleep(0.35)

        chapters = list(all_chapters.values())
        chapters.sort(key=lambda x: x["order"])

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(chapters)} chapters to {output_json}")
        if chapters:
            print("First 3:")
            for ch in chapters[:3]:
                print(f"  {ch['title']} ({ch['id']})")
            print("Last 3:")
            for ch in chapters[-3:]:
                print(f"  {ch['title']} ({ch['id']})")

    finally:
        driver.quit()

    return chapters


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--book-id", default=DEFAULT_BOOK_ID)
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()

    collect_chapters(book_id=args.book_id, headless=not args.show)

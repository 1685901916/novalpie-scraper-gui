"""
获取 zoolib.cc 的章节列表
自动等待页面加载，需要手动完成Cloudflare验证
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
import time
import json
import config

def get_all_chapters():
    """获取所有章节"""

    options = EdgeOptions()
    options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Edge(options=options)

    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })

    try:
        print("=" * 60)
        print("zoolib.cc chapter list extractor")
        print("=" * 60)

        print("\n[1/4] Visiting main page...")
        driver.get(config.BASE_URL)
        time.sleep(3)

        print("[2/4] Adding cookies...")
        for name, value in config.COOKIES.items():
            try:
                driver.add_cookie({
                    'name': name,
                    'value': value,
                    'domain': 'zoolib.cc'
                })
            except Exception as e:
                print(f"  Cookie {name} failed: {e}")

        print(f"[3/4] Visiting detail page: {config.DETAIL_URL}")
        driver.get(config.DETAIL_URL)

        print("\n" + "=" * 60)
        print("Waiting for page to load...")
        print("If Cloudflare verification appears,")
        print("please complete it manually in the browser.")
        print("=" * 60)

        # 等待章节按钮出现（最多等待180秒，给用户时间完成验证）
        print("\n[4/4] Waiting for chapter buttons (max 180s)...")

        found_chapters = False
        for i in range(180):
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]')
                if buttons and len(buttons) > 0:
                    print(f"\nFound {len(buttons)} chapter buttons!")
                    found_chapters = True
                    break
            except:
                pass

            if i % 10 == 0:
                print(f"  Waiting... {i}s")
            time.sleep(1)

        if not found_chapters:
            print("\nNo chapter buttons found after 180s")
            print("Trying alternative selectors...")

            selectors_to_try = [
                '[data-chapter-id]',
                '.chapter-item',
                'a[href*="chapter"]',
            ]

            for sel in selectors_to_try:
                try:
                    elems = driver.find_elements(By.CSS_SELECTOR, sel)
                    if elems:
                        print(f"Found {len(elems)} elements with selector: {sel}")
                except:
                    pass

            print("\nPage title:", driver.title)
            print("Current URL:", driver.current_url)

            # 保存页面源码用于调试
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("Saved page source to debug_page.html")

            # 继续等待30秒
            print("\nWaiting another 30s...")
            time.sleep(30)

            buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]')
            if not buttons:
                print("Still no buttons found")
                driver.quit()
                return []

        time.sleep(3)

        # 开始自动滚动收集章节
        print("\nStarting auto-scroll to collect chapters...")

        scroll_container = None
        selectors = [
            "div.max-h-60vh",
            "div[class*='overflow-y-auto']",
            "div[class*='max-h']",
        ]

        for selector in selectors:
            try:
                container = driver.find_element(By.CSS_SELECTOR, selector)
                if container:
                    scroll_container = container
                    print(f"Found scroll container: {selector}")
                    break
            except:
                continue

        all_chapters = {}
        last_count = 0
        no_change_count = 0
        max_no_change = 80
        max_scroll_count = 600
        scroll_count = 0

        print("\nScrolling and collecting...")

        while no_change_count < max_no_change and scroll_count < max_scroll_count:
            if scroll_count < 50:
                scroll_increment = 800
                delay = 0.3
            elif scroll_count < 200:
                scroll_increment = 500
                delay = 0.5
            else:
                scroll_increment = 300
                delay = 0.6

            buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]')

            new_found = 0
            for btn in buttons:
                try:
                    chapter_id = btn.get_attribute('data-chapter-id')
                    if chapter_id and chapter_id not in all_chapters:
                        try:
                            title_elem = btn.find_element(By.CSS_SELECTOR, '.font-medium')
                            title = title_elem.text.strip()
                        except:
                            title = f"Chapter {len(all_chapters) + 1}"

                        all_chapters[chapter_id] = {
                            'id': chapter_id,
                            'title': title
                        }
                        new_found += 1
                except:
                    continue

            current_count = len(all_chapters)

            if scroll_count % 10 == 0:
                print(f"[{scroll_count:3d}] Collected {current_count} chapters | New: {new_found} | No change: {no_change_count}")

            if current_count == last_count:
                no_change_count += 1
            else:
                no_change_count = 0
                last_count = current_count

            if buttons:
                try:
                    last_button = buttons[-1]
                    driver.execute_script("arguments[0].scrollIntoView({block: 'end', behavior: 'smooth'});", last_button)
                    time.sleep(delay * 0.5)

                    if scroll_container:
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_container)
                        time.sleep(delay * 0.3)

                    driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
                    time.sleep(delay * 0.2)
                except:
                    pass
            else:
                driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
                time.sleep(delay)

            scroll_count += 1

        chapters = list(all_chapters.values())

        import re
        def get_chapter_num(ch):
            match = re.search(r'\d+', ch['title'])
            return int(match.group()) if match else 0

        chapters.sort(key=get_chapter_num)

        print(f"\n{'=' * 60}")
        print(f"Successfully collected {len(chapters)} chapters!")
        print(f"{'=' * 60}")

        with open('all_chapters.json', 'w', encoding='utf-8') as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)
        print("Saved to all_chapters.json")

        chapter_list = []
        for ch in chapters:
            chapter_list.append({
                'id': ch['id'],
                'title': ch['title'],
                'url': f"{config.READER_URL}?novel={config.NOVEL_ID}&chapter={ch['id']}"
            })

        with open('chapters_list.json', 'w', encoding='utf-8') as f:
            json.dump(chapter_list, f, ensure_ascii=False, indent=2)
        print("Saved to chapters_list.json (with URLs)")

        if chapters:
            print("\nFirst 5 chapters:")
            for ch in chapters[:5]:
                print(f"  {ch['title']} - ID: {ch['id']}")

            print("\nLast 5 chapters:")
            for ch in chapters[-5:]:
                print(f"  {ch['title']} - ID: {ch['id']}")

        return chapter_list

    finally:
        print("\nKeeping browser open for 10s...")
        time.sleep(10)
        driver.quit()


if __name__ == "__main__":
    chapters = get_all_chapters()
    print(f"\nTotal chapters: {len(chapters) if chapters else 0}")

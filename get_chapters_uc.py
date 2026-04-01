"""
获取 zoolib.cc 的章节列表
使用 undetected-chromedriver 绕过 Cloudflare 检测
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re
import config


def get_all_chapters():
    """获取所有章节"""

    print("=" * 60)
    print("zoolib.cc Chapter Extractor")
    print("Using undetected-chromedriver")
    print("=" * 60)

    # 创建 undetected Chrome 浏览器
    print("\n[1/5] Starting browser...")

    options = uc.ChromeOptions()
    options.add_argument(f'--user-agent={config.HEADERS["User-Agent"]}')
    options.add_argument('--lang=zh-CN')

    driver = uc.Chrome(options=options)

    try:
        # 访问主页
        print("[2/5] Visiting main page...")
        driver.get(config.BASE_URL)
        time.sleep(3)

        # 添加Cookie
        print("[3/5] Adding cookies...")
        for name, value in config.COOKIES.items():
            try:
                driver.add_cookie({
                    'name': name,
                    'value': value,
                    'domain': 'zoolib.cc'
                })
            except Exception as e:
                print(f"  Cookie {name}: {e}")

        # 访问详情页
        print(f"[4/5] Visiting detail page: {config.DETAIL_URL}")
        driver.get(config.DETAIL_URL)

        # 等待页面加载
        print("\nWaiting for page to load...")
        print("If Cloudflare challenge appears, please wait...")

        # 等待章节按钮出现（最多120秒）
        found = False
        for i in range(120):
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]')
                if buttons and len(buttons) > 0:
                    print(f"\nFound {len(buttons)} chapter buttons!")
                    found = True
                    break
            except:
                pass

            # 检查是否在Cloudflare验证页面
            if "challenge" in driver.page_source.lower() or "checking" in driver.page_source.lower():
                if i % 10 == 0:
                    print(f"  Cloudflare challenge in progress... {i}s")
            elif i % 10 == 0:
                print(f"  Waiting... {i}s")

            time.sleep(1)

        if not found:
            print("\nFailed to load chapter buttons after 120s")
            print("Page title:", driver.title)
            print("Current URL:", driver.current_url)

            # 保存页面源码用于调试
            with open('debug_uc_page.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("Saved page source to debug_uc_page.html")
            return []

        time.sleep(3)

        # 开始滚动收集章节
        print("\n[5/5] Starting auto-scroll to collect chapters...")

        # 查找滚动容器
        scroll_container = None
        container_selectors = [
            "div.max-h-60vh",
            "div[class*='overflow-y-auto']",
            "div[class*='max-h']",
        ]

        for selector in container_selectors:
            try:
                container = driver.find_element(By.CSS_SELECTOR, selector)
                if container:
                    scroll_container = container
                    print(f"Found scroll container: {selector}")
                    break
            except:
                continue

        # 收集章节
        all_chapters = {}
        last_count = 0
        no_change_count = 0
        max_no_change = 80
        max_scroll_count = 600
        scroll_count = 0

        print("\nScrolling and collecting chapters...")

        while no_change_count < max_no_change and scroll_count < max_scroll_count:
            # 动态调整滚动参数
            if scroll_count < 50:
                scroll_increment = 800
                delay = 0.3
            elif scroll_count < 200:
                scroll_increment = 500
                delay = 0.5
            else:
                scroll_increment = 300
                delay = 0.6

            # 获取当前可见的章节按钮
            buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]')

            # 收集章节信息
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

            # 每10次滚动显示进度
            if scroll_count % 10 == 0:
                print(f"[{scroll_count:3d}] Collected {current_count} chapters | New: {new_found} | No change: {no_change_count}")

            # 检查是否有新章节
            if current_count == last_count:
                no_change_count += 1
            else:
                no_change_count = 0
                last_count = current_count

            # 多层滚动策略
            if buttons:
                try:
                    # 滚动到最后一个按钮
                    last_button = buttons[-1]
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'end', behavior: 'smooth'});",
                        last_button
                    )
                    time.sleep(delay * 0.5)

                    # 滚动容器
                    if scroll_container:
                        driver.execute_script(
                            "arguments[0].scrollTop = arguments[0].scrollHeight;",
                            scroll_container
                        )
                        time.sleep(delay * 0.3)

                    # 滚动整个页面
                    driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
                    time.sleep(delay * 0.2)
                except:
                    pass
            else:
                driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
                time.sleep(delay)

            scroll_count += 1

        # 转换为列表并排序
        chapters = list(all_chapters.values())

        def get_chapter_num(ch):
            match = re.search(r'\d+', ch['title'])
            return int(match.group()) if match else 0

        chapters.sort(key=get_chapter_num)

        print(f"\n{'=' * 60}")
        print(f"Successfully collected {len(chapters)} chapters!")
        print(f"{'=' * 60}")

        # 保存原始数据
        with open('all_chapters.json', 'w', encoding='utf-8') as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)
        print("Saved to all_chapters.json")

        # 转换为爬虫需要的格式（带URL）
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

        # 显示前后几章
        if chapters:
            print("\nFirst 5 chapters:")
            for ch in chapters[:5]:
                print(f"  {ch['title']} - ID: {ch['id']}")

            print("\nLast 5 chapters:")
            for ch in chapters[-5:]:
                print(f"  {ch['title']} - ID: {ch['id']}")

        return chapter_list

    finally:
        print("\nClosing browser...")
        driver.quit()


if __name__ == "__main__":
    chapters = get_all_chapters()
    print(f"\nTotal chapters: {len(chapters) if chapters else 0}")

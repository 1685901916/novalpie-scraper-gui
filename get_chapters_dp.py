"""
获取 zoolib.cc 的章节列表
使用 DrissionPage 绕过 Cloudflare 检测
"""

from DrissionPage import ChromiumPage, ChromiumOptions
import time
import json
import re
import config


def get_all_chapters():
    """获取所有章节"""

    print("=" * 60)
    print("zoolib.cc Chapter Extractor")
    print("Using DrissionPage")
    print("=" * 60)

    # 配置浏览器选项
    co = ChromiumOptions()
    co.set_argument('--lang=zh-CN')
    # 使用系统已安装的Edge浏览器
    co.set_browser_path('msedge')

    print("\n[1/5] Starting browser...")
    page = ChromiumPage(co)

    try:
        # 访问主页
        print("[2/5] Visiting main page...")
        page.get(config.BASE_URL)
        time.sleep(3)

        # 添加Cookie
        print("[3/5] Adding cookies...")
        for name, value in config.COOKIES.items():
            try:
                page.set.cookies({name: value})
            except Exception as e:
                print(f"  Cookie {name}: {e}")

        # 访问详情页
        print(f"[4/5] Visiting detail page: {config.DETAIL_URL}")
        page.get(config.DETAIL_URL)

        # 等待页面加载
        print("\nWaiting for page to load...")
        print("If Cloudflare challenge appears, please wait...")

        # 等待章节按钮出现
        found = False
        for i in range(120):
            try:
                buttons = page.eles('css:button[data-chapter-id]')
                if buttons and len(buttons) > 0:
                    print(f"\nFound {len(buttons)} chapter buttons!")
                    found = True
                    break
            except:
                pass

            # 检查页面状态
            html = page.html.lower()
            if "challenge" in html or "checking" in html or "verify" in html:
                if i % 10 == 0:
                    print(f"  Cloudflare challenge in progress... {i}s")
            elif i % 10 == 0:
                print(f"  Waiting... {i}s")

            time.sleep(1)

        if not found:
            print("\nFailed to load chapter buttons after 120s")
            print("Page title:", page.title)
            print("Current URL:", page.url)

            # 保存页面源码用于调试
            with open('debug_dp_page.html', 'w', encoding='utf-8') as f:
                f.write(page.html)
            print("Saved page source to debug_dp_page.html")
            return []

        time.sleep(3)

        # 开始滚动收集章节
        print("\n[5/5] Starting auto-scroll to collect chapters...")

        # 查找滚动容器
        scroll_container = None
        container_selectors = [
            "css:div.max-h-60vh",
            "css:div[class*='overflow-y-auto']",
            "css:div[class*='max-h']",
        ]

        for selector in container_selectors:
            try:
                container = page.ele(selector)
                if container:
                    scroll_container = container
                    print(f"Found scroll container")
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
            # 动态调整参数
            if scroll_count < 50:
                delay = 0.3
            elif scroll_count < 200:
                delay = 0.5
            else:
                delay = 0.6

            # 获取当前可见的章节按钮
            buttons = page.eles('css:button[data-chapter-id]')

            # 收集章节信息
            new_found = 0
            for btn in buttons:
                try:
                    chapter_id = btn.attr('data-chapter-id')
                    if chapter_id and chapter_id not in all_chapters:
                        try:
                            title_elem = btn.ele('css:.font-medium')
                            title = title_elem.text.strip() if title_elem else f"Chapter {len(all_chapters) + 1}"
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

            # 滚动策略
            if buttons:
                try:
                    # 滚动到最后一个按钮
                    last_button = buttons[-1]
                    last_button.scroll.to_see()
                    time.sleep(delay * 0.5)

                    # 滚动容器
                    if scroll_container:
                        page.run_js('arguments[0].scrollTop = arguments[0].scrollHeight;', scroll_container)
                        time.sleep(delay * 0.3)

                    # 滚动整个页面
                    page.scroll.down(500)
                    time.sleep(delay * 0.2)
                except:
                    page.scroll.down(500)
                    time.sleep(delay)
            else:
                page.scroll.down(500)
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
        page.quit()


if __name__ == "__main__":
    chapters = get_all_chapters()
    print(f"\nTotal chapters: {len(chapters) if chapters else 0}")

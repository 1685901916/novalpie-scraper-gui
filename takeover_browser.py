"""
接管用户已打开的浏览器收集章节
使用方法:
1. 手动在Edge浏览器中打开 https://zoolib.cc/book-detail/350009
2. 完成Cloudflare验证，确保页面正常显示章节列表
3. 运行此脚本，它会接管浏览器并自动滚动收集章节
"""

from DrissionPage import ChromiumPage
import time
import json
import re
import config


def collect_chapters_from_browser():
    """从已打开的浏览器收集章节"""

    print("=" * 60)
    print("Chapter Collector - Takeover Mode")
    print("=" * 60)
    print("\nThis script will take over your existing browser session.")
    print("Make sure you have:")
    print("1. Edge browser open with zoolib.cc/book-detail/350009")
    print("2. Completed Cloudflare verification")
    print("3. Can see the chapter list on the page")
    print("=" * 60)

    # 接管已运行的浏览器
    print("\n[1/3] Connecting to existing browser...")

    try:
        # 尝试连接到已运行的Edge浏览器
        page = ChromiumPage()
        print(f"Connected! Current URL: {page.url}")
        print(f"Page title: {page.title}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        print("\nPlease make sure Edge browser is running with the target page open.")
        return []

    # 检查是否在正确的页面
    if 'zoolib.cc' not in page.url:
        print(f"\nWarning: Current page is not zoolib.cc")
        print(f"Current URL: {page.url}")
        print("\nNavigating to detail page...")
        page.get(config.DETAIL_URL)
        time.sleep(5)

    # 检查章节按钮
    print("\n[2/3] Looking for chapter buttons...")

    buttons = page.eles('css:button[data-chapter-id]')
    if not buttons:
        print("No chapter buttons found!")
        print("Please make sure the page has fully loaded and Cloudflare is passed.")

        # 保存页面用于调试
        with open('debug_takeover.html', 'w', encoding='utf-8') as f:
            f.write(page.html)
        print("Saved page to debug_takeover.html")
        return []

    print(f"Found {len(buttons)} chapter buttons initially")

    # 开始滚动收集
    print("\n[3/3] Starting auto-scroll to collect all chapters...")

    all_chapters = {}
    last_count = 0
    no_change_count = 0
    max_no_change = 80
    scroll_count = 0

    while no_change_count < max_no_change and scroll_count < 600:
        # 动态调整参数
        if scroll_count < 50:
            delay = 0.3
        elif scroll_count < 200:
            delay = 0.5
        else:
            delay = 0.6

        # 获取章节按钮
        buttons = page.eles('css:button[data-chapter-id]')

        # 收集章节
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

        if scroll_count % 10 == 0:
            print(f"[{scroll_count:3d}] Collected {current_count} chapters | New: {new_found} | No change: {no_change_count}")

        if current_count == last_count:
            no_change_count += 1
        else:
            no_change_count = 0
            last_count = current_count

        # 滚动
        if buttons:
            try:
                buttons[-1].scroll.to_see()
                time.sleep(delay * 0.5)
                page.scroll.down(500)
                time.sleep(delay * 0.5)
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

    # 保存数据
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


if __name__ == "__main__":
    chapters = collect_chapters_from_browser()
    print(f"\nTotal chapters: {len(chapters) if chapters else 0}")

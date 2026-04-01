"""
改进版：使用更好的滚动策略收集所有章节
专门针对虚拟列表优化
"""

from DrissionPage import ChromiumPage, ChromiumOptions
import time
import json
import re
import os
import subprocess
import config


def main():
    print("=" * 60)
    print("zoolib.cc Chapter Collector v2")
    print("Optimized for virtual list scrolling")
    print("=" * 60)

    username = os.environ.get('USERNAME', 'Arthur')
    edge_user_data = f"C:\\Users\\{username}\\AppData\\Local\\Microsoft\\Edge\\User Data"

    print(f"\nUsing Edge profile: {edge_user_data}")

    # 关闭Edge
    print("\n[Step 1] Closing Edge processes...")
    os.system('taskkill /f /im msedge.exe 2>nul')
    time.sleep(3)

    # 启动Edge
    print("[Step 2] Starting Edge...")
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    debug_port = 9222
    cmd = f'"{edge_path}" --remote-debugging-port={debug_port} --user-data-dir="{edge_user_data}" {config.DETAIL_URL}'
    subprocess.Popen(cmd, shell=True)
    time.sleep(8)

    # 连接
    print("\n[Step 3] Connecting...")
    co = ChromiumOptions()
    co.set_local_port(debug_port)

    try:
        page = ChromiumPage(co)
        print(f"Connected! URL: {page.url}")
    except Exception as e:
        print(f"Failed: {e}")
        return

    # 等待页面
    print("\n[Step 4] Waiting for page...")

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

        if i % 10 == 0:
            print(f"  Waiting... ({i}s)")
        time.sleep(1)

    if not found:
        print("\nNo chapter buttons found")
        return

    time.sleep(3)

    # 查找章节列表的滚动容器
    print("\n[Step 5] Finding scroll container...")

    scroll_container = None
    container_selectors = [
        'css:div.max-h-60vh',
        'css:div.overflow-y-auto',
        'css:div[class*="overflow-y-auto"]',
        'css:div[class*="max-h-"]',
    ]

    for sel in container_selectors:
        try:
            elem = page.ele(sel)
            if elem:
                # 检查是否包含章节按钮
                if elem.ele('css:button[data-chapter-id]'):
                    scroll_container = elem
                    print(f"Found container with selector: {sel}")
                    break
        except:
            continue

    if not scroll_container:
        print("Warning: Could not find specific scroll container")
        print("Will use page scrolling instead")

    # 收集章节（改进的滚动策略）
    print("\n[Step 6] Collecting chapters with improved scrolling...")

    all_chapters = {}
    last_count = 0
    no_change_count = 0
    max_no_change = 100  # 增加等待次数
    scroll_count = 0

    while no_change_count < max_no_change and scroll_count < 800:
        # 动态调整
        if scroll_count < 50:
            scroll_amount = 800
            delay = 0.25
        elif scroll_count < 150:
            scroll_amount = 600
            delay = 0.35
        elif scroll_count < 300:
            scroll_amount = 400
            delay = 0.45
        else:
            scroll_amount = 300
            delay = 0.55

        # 获取章节
        buttons = page.eles('css:button[data-chapter-id]')

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
            print(f"[{scroll_count:3d}] Total: {current_count} | New: {new_found} | Stale: {no_change_count}/{max_no_change}")

        if current_count == last_count:
            no_change_count += 1
        else:
            no_change_count = 0
            last_count = current_count

        # 改进的滚动策略
        try:
            if buttons:
                last_btn = buttons[-1]

                # 策略1: 直接滚动到最后一个按钮
                last_btn.scroll.to_see()
                time.sleep(delay * 0.3)

                # 策略2: 滚动容器
                if scroll_container:
                    # 使用JavaScript滚动容器
                    page.run_js(f'''
                        var container = arguments[0];
                        container.scrollTop += {scroll_amount};
                    ''', scroll_container)
                    time.sleep(delay * 0.3)

                # 策略3: 模拟鼠标滚轮在最后一个按钮上
                try:
                    last_btn.scroll.down(scroll_amount)
                except:
                    pass
                time.sleep(delay * 0.2)

                # 策略4: 页面滚动
                page.scroll.down(scroll_amount // 2)
                time.sleep(delay * 0.2)

            else:
                page.scroll.down(scroll_amount)
                time.sleep(delay)

        except Exception as e:
            if scroll_count % 50 == 0:
                print(f"  Scroll error: {e}")
            page.scroll.down(scroll_amount)
            time.sleep(delay)

        scroll_count += 1

        # 如果连续很久没有新章节，尝试重置滚动位置
        if no_change_count == 50 and scroll_container:
            print("  Trying to reset scroll position...")
            try:
                page.run_js('arguments[0].scrollTop = 0;', scroll_container)
                time.sleep(1)
                page.run_js('arguments[0].scrollTop = arguments[0].scrollHeight;', scroll_container)
                time.sleep(1)
            except:
                pass

    # 保存结果
    chapters = list(all_chapters.values())

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
    print("Saved to chapters_list.json")

    if chapters:
        print("\nFirst 5:")
        for ch in chapters[:5]:
            print(f"  {ch['title']} - ID: {ch['id']}")

        print("\nLast 5:")
        for ch in chapters[-5:]:
            print(f"  {ch['title']} - ID: {ch['id']}")

        # 检查缺失
        nums = [get_chapter_num(ch) for ch in chapters]
        if nums:
            max_num = max(nums)
            missing = set(range(1, max_num + 1)) - set(nums)
            if missing:
                print(f"\nMissing {len(missing)} chapters: {sorted(missing)[:20]}...")

    print("\nDone!")


if __name__ == "__main__":
    main()

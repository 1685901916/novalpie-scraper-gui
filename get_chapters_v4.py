"""
针对 vue-recycle-scroller 虚拟滚动组件优化的章节收集器
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
    print("zoolib.cc Chapter Collector v4")
    print("Optimized for vue-recycle-scroller")
    print("=" * 60)

    username = os.environ.get('USERNAME', 'Arthur')
    edge_user_data = f"C:\\Users\\{username}\\AppData\\Local\\Microsoft\\Edge\\User Data"

    print("\n[Step 1] Closing Edge...")
    os.system('taskkill /f /im msedge.exe 2>nul')
    time.sleep(3)

    print("[Step 2] Starting Edge...")
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    debug_port = 9222
    cmd = f'"{edge_path}" --remote-debugging-port={debug_port} --user-data-dir="{edge_user_data}" {config.DETAIL_URL}'
    subprocess.Popen(cmd, shell=True)
    time.sleep(8)

    print("\n[Step 3] Connecting...")
    co = ChromiumOptions()
    co.set_local_port(debug_port)

    try:
        page = ChromiumPage(co)
        print(f"Connected! URL: {page.url}")
    except Exception as e:
        print(f"Failed: {e}")
        return

    print("\n[Step 4] Waiting for page...")
    found = False
    for i in range(60):
        try:
            buttons = page.eles('css:button[data-chapter-id]')
            if buttons and len(buttons) > 0:
                print(f"Found chapter buttons!")
                found = True
                break
        except:
            pass
        if i % 10 == 0:
            print(f"  Waiting... ({i}s)")
        time.sleep(1)

    if not found:
        print("No chapter buttons found")
        return

    time.sleep(2)

    # 查找 vue-recycle-scroller 容器
    print("\n[Step 5] Finding vue-recycle-scroller container...")

    js_find_scroller = '''
    var scroller = document.querySelector('.vue-recycle-scroller');
    if (scroller) {
        return {
            found: true,
            scrollHeight: scroller.scrollHeight,
            clientHeight: scroller.clientHeight,
            scrollTop: scroller.scrollTop
        };
    }
    return {found: false};
    '''

    scroller_info = page.run_js(js_find_scroller)
    print(f"Scroller info: {scroller_info}")

    if not scroller_info.get('found'):
        print("vue-recycle-scroller not found!")
        return

    print(f"Scroller height: {scroller_info['scrollHeight']}, visible: {scroller_info['clientHeight']}")

    # 使用专门的滚动方法
    print("\n[Step 6] Collecting chapters with vue-recycle-scroller scrolling...")

    all_chapters = {}
    scroll_count = 0
    no_change_count = 0
    max_no_change = 120
    last_count = 0

    # 计算需要滚动的次数
    total_height = scroller_info['scrollHeight']
    visible_height = scroller_info['clientHeight']
    scroll_step = visible_height // 2  # 每次滚动半个可见高度

    print(f"Scroll step: {scroll_step}px")

    while no_change_count < max_no_change and scroll_count < 1000:
        # 收集当前可见的章节
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
            # 获取当前滚动位置
            pos_info = page.run_js('''
                var s = document.querySelector('.vue-recycle-scroller');
                return s ? {top: s.scrollTop, max: s.scrollHeight - s.clientHeight} : {};
            ''')
            pos = pos_info.get('top', 0)
            max_pos = pos_info.get('max', 0)
            progress = (pos / max_pos * 100) if max_pos > 0 else 0
            print(f"[{scroll_count:3d}] Chapters: {current_count} | New: {new_found} | Stale: {no_change_count} | Scroll: {progress:.1f}%")

        if current_count == last_count:
            no_change_count += 1
        else:
            no_change_count = 0
            last_count = current_count

        # 滚动 vue-recycle-scroller
        js_scroll = f'''
        var scroller = document.querySelector('.vue-recycle-scroller');
        if (scroller) {{
            scroller.scrollTop += {scroll_step};
            return scroller.scrollTop;
        }}
        return -1;
        '''

        scroll_pos = page.run_js(js_scroll)

        # 等待虚拟滚动渲染
        time.sleep(0.2)

        # 如果滚动位置不变，可能到底了
        if scroll_count > 0:
            new_pos = page.run_js('var s = document.querySelector(".vue-recycle-scroller"); return s ? s.scrollTop : -1;')
            if new_pos == scroll_pos and new_pos > 0:
                no_change_count += 5  # 加速停止

        scroll_count += 1

        # 每100次滚动，尝试重置到开头再滚动一遍
        if scroll_count == 400 and current_count < 500:
            print("  Resetting scroll position...")
            page.run_js('var s = document.querySelector(".vue-recycle-scroller"); if(s) s.scrollTop = 0;')
            time.sleep(1)

    # 保存结果
    chapters = list(all_chapters.values())

    def get_chapter_num(ch):
        match = re.search(r'\d+', ch['title'])
        return int(match.group()) if match else 0

    chapters.sort(key=get_chapter_num)

    print(f"\n{'=' * 60}")
    print(f"Collected {len(chapters)} chapters!")
    print(f"{'=' * 60}")

    with open('all_chapters.json', 'w', encoding='utf-8') as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)

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
        nums = [get_chapter_num(ch) for ch in chapters]
        max_num = max(nums) if nums else 0
        min_num = min(nums) if nums else 0
        print(f"\nChapter range: {min_num} - {max_num}")

        missing = set(range(1, max_num + 1)) - set(nums)
        if missing:
            print(f"Missing {len(missing)} chapters")

    print("\nDone!")


if __name__ == "__main__":
    main()

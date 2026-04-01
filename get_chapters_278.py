"""
点击"更多"按钮展开章节列表，然后收集所有278章
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
    print("zoolib.cc - Collect 278 chapters")
    print("=" * 60)

    username = os.environ.get('USERNAME', 'Arthur')
    edge_user_data = f"C:\\Users\\{username}\\AppData\\Local\\Microsoft\\Edge\\User Data"

    print("\n[1] Closing Edge...")
    os.system('taskkill /f /im msedge.exe 2>nul')
    time.sleep(3)

    print("[2] Starting Edge...")
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    debug_port = 9222
    cmd = f'"{edge_path}" --remote-debugging-port={debug_port} --user-data-dir="{edge_user_data}" {config.DETAIL_URL}'
    subprocess.Popen(cmd, shell=True)
    time.sleep(8)

    print("\n[3] Connecting...")
    co = ChromiumOptions()
    co.set_local_port(debug_port)

    try:
        page = ChromiumPage(co)
        print(f"Connected! URL: {page.url}")
    except Exception as e:
        print(f"Failed: {e}")
        return

    print("\n[4] Waiting for page...")
    time.sleep(5)

    # 点击"更多"按钮展开章节列表
    print("\n[5] Looking for 'More' button to expand chapter list...")

    # 尝试多种方式找到并点击"更多"按钮
    js_click_more = '''
    // 找到包含"更多"的按钮或链接
    var buttons = document.querySelectorAll('button, a, span, div');
    var clicked = false;
    for (var i = 0; i < buttons.length; i++) {
        var text = buttons[i].textContent.trim();
        if (text === '更多' || text.includes('更多')) {
            console.log('Found button:', text);
            buttons[i].click();
            clicked = true;
            break;
        }
    }
    return clicked;
    '''

    try:
        clicked = page.run_js(js_click_more)
        if clicked:
            print("Clicked 'More' button!")
            time.sleep(3)
        else:
            print("'More' button not found, trying alternative...")
    except Exception as e:
        print(f"Click error: {e}")

    # 等待章节列表展开
    time.sleep(3)

    # 查找滚动容器
    print("\n[6] Finding scroll container...")

    js_find_scroller = '''
    var scrollers = document.querySelectorAll('.vue-recycle-scroller, [class*="overflow-y-auto"], [class*="max-h"]');
    var result = [];
    scrollers.forEach(function(s) {
        if (s.scrollHeight > 100) {
            result.push({
                class: s.className.substring(0, 50),
                scrollHeight: s.scrollHeight,
                clientHeight: s.clientHeight
            });
        }
    });
    return result;
    '''

    scrollers = page.run_js(js_find_scroller)
    print(f"Found scrollers: {scrollers}")

    # 收集章节
    print("\n[7] Collecting chapters...")

    all_chapters = {}
    scroll_count = 0
    no_change_count = 0
    max_no_change = 150
    last_count = 0
    target_chapters = 278

    while no_change_count < max_no_change and scroll_count < 1200:
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
            progress = (current_count / target_chapters) * 100
            print(f"[{scroll_count:3d}] Chapters: {current_count}/{target_chapters} ({progress:.1f}%) | New: {new_found} | Stale: {no_change_count}")

        # 如果已经收集到足够的章节，提前结束
        if current_count >= target_chapters:
            print(f"\nReached target: {current_count} chapters!")
            break

        if current_count == last_count:
            no_change_count += 1
        else:
            no_change_count = 0
            last_count = current_count

        # 滚动策略：尝试多种方式
        js_scroll = '''
        var scrolled = false;

        // 方法1: 滚动vue-recycle-scroller
        var scroller = document.querySelector('.vue-recycle-scroller');
        if (scroller && scroller.scrollHeight > scroller.clientHeight) {
            scroller.scrollTop += 300;
            scrolled = true;
        }

        // 方法2: 滚动任何可滚动的章节容器
        if (!scrolled) {
            var containers = document.querySelectorAll('[class*="overflow-y-auto"], [class*="max-h"]');
            containers.forEach(function(c) {
                if (c.scrollHeight > c.clientHeight && c.querySelector('button[data-chapter-id]')) {
                    c.scrollTop += 300;
                    scrolled = true;
                }
            });
        }

        // 方法3: 滚动到最后一个章节按钮
        if (!scrolled) {
            var buttons = document.querySelectorAll('button[data-chapter-id]');
            if (buttons.length > 0) {
                var lastBtn = buttons[buttons.length - 1];
                lastBtn.scrollIntoView({block: 'end', behavior: 'smooth'});
                scrolled = true;
            }
        }

        return scrolled;
        '''

        try:
            page.run_js(js_scroll)
        except:
            pass

        time.sleep(0.25)
        scroll_count += 1

        # 每100次滚动尝试重新点击"更多"
        if scroll_count % 100 == 0 and current_count < target_chapters:
            print("  Trying to click 'More' again...")
            try:
                page.run_js(js_click_more)
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

        # 检查缺失
        missing = set(range(1, target_chapters + 1)) - set(nums)
        if missing:
            print(f"Missing {len(missing)} chapters: {sorted(missing)[:20]}...")
        else:
            print("All chapters collected!")

    print("\nDone!")


if __name__ == "__main__":
    main()

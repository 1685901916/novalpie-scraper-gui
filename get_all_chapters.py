"""
完整版：先展开章节列表，然后使用事件派发滚动
确保vue-recycle-scroller正确响应滚动
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
    print("zoolib.cc - Complete Chapter Collector")
    print("Target: 278 chapters")
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
    time.sleep(10)

    print("\n[3] Connecting...")
    co = ChromiumOptions()
    co.set_local_port(debug_port)

    try:
        page = ChromiumPage(co)
        print(f"Connected! URL: {page.url}")
    except Exception as e:
        print(f"Failed: {e}")
        return

    print("\n[4] Waiting for page to load...")
    time.sleep(5)

    # 等待章节按钮出现
    for i in range(30):
        buttons = page.eles('css:button[data-chapter-id]')
        if buttons and len(buttons) > 0:
            print(f"Found {len(buttons)} chapter buttons")
            break
        time.sleep(1)

    time.sleep(2)

    # 点击"更多"按钮展开章节列表
    print("\n[5] Expanding chapter list (clicking More)...")

    js_expand = '''
    (function() {
        // 查找并点击"更多"按钮
        var elements = document.querySelectorAll('button, a, span, div');
        for (var i = 0; i < elements.length; i++) {
            var text = elements[i].textContent.trim();
            if (text === '更多' || text === 'More' || text.includes('展开')) {
                elements[i].click();
                return 'Clicked: ' + text;
            }
        }
        return 'No expand button found';
    })();
    '''

    result = page.run_js(js_expand)
    print(f"Expand result: {result}")
    time.sleep(3)

    # 查找滚动容器
    print("\n[6] Finding scroll container...")

    js_find_container = '''
    (function() {
        // 查找包含章节按钮的可滚动容器
        var buttons = document.querySelectorAll('button[data-chapter-id]');
        if (buttons.length === 0) return null;

        var container = buttons[0].parentElement;
        while (container) {
            var style = window.getComputedStyle(container);
            var overflowY = style.overflowY;
            if ((overflowY === 'auto' || overflowY === 'scroll') &&
                container.scrollHeight > container.clientHeight) {
                return {
                    class: container.className.substring(0, 100),
                    scrollHeight: container.scrollHeight,
                    clientHeight: container.clientHeight,
                    scrollTop: container.scrollTop
                };
            }
            container = container.parentElement;
        }

        // 尝试查找vue-recycle-scroller
        var scroller = document.querySelector('.vue-recycle-scroller');
        if (scroller) {
            return {
                class: 'vue-recycle-scroller',
                scrollHeight: scroller.scrollHeight,
                clientHeight: scroller.clientHeight,
                scrollTop: scroller.scrollTop
            };
        }

        return null;
    })();
    '''

    container_info = page.run_js(js_find_container)
    print(f"Container: {container_info}")

    # 收集章节 - 使用改进的滚动策略
    print("\n[7] Collecting chapters with improved scrolling...")

    all_chapters = {}
    scroll_count = 0
    max_scrolls = 500
    no_change_count = 0
    max_no_change = 80
    last_count = 0
    target = 278

    while no_change_count < max_no_change and scroll_count < max_scrolls:
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
            progress = (current_count / target) * 100
            print(f"[{scroll_count:3d}] Chapters: {current_count}/{target} ({progress:.1f}%) | New: {new_found} | Stale: {no_change_count}")

        if current_count >= target:
            print(f"\n*** Target reached: {current_count} chapters! ***")
            break

        if current_count == last_count:
            no_change_count += 1
        else:
            no_change_count = 0
            last_count = current_count

        # 滚动策略：使用JavaScript派发滚动事件
        js_scroll = '''
        (function() {
            // 方法1: 滚动vue-recycle-scroller
            var scroller = document.querySelector('.vue-recycle-scroller');
            if (scroller) {
                scroller.scrollTop += 200;
                scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
                return 'scrolled vue-recycle-scroller';
            }

            // 方法2: 滚动任何包含章节的可滚动容器
            var buttons = document.querySelectorAll('button[data-chapter-id]');
            if (buttons.length > 0) {
                var container = buttons[0].parentElement;
                while (container) {
                    var style = window.getComputedStyle(container);
                    if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                        container.scrollHeight > container.clientHeight) {
                        container.scrollTop += 200;
                        container.dispatchEvent(new Event('scroll', {bubbles: true}));
                        return 'scrolled container';
                    }
                    container = container.parentElement;
                }
            }

            // 方法3: 滚动页面
            window.scrollBy(0, 200);
            return 'scrolled window';
        })();
        '''

        try:
            page.run_js(js_scroll)
        except:
            pass

        time.sleep(0.3)
        scroll_count += 1

        # 每50次滚动尝试滚动到底部再回到顶部
        if no_change_count == 40:
            print("  Trying scroll reset...")
            js_reset = '''
            var scroller = document.querySelector('.vue-recycle-scroller');
            if (scroller) {
                scroller.scrollTop = 0;
            }
            '''
            page.run_js(js_reset)
            time.sleep(1)

        # 每60次无变化，尝试滚动到底部
        if no_change_count == 60:
            print("  Trying scroll to bottom...")
            js_bottom = '''
            var scroller = document.querySelector('.vue-recycle-scroller');
            if (scroller) {
                scroller.scrollTop = scroller.scrollHeight;
            }
            '''
            page.run_js(js_bottom)
            time.sleep(1)

    # 如果没有收集到足够的章节，尝试使用另一种方法
    if len(all_chapters) < target:
        print(f"\n[8] Only got {len(all_chapters)} chapters, trying wheel events...")

        # 使用模拟鼠标滚轮事件
        for i in range(100):
            js_wheel = '''
            (function() {
                var scroller = document.querySelector('.vue-recycle-scroller');
                if (!scroller) {
                    var buttons = document.querySelectorAll('button[data-chapter-id]');
                    if (buttons.length > 0) {
                        scroller = buttons[0].closest('[class*="overflow"]');
                    }
                }
                if (scroller) {
                    var wheelEvent = new WheelEvent('wheel', {
                        deltaY: 100,
                        deltaMode: 0,
                        bubbles: true
                    });
                    scroller.dispatchEvent(wheelEvent);
                    scroller.scrollTop += 150;
                    return true;
                }
                return false;
            })();
            '''
            page.run_js(js_wheel)
            time.sleep(0.25)

            # 收集章节
            buttons = page.eles('css:button[data-chapter-id]')
            for btn in buttons:
                try:
                    chapter_id = btn.attr('data-chapter-id')
                    if chapter_id and chapter_id not in all_chapters:
                        try:
                            title_elem = btn.ele('css:.font-medium')
                            title = title_elem.text.strip() if title_elem else f"Chapter {len(all_chapters) + 1}"
                        except:
                            title = f"Chapter {len(all_chapters) + 1}"
                        all_chapters[chapter_id] = {'id': chapter_id, 'title': title}
                except:
                    continue

            if i % 20 == 0:
                print(f"  Wheel scroll {i}: {len(all_chapters)} chapters")

            if len(all_chapters) >= target:
                break

    # 保存结果
    chapters = list(all_chapters.values())

    def get_chapter_num(ch):
        match = re.search(r'\d+', ch['title'])
        return int(match.group()) if match else 0

    chapters.sort(key=get_chapter_num)

    print(f"\n{'=' * 60}")
    print(f"Collected {len(chapters)} unique chapters!")
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

        print("\nFirst 5:")
        for ch in chapters[:5]:
            print(f"  {ch['title']} - ID: {ch['id']}")

        print("\nLast 5:")
        for ch in chapters[-5:]:
            print(f"  {ch['title']} - ID: {ch['id']}")

        missing = set(range(1, target + 1)) - set(nums)
        if missing:
            print(f"\nMissing {len(missing)} chapters: {sorted(missing)[:20]}...")
        else:
            print("\n*** All 278 chapters collected! ***")

    print("\nDone!")


if __name__ == "__main__":
    main()

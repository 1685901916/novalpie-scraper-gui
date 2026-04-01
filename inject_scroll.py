"""
在浏览器中注入滚动脚本，让vue-recycle-scroller自动加载所有章节
然后一次性收集
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
    print("zoolib.cc - Inject scroll script")
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

    # 注入自动滚动脚本
    print("\n[5] Injecting auto-scroll script...")

    inject_script = '''
    (function() {
        var scroller = document.querySelector('.vue-recycle-scroller');
        if (!scroller) {
            console.log('No scroller found');
            return 'No scroller';
        }

        var chaptersCollected = new Map();
        var scrollCount = 0;
        var maxScrolls = 500;
        var noNewCount = 0;
        var maxNoNew = 50;

        function collectChapters() {
            var buttons = document.querySelectorAll('button[data-chapter-id]');
            var newFound = 0;
            buttons.forEach(function(btn) {
                var id = btn.getAttribute('data-chapter-id');
                if (id && !chaptersCollected.has(id)) {
                    var titleElem = btn.querySelector('.font-medium');
                    var title = titleElem ? titleElem.textContent.trim() : 'Chapter ' + (chaptersCollected.size + 1);
                    chaptersCollected.set(id, {id: id, title: title});
                    newFound++;
                }
            });
            return newFound;
        }

        function scrollDown() {
            if (scrollCount >= maxScrolls || noNewCount >= maxNoNew) {
                // 完成，保存结果到window对象
                window.__CHAPTERS_RESULT__ = Array.from(chaptersCollected.values());
                console.log('Done! Collected ' + chaptersCollected.size + ' chapters');
                return;
            }

            var newFound = collectChapters();

            if (newFound === 0) {
                noNewCount++;
            } else {
                noNewCount = 0;
            }

            // 滚动
            scroller.scrollTop += 300;

            scrollCount++;
            if (scrollCount % 20 === 0) {
                console.log('Scroll ' + scrollCount + ': ' + chaptersCollected.size + ' chapters, noNew=' + noNewCount);
            }

            // 继续滚动
            setTimeout(scrollDown, 150);
        }

        // 开始滚动
        console.log('Starting auto-scroll...');
        scrollDown();

        return 'Script injected, scrolling...';
    })();
    '''

    try:
        result = page.run_js(inject_script)
        print(f"Injection result: {result}")
    except Exception as e:
        print(f"Injection error: {e}")

    # 等待脚本完成
    print("\n[6] Waiting for scroll to complete...")

    for i in range(120):  # 最多等待2分钟
        time.sleep(1)

        try:
            chapters = page.run_js('return window.__CHAPTERS_RESULT__;')
            if chapters and len(chapters) > 0:
                print(f"\nGot {len(chapters)} chapters from script!")
                break
        except:
            pass

        if i % 10 == 0:
            # 检查进度
            try:
                count = page.run_js('return window.__CHAPTERS_RESULT__ ? window.__CHAPTERS_RESULT__.length : "still running";')
                print(f"  {i}s: {count}")
            except:
                pass

    # 收集结果
    print("\n[7] Collecting results...")

    try:
        chapters = page.run_js('return window.__CHAPTERS_RESULT__;')
        if not chapters:
            # 如果脚本结果为空，直接从DOM收集
            print("Script result empty, collecting from DOM...")
            buttons = page.eles('css:button[data-chapter-id]')
            chapters = []
            for btn in buttons:
                try:
                    chapter_id = btn.attr('data-chapter-id')
                    if chapter_id:
                        title_elem = btn.ele('css:.font-medium')
                        title = title_elem.text.strip() if title_elem else f"Chapter {len(chapters) + 1}"
                        chapters.append({'id': chapter_id, 'title': title})
                except:
                    pass
    except Exception as e:
        print(f"Collection error: {e}")
        chapters = []

    if not chapters:
        print("No chapters collected!")
        return

    # 去重并排序
    unique_chapters = {}
    for ch in chapters:
        if ch['id'] not in unique_chapters:
            unique_chapters[ch['id']] = ch

    chapters = list(unique_chapters.values())

    def get_chapter_num(ch):
        match = re.search(r'\d+', ch['title'])
        return int(match.group()) if match else 0

    chapters.sort(key=get_chapter_num)

    print(f"\n{'=' * 60}")
    print(f"Collected {len(chapters)} unique chapters!")
    print(f"{'=' * 60}")

    # 保存
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
        print(f"Chapter range: {min(nums)} - {max(nums)}")

        missing = set(range(1, 279)) - set(nums)
        if missing:
            print(f"Missing {len(missing)} chapters")
        else:
            print("All 278 chapters collected!")

    print("\nDone!")


if __name__ == "__main__":
    main()

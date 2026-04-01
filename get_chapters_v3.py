"""
使用JavaScript直接从页面获取章节数据
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
    print("zoolib.cc Chapter Collector v3")
    print("Using JavaScript to extract all chapters")
    print("=" * 60)

    username = os.environ.get('USERNAME', 'Arthur')
    edge_user_data = f"C:\\Users\\{username}\\AppData\\Local\\Microsoft\\Edge\\User Data"

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
    for i in range(60):
        try:
            buttons = page.eles('css:button[data-chapter-id]')
            if buttons and len(buttons) > 0:
                print(f"\nFound chapter buttons!")
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

    time.sleep(2)

    # 保存页面HTML用于分析
    print("\n[Step 5] Saving page HTML for analysis...")
    with open('page_analysis.html', 'w', encoding='utf-8') as f:
        f.write(page.html)
    print("Saved to page_analysis.html")

    # 尝试从页面的React/Vue状态中获取所有章节数据
    print("\n[Step 6] Trying to extract chapters from page state...")

    # 方法1: 查找包含章节数据的script标签
    js_code = '''
    // 尝试从__NUXT__或类似的全局状态获取数据
    var chapters = [];

    // 检查是否有全局状态
    if (window.__NUXT__) {
        console.log('Found __NUXT__');
        var data = JSON.stringify(window.__NUXT__);
        return {type: 'nuxt', data: data};
    }

    if (window.__NEXT_DATA__) {
        console.log('Found __NEXT_DATA__');
        return {type: 'next', data: JSON.stringify(window.__NEXT_DATA__)};
    }

    // 查找所有script标签中的JSON数据
    var scripts = document.querySelectorAll('script');
    for (var i = 0; i < scripts.length; i++) {
        var text = scripts[i].textContent;
        if (text && text.includes('chapter') && text.includes('id')) {
            if (text.length > 1000 && text.length < 1000000) {
                return {type: 'script', data: text};
            }
        }
    }

    // 如果都没找到，返回当前DOM中的章节
    var buttons = document.querySelectorAll('button[data-chapter-id]');
    var result = [];
    buttons.forEach(function(btn) {
        var id = btn.getAttribute('data-chapter-id');
        var titleElem = btn.querySelector('.font-medium');
        var title = titleElem ? titleElem.textContent.trim() : 'Chapter';
        result.push({id: id, title: title});
    });

    return {type: 'dom', data: JSON.stringify(result)};
    '''

    try:
        result = page.run_js(js_code)
        print(f"Result type: {result.get('type', 'unknown')}")

        if result['type'] == 'dom':
            data = json.loads(result['data'])
            print(f"Found {len(data)} chapters from DOM")

        # 保存结果
        with open('page_state.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("Saved state to page_state.json")

    except Exception as e:
        print(f"JS extraction failed: {e}")

    # 方法2: 手动滚动并点击展开
    print("\n[Step 7] Trying manual scroll with click interactions...")

    # 查找可能的"展开全部"按钮
    expand_selectors = [
        'css:button:contains("更多")',
        'css:button:contains("展开")',
        'css:button:contains("全部")',
        'css:a:contains("更多")',
        'css:span:contains("更多")',
    ]

    for sel in expand_selectors:
        try:
            elem = page.ele(sel)
            if elem:
                print(f"Found expand button: {sel}")
                elem.click()
                time.sleep(2)
        except:
            pass

    # 查找虚拟列表容器
    print("\n[Step 8] Looking for virtual list container...")

    # 获取所有div的class
    js_find_container = '''
    var allDivs = document.querySelectorAll('div');
    var candidates = [];
    allDivs.forEach(function(div) {
        var style = window.getComputedStyle(div);
        var overflow = style.overflow + style.overflowY;
        if ((overflow.includes('auto') || overflow.includes('scroll')) && div.scrollHeight > div.clientHeight) {
            var hasChapter = div.querySelector('button[data-chapter-id]');
            if (hasChapter) {
                candidates.push({
                    class: div.className,
                    height: div.scrollHeight,
                    clientHeight: div.clientHeight
                });
            }
        }
    });
    return candidates;
    '''

    try:
        containers = page.run_js(js_find_container)
        print(f"Found {len(containers)} potential scroll containers:")
        for c in containers:
            print(f"  Class: {c.get('class', 'N/A')[:50]}, Height: {c.get('height')}/{c.get('clientHeight')}")
    except Exception as e:
        print(f"Container search failed: {e}")

    # 方法3: 使用找到的容器进行滚动
    print("\n[Step 9] Collecting with targeted scrolling...")

    all_chapters = {}
    scroll_count = 0
    no_change_count = 0
    max_no_change = 100

    # 使用JavaScript滚动
    js_scroll = '''
    var containers = document.querySelectorAll('div');
    var scrolled = false;
    containers.forEach(function(div) {
        var style = window.getComputedStyle(div);
        var overflow = style.overflow + style.overflowY;
        if ((overflow.includes('auto') || overflow.includes('scroll')) && div.scrollHeight > div.clientHeight) {
            var hasChapter = div.querySelector('button[data-chapter-id]');
            if (hasChapter) {
                div.scrollTop += arguments[0];
                scrolled = true;
            }
        }
    });
    return scrolled;
    '''

    last_count = 0

    while no_change_count < max_no_change and scroll_count < 800:
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

                    all_chapters[chapter_id] = {
                        'id': chapter_id,
                        'title': title
                    }
            except:
                continue

        current_count = len(all_chapters)

        if scroll_count % 20 == 0:
            print(f"[{scroll_count:3d}] Total: {current_count} | Stale: {no_change_count}")

        if current_count == last_count:
            no_change_count += 1
        else:
            no_change_count = 0
            last_count = current_count

        # 滚动
        scroll_amount = 500 if scroll_count < 100 else (400 if scroll_count < 300 else 300)

        try:
            # 使用JS滚动容器
            page.run_js(js_scroll, scroll_amount)
        except:
            pass

        time.sleep(0.3)
        scroll_count += 1

    # 保存结果
    chapters = list(all_chapters.values())

    def get_chapter_num(ch):
        match = re.search(r'\d+', ch['title'])
        return int(match.group()) if match else 0

    chapters.sort(key=get_chapter_num)

    print(f"\n{'=' * 60}")
    print(f"Collected {len(chapters)} chapters")
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

    if chapters:
        print(f"\nFirst: {chapters[0]['title']} - Last: {chapters[-1]['title']}")

        nums = [get_chapter_num(ch) for ch in chapters]
        if nums:
            max_num = max(nums)
            print(f"Chapter range: 1 - {max_num}")

    print("\nDone!")


if __name__ == "__main__":
    main()

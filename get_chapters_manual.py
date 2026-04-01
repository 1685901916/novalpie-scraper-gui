"""
完整方案：启动带调试端口的浏览器，手动验证后自动收集章节

使用方法:
1. 运行此脚本
2. 浏览器会打开zoolib.cc
3. 如果出现Cloudflare验证，手动点击完成
4. 页面加载完成后，脚本自动开始收集章节
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
    print("zoolib.cc Chapter Collector")
    print("Manual verification + Auto collection")
    print("=" * 60)

    # 先关闭所有Edge进程
    print("\n[Step 1] Closing existing Edge processes...")
    os.system('taskkill /f /im msedge.exe 2>nul')
    time.sleep(2)

    # 启动带调试端口的Edge
    print("[Step 2] Starting Edge with debug port...")
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    debug_port = 9222
    user_data_dir = os.path.join(os.environ['TEMP'], 'edge_debug_profile')

    cmd = f'"{edge_path}" --remote-debugging-port={debug_port} --user-data-dir="{user_data_dir}" {config.DETAIL_URL}'
    subprocess.Popen(cmd, shell=True)

    print(f"Edge started with debug port {debug_port}")
    print(f"Opening: {config.DETAIL_URL}")

    # 等待浏览器启动
    time.sleep(5)

    # 连接到浏览器
    print("\n[Step 3] Connecting to browser...")
    co = ChromiumOptions()
    co.set_local_port(debug_port)

    try:
        page = ChromiumPage(co)
        print(f"Connected! URL: {page.url}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        print("Please try again or manually complete the process.")
        return

    # 等待Cloudflare验证完成
    print("\n[Step 4] Waiting for Cloudflare verification...")
    print("If a verification challenge appears, please complete it manually.")
    print("Press Enter when the page has fully loaded...\n")

    # 持续检查是否有章节按钮
    found = False
    check_count = 0

    while not found and check_count < 180:
        try:
            buttons = page.eles('css:button[data-chapter-id]')
            if buttons and len(buttons) > 0:
                print(f"\nFound {len(buttons)} chapter buttons!")
                found = True
                break
        except:
            pass

        # 检查页面内容
        html = page.html.lower() if page.html else ""
        if "challenge" in html or "checking" in html or "verify" in html:
            if check_count % 10 == 0:
                print(f"  Cloudflare verification in progress... ({check_count}s)")
        elif check_count % 10 == 0:
            print(f"  Waiting for page... ({check_count}s)")

        time.sleep(1)
        check_count += 1

    if not found:
        print("\nNo chapter buttons found after 180s")
        print("Current URL:", page.url)
        print("Please check the browser manually.")

        with open('debug_manual.html', 'w', encoding='utf-8') as f:
            f.write(page.html)
        print("Saved page to debug_manual.html")
        return

    time.sleep(3)

    # 开始收集章节
    print("\n[Step 5] Starting auto-scroll to collect chapters...")

    all_chapters = {}
    last_count = 0
    no_change_count = 0
    max_no_change = 80
    scroll_count = 0

    while no_change_count < max_no_change and scroll_count < 600:
        delay = 0.3 if scroll_count < 50 else (0.5 if scroll_count < 200 else 0.6)

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
            print(f"[{scroll_count:3d}] Collected {current_count} | New: {new_found} | No change: {no_change_count}")

        if current_count == last_count:
            no_change_count += 1
        else:
            no_change_count = 0
            last_count = current_count

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

    # 排序保存
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
        print("\nFirst 5 chapters:")
        for ch in chapters[:5]:
            print(f"  {ch['title']} - ID: {ch['id']}")

        print("\nLast 5 chapters:")
        for ch in chapters[-5:]:
            print(f"  {ch['title']} - ID: {ch['id']}")

    print("\nDone! Browser will remain open.")
    print("You can close it manually when finished.")


if __name__ == "__main__":
    main()

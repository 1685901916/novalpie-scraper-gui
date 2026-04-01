"""
使用用户现有的Edge浏览器配置文件
保留登录状态，手动完成Cloudflare验证后自动收集章节

注意：运行前请先关闭所有Edge浏览器窗口！
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
    print("Using your existing Edge profile (with login)")
    print("=" * 60)

    # 获取用户名
    username = os.environ.get('USERNAME', 'Arthur')

    # Edge用户配置文件路径
    edge_user_data = f"C:\\Users\\{username}\\AppData\\Local\\Microsoft\\Edge\\User Data"

    if not os.path.exists(edge_user_data):
        print(f"Edge profile not found at: {edge_user_data}")
        return

    print(f"\nUsing Edge profile: {edge_user_data}")
    print("\n*** IMPORTANT: Please close ALL Edge browser windows first! ***")
    print("Press Enter when ready...")

    # 关闭Edge进程
    print("\n[Step 1] Closing Edge processes...")
    os.system('taskkill /f /im msedge.exe 2>nul')
    time.sleep(3)

    # 启动带调试端口的Edge（使用用户配置）
    print("[Step 2] Starting Edge with your profile...")
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    debug_port = 9222

    # 使用用户的实际配置文件
    cmd = f'"{edge_path}" --remote-debugging-port={debug_port} --user-data-dir="{edge_user_data}" {config.DETAIL_URL}'
    subprocess.Popen(cmd, shell=True)

    print(f"Edge started with debug port {debug_port}")
    print(f"Opening: {config.DETAIL_URL}")

    time.sleep(8)

    # 连接到浏览器
    print("\n[Step 3] Connecting to browser...")
    co = ChromiumOptions()
    co.set_local_port(debug_port)

    try:
        page = ChromiumPage(co)
        print(f"Connected! URL: {page.url}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # 等待页面加载
    print("\n[Step 4] Waiting for page to load...")
    print("If Cloudflare verification appears, please complete it manually.")

    found = False
    for i in range(180):
        try:
            buttons = page.eles('css:button[data-chapter-id]')
            if buttons and len(buttons) > 0:
                print(f"\nFound {len(buttons)} chapter buttons!")
                found = True
                break
        except:
            pass

        html = page.html.lower() if page.html else ""
        if "challenge" in html or "checking" in html or "verify" in html:
            if i % 10 == 0:
                print(f"  Cloudflare verification... ({i}s)")
        elif i % 10 == 0:
            print(f"  Waiting... ({i}s)")

        time.sleep(1)

    if not found:
        print("\nNo chapter buttons found")
        print("Current URL:", page.url)
        with open('debug_profile.html', 'w', encoding='utf-8') as f:
            f.write(page.html)
        print("Saved page to debug_profile.html")
        return

    time.sleep(3)

    # 收集章节
    print("\n[Step 5] Collecting chapters...")

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
        print("\nFirst 5 chapters:")
        for ch in chapters[:5]:
            print(f"  {ch['title']} - ID: {ch['id']}")

        print("\nLast 5 chapters:")
        for ch in chapters[-5:]:
            print(f"  {ch['title']} - ID: {ch['id']}")

    print("\nDone! Browser will remain open.")


if __name__ == "__main__":
    main()

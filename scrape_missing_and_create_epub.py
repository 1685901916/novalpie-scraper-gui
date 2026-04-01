"""
1. 爬取缺失的第181、182话
2. 删除第536话
3. 生成完整的535章纯中文EPUB
"""

import json
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from bs4 import BeautifulSoup
from ebooklib import epub
import config

def create_driver():
    """创建浏览器"""
    options = EdgeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

    driver = webdriver.Edge(options=options)
    driver.get(config.BASE_URL)
    for name, value in config.COOKIES.items():
        driver.add_cookie({'name': name, 'value': value})

    return driver


def fetch_chapter(chapter_url, chapter_id, driver):
    """获取单个章节内容"""
    try:
        driver.get(chapter_url)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.chapter-item')))
        time.sleep(1)

        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        chapter_div = soup.find('div', class_='chapter-item')
        if not chapter_div:
            return None

        title = chapter_div.get('data-chapter-title', f'第{chapter_id}章')

        for br in chapter_div.find_all('br'):
            br.replace_with('\n')

        content = chapter_div.get_text()
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(line for line in lines if line)

        return {'id': chapter_id, 'title': title, 'content': content}

    except Exception as e:
        print(f"获取章节失败 ID={chapter_id}: {e}")
        return None


def clean_content(content):
    """清理内容"""
    patterns = [
        r'章节讨论.*?写第一条评论',
        r'章节讨论.*',
        r'写评论.*?写第一条评论',
        r'暂无评论来说说你的看法吧！.*',
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)

    return content.strip()


def extract_chapter_number(title):
    """提取章节号"""
    patterns = [
        r'第(\d+)[话章]',
        r'(\d+)화',
        r'Chapter\s*(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return int(match.group(1))

    return 0


def main():
    print("=" * 60)
    print("补全缺失章节并生成完整EPUB")
    print("=" * 60)

    # 1. 读取现有数据
    print("\n步骤1: 读取现有数据")
    with open('scrape_progress.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    chapters_content = data.get('chapters_content', [])
    print(f"现有章节: {len(chapters_content)}")

    # 2. 爬取缺失的章节
    print("\n步骤2: 爬取缺失的第181、182话")

    missing_chapters = [
        {'id': '6594181', 'url': 'https://novels.whx1216.top/reader?novel=354291&chapter=6594181'},
        {'id': '6594182', 'url': 'https://novels.whx1216.top/reader?novel=354291&chapter=6594182'}
    ]

    driver = None
    new_chapters = []

    try:
        driver = create_driver()
        print("浏览器启动成功")

        for ch in missing_chapters:
            print(f"爬取章节 ID={ch['id']}")
            content = fetch_chapter(ch['url'], ch['id'], driver)

            if content:
                new_chapters.append(content)
                print(f"  Success")
            else:
                print(f"  Failed")

            time.sleep(1)

    finally:
        if driver:
            driver.quit()

    # 3. 合并数据
    print(f"\n步骤3: 合并数据")
    all_chapters = chapters_content + new_chapters
    print(f"合并后总数: {len(all_chapters)}")

    # 4. 处理章节（去重、排序、统一标题）
    print("\n步骤4: 处理章节")

    processed_chapters = {}

    for ch in all_chapters:
        title = ch.get('title', '')
        content = ch.get('content', '')

        chapter_num = extract_chapter_number(title)

        if chapter_num == 0 or chapter_num > 535:  # 排除第536话
            continue

        content = clean_content(content)

        if not content:
            continue

        # 去重：保留内容更长的
        if chapter_num in processed_chapters:
            if len(content) > len(processed_chapters[chapter_num]['content']):
                processed_chapters[chapter_num] = {
                    'number': chapter_num,
                    'title': f'重生路人甲成为天才 第{chapter_num}话',
                    'content': content
                }
        else:
            processed_chapters[chapter_num] = {
                'number': chapter_num,
                'title': f'重生路人甲成为天才 第{chapter_num}话',
                'content': content
            }

    # 排序
    sorted_chapters = sorted(processed_chapters.values(), key=lambda x: x['number'])

    print(f"处理后章节数: {len(sorted_chapters)}")
    print(f"章节号范围: {sorted_chapters[0]['number']} - {sorted_chapters[-1]['number']}")

    # 检查完整性
    chapter_nums = set(ch['number'] for ch in sorted_chapters)
    missing = set(range(1, 536)) - chapter_nums

    if missing:
        print(f"\n警告: 仍缺失 {len(missing)} 章: {sorted(missing)}")
    else:
        print(f"\n完整: 1-535章全部齐全")

    # 5. 生成EPUB
    print("\n步骤5: 生成EPUB")
    output_file = "重生路人甲成为天才_完整535章.epub"

    book = epub.EpubBook()
    book.set_identifier('rebirth_genius_535_complete')
    book.set_title('重生路人甲成为天才')
    book.set_language('zh')
    book.add_author('未知')

    epub_chapters = []
    spine = ['nav']

    for i, ch in enumerate(sorted_chapters, 1):
        chapter = epub.EpubHtml(
            title=ch['title'],
            file_name=f'chapter_{ch["number"]:03d}.xhtml',
            lang='zh'
        )

        paragraphs = ch['content'].split('\n')
        html_content = f'<h1>{ch["title"]}</h1>\n'

        for p in paragraphs:
            p = p.strip()
            if p:
                html_content += f'<p>{p}</p>\n'

        chapter.content = html_content

        book.add_item(chapter)
        epub_chapters.append(chapter)
        spine.append(chapter)

        if (i % 50 == 0) or (i == len(sorted_chapters)):
            print(f"  进度: {i}/{len(sorted_chapters)}")

    book.toc = epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    # CSS样式
    style = '''
    body {
        font-family: "Microsoft YaHei", "SimSun", serif;
        line-height: 1.8;
        margin: 2em;
    }
    h1 {
        text-align: center;
        font-size: 1.5em;
        margin: 2em 0 1em 0;
        font-weight: bold;
    }
    p {
        text-indent: 2em;
        margin: 0.5em 0;
    }
    '''

    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style
    )
    book.add_item(nav_css)

    epub.write_epub(output_file, book, {})

    print(f"\n完成!")
    print(f"文件: {output_file}")
    print(f"章节数: {len(sorted_chapters)}")

    # 显示章节列表
    print("\nFirst 10 chapters:")
    for ch in sorted_chapters[:10]:
        print(f"  Chapter {ch['number']}")

    print("\nLast 10 chapters:")
    for ch in sorted_chapters[-10:]:
        print(f"  Chapter {ch['number']}")

    print("\n" + "=" * 60)
    print(f"总章节数: {len(sorted_chapters)}")
    print(f"输出文件: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()

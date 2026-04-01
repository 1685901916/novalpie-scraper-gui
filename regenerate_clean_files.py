"""
基于现有数据重新生成干净的TXT和EPUB文件
- 清理"章节讨论"等无关内容
- 统一中文标题
- 按章节号排序
"""

import json
import re
from ebooklib import epub

def clean_chapter_content(content):
    """清理章节内容"""
    patterns = [
        r'章节讨论\s*\(\d+\).*?写第一条评论',
        r'章节讨论.*',
        r'写评论.*?写第一条评论',
        r'暂无评论来说说你的看法吧！.*',
        r'写第一条评论.*',
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)

    lines = content.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]

    return '\n'.join(cleaned_lines)


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


def save_to_txt(chapters, filename):
    """保存为TXT格式"""
    print(f"Generating TXT: {filename}")

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("重生路人甲成为天才\n")
        f.write("作者：未知\n\n")

        for ch in chapters:
            f.write(f"\n{ch['title']}\n\n")
            f.write(f"{ch['content']}\n")

        f.write(f"\n\n全文完\n")

    print(f"TXT generated: {filename}")


def save_to_epub(chapters, filename):
    """保存为EPUB格式"""
    print(f"Generating EPUB: {filename}")

    book = epub.EpubBook()
    book.set_identifier('rebirth_genius_clean')
    book.set_title('重生路人甲成为天才')
    book.set_language('zh')
    book.add_author('未知')

    epub_chapters = []
    spine = ['nav']

    for i, ch in enumerate(chapters, 1):
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

        if (i % 50 == 0) or (i == len(chapters)):
            print(f"  Progress: {i}/{len(chapters)}")

    book.toc = epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

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

    epub.write_epub(filename, book, {})

    print(f"EPUB generated: {filename}")


print("=" * 60)
print("Regenerate Clean TXT and EPUB Files")
print("=" * 60)

# 读取数据
print("\nStep 1: Load data")
with open('scrape_progress.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

chapters_content = data.get('chapters_content', [])
print(f"Total chapters: {len(chapters_content)}")

# 处理章节
print("\nStep 2: Process and clean chapters")
processed_chapters = {}

for ch in chapters_content:
    title = ch.get('title', '')
    content = ch.get('content', '')

    chapter_num = extract_chapter_number(title)

    if chapter_num == 0:
        continue

    # 清理内容
    content = clean_chapter_content(content)

    if not content:
        continue

    # 统一标题
    standard_title = f'重生路人甲成为天才 第{chapter_num}话'

    # 去重
    if chapter_num in processed_chapters:
        if len(content) > len(processed_chapters[chapter_num]['content']):
            processed_chapters[chapter_num] = {
                'number': chapter_num,
                'title': standard_title,
                'content': content
            }
    else:
        processed_chapters[chapter_num] = {
            'number': chapter_num,
            'title': standard_title,
            'content': content
        }

# 排序
sorted_chapters = sorted(processed_chapters.values(), key=lambda x: x['number'])

print(f"Processed chapters: {len(sorted_chapters)}")
print(f"Chapter range: {sorted_chapters[0]['number']} - {sorted_chapters[-1]['number']}")

# 检查完整性
chapter_nums = set(ch['number'] for ch in sorted_chapters)
max_chapter = max(chapter_nums)
missing = sorted(set(range(1, max_chapter + 1)) - chapter_nums)

if missing:
    print(f"\nWarning: Missing {len(missing)} chapters")
    if len(missing) <= 20:
        print(f"Missing: {missing}")
else:
    print(f"\nComplete: All chapters present")

# 生成文件
print("\nStep 3: Generate output files")

txt_filename = f"重生路人甲成为天才_{len(sorted_chapters)}章.txt"
epub_filename = f"重生路人甲成为天才_{len(sorted_chapters)}章.epub"

save_to_txt(sorted_chapters, txt_filename)
save_to_epub(sorted_chapters, epub_filename)

# 总结
print("\n" + "=" * 60)
print("Done!")
print("=" * 60)
print(f"Total chapters: {len(sorted_chapters)}")
print(f"TXT file: {txt_filename}")
print(f"EPUB file: {epub_filename}")
if missing:
    print(f"Missing chapters: {len(missing)}")
print("=" * 60)

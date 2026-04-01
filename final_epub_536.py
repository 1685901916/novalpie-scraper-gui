"""
最终版本：生成完整536章纯中文EPUB
- 包含第1-536话
- 统一所有标题为中文格式
- 按章节号排序
- 清理讨论区文字
"""

import json
import re
from ebooklib import epub

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


print("=" * 60)
print("Generate Complete 536-Chapter EPUB")
print("=" * 60)

# 读取数据
print("\nStep 1: Load data")
with open('scrape_progress.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

chapters_content = data.get('chapters_content', [])
print(f"Total chapters: {len(chapters_content)}")

# 处理章节
print("\nStep 2: Process chapters")
processed_chapters = {}

for ch in chapters_content:
    title = ch.get('title', '')
    content = ch.get('content', '')

    # 提取章节号
    chapter_num = extract_chapter_number(title)

    # 保留1-536章
    if chapter_num == 0 or chapter_num > 536:
        continue

    # 清理内容
    content = clean_content(content)

    if not content:
        continue

    # 统一标题为中文格式
    standard_title = f'重生路人甲成为天才 第{chapter_num}话'

    # 去重：保留内容更长的版本
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

# 按章节号排序
sorted_chapters = sorted(processed_chapters.values(), key=lambda x: x['number'])

print(f"Processed chapters: {len(sorted_chapters)}")
print(f"Chapter range: {sorted_chapters[0]['number']} - {sorted_chapters[-1]['number']}")

# 检查完整性
chapter_nums = set(ch['number'] for ch in sorted_chapters)
missing = sorted(set(range(1, 537)) - chapter_nums)

if missing:
    print(f"\nWarning: Missing {len(missing)} chapters")
    if len(missing) <= 20:
        print(f"Missing: {missing}")
else:
    print(f"\nComplete: All 536 chapters present")

# 生成EPUB
print("\nStep 3: Create EPUB")
output_file = "重生路人甲成为天才_完整536章.epub"

book = epub.EpubBook()
book.set_identifier('rebirth_genius_536_complete')
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

    # 生成HTML内容
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
        print(f"  Progress: {i}/{len(sorted_chapters)}")

# 添加目录和导航
book.toc = epub_chapters
book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())
book.spine = spine

# 添加CSS样式
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

# 写入文件
epub.write_epub(output_file, book, {})

print(f"\nDone!")
print(f"File: {output_file}")
print(f"Chapters: {len(sorted_chapters)}")

# 显示章节范围
print(f"\nFirst 10 chapters:")
for ch in sorted_chapters[:10]:
    print(f"  Chapter {ch['number']}")

print(f"\nLast 10 chapters:")
for ch in sorted_chapters[-10:]:
    print(f"  Chapter {ch['number']}")

print("\n" + "=" * 60)
print(f"Total: {len(sorted_chapters)} chapters")
print(f"Output: {output_file}")
print("=" * 60)

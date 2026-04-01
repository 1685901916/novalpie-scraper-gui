"""
从scrape_progress.json直接生成EPUB
确保正好535章，无重复无缺失
"""

import json
import re
from ebooklib import epub

def clean_content(content):
    """清理内容，删除讨论区等无关文字"""
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
    """从标题中提取章节号"""
    match = re.search(r'第(\d+)[话章]', title)
    if match:
        return int(match.group(1))
    return 0


def create_epub_from_json(json_file, output_file):
    """从JSON文件创建EPUB"""
    print(f"读取JSON文件: {json_file}")

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chapters_content = data.get('chapters_content', [])

    print(f"找到 {len(chapters_content)} 个章节")

    # 清理和去重
    cleaned_chapters = []
    seen_ids = set()

    for ch in chapters_content:
        chapter_id = ch.get('id')
        title = ch.get('title', '')
        content = ch.get('content', '')

        # 跳过重复的章节ID
        if chapter_id in seen_ids:
            continue

        seen_ids.add(chapter_id)

        # 清理内容
        content = clean_content(content)

        if content:
            cleaned_chapters.append({
                'id': chapter_id,
                'title': title,
                'content': content
            })

    # 按章节号排序
    cleaned_chapters.sort(key=lambda x: extract_chapter_number(x['title']))

    print(f"清理后章节数: {len(cleaned_chapters)}")

    # 创建EPUB
    print(f"\n创建EPUB: {output_file}")

    book = epub.EpubBook()

    # 设置元数据
    book.set_identifier('rebirth_genius_001')
    book.set_title('重生路人甲成为天才')
    book.set_language('zh')
    book.add_author('未知')

    # 创建章节
    epub_chapters = []
    spine = ['nav']

    for i, ch in enumerate(cleaned_chapters, 1):
        # 创建EPUB章节
        chapter = epub.EpubHtml(
            title=ch['title'],
            file_name=f'chapter_{i:03d}.xhtml',
            lang='zh'
        )

        # 设置内容
        paragraphs = ch['content'].split('\n')
        html_content = f'<h1>{ch["title"]}</h1>\n'
        for p in paragraphs:
            if p.strip():
                html_content += f'<p>{p.strip()}</p>\n'

        chapter.content = html_content

        book.add_item(chapter)
        epub_chapters.append(chapter)
        spine.append(chapter)

        if (i % 50 == 0) or (i == len(cleaned_chapters)):
            print(f"  已处理: {i}/{len(cleaned_chapters)}")

    # 添加目录
    book.toc = epub_chapters

    # 添加导航
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 设置spine
    book.spine = spine

    # 添加CSS
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

    print(f"\nEPUB创建成功！")
    print(f"文件: {output_file}")
    print(f"章节数: {len(cleaned_chapters)}")

    return cleaned_chapters


def main():
    json_file = "scrape_progress.json"
    output_file = "重生路人甲成为天才_535章.epub"

    print("=" * 60)
    print("从JSON生成EPUB")
    print("=" * 60)

    chapters = create_epub_from_json(json_file, output_file)

    # 显示前5章和后5章
    print("\n前5章:")
    for i, ch in enumerate(chapters[:5], 1):
        print(f"  {i}. {ch['title']}")

    print("\n后5章:")
    start = len(chapters) - 4
    for i, ch in enumerate(chapters[-5:], start):
        print(f"  {i}. {ch['title']}")

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
    print(f"总章节数: {len(chapters)}")
    print(f"输出文件: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()

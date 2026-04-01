"""
生成纯中文、顺序正确的EPUB
1. 所有标题统一为：重生路人甲成为天才 第X话
2. 按章节号1-535排序
3. 删除讨论区文字
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
    """从标题中提取章节号"""
    # 匹配各种格式：第X话、第X章、Xhwa等
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


def create_clean_epub(json_file, output_file):
    """创建干净的EPUB"""
    print("=" * 60)
    print("生成纯中文EPUB")
    print("=" * 60)

    # 读取数据
    print(f"\n读取: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chapters_content = data.get('chapters_content', [])
    print(f"原始章节数: {len(chapters_content)}")

    # 处理章节
    processed_chapters = {}

    for ch in chapters_content:
        title = ch.get('title', '')
        content = ch.get('content', '')

        # 提取章节号
        chapter_num = extract_chapter_number(title)

        if chapter_num == 0:
            continue

        # 清理内容
        content = clean_content(content)

        if not content:
            continue

        # 如果该章节号已存在，保留内容更长的那个
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

    # 按章节号排序
    sorted_chapters = sorted(processed_chapters.values(), key=lambda x: x['number'])

    print(f"处理后章节数: {len(sorted_chapters)}")
    print(f"章节号范围: {sorted_chapters[0]['number']} - {sorted_chapters[-1]['number']}")

    # 检查缺失章节
    chapter_nums = set(ch['number'] for ch in sorted_chapters)
    expected = set(range(1, 536))
    missing = expected - chapter_nums

    if missing:
        print(f"\n警告：缺失 {len(missing)} 章")
        if len(missing) <= 20:
            print(f"缺失章节: {sorted(missing)}")
    else:
        print("\n✓ 章节完整，无缺失")

    # 创建EPUB
    print(f"\n创建EPUB: {output_file}")

    book = epub.EpubBook()
    book.set_identifier('rebirth_genius_535')
    book.set_title('重生路人甲成为天才')
    book.set_language('zh')
    book.add_author('未知')

    epub_chapters = []
    spine = ['nav']

    for i, ch in enumerate(sorted_chapters, 1):
        # 创建章节
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
            print(f"  进度: {i}/{len(sorted_chapters)}")

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

    print(f"\n完成！")
    print(f"文件: {output_file}")
    print(f"章节数: {len(sorted_chapters)}")

    return sorted_chapters


def main():
    json_file = "scrape_progress.json"
    output_file = "重生路人甲成为天才_纯中文.epub"

    chapters = create_clean_epub(json_file, output_file)

    # 显示前10章和后10章
    print("\n" + "=" * 60)
    print("前10章:")
    for ch in chapters[:10]:
        print(f"  第{ch['number']}话")

    print("\n后10章:")
    for ch in chapters[-10:]:
        print(f"  第{ch['number']}话")

    print("\n" + "=" * 60)
    print(f"总章节数: {len(chapters)}")
    print(f"输出文件: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()

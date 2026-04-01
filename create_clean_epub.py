"""
清理TXT内容并转换为EPUB格式
1. 删除每章末尾的"章节讨论"等无关文字
2. 保留原始章节标题（第X话）
3. 生成标准EPUB格式
"""

import re
from ebooklib import epub
import os

def clean_chapter_content(content):
    """清理章节内容，删除末尾的讨论区文字"""
    # 删除"章节讨论"及其后面的所有内容
    patterns = [
        r'章节讨论.*?写第一条评论',
        r'章节讨论.*',
        r'写评论.*?写第一条评论',
        r'暂无评论来说说你的看法吧！.*',
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)

    # 删除末尾多余的空行
    content = content.rstrip()

    return content


def parse_txt_to_chapters(txt_file):
    """解析TXT文件，提取章节"""
    print(f"读取文件: {txt_file}")

    with open(txt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按分隔线分割章节
    blocks = re.split(r'\n={40,}\n', content)

    chapters = []

    for block in blocks:
        block = block.strip()
        if not block or block == '重生路人甲成为天才':
            continue

        lines = block.split('\n')

        # 查找章节标题（第X话格式）
        title = None
        content_start = 0

        for i, line in enumerate(lines[:5]):
            line = line.strip()
            # 匹配"第X话"或"第X章"格式
            if re.match(r'^(重生路人甲成为天才\s+)?第\d+[话章]', line):
                title = line
                # 如果标题包含书名，只保留"第X话"部分
                title = re.sub(r'^重生路人甲成为天才\s+', '', title)
                content_start = i + 1
                break

        if not title:
            continue

        # 获取章节内容
        chapter_lines = []
        for line in lines[content_start:]:
            line = line.strip()
            # 跳过重复的标题和分隔线
            if line and line != title and not re.match(r'^=+$', line):
                chapter_lines.append(line)

        if chapter_lines:
            # 合并内容
            chapter_content = '\n'.join(chapter_lines)

            # 清理内容（删除讨论区文字）
            chapter_content = clean_chapter_content(chapter_content)

            if chapter_content.strip():
                chapters.append({
                    'title': title,
                    'content': chapter_content
                })

    return chapters


def create_epub(chapters, output_file):
    """创建EPUB文件"""
    print(f"\n创建EPUB文件: {output_file}")

    # 创建EPUB对象
    book = epub.EpubBook()

    # 设置元数据
    book.set_identifier('rebirth_genius_001')
    book.set_title('重生路人甲成为天才')
    book.set_language('zh')
    book.add_author('未知')

    # 创建章节列表
    epub_chapters = []
    spine = ['nav']

    print(f"处理 {len(chapters)} 个章节...")

    for i, ch in enumerate(chapters, 1):
        # 创建EPUB章节
        chapter = epub.EpubHtml(
            title=ch['title'],
            file_name=f'chapter_{i:03d}.xhtml',
            lang='zh'
        )

        # 设置章节内容（使用段落格式）
        paragraphs = ch['content'].split('\n')
        html_content = f'<h1>{ch["title"]}</h1>\n'
        for p in paragraphs:
            if p.strip():
                html_content += f'<p>{p}</p>\n'

        chapter.content = html_content

        # 添加到书籍
        book.add_item(chapter)
        epub_chapters.append(chapter)
        spine.append(chapter)

        if (i % 50 == 0) or (i == len(chapters)):
            print(f"  已处理: {i}/{len(chapters)}")

    # 添加目录
    book.toc = epub_chapters

    # 添加导航文件
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 设置spine
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

    # 写入EPUB文件
    epub.write_epub(output_file, book, {})

    print(f"\n✓ EPUB创建成功！")
    print(f"✓ 文件: {output_file}")
    print(f"✓ 章节数: {len(chapters)}")


def main():
    input_file = "重生路人甲成为天才_完整版_535章.txt"
    output_file = "重生路人甲成为天才.epub"

    print("=" * 60)
    print("TXT转EPUB工具")
    print("=" * 60)

    # 检查输入文件
    if not os.path.exists(input_file):
        print(f"错误：找不到文件 {input_file}")
        return

    # 解析章节
    chapters = parse_txt_to_chapters(input_file)

    print(f"\n提取到 {len(chapters)} 个章节")

    if len(chapters) == 0:
        print("错误：没有找到任何章节！")
        return

    # 显示前3章和后3章
    print("\n前3章:")
    for i, ch in enumerate(chapters[:3], 1):
        print(f"  {i}. {ch['title']}")

    print("\n后3章:")
    for i, ch in enumerate(chapters[-3:], len(chapters)-2):
        print(f"  {i}. {ch['title']}")

    # 创建EPUB
    create_epub(chapters, output_file)

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print(f"章节总数: {len(chapters)}")
    print("=" * 60)


if __name__ == "__main__":
    main()

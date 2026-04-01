"""
优化TXT文件格式，使阅读软件能够识别目录
支持多种阅读器的目录识别格式
"""

import json
import re

def optimize_txt_format(input_file, output_file):
    """
    优化TXT格式，使用阅读软件通用的目录识别格式

    常见阅读器目录识别规则：
    1. 章节标题独占一行
    2. 标题前后有空行
    3. 标题格式：第X章/第X话/Chapter X 等
    4. 避免重复标题
    """

    print("读取原文件...")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按分隔线分割章节
    chapters = re.split(r'\n={40,}\n', content)

    print(f"检测到 {len(chapters)} 个章节块")

    # 处理章节
    formatted_chapters = []
    chapter_count = 0

    for block in chapters:
        block = block.strip()
        if not block or block == '重生路人甲成为天才':
            continue

        lines = block.split('\n')

        # 查找章节标题（通常在前几行）
        title = None
        content_start = 0

        for i, line in enumerate(lines[:5]):  # 只检查前5行
            line = line.strip()
            # 匹配章节标题格式
            if re.search(r'第\d+[话章]|Chapter\s*\d+|\d+화', line):
                title = line
                content_start = i + 1
                break

        if not title:
            continue

        # 获取章节内容（跳过重复的标题）
        chapter_content = []
        for line in lines[content_start:]:
            line = line.strip()
            # 跳过重复的标题行和分隔线
            if line and line != title and not re.match(r'^=+$', line):
                chapter_content.append(line)

        if chapter_content:
            chapter_count += 1
            formatted_chapters.append({
                'title': title,
                'content': '\n'.join(chapter_content)
            })

    print(f"成功处理 {chapter_count} 章")

    # 写入优化后的文件
    print("生成优化后的TXT文件...")
    with open(output_file, 'w', encoding='utf-8') as f:
        # 书名
        f.write("重生路人甲成为天才\n\n\n")

        # 写入章节（使用阅读器友好的格式）
        for i, ch in enumerate(formatted_chapters, 1):
            # 章节标题格式：
            # - 前后各有2个空行
            # - 标题独占一行
            # - 不使用分隔线（很多阅读器不识别）

            f.write(f"\n\n{ch['title']}\n\n")
            f.write(f"{ch['content']}\n")

        # 结尾
        f.write(f"\n\n\n全文完\n总计：{chapter_count} 章\n")

    print(f"✓ 优化完成！")
    print(f"✓ 输出文件：{output_file}")
    print(f"✓ 总章节数：{chapter_count}")

    return chapter_count


def main():
    input_file = "重生路人甲成为天才_完整版_535章.txt"
    output_file = "重生路人甲成为天才_优化版.txt"

    try:
        chapter_count = optimize_txt_format(input_file, output_file)

        print("\n" + "=" * 60)
        print("格式优化说明：")
        print("=" * 60)
        print("1. 移除了所有分隔线（=====）")
        print("2. 章节标题独占一行，前后有空行")
        print("3. 移除了重复的章节标题")
        print("4. 统一了章节间距")
        print("5. 符合主流阅读软件的目录识别规则")
        print("=" * 60)
        print("\n支持的阅读软件：")
        print("- 多看阅读")
        print("- 掌阅iReader")
        print("- 微信读书")
        print("- Kindle")
        print("- 静读天下")
        print("- 其他支持TXT目录识别的阅读器")
        print("=" * 60)

    except FileNotFoundError:
        print(f"错误：找不到文件 {input_file}")
    except Exception as e:
        print(f"错误：{e}")


if __name__ == "__main__":
    main()

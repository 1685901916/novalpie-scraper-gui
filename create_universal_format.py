"""
创建通用格式的TXT文件，支持更多阅读器的目录识别
"""

import re

def create_universal_format(input_file, output_file):
    """
    创建通用格式，支持多种阅读器：
    1. 章节标题格式：第X章 标题
    2. 标题前有空行，后有空行
    3. 不使用任何特殊符号
    """

    print("读取文件...")
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

        # 查找章节标题
        title = None
        content_start = 0

        for i, line in enumerate(lines[:5]):
            line = line.strip()
            # 匹配章节标题格式
            if re.search(r'第\d+[话章]|Chapter\s*\d+|\d+화', line):
                title = line
                content_start = i + 1
                break

        if not title:
            continue

        # 获取章节内容
        chapter_content = []
        for line in lines[content_start:]:
            line = line.strip()
            if line and line != title and not re.match(r'^=+$', line):
                chapter_content.append(line)

        if chapter_content:
            chapter_count += 1

            # 标准化章节标题格式
            # 提取章节号
            match = re.search(r'(\d+)[话章]', title)
            if match:
                chapter_num = match.group(1)
                standard_title = f"第{chapter_num}章"
            else:
                standard_title = title

            formatted_chapters.append({
                'title': standard_title,
                'content': '\n'.join(chapter_content)
            })

    print(f"成功处理 {chapter_count} 章")

    # 写入文件
    print("生成文件...")
    with open(output_file, 'w', encoding='utf-8') as f:
        # 书名
        f.write("重生路人甲成为天才\n")
        f.write("作者：未知\n\n")

        # 写入章节
        for ch in formatted_chapters:
            # 格式：空行 + 章节标题 + 空行 + 内容
            f.write(f"\n{ch['title']}\n\n")
            f.write(f"{ch['content']}\n")

        # 结尾
        f.write(f"\n\n全文完\n")

    print(f"完成！共 {chapter_count} 章")
    return chapter_count


def main():
    input_file = "重生路人甲成为天才_完整版_535章.txt"
    output_file = "重生路人甲成为天才_通用版.txt"

    try:
        chapter_count = create_universal_format(input_file, output_file)

        print("\n" + "=" * 60)
        print("格式说明：")
        print("=" * 60)
        print("1. 章节标题统一为：第X章")
        print("2. 标题前后各有一个空行")
        print("3. 无任何特殊符号和分隔线")
        print("4. 符合TXT标准格式")
        print("=" * 60)
        print("\n测试建议：")
        print("1. 用阅读软件打开文件")
        print("2. 查看是否能自动识别目录")
        print("3. 如果还不行，可以尝试：")
        print("   - 在阅读器设置中调整目录识别规则")
        print("   - 使用'第.*章'作为章节匹配规则")
        print("=" * 60)

    except FileNotFoundError:
        print(f"错误：找不到文件 {input_file}")
    except Exception as e:
        print(f"错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

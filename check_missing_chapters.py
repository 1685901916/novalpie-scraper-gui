"""
检查缺失的章节，并分析章节分布
"""

import json
import re

# 读取数据
with open('scrape_progress.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

chapters_content = data.get('chapters_content', [])

print(f"总章节数: {len(chapters_content)}")

# 提取所有章节号
def extract_chapter_number(title):
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

chapter_map = {}
for ch in chapters_content:
    title = ch.get('title', '')
    num = extract_chapter_number(title)
    if num > 0:
        if num not in chapter_map:
            chapter_map[num] = []
        chapter_map[num].append({
            'title': title,
            'content_length': len(ch.get('content', ''))
        })

print(f"唯一章节号数量: {len(chapter_map)}")
print(f"章节号范围: {min(chapter_map.keys())} - {max(chapter_map.keys())}")

# 检查1-535范围内的缺失
missing_in_535 = []
for i in range(1, 536):
    if i not in chapter_map:
        missing_in_535.append(i)

print(f"\n1-535范围内缺失: {len(missing_in_535)}章")
if missing_in_535:
    print(f"缺失章节: {missing_in_535}")

# 检查是否有536
if 536 in chapter_map:
    print(f"\n发现第536话:")
    for item in chapter_map[536]:
        print(f"  标题: {item['title']}")
        print(f"  内容长度: {item['content_length']}字符")

# 检查重复章节
duplicates = {k: v for k, v in chapter_map.items() if len(v) > 1}
if duplicates:
    print(f"\n发现重复章节: {len(duplicates)}个")
    for num in sorted(duplicates.keys())[:5]:
        print(f"  第{num}话: {len(duplicates[num])}个版本")

# 统计
print(f"\n统计:")
print(f"  原始数据: {len(chapters_content)}章")
print(f"  去重后: {len(chapter_map)}章")
print(f"  1-535范围: {535 - len(missing_in_535)}章")
print(f"  缺失: {len(missing_in_535)}章")

# 建议
print(f"\n建议:")
if 536 in chapter_map and len(missing_in_535) > 0:
    print(f"  可能第536话是误标记的，实际应该是缺失章节之一")
if len(missing_in_535) == 0:
    print(f"  1-535章节完整，可以生成535章的EPUB")
else:
    print(f"  需要重新爬取缺失的章节: {missing_in_535}")

"""
检查第181、182话的爬取结果
"""

import json
import re

# 读取数据
with open('scrape_progress.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

chapters_content = data.get('chapters_content', [])

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

# 查找所有包含181或182的章节
print("查找第181、182话...")
print("=" * 60)

for i, ch in enumerate(chapters_content):
    title = ch.get('title', '')
    content = ch.get('content', '')
    chapter_id = ch.get('id', '')

    num = extract_chapter_number(title)

    if num == 181 or num == 182 or '181' in chapter_id or '182' in chapter_id:
        print(f"\n找到章节 #{i+1}:")
        print(f"  ID: {chapter_id}")
        print(f"  标题: {title}")
        print(f"  提取的章节号: {num}")
        print(f"  内容长度: {len(content)}字符")
        print(f"  内容前100字: {content[:100]}")

print("\n" + "=" * 60)

# 统计所有章节号
all_nums = {}
for ch in chapters_content:
    num = extract_chapter_number(ch.get('title', ''))
    if num > 0:
        all_nums[num] = all_nums.get(num, 0) + 1

print(f"\n章节号统计:")
print(f"  总唯一章节号: {len(all_nums)}")
print(f"  范围: {min(all_nums.keys())} - {max(all_nums.keys())}")

# 检查181、182
if 181 in all_nums:
    print(f"  第181话: 存在 ({all_nums[181]}个)")
else:
    print(f"  第181话: 不存在")

if 182 in all_nums:
    print(f"  第182话: 存在 ({all_nums[182]}个)")
else:
    print(f"  第182话: 不存在")

# 检查缺失
missing = []
for i in range(1, 536):
    if i not in all_nums:
        missing.append(i)

print(f"\n缺失章节 ({len(missing)}个): {missing}")

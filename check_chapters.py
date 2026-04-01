import re

# 读取文件
with open('重生路人甲成为天才_完整版_535章.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# 按分隔线分割
blocks = re.split(r'\n={40,}\n', content)

chapters = {}
chapter_list = []

for block in blocks:
    block = block.strip()
    if not block:
        continue

    # 查找章节标题
    match = re.search(r'^(重生路人甲成为天才\s+)?第(\d+)[话章]', block, re.MULTILINE)
    if match:
        num = int(match.group(2))
        if num not in chapters:
            chapters[num] = []
        chapters[num].append(block[:100])  # 保存前100字符用于对比

print(f"总章节块数: {len(blocks)}")
print(f"找到的唯一章节号: {len(chapters)}")
print(f"章节号范围: {min(chapters.keys())} - {max(chapters.keys())}")

# 检查重复
duplicates = {k: v for k, v in chapters.items() if len(v) > 1}
if duplicates:
    print(f"\n发现重复章节: {len(duplicates)}个")
    for num in sorted(duplicates.keys())[:5]:
        print(f"  第{num}话: {len(duplicates[num])}次")
else:
    print("\n无重复章节")

# 检查缺失
all_nums = set(chapters.keys())
expected = set(range(1, 536))
missing = expected - all_nums
if missing:
    print(f"\n缺失章节: {sorted(missing)}")
else:
    print("\n章节连续，无缺失")

# 检查是否有536章
if 536 in chapters:
    print("\n注意: 发现第536话，但文件名显示应该是535章")

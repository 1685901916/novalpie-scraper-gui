"""
测试清理函数是否能正确过滤"章节讨论"等内容
"""

import re

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

    # 删除多余的空行
    lines = content.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]

    return '\n'.join(cleaned_lines)


# 测试用例
test_content = """这是章节的正文内容。
主角做了一些事情。
故事继续发展。

章节讨论 (0)第534章·重生路人甲成为天才 第535话 写评论 暂无评论来说说你的看法吧！ 写第一条评论

这部分不应该出现。
"""

print("原始内容:")
print("=" * 60)
print(test_content)
print("=" * 60)

cleaned = clean_chapter_content(test_content)

print("\n清理后内容:")
print("=" * 60)
print(cleaned)
print("=" * 60)

# 检查是否成功删除
if "章节讨论" in cleaned:
    print("\n❌ 失败：仍包含'章节讨论'")
else:
    print("\n✅ 成功：已删除'章节讨论'相关内容")

if "写评论" in cleaned:
    print("❌ 失败：仍包含'写评论'")
else:
    print("✅ 成功：已删除'写评论'相关内容")

import json
import config

# 读取章节数据
with open('all_chapters.json', 'r', encoding='utf-8') as f:
    chapters = json.load(f)

print(f"总章节数: {len(chapters)}")
print(f"更新前有URL的章节: {sum(1 for c in chapters if c.get('url'))}")

# 为每个章节添加URL
for chapter in chapters:
    if 'id' in chapter:
        chapter['url'] = f"{config.READER_URL}?novel={config.NOVEL_ID}&chapter={chapter['id']}"

print(f"更新后有URL的章节: {sum(1 for c in chapters if c.get('url'))}")

# 保存更新后的数据
with open('all_chapters.json', 'w', encoding='utf-8') as f:
    json.dump(chapters, f, ensure_ascii=False, indent=2)

print("✅ URL添加完成！")

# 显示前3章作为示例
print("\n前3章示例:")
for i, ch in enumerate(chapters[:3], 1):
    print(f"{i}. ID: {ch.get('id')}, URL: {ch.get('url')}")

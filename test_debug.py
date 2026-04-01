"""
调试脚本 - 检查网页内容和选择器
"""

import requests
from bs4 import BeautifulSoup
import config

print("正在请求详情页...")
response = requests.get(
    config.DETAIL_URL,
    cookies=config.COOKIES,
    headers=config.HEADERS,
    timeout=config.TIMEOUT
)

print(f"状态码: {response.status_code}")
print(f"响应长度: {len(response.text)} 字符")

# 保存HTML到文件以便检查
with open('debug_detail_page.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
print("已保存HTML到 debug_detail_page.html")

soup = BeautifulSoup(response.text, 'lxml')

# 尝试多种方式查找章节
print("\n=== 查找章节按钮 ===")
buttons = soup.find_all('button', {'data-chapter-id': True})
print(f"找到 data-chapter-id 按钮: {len(buttons)} 个")

if buttons:
    print("\n前3个按钮示例:")
    for i, btn in enumerate(buttons[:3]):
        print(f"\n按钮 {i+1}:")
        print(f"  data-chapter-id: {btn.get('data-chapter-id')}")
        print(f"  文本内容: {btn.get_text(strip=True)[:50]}")
else:
    print("\n未找到按钮，尝试其他方式...")

    # 尝试查找所有button
    all_buttons = soup.find_all('button')
    print(f"找到所有button标签: {len(all_buttons)} 个")

    if all_buttons:
        print("\n前3个button示例:")
        for i, btn in enumerate(all_buttons[:3]):
            print(f"\nButton {i+1}:")
            print(f"  属性: {btn.attrs}")
            print(f"  文本: {btn.get_text(strip=True)[:50]}")

    # 查找包含章节的div
    chapter_divs = soup.find_all('div', class_=lambda x: x and 'chapter' in x.lower())
    print(f"\n找到包含'chapter'的div: {len(chapter_divs)} 个")

print("\n=== 检查完成 ===")

"""
直接测试可能的API端点
"""

import requests
import json
import config

print("测试可能的章节列表API端点...\n")

# 可能的API端点列表
api_endpoints = [
    # 标准REST API格式
    f"https://novelsapi.whx1216.top/api/novels/{config.NOVEL_ID}/chapters",
    f"https://novelsapi.whx1216.top/api/novels/{config.NOVEL_ID}/chapters?limit=1000",
    f"https://novelsapi.whx1216.top/api/novels/{config.NOVEL_ID}",
    f"https://novelsapi.whx1216.top/api/v1/novels/{config.NOVEL_ID}/chapters",

    # GraphQL可能性
    f"https://novelsapi.whx1216.top/graphql",

    # 其他可能的格式
    f"https://novelsapi.whx1216.top/novels/{config.NOVEL_ID}/chapters",
    f"https://novels.whx1216.top/api/novels/{config.NOVEL_ID}/chapters",
    f"https://novels.whx1216.top/api/chapters?novel_id={config.NOVEL_ID}",
]

headers = {
    **config.HEADERS,
    'Accept': 'application/json, text/plain, */*',
}

for i, url in enumerate(api_endpoints, 1):
    print(f"[{i}/{len(api_endpoints)}] 测试: {url}")

    try:
        response = requests.get(
            url,
            cookies=config.COOKIES,
            headers=headers,
            timeout=10
        )

        print(f"  状态码: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  ✓ 返回JSON数据!")
                print(f"  数据类型: {type(data)}")

                if isinstance(data, dict):
                    print(f"  键: {list(data.keys())[:10]}")

                    # 检查是否包含章节信息
                    if 'chapters' in data:
                        print(f"  ✓✓ 找到chapters字段! 章节数: {len(data['chapters'])}")
                    elif 'data' in data and isinstance(data['data'], dict) and 'chapters' in data['data']:
                        print(f"  ✓✓ 找到data.chapters字段! 章节数: {len(data['data']['chapters'])}")

                elif isinstance(data, list):
                    print(f"  列表长度: {len(data)}")
                    if data:
                        print(f"  第一项: {list(data[0].keys()) if isinstance(data[0], dict) else data[0]}")

                # 保存响应
                filename = f'api_test_{i}.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  已保存到: {filename}")

            except json.JSONDecodeError:
                print(f"  ✗ 不是有效的JSON")
                print(f"  内容预览: {response.text[:200]}")
        else:
            print(f"  ✗ 请求失败")

    except requests.RequestException as e:
        print(f"  ✗ 请求异常: {e}")

    print()

print("\n" + "="*60)
print("提示：如果没有找到API，可能需要：")
print("1. 在浏览器中打开开发者工具(F12)")
print("2. 切换到Network标签")
print("3. 刷新详情页")
print("4. 查找包含'chapter'或'novel'的XHR/Fetch请求")
print("5. 复制该请求的URL并告诉我")
print("="*60)

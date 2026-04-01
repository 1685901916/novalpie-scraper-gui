"""
测试API端点
"""

import requests
import json
import config

# 测试不同的API端点
api_endpoints = [
    f"https://novelsapi.whx1216.top/api/novels/{config.NOVEL_ID}/chapters",
    f"https://novelsapi.whx1216.top/api/novels/{config.NOVEL_ID}",
    f"https://novelsapi.whx1216.top/api/novel/{config.NOVEL_ID}/chapters",
    f"https://novelsapi.whx1216.top/api/chapter/list?novel_id={config.NOVEL_ID}",
]

print("测试API端点...\n")

for api_url in api_endpoints:
    print(f"尝试: {api_url}")
    try:
        response = requests.get(
            api_url,
            cookies=config.COOKIES,
            headers=config.HEADERS,
            timeout=10
        )
        print(f"  状态码: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  返回数据类型: {type(data)}")
                if isinstance(data, dict):
                    print(f"  数据键: {list(data.keys())[:10]}")
                elif isinstance(data, list):
                    print(f"  列表长度: {len(data)}")
                    if data:
                        print(f"  第一项: {data[0]}")

                # 保存成功的响应
                with open(f'api_response_{api_endpoints.index(api_url)}.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  ✓ 已保存响应到文件")
            except:
                print(f"  响应内容: {response.text[:200]}")
        else:
            print(f"  错误: {response.text[:200]}")
    except Exception as e:
        print(f"  异常: {e}")
    print()

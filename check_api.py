"""
直接通过API获取章节列表
"""

import requests
import json
import config

def get_chapters_via_api():
    print("=" * 60)
    print("Trying to get chapters via API")
    print("=" * 60)

    # 构建cookies
    cookies = {k: v for k, v in config.COOKIES.items()}

    headers = config.HEADERS.copy()
    headers['Accept'] = 'application/json, text/plain, */*'

    # 尝试多种可能的API端点
    api_endpoints = [
        f"https://zoolib.cc/api/book/{config.NOVEL_ID}/chapters",
        f"https://zoolib.cc/api/novel/{config.NOVEL_ID}/chapters",
        f"https://zoolib.cc/api/books/{config.NOVEL_ID}/chapters",
        f"https://zoolib.cc/api/chapters?novel_id={config.NOVEL_ID}",
        f"https://zoolib.cc/api/book-detail/{config.NOVEL_ID}",
        f"https://zoolib.cc/book-detail/{config.NOVEL_ID}/chapters",
    ]

    session = requests.Session()
    session.headers.update(headers)
    session.cookies.update(cookies)

    for endpoint in api_endpoints:
        print(f"\nTrying: {endpoint}")
        try:
            response = session.get(endpoint, timeout=15)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Got JSON response: {type(data)}")
                    print(f"Keys: {data.keys() if isinstance(data, dict) else 'N/A'}")

                    # 保存响应
                    with open(f'api_response_{endpoint.split("/")[-1]}.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print(f"Saved to api_response_{endpoint.split('/')[-1]}.json")

                except:
                    print(f"Response is not JSON: {response.text[:200]}")
            else:
                print(f"Response: {response.text[:200]}")

        except Exception as e:
            print(f"Error: {e}")

    print("\nDone checking APIs")


if __name__ == "__main__":
    get_chapters_via_api()

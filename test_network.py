"""
分析网络请求，查找章节列表API
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import time
import json
import config

# 启用性能日志
caps = DesiredCapabilities.EDGE.copy()
caps['goog:loggingPrefs'] = {'performance': 'ALL'}

options = EdgeOptions()
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

driver = webdriver.Edge(options=options)

try:
    # 添加Cookie
    driver.get(config.BASE_URL)
    for name, value in config.COOKIES.items():
        driver.add_cookie({'name': name, 'value': value})

    print("访问详情页...")
    driver.get(config.DETAIL_URL)

    # 等待页面加载
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-chapter-id]')))
    time.sleep(5)

    print("\n分析网络请求...")

    # 获取性能日志
    logs = driver.get_log('performance')

    api_requests = []

    for entry in logs:
        try:
            log = json.loads(entry['message'])['message']

            if log['method'] == 'Network.responseReceived':
                response = log['params']['response']
                url = response['url']

                # 查找可能包含章节数据的API请求
                if 'api' in url.lower() or 'chapter' in url.lower() or 'novel' in url.lower():
                    if '354291' in url or 'chapter' in url:
                        api_requests.append({
                            'url': url,
                            'status': response['status'],
                            'type': response.get('mimeType', 'unknown')
                        })
                        print(f"\n找到API请求:")
                        print(f"  URL: {url}")
                        print(f"  状态: {response['status']}")
                        print(f"  类型: {response.get('mimeType', 'unknown')}")
        except:
            pass

    print(f"\n共找到 {len(api_requests)} 个相关API请求")

    # 尝试直接访问可能的API端点
    print("\n\n尝试常见的API端点...")

    test_apis = [
        f"https://novelsapi.whx1216.top/api/novels/{config.NOVEL_ID}/chapters",
        f"https://novelsapi.whx1216.top/api/novels/{config.NOVEL_ID}/chapters?page=1&limit=1000",
        f"https://novelsapi.whx1216.top/api/v1/novels/{config.NOVEL_ID}/chapters",
        f"https://novels.whx1216.top/api/novels/{config.NOVEL_ID}/chapters",
    ]

    for api_url in test_apis:
        print(f"\n测试: {api_url}")
        try:
            driver.get(api_url)
            time.sleep(1)

            # 检查是否返回JSON
            page_source = driver.page_source
            if page_source.startswith('{') or page_source.startswith('['):
                print("  ✓ 返回JSON数据!")
                print(f"  前200字符: {page_source[:200]}")

                # 保存完整响应
                with open(f'api_response_{test_apis.index(api_url)}.json', 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print(f"  已保存到 api_response_{test_apis.index(api_url)}.json")
            else:
                print("  ✗ 不是JSON响应")
        except Exception as e:
            print(f"  错误: {e}")

    input("\n按回车键关闭...")

finally:
    driver.quit()

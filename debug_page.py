"""
Debug script to analyze page structure
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from bs4 import BeautifulSoup
import config

def create_driver():
    options = EdgeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

    driver = webdriver.Edge(options=options)
    driver.get(config.BASE_URL)

    for name, value in config.COOKIES.items():
        try:
            driver.add_cookie({'name': name, 'value': value, 'domain': '.zoolib.cc'})
        except:
            driver.add_cookie({'name': name, 'value': value})

    return driver

print("=" * 60)
print("Debug Page Structure")
print("=" * 60)

driver = create_driver()

try:
    print(f"\nVisiting: {config.DETAIL_URL}")
    driver.get(config.DETAIL_URL)
    time.sleep(5)

    # 保存页面HTML
    html = driver.page_source
    with open('debug_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("\nSaved page to: debug_page.html")

    soup = BeautifulSoup(html, 'lxml')

    # 查找所有链接
    print("\n" + "=" * 60)
    print("All links with 'chapter' or 'reader':")
    print("=" * 60)

    links = soup.find_all('a', href=True)
    chapter_links = []

    for link in links:
        href = link.get('href', '')
        if 'chapter' in href.lower() or 'reader' in href.lower():
            chapter_links.append({
                'href': href,
                'text': link.get_text(strip=True)[:50]
            })

    print(f"Found {len(chapter_links)} chapter-related links")
    for i, link in enumerate(chapter_links[:20]):
        print(f"  {i+1}. {link['href'][:80]}")
        print(f"      Text: {link['text']}")

    # 查找所有包含chapter的元素
    print("\n" + "=" * 60)
    print("Elements with 'chapter' class:")
    print("=" * 60)

    chapter_elems = soup.find_all(class_=lambda x: x and 'chapter' in x.lower())
    print(f"Found {len(chapter_elems)} elements")
    for i, elem in enumerate(chapter_elems[:10]):
        print(f"  {i+1}. <{elem.name}> class={elem.get('class')}")

    # 查找data属性
    print("\n" + "=" * 60)
    print("Elements with data-chapter attributes:")
    print("=" * 60)

    data_elems = soup.find_all(attrs={'data-chapter': True})
    print(f"Found {len(data_elems)} elements")
    for i, elem in enumerate(data_elems[:10]):
        print(f"  {i+1}. <{elem.name}> data-chapter={elem.get('data-chapter')}")

    # 查找episode相关
    print("\n" + "=" * 60)
    print("Elements with 'episode' class:")
    print("=" * 60)

    episode_elems = soup.find_all(class_=lambda x: x and 'episode' in x.lower())
    print(f"Found {len(episode_elems)} elements")
    for i, elem in enumerate(episode_elems[:10]):
        print(f"  {i+1}. <{elem.name}> class={elem.get('class')}")

    # 完成
    print("\n" + "=" * 60)
    print("Debug complete. Check debug_page.html for full HTML.")
    print("=" * 60)

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
    print("Browser closed")

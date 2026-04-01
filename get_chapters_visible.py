"""
获取章节列表 - 非headless模式
用于绕过Cloudflare反爬虫保护
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from bs4 import BeautifulSoup
import config

def create_driver():
    """创建浏览器（非headless）"""
    options = EdgeOptions()
    # 不使用headless模式
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

    driver = webdriver.Edge(options=options)

    # 隐藏webdriver特征
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })

    return driver


def get_chapters():
    print("=" * 60)
    print("Get Chapters (Non-headless mode)")
    print("=" * 60)

    driver = create_driver()

    try:
        # 先访问主页添加Cookie
        print("\nStep 1: Visit homepage...")
        driver.get(config.BASE_URL)
        time.sleep(3)

        # 添加Cookie
        print("Step 2: Adding cookies...")
        for name, value in config.COOKIES.items():
            try:
                driver.add_cookie({'name': name, 'value': value, 'domain': '.zoolib.cc'})
            except Exception as e:
                print(f"  Cookie {name}: {e}")

        # 刷新页面
        driver.refresh()
        time.sleep(3)

        # 访问小说详情页
        print(f"\nStep 3: Visit book detail page...")
        print(f"URL: {config.DETAIL_URL}")
        driver.get(config.DETAIL_URL)

        # 等待Cloudflare验证
        print("\nStep 4: Waiting for Cloudflare verification...")
        print("(This may take 10-30 seconds)")
        time.sleep(15)

        # 检查是否有Cloudflare挑战页面
        if "challenge" in driver.page_source.lower() or "checking" in driver.page_source.lower():
            print("Cloudflare challenge detected, waiting longer...")
            time.sleep(20)

        # 滚动加载章节
        print("\nStep 5: Scrolling to load chapters...")
        for i in range(30):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)

            # 尝试点击加载更多
            try:
                load_more = driver.find_element(By.CSS_SELECTOR, '[class*="more"], button[class*="load"]')
                load_more.click()
                time.sleep(1)
            except:
                pass

        # 获取页面源码
        print("\nStep 6: Parsing page...")
        html = driver.page_source

        # 保存HTML供调试
        with open('book_detail.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("Saved HTML to: book_detail.html")

        soup = BeautifulSoup(html, 'lxml')

        # 查找章节链接
        chapters = []

        # 查找所有包含reader的链接
        import re
        links = soup.find_all('a', href=re.compile(r'reader.*chapter|chapter'))

        print(f"\nFound {len(links)} potential chapter links")

        for link in links:
            href = link.get('href', '')
            match = re.search(r'chapter[=\/](\d+)', href)
            if match:
                chapter_id = match.group(1)

                if href.startswith('/'):
                    url = config.BASE_URL + href
                else:
                    url = href

                title = link.get_text(strip=True) or f"Chapter {chapter_id}"

                chapters.append({
                    'id': chapter_id,
                    'title': title,
                    'url': url
                })

        # 去重
        unique = {}
        for ch in chapters:
            if ch['id'] not in unique:
                unique[ch['id']] = ch

        chapters = list(unique.values())

        print(f"\nTotal unique chapters: {len(chapters)}")

        if chapters:
            # 保存
            with open('chapters_list.json', 'w', encoding='utf-8') as f:
                json.dump(chapters, f, ensure_ascii=False, indent=2)
            print(f"Saved to: chapters_list.json")

            print(f"\nFirst 5 chapters:")
            for ch in chapters[:5]:
                print(f"  ID: {ch['id']}, Title: {ch['title'][:30]}")

            print(f"\nLast 5 chapters:")
            for ch in chapters[-5:]:
                print(f"  ID: {ch['id']}, Title: {ch['title'][:30]}")
        else:
            print("\nNo chapters found!")
            print("Please check the HTML file or try manually.")

        return chapters

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        print("\nClosing browser in 5 seconds...")
        time.sleep(5)
        driver.quit()
        print("Browser closed")


if __name__ == "__main__":
    get_chapters()

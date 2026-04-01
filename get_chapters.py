"""
获取章节列表 - zoolib.cc
"""

import time
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from bs4 import BeautifulSoup
import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('get_chapters.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_driver():
    """创建浏览器"""
    options = EdgeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

    driver = webdriver.Edge(options=options)
    driver.get(config.BASE_URL)

    # 添加Cookie
    for name, value in config.COOKIES.items():
        driver.add_cookie({'name': name, 'value': value, 'domain': '.zoolib.cc'})

    return driver


def get_all_chapters():
    """获取所有章节列表"""
    logger.info("=" * 60)
    logger.info("Get All Chapters from zoolib.cc")
    logger.info("=" * 60)

    driver = None

    try:
        logger.info("Starting browser...")
        driver = create_driver()

        # 访问小说详情页
        logger.info(f"Visiting: {config.DETAIL_URL}")
        driver.get(config.DETAIL_URL)

        # 等待页面加载
        wait = WebDriverWait(driver, 20)
        time.sleep(3)

        # 尝试展开所有章节（如果有"展开全部"按钮）
        try:
            expand_btn = driver.find_element(By.CSS_SELECTOR, '[class*="expand"], [class*="more"], button[class*="chapter"]')
            expand_btn.click()
            time.sleep(2)
        except:
            pass

        # 滚动加载所有章节
        logger.info("Scrolling to load all chapters...")
        last_height = driver.execute_script("return document.body.scrollHeight")

        for i in range(50):  # 最多滚动50次
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                # 再尝试点击"加载更多"按钮
                try:
                    load_more = driver.find_element(By.CSS_SELECTOR, '[class*="load-more"], [class*="more"]')
                    load_more.click()
                    time.sleep(2)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                except:
                    pass

                if new_height == last_height:
                    break

            last_height = new_height
            if (i + 1) % 10 == 0:
                logger.info(f"  Scrolled {i + 1} times...")

        # 获取页面HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # 查找章节链接
        chapters = []

        # 尝试多种选择器
        selectors = [
            'a[href*="/reader?"]',
            'a[href*="chapter"]',
            '[class*="chapter"] a',
            '[class*="episode"] a',
            'a[class*="chapter"]',
        ]

        for selector in selectors:
            links = soup.select(selector)
            if links:
                logger.info(f"Found {len(links)} links with selector: {selector}")

                for link in links:
                    href = link.get('href', '')
                    if 'chapter=' in href or 'reader' in href:
                        # 提取章节ID
                        import re
                        match = re.search(r'chapter[=\/](\d+)', href)
                        if match:
                            chapter_id = match.group(1)

                            # 构建完整URL
                            if href.startswith('/'):
                                url = config.BASE_URL + href
                            elif href.startswith('http'):
                                url = href
                            else:
                                url = f"{config.READER_URL}?novel={config.NOVEL_ID}&chapter={chapter_id}"

                            # 获取标题
                            title = link.get_text(strip=True) or f"Chapter {chapter_id}"

                            chapters.append({
                                'id': chapter_id,
                                'title': title,
                                'url': url
                            })

                if chapters:
                    break

        # 去重
        unique_chapters = {}
        for ch in chapters:
            if ch['id'] not in unique_chapters:
                unique_chapters[ch['id']] = ch

        chapters = list(unique_chapters.values())

        logger.info(f"Total unique chapters: {len(chapters)}")

        # 保存到JSON
        if chapters:
            with open('chapters_list.json', 'w', encoding='utf-8') as f:
                json.dump(chapters, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved to: chapters_list.json")

        return chapters

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")


def main():
    chapters = get_all_chapters()

    if chapters:
        print(f"\n" + "=" * 60)
        print(f"Total chapters: {len(chapters)}")
        print(f"\nFirst 5 chapters:")
        for ch in chapters[:5]:
            print(f"  ID: {ch['id']}, Title: {ch['title'][:30]}...")
        print(f"\nLast 5 chapters:")
        for ch in chapters[-5:]:
            print(f"  ID: {ch['id']}, Title: {ch['title'][:30]}...")
        print("=" * 60)
    else:
        print("\nNo chapters found!")
        print("Please check if the website structure has changed.")


if __name__ == "__main__":
    main()

"""
手动爬取第181、182话并添加到数据中
"""

import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from bs4 import BeautifulSoup
import config

def create_driver():
    """创建浏览器"""
    options = EdgeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

    driver = webdriver.Edge(options=options)
    driver.get(config.BASE_URL)
    for name, value in config.COOKIES.items():
        driver.add_cookie({'name': name, 'value': value})

    return driver


def fetch_chapter(chapter_url, chapter_num, driver):
    """获取单个章节内容"""
    try:
        print(f"Fetching chapter {chapter_num}...")
        driver.get(chapter_url)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.chapter-item')))
        time.sleep(2)

        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        chapter_div = soup.find('div', class_='chapter-item')
        if not chapter_div:
            print(f"  Error: chapter-item not found")
            return None

        # 获取标题
        title = chapter_div.get('data-chapter-title', '')
        print(f"  Title found: Yes")

        # 处理换行
        for br in chapter_div.find_all('br'):
            br.replace_with('\n')

        # 获取内容
        content = chapter_div.get_text()
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(line for line in lines if line)

        print(f"  Content length: {len(content)} chars")

        # 强制使用中文标题
        chinese_title = f'重生路人甲成为天才 第{chapter_num}话'

        return {
            'id': f'manual_{chapter_num}',
            'title': chinese_title,
            'content': content
        }

    except Exception as e:
        print(f"  Error: {e}")
        return None


print("=" * 60)
print("Manual Scrape Chapter 181 & 182")
print("=" * 60)

# 章节URL
chapters_to_scrape = [
    {'num': 181, 'url': 'https://novels.whx1216.top/reader?novel=354291&chapter=6594181'},
    {'num': 182, 'url': 'https://novels.whx1216.top/reader?novel=354291&chapter=6594182'}
]

driver = None
new_chapters = []

try:
    print("\nStarting browser...")
    driver = create_driver()
    print("Browser started\n")

    for ch in chapters_to_scrape:
        content = fetch_chapter(ch['url'], ch['num'], driver)

        if content:
            new_chapters.append(content)
            print(f"  Success!\n")
        else:
            print(f"  Failed!\n")

        time.sleep(2)

finally:
    if driver:
        driver.quit()
        print("Browser closed")

# 读取现有数据
print("\nLoading existing data...")
with open('scrape_progress.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

chapters_content = data.get('chapters_content', [])
print(f"Existing chapters: {len(chapters_content)}")

# 删除旧的181、182章（如果存在）
print("\nRemoving old chapter 181 & 182 (if any)...")
import re

def extract_chapter_number(title):
    patterns = [r'第(\d+)[话章]', r'(\d+)화', r'Chapter\s*(\d+)']
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return int(match.group(1))
    return 0

filtered_chapters = []
removed_count = 0

for ch in chapters_content:
    num = extract_chapter_number(ch.get('title', ''))
    if num == 181 or num == 182:
        removed_count += 1
        continue
    filtered_chapters.append(ch)

print(f"Removed: {removed_count} old chapters")

# 添加新章节
print(f"\nAdding {len(new_chapters)} new chapters...")
filtered_chapters.extend(new_chapters)

# 保存
data['chapters_content'] = filtered_chapters

print(f"\nSaving to scrape_progress.json...")
with open('scrape_progress.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved! Total chapters: {len(filtered_chapters)}")

print("\n" + "=" * 60)
print("Done!")
print("=" * 60)
print(f"New chapters added: {len(new_chapters)}")
print(f"Total chapters: {len(filtered_chapters)}")
print("\nNow run: python final_epub_535.py")
print("=" * 60)

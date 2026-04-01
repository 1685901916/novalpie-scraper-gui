"""
使用已有的章节JSON数据来爬取小说内容
"""

import json
import time
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
        logging.FileHandler('scraper_from_json.log', encoding='utf-8'),
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
    for name, value in config.COOKIES.items():
        driver.add_cookie({'name': name, 'value': value})

    return driver


def fetch_chapter(chapter_id, chapter_title, driver):
    """获取单个章节内容"""
    url = f"{config.READER_URL}?novel={config.NOVEL_ID}&chapter={chapter_id}"

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.chapter-item')))
        time.sleep(1)

        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        chapter_div = soup.find('div', class_='chapter-item')
        if not chapter_div:
            return None

        title = chapter_div.get('data-chapter-title', chapter_title)

        for br in chapter_div.find_all('br'):
            br.replace_with('\n')

        content = chapter_div.get_text()
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(line for line in lines if line)

        return {'title': title, 'content': content}

    except Exception as e:
        logger.error(f"获取章节失败 {chapter_title}: {e}")
        return None


def save_to_txt(chapters_content, filename):
    """保存为TXT文件，带目录"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("重生路人甲成为天才\n\n")

            # 写入目录
            f.write("=" * 50 + "\n")
            f.write("目录\n")
            f.write("=" * 50 + "\n\n")
            for i, ch in enumerate(chapters_content, 1):
                f.write(f"{i}. {ch['title']}\n")
            f.write("\n\n")

            # 写入正文
            for ch in chapters_content:
                f.write("=" * 50 + "\n")
                f.write(f"{ch['title']}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"{ch['content']}\n\n\n")

            f.write("=" * 50 + "\n")
            f.write(f"总计：{len(chapters_content)} 章\n")

        logger.info(f"成功保存到: {filename}")
    except Exception as e:
        logger.error(f"保存失败: {e}")


def main():
    # 读取章节数据
    logger.info("读取章节数据...")
    with open('all_chapters.json', 'r', encoding='utf-8') as f:
        chapters_data = json.load(f)

    # 去重并排序
    unique_chapters = {}
    for ch in chapters_data:
        if ch['id'] not in unique_chapters:
            unique_chapters[ch['id']] = ch

    chapters = list(unique_chapters.values())

    # 按章节号排序
    def get_num(ch):
        import re
        match = re.search(r'\d+', ch['title'])
        return int(match.group()) if match else 0

    chapters.sort(key=get_num)

    logger.info(f"共有 {len(chapters)} 个唯一章节")

    # 开始爬取
    driver = None
    chapters_content = []
    failed = []

    try:
        logger.info("启动浏览器...")
        driver = create_driver()

        for i, ch in enumerate(chapters, 1):
            logger.info(f"[{i}/{len(chapters)}] 爬取: {ch['title']}")

            content = fetch_chapter(ch['id'], ch['title'], driver)

            if content:
                chapters_content.append(content)
                logger.info(f"  成功")
            else:
                failed.append(ch)
                logger.error(f"  失败")

            if i < len(chapters):
                time.sleep(config.REQUEST_DELAY)

    finally:
        if driver:
            driver.quit()

    # 保存结果
    if chapters_content:
        logger.info("\n保存文件...")
        save_to_txt(chapters_content, "重生路人甲成为天才_完整版.txt")

        logger.info("=" * 60)
        logger.info(f"爬取完成！")
        logger.info(f"成功: {len(chapters_content)} 章")
        logger.info(f"失败: {len(failed)} 章")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()

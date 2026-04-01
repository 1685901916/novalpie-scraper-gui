"""
小说爬虫主程序
爬取 novels.whx1216.top 网站上的小说内容并保存为TXT文件
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILENAME, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_driver():
    """创建Selenium WebDriver"""
    options = EdgeOptions()
    options.add_argument('--headless')  # 无头模式
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

    driver = webdriver.Edge(options=options)

    # 添加Cookie
    driver.get(config.BASE_URL)
    for name, value in config.COOKIES.items():
        driver.add_cookie({'name': name, 'value': value})

    return driver


def get_chapter_list() -> List[Dict[str, str]]:
    """
    使用Selenium从详情页获取所有章节的列表

    Returns:
        章节列表，每个元素包含 id, title, url
    """
    logger.info(f"开始获取章节列表: {config.DETAIL_URL}")

    driver = None
    try:
        driver = create_driver()
        driver.get(config.DETAIL_URL)

        # 等待章节列表加载
        logger.info("等待页面加载...")
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-chapter-id]')))

        # 额外等待确保所有章节加载完成
        time.sleep(3)

        # 获取页面HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # 查找所有章节按钮
        buttons = soup.find_all('button', {'data-chapter-id': True})

        if not buttons:
            logger.error("未找到章节按钮")
            return []

        chapters = []
        for button in buttons:
            chapter_id = button['data-chapter-id']

            # 提取章节标题
            title_div = button.find('div', class_='font-medium')
            if title_div:
                title = title_div.get_text(strip=True)
            else:
                title = f"第{len(chapters) + 1}章"

            chapter_url = f"{config.READER_URL}?novel={config.NOVEL_ID}&chapter={chapter_id}"

            chapters.append({
                'id': chapter_id,
                'title': title,
                'url': chapter_url
            })

        logger.info(f"成功获取 {len(chapters)} 个章节")
        return chapters

    except Exception as e:
        logger.error(f"获取章节列表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
    finally:
        if driver:
            driver.quit()


def fetch_chapter_content(chapter: Dict[str, str], driver) -> Optional[Dict[str, str]]:
    """
    使用Selenium获取单个章节的内容

    Args:
        chapter: 章节信息字典，包含 id, title, url
        driver: 共享的WebDriver实例

    Returns:
        包含 title 和 content 的字典，失败返回 None
    """
    chapter_url = chapter['url']

    try:
        driver.get(chapter_url)

        # 等待章节内容加载
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.chapter-item')))

        # 额外等待确保内容完全加载
        time.sleep(1)

        # 获取页面HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # 查找章节容器
        chapter_div = soup.find('div', class_='chapter-item')

        if not chapter_div:
            logger.error(f"未找到章节内容容器: {chapter['title']}")
            return None

        # 获取章节标题
        title = chapter_div.get('data-chapter-title', chapter['title'])

        # 提取章节内容，将<br>标签替换为换行符
        for br in chapter_div.find_all('br'):
            br.replace_with('\n')

        content = chapter_div.get_text()

        # 清理多余的空行
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(line for line in lines if line)

        return {
            'title': title,
            'content': content
        }

    except Exception as e:
        logger.error(f"获取章节内容失败: {chapter['title']} - {e}")
        return None


def save_to_txt(chapters_content: List[Dict[str, str]], filename: str):
    """
    将章节内容保存为TXT文件

    Args:
        chapters_content: 章节内容列表
        filename: 输出文件名
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入标题
            f.write("重生路人甲成为天才\n\n")

            # 写入每个章节
            for i, chapter in enumerate(chapters_content, 1):
                f.write(f"{'=' * 50}\n")
                f.write(f"{chapter['title']}\n")
                f.write(f"{'=' * 50}\n\n")
                f.write(f"{chapter['content']}\n\n")

            # 写入统计信息
            f.write(f"\n{'=' * 50}\n")
            f.write(f"总计：{len(chapters_content)} 章\n")

        logger.info(f"成功保存到文件: {filename}")
    except Exception as e:
        logger.error(f"保存文件失败: {e}")


def main():
    """
    主函数
    """
    logger.info("=" * 60)
    logger.info("小说爬虫程序启动")
    logger.info("=" * 60)

    # 步骤1: 获取章节列表
    chapters = get_chapter_list()
    if not chapters:
        logger.error("无法获取章节列表，程序退出")
        return

    logger.info(f"共找到 {len(chapters)} 个章节")

    # 步骤2: 爬取每个章节内容
    chapters_content = []
    failed_chapters = []

    # 创建一个共享的浏览器实例
    driver = None
    try:
        logger.info("正在启动浏览器...")
        driver = create_driver()

        for i, chapter in enumerate(chapters, 1):
            logger.info(f"正在爬取 [{i}/{len(chapters)}]: {chapter['title']}")

            content = fetch_chapter_content(chapter, driver)

            if content:
                chapters_content.append(content)
                logger.info(f"✓ 成功: {chapter['title']}")
            else:
                failed_chapters.append(chapter)
                logger.error(f"✗ 失败: {chapter['title']}")

            # 添加延迟，避免请求过快
            if i < len(chapters):
                time.sleep(config.REQUEST_DELAY)
    finally:
        if driver:
            logger.info("关闭浏览器...")
            driver.quit()

    # 步骤3: 保存为TXT文件
    if chapters_content:
        logger.info(f"\n开始保存文件...")
        save_to_txt(chapters_content, config.OUTPUT_FILENAME)

        # 输出统计信息
        logger.info("=" * 60)
        logger.info(f"爬取完成！")
        logger.info(f"成功: {len(chapters_content)} 章")
        logger.info(f"失败: {len(failed_chapters)} 章")

        if failed_chapters:
            logger.warning("\n失败的章节:")
            for chapter in failed_chapters:
                logger.warning(f"  - {chapter['title']} (ID: {chapter['id']})")

        logger.info(f"\n输出文件: {config.OUTPUT_FILENAME}")
        logger.info("=" * 60)
    else:
        logger.error("没有成功爬取任何章节内容")


if __name__ == "__main__":
    main()

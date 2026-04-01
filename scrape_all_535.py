"""
爬取all_chapters.json中的535章内容
支持断点续传和进度保存
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
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scrape_535.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 进度文件
PROGRESS_FILE = 'scrape_progress.json'


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


def fetch_chapter(chapter_url, chapter_id, driver):
    """获取单个章节内容"""
    try:
        driver.get(chapter_url)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.chapter-item')))
        time.sleep(1)

        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        chapter_div = soup.find('div', class_='chapter-item')
        if not chapter_div:
            return None

        # 获取标题
        title = chapter_div.get('data-chapter-title', f'第{chapter_id}章')

        # 处理换行
        for br in chapter_div.find_all('br'):
            br.replace_with('\n')

        # 获取内容
        content = chapter_div.get_text()
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(line for line in lines if line)

        return {'id': chapter_id, 'title': title, 'content': content}

    except Exception as e:
        logger.error(f"获取章节失败 ID={chapter_id}: {e}")
        return None


def load_progress():
    """加载进度"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'completed': [], 'chapters_content': []}
    return {'completed': [], 'chapters_content': []}


def save_progress(progress):
    """保存进度"""
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存进度失败: {e}")


def save_to_txt(chapters_content, filename):
    """保存为TXT文件，符合阅读软件目录识别格式"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # 书名
            f.write("重生路人甲成为天才\n\n")

            # 写入正文（不写目录，让阅读软件自动识别）
            for i, ch in enumerate(chapters_content, 1):
                # 章节标题格式：使用分隔线
                f.write("\n" + "=" * 50 + "\n")
                f.write(f"{ch['title']}\n")
                f.write("=" * 50 + "\n\n")

                # 章节内容
                f.write(f"{ch['content']}\n\n")

            # 结尾
            f.write("\n" + "=" * 50 + "\n")
            f.write(f"总计：{len(chapters_content)} 章\n")
            f.write("=" * 50 + "\n")

        logger.info(f"✓ 成功保存到: {filename}")
        return True
    except Exception as e:
        logger.error(f"✗ 保存失败: {e}")
        return False


def main():
    # 读取章节数据
    logger.info("=" * 60)
    logger.info("开始爬取535章小说内容")
    logger.info("=" * 60)

    with open('all_chapters.json', 'r', encoding='utf-8') as f:
        chapters_data = json.load(f)

    logger.info(f"读取到 {len(chapters_data)} 个章节")

    # 加载进度
    progress = load_progress()
    completed_ids = set(progress['completed'])
    chapters_content = progress['chapters_content']

    if completed_ids:
        logger.info(f"发现已完成 {len(completed_ids)} 章，继续爬取...")

    # 过滤未完成的章节
    remaining_chapters = [ch for ch in chapters_data if ch['id'] not in completed_ids]
    logger.info(f"剩余 {len(remaining_chapters)} 章待爬取")

    if not remaining_chapters:
        logger.info("所有章节已完成！")
        if chapters_content:
            save_to_txt(chapters_content, "重生路人甲成为天才_完整版_535章.txt")
        return

    # 开始爬取
    driver = None
    failed = []

    try:
        logger.info("启动浏览器...")
        driver = create_driver()
        logger.info("浏览器启动成功")

        for i, ch in enumerate(remaining_chapters, 1):
            chapter_id = ch['id']
            chapter_url = ch['url']

            logger.info(f"[{len(completed_ids) + i}/{len(chapters_data)}] 爬取章节 ID={chapter_id}")

            content = fetch_chapter(chapter_url, chapter_id, driver)

            if content:
                chapters_content.append(content)
                completed_ids.add(chapter_id)
                logger.info(f"  ✓ 成功: {content['title']}")

                # 每10章保存一次进度
                if len(completed_ids) % 10 == 0:
                    progress['completed'] = list(completed_ids)
                    progress['chapters_content'] = chapters_content
                    save_progress(progress)
                    logger.info(f"  >> 进度已保存 ({len(completed_ids)}/{len(chapters_data)})")
            else:
                failed.append(ch)
                logger.error(f"  ✗ 失败")

            # 延迟
            if i < len(remaining_chapters):
                time.sleep(config.REQUEST_DELAY)

    except KeyboardInterrupt:
        logger.info("\n用户中断，保存进度...")
        progress['completed'] = list(completed_ids)
        progress['chapters_content'] = chapters_content
        save_progress(progress)
        logger.info("进度已保存，下次运行将继续")

    except Exception as e:
        logger.error(f"发生错误: {e}")

    finally:
        if driver:
            driver.quit()
            logger.info("浏览器已关闭")

    # 最终保存
    progress['completed'] = list(completed_ids)
    progress['chapters_content'] = chapters_content
    save_progress(progress)

    # 保存TXT文件
    if chapters_content:
        logger.info("\n" + "=" * 60)
        logger.info("保存TXT文件...")
        save_to_txt(chapters_content, "重生路人甲成为天才_完整版_535章.txt")

        logger.info("=" * 60)
        logger.info(f"爬取完成！")
        logger.info(f"✓ 成功: {len(chapters_content)} 章")
        logger.info(f"✗ 失败: {len(failed)} 章")
        if failed:
            logger.info(f"失败章节ID: {[ch['id'] for ch in failed]}")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()

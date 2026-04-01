"""
完整版小说爬虫 - 支持虚拟滚动加载所有章节
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_full.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_driver():
    """创建Selenium WebDriver"""
    options = EdgeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

    driver = webdriver.Edge(options=options)

    # 添加Cookie
    driver.get(config.BASE_URL)
    for name, value in config.COOKIES.items():
        driver.add_cookie({'name': name, 'value': value})

    return driver


def get_all_chapters_with_scroll(driver) -> List[Dict[str, str]]:
    """
    通过滚动加载所有章节
    """
    logger.info(f"开始获取章节列表: {config.DETAIL_URL}")

    driver.get(config.DETAIL_URL)

    # 等待页面加载
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-chapter-id]')))
    time.sleep(3)

    # 找到章节列表容器
    logger.info("查找章节列表容器...")

    # 尝试找到可滚动的章节容器
    try:
        # 查找包含章节的滚动容器
        scroll_container = driver.find_element(By.CSS_SELECTOR, "div[class*='max-h'], div[class*='overflow']")
        logger.info(f"找到滚动容器: {scroll_container.get_attribute('class')}")
    except:
        logger.warning("未找到特定滚动容器，使用整个页面")
        scroll_container = None

    chapters_set = set()  # 使用集合去重
    last_count = 0
    no_change_count = 0
    max_no_change = 10  # 连续10次没有新章节就停止

    logger.info("开始滚动加载章节...")

    while no_change_count < max_no_change:
        # 获取当前所有章节
        buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]')
        current_count = len(buttons)

        # 收集章节ID
        for btn in buttons:
            chapter_id = btn.get_attribute('data-chapter-id')
            if chapter_id:
                chapters_set.add(chapter_id)

        logger.info(f"当前找到 {current_count} 个章节按钮，去重后 {len(chapters_set)} 个唯一章节")

        # 如果章节数没有增加
        if len(chapters_set) == last_count:
            no_change_count += 1
            logger.info(f"章节数未增加 ({no_change_count}/{max_no_change})")
        else:
            no_change_count = 0
            last_count = len(chapters_set)

        # 滚动到最后一个章节按钮
        if buttons:
            try:
                last_button = buttons[-1]
                driver.execute_script("arguments[0].scrollIntoView({block: 'end', behavior: 'smooth'});", last_button)
                time.sleep(0.5)

                # 如果有滚动容器，也滚动容器
                if scroll_container:
                    driver.execute_script("""
                        arguments[0].scrollTop = arguments[0].scrollHeight;
                    """, scroll_container)
                    time.sleep(0.5)
            except Exception as e:
                logger.warning(f"滚动失败: {e}")

        # 额外向下滚动页面
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(0.3)

    logger.info(f"滚动完成，共找到 {len(chapters_set)} 个唯一章节")

    # 最后再获取一次所有章节信息
    html = driver.page_source
    soup = BeautifulSoup(html, 'lxml')

    buttons = soup.find_all('button', {'data-chapter-id': True})

    chapters = []
    seen_ids = set()

    for button in buttons:
        chapter_id = button['data-chapter-id']

        # 去重
        if chapter_id in seen_ids:
            continue
        seen_ids.add(chapter_id)

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


def fetch_chapter_content(chapter: Dict[str, str], driver) -> Optional[Dict[str, str]]:
    """获取单个章节内容"""
    try:
        driver.get(chapter['url'])

        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.chapter-item')))
        time.sleep(1)

        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        chapter_div = soup.find('div', class_='chapter-item')
        if not chapter_div:
            logger.error(f"未找到章节内容: {chapter['title']}")
            return None

        title = chapter_div.get('data-chapter-title', chapter['title'])

        # 提取内容
        for br in chapter_div.find_all('br'):
            br.replace_with('\n')

        content = chapter_div.get_text()
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(line for line in lines if line)

        return {'title': title, 'content': content}

    except Exception as e:
        logger.error(f"获取章节失败: {chapter['title']} - {e}")
        return None


def save_to_txt_with_toc(chapters_content: List[Dict[str, str]], filename: str):
    """
    保存为TXT文件，添加目录支持
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入书名
            f.write("重生路人甲成为天才\n\n")

            # 写入目录
            f.write("=" * 50 + "\n")
            f.write("目录\n")
            f.write("=" * 50 + "\n\n")
            for i, chapter in enumerate(chapters_content, 1):
                f.write(f"{i}. {chapter['title']}\n")
            f.write("\n\n")

            # 写入正文
            for i, chapter in enumerate(chapters_content, 1):
                f.write("=" * 50 + "\n")
                f.write(f"{chapter['title']}\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"{chapter['content']}\n\n\n")

            # 统计信息
            f.write("=" * 50 + "\n")
            f.write(f"总计：{len(chapters_content)} 章\n")

        logger.info(f"成功保存到: {filename}")
    except Exception as e:
        logger.error(f"保存失败: {e}")


def main():
    logger.info("=" * 60)
    logger.info("完整版小说爬虫启动")
    logger.info("=" * 60)

    driver = None
    try:
        # 步骤1: 获取所有章节
        driver = create_driver()
        chapters = get_all_chapters_with_scroll(driver)

        if not chapters:
            logger.error("无法获取章节列表")
            return

        logger.info(f"共找到 {len(chapters)} 个章节")

        # 步骤2: 爬取内容
        chapters_content = []
        failed_chapters = []

        for i, chapter in enumerate(chapters, 1):
            logger.info(f"正在爬取 [{i}/{len(chapters)}]: {chapter['title']}")

            content = fetch_chapter_content(chapter, driver)

            if content:
                chapters_content.append(content)
                logger.info(f"✓ 成功: {chapter['title']}")
            else:
                failed_chapters.append(chapter)
                logger.error(f"✗ 失败: {chapter['title']}")

            if i < len(chapters):
                time.sleep(config.REQUEST_DELAY)

        # 步骤3: 保存
        if chapters_content:
            logger.info("\n开始保存文件...")
            save_to_txt_with_toc(chapters_content, "重生路人甲成为天才_完整版.txt")

            logger.info("=" * 60)
            logger.info("爬取完成！")
            logger.info(f"成功: {len(chapters_content)} 章")
            logger.info(f"失败: {len(failed_chapters)} 章")

            if failed_chapters:
                logger.warning("\n失败的章节:")
                for ch in failed_chapters:
                    logger.warning(f"  - {ch['title']} (ID: {ch['id']})")

            logger.info(f"\n输出文件: 重生路人甲成为天才_完整版.txt")
            logger.info("=" * 60)
        else:
            logger.error("没有成功爬取任何章节")

    finally:
        if driver:
            logger.info("关闭浏览器...")
            driver.quit()

2
if __name__ == "__main__":
    main()

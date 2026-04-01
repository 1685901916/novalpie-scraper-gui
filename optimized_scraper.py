"""
优化的小说爬虫
- 自动过滤"章节讨论"等无关内容
- 完成后自动生成TXT和EPUB两种格式
- 支持断点续传
"""

import json
import time
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from bs4 import BeautifulSoup
from ebooklib import epub
import config
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('optimized_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 进度文件
PROGRESS_FILE = 'scraper_progress.json'


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


def clean_chapter_content(content):
    """
    清理章节内容，删除无关文字
    - 章节讨论
    - 写评论
    - 暂无评论
    等
    """
    # 定义要删除的模式
    patterns = [
        r'章节讨论\s*\(\d+\).*?写第一条评论',  # 章节讨论 (0)第X章·标题 写评论 暂无评论来说说你的看法吧！ 写第一条评论
        r'章节讨论.*',
        r'写评论.*?写第一条评论',
        r'暂无评论来说说你的看法吧！.*',
        r'写第一条评论.*',
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)

    # 删除多余的空行
    lines = content.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]

    return '\n'.join(cleaned_lines)


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

        # 清理内容
        content = clean_chapter_content(content)

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


def extract_chapter_number(title):
    """提取章节号"""
    patterns = [
        r'第(\d+)[话章]',
        r'(\d+)화',
        r'Chapter\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return int(match.group(1))
    return 0


def save_to_txt(chapters, filename):
    """保存为TXT格式"""
    try:
        logger.info(f"生成TXT文件: {filename}")

        with open(filename, 'w', encoding='utf-8') as f:
            # 书名
            f.write("重生路人甲成为天才\n")
            f.write("作者：未知\n\n")

            # 写入章节
            for ch in chapters:
                f.write(f"\n{ch['title']}\n\n")
                f.write(f"{ch['content']}\n")

            # 结尾
            f.write(f"\n\n全文完\n")

        logger.info(f"TXT文件生成成功: {filename}")
        return True
    except Exception as e:
        logger.error(f"TXT文件生成失败: {e}")
        return False


def save_to_epub(chapters, filename):
    """保存为EPUB格式"""
    try:
        logger.info(f"生成EPUB文件: {filename}")

        book = epub.EpubBook()
        book.set_identifier('rebirth_genius')
        book.set_title('重生路人甲成为天才')
        book.set_language('zh')
        book.add_author('未知')

        epub_chapters = []
        spine = ['nav']

        for i, ch in enumerate(chapters, 1):
            chapter = epub.EpubHtml(
                title=ch['title'],
                file_name=f'chapter_{i:03d}.xhtml',
                lang='zh'
            )

            # 生成HTML内容
            paragraphs = ch['content'].split('\n')
            html_content = f'<h1>{ch["title"]}</h1>\n'

            for p in paragraphs:
                p = p.strip()
                if p:
                    html_content += f'<p>{p}</p>\n'

            chapter.content = html_content

            book.add_item(chapter)
            epub_chapters.append(chapter)
            spine.append(chapter)

            if (i % 50 == 0) or (i == len(chapters)):
                logger.info(f"  EPUB进度: {i}/{len(chapters)}")

        # 添加目录和导航
        book.toc = epub_chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = spine

        # 添加CSS样式
        style = '''
        body {
            font-family: "Microsoft YaHei", "SimSun", serif;
            line-height: 1.8;
            margin: 2em;
        }
        h1 {
            text-align: center;
            font-size: 1.5em;
            margin: 2em 0 1em 0;
            font-weight: bold;
        }
        p {
            text-indent: 2em;
            margin: 0.5em 0;
        }
        '''

        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style
        )
        book.add_item(nav_css)

        # 写入文件
        epub.write_epub(filename, book, {})

        logger.info(f"EPUB文件生成成功: {filename}")
        return True
    except Exception as e:
        logger.error(f"EPUB文件生成失败: {e}")
        return False


def main():
    logger.info("=" * 60)
    logger.info("开始爬取小说")
    logger.info("=" * 60)

    # 读取章节列表
    with open('all_chapters.json', 'r', encoding='utf-8') as f:
        chapters_data = json.load(f)

    logger.info(f"总章节数: {len(chapters_data)}")

    # 加载进度
    progress = load_progress()
    completed_ids = set(progress['completed'])
    chapters_content = progress['chapters_content']

    if completed_ids:
        logger.info(f"已完成 {len(completed_ids)} 章，继续爬取...")

    # 过滤未完成的章节
    remaining_chapters = [ch for ch in chapters_data if ch['id'] not in completed_ids]
    logger.info(f"剩余 {len(remaining_chapters)} 章待爬取")

    if not remaining_chapters:
        logger.info("所有章节已完成！")
    else:
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
                    logger.info(f"  成功")

                    # 每10章保存一次进度
                    if len(completed_ids) % 10 == 0:
                        progress['completed'] = list(completed_ids)
                        progress['chapters_content'] = chapters_content
                        save_progress(progress)
                        logger.info(f"  进度已保存 ({len(completed_ids)}/{len(chapters_data)})")
                else:
                    failed.append(ch)
                    logger.error(f"  失败")

                # 延迟
                if i < len(remaining_chapters):
                    time.sleep(config.REQUEST_DELAY)

        except KeyboardInterrupt:
            logger.info("\n用户中断，保存进度...")
            progress['completed'] = list(completed_ids)
            progress['chapters_content'] = chapters_content
            save_progress(progress)
            logger.info("进度已保存")
            return

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

    # 处理和排序章节
    logger.info("\n" + "=" * 60)
    logger.info("处理章节数据...")
    logger.info("=" * 60)

    processed_chapters = {}

    for ch in chapters_content:
        title = ch.get('title', '')
        content = ch.get('content', '')

        chapter_num = extract_chapter_number(title)

        if chapter_num == 0:
            continue

        # 统一标题为中文格式
        standard_title = f'重生路人甲成为天才 第{chapter_num}话'

        # 去重：保留内容更长的版本
        if chapter_num in processed_chapters:
            if len(content) > len(processed_chapters[chapter_num]['content']):
                processed_chapters[chapter_num] = {
                    'number': chapter_num,
                    'title': standard_title,
                    'content': content
                }
        else:
            processed_chapters[chapter_num] = {
                'number': chapter_num,
                'title': standard_title,
                'content': content
            }

    # 按章节号排序
    sorted_chapters = sorted(processed_chapters.values(), key=lambda x: x['number'])

    logger.info(f"处理后章节数: {len(sorted_chapters)}")
    logger.info(f"章节范围: 第{sorted_chapters[0]['number']}话 - 第{sorted_chapters[-1]['number']}话")

    # 检查完整性
    chapter_nums = set(ch['number'] for ch in sorted_chapters)
    max_chapter = max(chapter_nums)
    missing = sorted(set(range(1, max_chapter + 1)) - chapter_nums)

    if missing:
        logger.warning(f"缺失 {len(missing)} 章: {missing[:20]}")
    else:
        logger.info(f"章节完整，无缺失")

    # 生成文件
    logger.info("\n" + "=" * 60)
    logger.info("生成输出文件...")
    logger.info("=" * 60)

    # 生成TXT
    txt_filename = f"重生路人甲成为天才_完整版_{len(sorted_chapters)}章.txt"
    save_to_txt(sorted_chapters, txt_filename)

    # 生成EPUB
    epub_filename = f"重生路人甲成为天才_完整版_{len(sorted_chapters)}章.epub"
    save_to_epub(sorted_chapters, epub_filename)

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("爬取完成！")
    logger.info("=" * 60)
    logger.info(f"总章节数: {len(sorted_chapters)}")
    logger.info(f"TXT文件: {txt_filename}")
    logger.info(f"EPUB文件: {epub_filename}")
    if missing:
        logger.warning(f"缺失章节: {len(missing)}章")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

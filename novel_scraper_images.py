"""
小说爬虫 - 支持图片
- 爬取章节内容和插图
- 过滤"章节讨论"等无关内容
- 生成TXT和EPUB(带图片)格式
"""

import json
import time
import logging
import re
import os
import requests
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from bs4 import BeautifulSoup
from ebooklib import epub
from PIL import Image
import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('novel_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 进度文件
PROGRESS_FILE = 'novel_progress.json'
IMAGES_DIR = 'novel_images'


def create_driver():
    """创建浏览器"""
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


def clean_content(content):
    """清理章节内容，删除无关文字"""
    patterns = [
        r'章节讨论\s*\(\d+\).*?写第一条评论',
        r'章节讨论.*',
        r'写评论.*?写第一条评论',
        r'暂无评论来说说你的看法吧！.*',
        r'写第一条评论.*',
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)

    lines = content.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]

    return '\n'.join(cleaned_lines)


def download_image(url, session=None):
    """下载图片"""
    try:
        if session:
            response = session.get(url, timeout=30)
        else:
            response = requests.get(url, timeout=30, headers=config.HEADERS)

        if response.status_code == 200:
            return response.content
    except Exception as e:
        logger.error(f"Download image failed: {url}, Error: {e}")

    return None


def fetch_chapter(chapter_url, chapter_id, driver):
    """获取章节内容（包含图片）"""
    try:
        driver.get(chapter_url)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.chapter-item, div[class*="chapter"], div[class*="content"]')))
        time.sleep(2)

        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        # 查找章节内容区域
        chapter_div = soup.find('div', class_='chapter-item')
        if not chapter_div:
            chapter_div = soup.find('div', class_=re.compile(r'chapter|content|reader'))

        if not chapter_div:
            return None

        # 获取标题
        title = chapter_div.get('data-chapter-title', '')
        if not title:
            title_elem = soup.find(['h1', 'h2'], class_=re.compile(r'title|chapter'))
            if title_elem:
                title = title_elem.get_text(strip=True)

        # 提取图片
        images = []
        img_tags = chapter_div.find_all('img')

        for idx, img in enumerate(img_tags):
            img_url = img.get('src') or img.get('data-src') or img.get('data-original')
            if img_url:
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = config.BASE_URL + img_url

                images.append({
                    'url': img_url,
                    'index': idx,
                    'placeholder': f'[IMAGE_{chapter_id}_{idx}]'
                })

                # 在文本中添加图片占位符
                img.replace_with(f'\n[IMAGE_{chapter_id}_{idx}]\n')

        # 处理换行
        for br in chapter_div.find_all('br'):
            br.replace_with('\n')

        # 获取文本内容
        content = chapter_div.get_text()
        content = clean_content(content)

        return {
            'id': chapter_id,
            'title': title,
            'content': content,
            'images': images
        }

    except Exception as e:
        logger.error(f"Fetch chapter failed ID={chapter_id}: {e}")
        return None


def load_progress():
    """加载进度"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'completed': [], 'chapters': [], 'images': {}}


def save_progress(progress):
    """保存进度"""
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Save progress failed: {e}")


def extract_chapter_number(title):
    """提取章节号"""
    patterns = [
        r'第(\d+)[话章]',
        r'(\d+)화',
        r'Chapter\s*(\d+)',
        r'EP\.?\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return int(match.group(1))
    return 0


def save_to_txt(chapters, filename):
    """保存为TXT格式（不含图片）"""
    logger.info(f"Generating TXT: {filename}")

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("重生路人甲成为天才\n")
        f.write("Author: Unknown\n\n")

        for ch in chapters:
            # 移除图片占位符
            content = re.sub(r'\[IMAGE_\d+_\d+\]', '', ch['content'])
            content = re.sub(r'\n{3,}', '\n\n', content)

            f.write(f"\n{ch['title']}\n\n")
            f.write(f"{content}\n")

        f.write(f"\n\nThe End\n")

    logger.info(f"TXT generated: {filename}")


def save_to_epub_with_images(chapters, filename, progress):
    """保存为EPUB格式（带图片）"""
    logger.info(f"Generating EPUB with images: {filename}")

    book = epub.EpubBook()
    book.set_identifier('rebirth_genius_with_images')
    book.set_title('重生路人甲成为天才')
    book.set_language('zh')
    book.add_author('Unknown')

    epub_chapters = []
    spine = ['nav']

    # 创建图片目录
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    # 下载图片的session
    session = requests.Session()
    session.headers.update(config.HEADERS)

    image_items = {}

    for i, ch in enumerate(chapters, 1):
        # 处理图片
        content_html = f'<h1>{ch["title"]}</h1>\n'

        paragraphs = ch['content'].split('\n')

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue

            # 检查是否是图片占位符
            img_match = re.match(r'\[IMAGE_(\d+)_(\d+)\]', p)
            if img_match:
                chapter_id = img_match.group(1)
                img_idx = img_match.group(2)
                img_key = f"{chapter_id}_{img_idx}"

                # 查找对应的图片URL
                img_url = None
                for img in ch.get('images', []):
                    if img['placeholder'] == p:
                        img_url = img['url']
                        break

                if img_url:
                    # 下载图片（如果还没下载）
                    if img_key not in progress.get('images', {}):
                        logger.info(f"  Downloading image: {img_key}")
                        img_data = download_image(img_url, session)

                        if img_data:
                            # 保存到本地
                            img_filename = f"{img_key}.jpg"
                            img_path = os.path.join(IMAGES_DIR, img_filename)

                            with open(img_path, 'wb') as f:
                                f.write(img_data)

                            progress['images'][img_key] = img_filename
                            save_progress(progress)

                    # 添加图片到EPUB
                    if img_key in progress.get('images', {}):
                        img_filename = progress['images'][img_key]
                        img_path = os.path.join(IMAGES_DIR, img_filename)

                        if os.path.exists(img_path) and img_key not in image_items:
                            with open(img_path, 'rb') as f:
                                img_data = f.read()

                            epub_img = epub.EpubImage()
                            epub_img.file_name = f'images/{img_filename}'
                            epub_img.media_type = 'image/jpeg'
                            epub_img.content = img_data

                            book.add_item(epub_img)
                            image_items[img_key] = epub_img.file_name

                        if img_key in image_items:
                            content_html += f'<p><img src="{image_items[img_key]}" alt="illustration"/></p>\n'
            else:
                content_html += f'<p>{p}</p>\n'

        # 创建章节
        chapter = epub.EpubHtml(
            title=ch['title'],
            file_name=f'chapter_{ch["number"]:03d}.xhtml',
            lang='zh'
        )
        chapter.content = content_html

        book.add_item(chapter)
        epub_chapters.append(chapter)
        spine.append(chapter)

        if (i % 50 == 0) or (i == len(chapters)):
            logger.info(f"  EPUB progress: {i}/{len(chapters)}")

    # 添加目录和导航
    book.toc = epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    # 添加CSS
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
    img {
        max-width: 100%;
        height: auto;
        display: block;
        margin: 1em auto;
    }
    '''

    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style
    )
    book.add_item(nav_css)

    epub.write_epub(filename, book, {})

    logger.info(f"EPUB generated: {filename}")


def main():
    logger.info("=" * 60)
    logger.info("Novel Scraper with Images")
    logger.info("=" * 60)

    # 读取章节列表
    chapters_file = 'chapters_list.json'
    if not os.path.exists(chapters_file):
        logger.error(f"Chapters file not found: {chapters_file}")
        logger.info("Please run get_chapters.py first!")
        return

    with open(chapters_file, 'r', encoding='utf-8') as f:
        chapters_data = json.load(f)

    logger.info(f"Total chapters in list: {len(chapters_data)}")

    # 加载进度
    progress = load_progress()
    completed_ids = set(progress['completed'])
    chapters_content = progress['chapters']

    if completed_ids:
        logger.info(f"Resuming from {len(completed_ids)} completed chapters...")

    # 过滤未完成的章节
    remaining = [ch for ch in chapters_data if ch['id'] not in completed_ids]
    logger.info(f"Remaining chapters: {len(remaining)}")

    if remaining:
        # 开始爬取
        driver = None

        try:
            logger.info("Starting browser...")
            driver = create_driver()
            logger.info("Browser started")

            for i, ch in enumerate(remaining, 1):
                chapter_id = ch['id']
                chapter_url = ch['url']

                logger.info(f"[{len(completed_ids) + i}/{len(chapters_data)}] Fetching ID={chapter_id}")

                content = fetch_chapter(chapter_url, chapter_id, driver)

                if content:
                    chapters_content.append(content)
                    completed_ids.add(chapter_id)
                    logger.info(f"  Success: {content['title'][:30]}...")

                    # 每10章保存一次
                    if len(completed_ids) % 10 == 0:
                        progress['completed'] = list(completed_ids)
                        progress['chapters'] = chapters_content
                        save_progress(progress)
                        logger.info(f"  Progress saved ({len(completed_ids)}/{len(chapters_data)})")
                else:
                    logger.error(f"  Failed")

                time.sleep(config.REQUEST_DELAY)

        except KeyboardInterrupt:
            logger.info("\nInterrupted! Saving progress...")
            progress['completed'] = list(completed_ids)
            progress['chapters'] = chapters_content
            save_progress(progress)
            logger.info("Progress saved")
            return

        except Exception as e:
            logger.error(f"Error: {e}")

        finally:
            if driver:
                driver.quit()
                logger.info("Browser closed")

        # 保存最终进度
        progress['completed'] = list(completed_ids)
        progress['chapters'] = chapters_content
        save_progress(progress)

    # 处理章节
    logger.info("\n" + "=" * 60)
    logger.info("Processing chapters...")
    logger.info("=" * 60)

    processed = {}

    for ch in chapters_content:
        title = ch.get('title', '')
        content = ch.get('content', '')
        images = ch.get('images', [])

        chapter_num = extract_chapter_number(title)

        if chapter_num == 0:
            continue

        standard_title = f'重生路人甲成为天才 第{chapter_num}话'

        if chapter_num in processed:
            if len(content) > len(processed[chapter_num]['content']):
                processed[chapter_num] = {
                    'number': chapter_num,
                    'title': standard_title,
                    'content': content,
                    'images': images
                }
        else:
            processed[chapter_num] = {
                'number': chapter_num,
                'title': standard_title,
                'content': content,
                'images': images
            }

    sorted_chapters = sorted(processed.values(), key=lambda x: x['number'])

    logger.info(f"Processed chapters: {len(sorted_chapters)}")

    if sorted_chapters:
        logger.info(f"Chapter range: {sorted_chapters[0]['number']} - {sorted_chapters[-1]['number']}")

        # 检查缺失
        chapter_nums = set(ch['number'] for ch in sorted_chapters)
        max_num = max(chapter_nums)
        missing = sorted(set(range(1, max_num + 1)) - chapter_nums)

        if missing:
            logger.warning(f"Missing {len(missing)} chapters: {missing[:20]}")

        # 生成文件
        logger.info("\n" + "=" * 60)
        logger.info("Generating output files...")
        logger.info("=" * 60)

        txt_file = f"重生路人甲成为天才_{len(sorted_chapters)}章.txt"
        epub_file = f"重生路人甲成为天才_{len(sorted_chapters)}章.epub"

        save_to_txt(sorted_chapters, txt_file)
        save_to_epub_with_images(sorted_chapters, epub_file, progress)

        logger.info("\n" + "=" * 60)
        logger.info("Done!")
        logger.info("=" * 60)
        logger.info(f"Total chapters: {len(sorted_chapters)}")
        logger.info(f"TXT file: {txt_file}")
        logger.info(f"EPUB file: {epub_file}")
        if missing:
            logger.warning(f"Missing chapters: {len(missing)}")
        logger.info("=" * 60)
    else:
        logger.error("No chapters to process!")


if __name__ == "__main__":
    main()

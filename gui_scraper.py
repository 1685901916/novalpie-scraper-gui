import json
import queue
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

import requests
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from bs4 import BeautifulSoup
from ebooklib import epub
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', ROOT_DIR))
else:
    ROOT_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = ROOT_DIR
DEFAULT_OUTPUT_DIR = ROOT_DIR / 'output'
DEFAULT_OUTPUT_DIR.mkdir(exist_ok=True)
SCRIPTS_DIR = RESOURCE_DIR / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from novalpie_utils import create_driver as create_novalpie_driver
from novalpie_utils import load_auth_token as load_novalpie_auth_token
from novalpie_utils import load_cookies as load_novalpie_cookies
from novalpie_utils import load_local_storage as load_novalpie_local_storage
from novalpie_utils import normalize_text as normalize_novalpie_text

AUTH_TOKEN_FILE = ROOT_DIR / 'novalpie_auth_token.txt'
COOKIE_FILE = ROOT_DIR / 'novalpie_cookies.json'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'

@dataclass
class SiteContext:
    base_url: str
    detail_url: str
    novel_id: str

class NovalpieSession:
    def __init__(self, log: Callable[[str], None]):
        self.log = log
        self.driver = None

    def parse_context(self, detail_url: str) -> SiteContext:
        parsed = urlparse(detail_url.strip())
        if not parsed.scheme or not parsed.netloc:
            raise ValueError('请输入完整书页链接，例如 https://novalpie.cc/book/6/')
        if 'novalpie.cc' not in parsed.netloc.lower():
            raise ValueError('当前 GUI 先支持 novalpie.cc')
        match = re.search(r'/book/(\d+)', parsed.path)
        if not match:
            raise ValueError('书页链接格式应为 https://novalpie.cc/book/书籍ID/')
        novel_id = match.group(1)
        base_url = f'{parsed.scheme}://{parsed.netloc}'
        return SiteContext(base_url=base_url, detail_url=f'{base_url}/book/{novel_id}/', novel_id=novel_id)

    def open_browser(self, detail_url: str) -> None:
        context = self.parse_context(detail_url)
        self.close()
        self.driver = create_novalpie_driver(
            headless=False,
            base_url=context.base_url,
            cookies=load_novalpie_cookies(),
            auth_token=load_novalpie_auth_token(),
            local_storage=load_novalpie_local_storage(),
        )
        self.driver.get(context.detail_url)
        self.log('已打开 novalpie 浏览器。')
        self.log('优先使用本地 token 进入书页，不建议直接打开 login 页。')

    def ensure_browser(self, detail_url: str) -> None:
        if self.driver is None:
            self.open_browser(detail_url)

    def close(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def get_token_from_browser(self) -> str:
        if self.driver is None:
            return ''
        try:
            token = self.driver.execute_script("return localStorage.getItem('auth_token') || '';")
            return (token or '').strip()
        except Exception:
            return ''

    def sync_token_to_file(self) -> str:
        token = self.get_token_from_browser()
        if token:
            AUTH_TOKEN_FILE.write_text(token, encoding='utf-8')
            self.log(f'已同步 token 到 {AUTH_TOKEN_FILE}')
        return token

    def save_cookies(self) -> int:
        if self.driver is None:
            return 0
        try:
            cookies = self.driver.get_cookies()
            COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding='utf-8')
            self.log(f'已保存 cookies 到 {COOKIE_FILE}')
            return len(cookies)
        except Exception:
            return 0

    def wait_until_ready(self, detail_url: str, progress: Callable[[str], None]) -> SiteContext:
        context = self.parse_context(detail_url)
        self.ensure_browser(detail_url)
        driver = self.driver
        if driver is None:
            raise RuntimeError('浏览器未启动。')
        deadline = time.time() + 120
        while time.time() < deadline:
            driver.get(context.detail_url)
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-chapter-id]')))
                progress('已进入书页，章节按钮可见。')
                self.sync_token_to_file()
                self.save_cookies()
                return context
            except TimeoutException:
                pass
            html = driver.page_source[:6000]
            if '/login' in driver.current_url:
                progress('当前还在登录页。请先在浏览器里登录。')
            elif 'Turnstile' in html or 'Cloudflare' in html or '验证失败' in html:
                progress('命中验证码。请先在浏览器窗口里手动处理。')
            else:
                progress('等待书页与目录加载...')
            time.sleep(2)
        raise TimeoutError('等待书页超时。请确认已登录并进入书本详情页。')

class NovalpieScraper:
    def __init__(self, session: NovalpieSession, log: Callable[[str], None]):
        self.session = session
        self.log = log

    def scrape(self, detail_url: str, output_dir: Path, export_txt: bool, export_epub: bool, export_json: bool, workers: int, delay: float, expected_chapters: int, progress: Callable[[str], None]) -> List[Path]:
        context = self.session.wait_until_ready(detail_url, progress)
        driver = self.session.driver
        if driver is None:
            raise RuntimeError('浏览器未初始化。')
        title = self._extract_book_title(driver, context)
        progress(f'书名: {title}')
        page_expected = self._extract_expected_count(driver)
        if page_expected > 0:
            progress(f'页面显示章节数: {page_expected}')
        if expected_chapters <= 0:
            expected_chapters = page_expected
        if expected_chapters > 0:
            progress(f'目标章节数: {expected_chapters}')
        cover_url = self._extract_cover_url(driver)
        if cover_url:
            progress(f'检测到封面地址: {cover_url}')
        chapters = self._collect_chapters(driver, context, expected_chapters, progress)
        if not chapters:
            raise RuntimeError('没有抓到目录。')
        if expected_chapters > 0 and len(chapters) < expected_chapters:
            raise RuntimeError(f'目录不完整，只抓到 {len(chapters)}/{expected_chapters} 章，已停止正文抓取。')
        progress(f'开始抓取正文，共 {len(chapters)} 章，线程数 {workers}')
        contents = self._fetch_all_chapters(context, chapters, workers, delay, progress)
        if not contents:
            raise RuntimeError('没有抓到正文内容。')
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_title = self._safe_filename(title)
        saved_paths = []
        cover_path = None
        if cover_url:
            cover_path = output_dir / f'{safe_title}_cover.jpg'
            if self._download_binary(cover_url, cover_path, referer=context.detail_url):
                saved_paths.append(cover_path)
        if export_txt:
            txt_path = output_dir / f'{safe_title}.txt'
            self._save_txt(title, contents, txt_path)
            saved_paths.append(txt_path)
        if export_epub:
            epub_path = output_dir / f'{safe_title}.epub'
            self._save_epub(title, contents, epub_path, cover_path)
            saved_paths.append(epub_path)
        if export_json:
            json_path = output_dir / f'{safe_title}_chapters.json'
            json_path.write_text(json.dumps({'book_id': context.novel_id, 'title': title, 'chapters': contents}, ensure_ascii=False, indent=2), encoding='utf-8')
            saved_paths.append(json_path)
        return saved_paths

    def _extract_book_title(self, driver, context: SiteContext) -> str:
        for selector in ['h1.text-xl', 'h1', "meta[property='og:title']", 'title']:
            try:
                if selector.startswith('meta'):
                    value = driver.execute_script("const el=document.querySelector(arguments[0]); return el ? (el.content || '') : '';", selector)
                    text = (value or '').strip()
                else:
                    text = (driver.find_element(By.CSS_SELECTOR, selector).text or '').strip()
                if text:
                    return text.replace(' - 书本详情', '').strip()
            except Exception:
                continue
        return f'novalpie_{context.novel_id}'

    def _extract_expected_count(self, driver) -> int:
        try:
            text = driver.find_element(By.TAG_NAME, 'body').text
        except Exception:
            return 0
        for pattern in [r'章节\s*(\d+)\s*章', r'共\s*(\d+)\s*章', r'(\d+)\s*章']:
            match = re.search(pattern, text)
            if match:
                try:
                    value = int(match.group(1))
                    if value > 0:
                        return value
                except Exception:
                    pass
        return 0

    def _find_cover_element(self, driver):
        for selector in ['main .card button img', 'main .card img.w-full', 'main .card img']:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            except Exception:
                continue
            for element in elements:
                try:
                    w = int(element.get_attribute('naturalWidth') or 0)
                    h = int(element.get_attribute('naturalHeight') or 0)
                    if w >= 150 and h >= 200:
                        return element
                except Exception:
                    continue
        return None

    def _extract_cover_url(self, driver) -> str:
        element = self._find_cover_element(driver)
        if element is None:
            return ''
        for attr in ['currentSrc', 'src', 'data-src']:
            try:
                value = driver.execute_script("const el=arguments[0]; const attr=arguments[1]; if (attr==='currentSrc') return el.currentSrc || ''; return el.getAttribute(attr) || '';", element, attr)
            except Exception:
                value = ''
            value = (value or '').strip()
            if value and not value.startswith('blob:') and not value.startswith('data:'):
                return value
        return ''

    def _click_catalog_tab(self, driver) -> None:
        for element in driver.find_elements(By.TAG_NAME, 'button'):
            text = (element.text or '').strip()
            if text.startswith('目录') or '目录' in text:
                try:
                    driver.execute_script('arguments[0].click();', element)
                    return
                except Exception:
                    continue

    def _click_expand_button(self, driver) -> None:
        script = """
        const nodes = Array.from(document.querySelectorAll('button, a, span, div'));
        for (const node of nodes) {
            const text = (node.textContent || '').trim();
            if (text === '更多' || text === 'More' || text.includes('展开')) {
                node.click();
                return true;
            }
        }
        return false;
        """
        try:
            driver.execute_script(script)
        except Exception:
            pass

    def _scroll_catalog(self, driver, strong: bool) -> None:
        step = 1500 if strong else 800
        script = """
        const step = arguments[0];
        const scroller = document.querySelector('.vue-recycle-scroller');
        if (scroller) {
            scroller.scrollTop += step;
            scroller.dispatchEvent(new Event('scroll', { bubbles: true }));
            scroller.dispatchEvent(new WheelEvent('wheel', { deltaY: step, bubbles: true }));
            return true;
        }
        const buttons = document.querySelectorAll('button[data-chapter-id]');
        if (buttons.length) buttons[buttons.length - 1].scrollIntoView({ block: 'end' });
        window.scrollBy(0, step);
        return false;
        """
        try:
            driver.execute_script(script, step)
            if strong:
                driver.execute_script('window.scrollBy(0, -120);')
        except Exception:
            pass

    def _extract_chapter_title_from_button(self, button, fallback_index: int) -> str:
        try:
            title = (button.find_element(By.CSS_SELECTOR, '.font-medium').text or '').strip()
            if title:
                return title
        except Exception:
            pass
        for line in [(x or '').strip() for x in (button.text or '').splitlines()]:
            if line and not line.startswith('第'):
                return line
        return f'第{fallback_index}章'

    def _clean_chapter_title(self, title: str) -> str:
        title = (title or '').strip()
        if not title:
            return ''
        title = re.sub(r'^\d+\.\s*', '', title).strip()
        title = re.sub(r'^第\s*\d+\s*章\s*', '', title).strip()
        return title

    def _format_chapter_title(self, chapter_number: int, title: str) -> str:
        cleaned = self._clean_chapter_title(title)
        if cleaned == '序章':
            return cleaned
        if chapter_number > 0:
            return f'第{chapter_number}章 {cleaned or "未命名章节"}'.strip()
        return cleaned or '未命名章节'

    def _build_request_headers(self) -> Dict[str, str]:
        headers = {'User-Agent': USER_AGENT, 'Referer': 'https://novalpie.cc/'}
        token = load_novalpie_auth_token().strip()
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return headers

    def _normalize_api_chapters(self, raw, context: SiteContext) -> List[Dict[str, str]]:
        items = []
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            if isinstance(raw.get('data'), list):
                items = raw['data']
            elif raw.get('success'):
                numeric_keys = [key for key in raw.keys() if str(key).isdigit()]
                if numeric_keys:
                    items = [raw[key] for key in sorted(numeric_keys, key=lambda value: int(value))]
        chapters = []
        for fallback_order, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            chapter_id = str(item.get('id') or '').strip()
            if not chapter_id:
                continue
            chapter_number = item.get('chapterNumber') or item.get('chapter_number') or fallback_order
            title = (item.get('title') or '').strip()
            try:
                chapter_number = int(chapter_number)
            except Exception:
                chapter_number = fallback_order
            try:
                order = max(0, int(chapter_number) - 1)
            except Exception:
                order = fallback_order - 1
            chapters.append(
                {
                    'id': chapter_id,
                    'title': self._format_chapter_title(chapter_number, title),
                    'raw_title': title,
                    'chapter_number': chapter_number,
                    'order': order,
                    'url': f'{context.base_url}/book/{context.novel_id}/{chapter_id}',
                }
            )
        chapters.sort(key=lambda item: (item['order'], int(item['id'])))
        return chapters

    def _collect_chapters_via_browser_fetch(self, context: SiteContext) -> List[Dict[str, str]]:
        driver = self.session.driver
        if driver is None:
            return []
        try:
            result = driver.execute_async_script(
                """
                const url = arguments[0];
                const done = arguments[arguments.length - 1];
                fetch(url, { credentials: 'include' })
                  .then(async (resp) => {
                    const text = await resp.text();
                    done({ ok: resp.ok, text });
                  })
                  .catch((error) => done({ ok: false, text: String(error || '') }));
                """,
                f'{context.base_url}/api/novels/{context.novel_id}/chapters',
            )
            if not result or not result.get('ok'):
                return []
            return self._normalize_api_chapters(json.loads(result.get('text') or '[]'), context)
        except Exception:
            return []

    def _collect_chapters_via_api(self, context: SiteContext, progress: Callable[[str], None]) -> List[Dict[str, str]]:
        url = f'{context.base_url}/api/novels/{context.novel_id}/chapters'
        last_error = ''
        for attempt in range(1, 4):
            try:
                response = requests.get(
                    url,
                    headers=self._build_request_headers(),
                    cookies=load_novalpie_cookies(),
                    timeout=25,
                )
                response.raise_for_status()
                chapters = self._normalize_api_chapters(response.json(), context)
                if chapters:
                    return chapters
                last_error = '接口返回为空'
            except Exception as exc:
                last_error = str(exc)
                progress(f'目录接口尝试 {attempt}/3 失败: {last_error}')
                time.sleep(1.2 * attempt)
        browser_chapters = self._collect_chapters_via_browser_fetch(context)
        if browser_chapters:
            return browser_chapters
        if last_error:
            progress(f'目录接口最终失败，改用页面滚动兜底: {last_error}')
        return []

    def _collect_chapters(self, driver, context: SiteContext, expected_chapters: int, progress: Callable[[str], None]) -> List[Dict[str, str]]:
        api_chapters = self._collect_chapters_via_api(context, progress)
        if api_chapters:
            if expected_chapters > 0:
                progress(f'目录接口返回: {len(api_chapters)}/{expected_chapters} 章')
            else:
                progress(f'目录接口返回: {len(api_chapters)} 章')
            if expected_chapters <= 0 or len(api_chapters) >= expected_chapters:
                return api_chapters
            progress('目录接口数量不足，回退到页面滚动补抓。')

        driver.get(context.detail_url)
        time.sleep(1.5)
        self._click_catalog_tab(driver)
        time.sleep(1)
        self._click_expand_button(driver)
        time.sleep(1)
        all_chapters = {}
        last_count = 0
        no_change = 0
        order = 0
        max_stale = 120 if expected_chapters > 0 else 40
        for index in range(1000):
            buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]')
            for button in buttons:
                chapter_id = (button.get_attribute('data-chapter-id') or '').strip()
                if not chapter_id or chapter_id in all_chapters:
                    continue
                all_chapters[chapter_id] = {
                    'id': chapter_id,
                    'title': self._extract_chapter_title_from_button(button, order + 1),
                    'order': order,
                    'url': f'{context.base_url}/book/{context.novel_id}/{chapter_id}',
                }
                order += 1
            count = len(all_chapters)
            if index % 10 == 0:
                if expected_chapters > 0:
                    progress(f'收集目录: {count}/{expected_chapters} 章')
                else:
                    progress(f'收集目录: {count} 章')
            if expected_chapters > 0 and count >= expected_chapters:
                break
            if count == last_count:
                no_change += 1
            else:
                no_change = 0
                last_count = count
            if no_change >= max_stale:
                break
            self._scroll_catalog(driver, strong=(expected_chapters > 0 and count < expected_chapters and no_change > 20))
            time.sleep(0.2)
        chapters = list(all_chapters.values())
        chapters.sort(key=lambda item: item['order'])
        if expected_chapters > 0:
            progress(f'目录收集完成: {len(chapters)}/{expected_chapters} 章')
        else:
            progress(f'目录收集完成: {len(chapters)} 章')
        return chapters

    def _fetch_all_chapters(self, context: SiteContext, chapters: List[Dict[str, str]], workers: int, delay: float, progress: Callable[[str], None]) -> List[Dict[str, str]]:
        cookies = load_novalpie_cookies()
        auth_token = load_novalpie_auth_token()
        local_storage = load_novalpie_local_storage()
        results = []
        total = len(chapters)
        thread_local = threading.local()
        drivers = []
        drivers_lock = threading.Lock()

        def get_driver():
            driver = getattr(thread_local, 'driver', None)
            if driver is None:
                driver = create_novalpie_driver(headless=True, base_url=context.base_url, cookies=cookies, auth_token=auth_token, local_storage=local_storage)
                thread_local.driver = driver
                with drivers_lock:
                    drivers.append(driver)
            return driver

        def fetch_one(chapter: Dict[str, str]) -> Optional[Dict[str, str]]:
            driver = get_driver()
            try:
                driver.get(chapter['url'])
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.chapter-item')))
                if delay > 0:
                    time.sleep(delay)
                soup = BeautifulSoup(driver.page_source, 'lxml')
                chapter_div = soup.select_one(f"div.chapter-item[data-chapter-id='{chapter['id']}']") or soup.select_one('div.chapter-item')
                if chapter_div is None:
                    return None
                for selector in ['div.chapter-comments', 'div.chapter-navigation-toolbar', 'div.chapter-separator']:
                    for node in chapter_div.select(selector):
                        node.decompose()
                for heading in chapter_div.find_all(['h1', 'h2', 'h3']):
                    heading.decompose()
                for br in chapter_div.find_all('br'):
                    br.replace_with('\n')
                images = []
                for image_index, node in enumerate(chapter_div.select('img.chapter-image, img'), start=1):
                    image_url = ''
                    for attr in ['src', 'data-src', 'data-original']:
                        value = (node.get(attr) or '').strip()
                        if value:
                            image_url = value
                            break
                    if not image_url or image_url.startswith('blob:') or image_url.startswith('data:'):
                        continue
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    elif image_url.startswith('/'):
                        image_url = context.base_url + image_url
                    placeholder = f"[IMAGE_{chapter['id']}_{image_index}]"
                    images.append({'url': image_url, 'placeholder': placeholder})
                    node.replace_with(f'\n{placeholder}\n')
                title = self._format_chapter_title(
                    int(chapter.get('chapter_number') or 0),
                    chapter.get('raw_title') or chapter_div.get('data-chapter-title') or chapter['title'],
                )
                content = normalize_novalpie_text(chapter_div.get_text())
                return {
                    'id': chapter['id'],
                    'title': title,
                    'raw_title': chapter.get('raw_title') or chapter_div.get('data-chapter-title') or '',
                    'chapter_number': chapter.get('chapter_number') or 0,
                    'content': content,
                    'images': images,
                    'order': chapter['order'],
                    'url': chapter['url'],
                }
            except Exception:
                return None

        try:
            with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
                future_map = {executor.submit(fetch_one, chapter): chapter for chapter in chapters}
                done = 0
                for future in as_completed(future_map):
                    chapter = future_map[future]
                    done += 1
                    item = future.result()
                    if item:
                        results.append(item)
                        progress(f"抓正文 {done}/{total}: {chapter['title']}")
                    else:
                        progress(f"抓正文失败 {done}/{total}: {chapter['title']}")
        finally:
            for driver in drivers:
                try:
                    driver.quit()
                except Exception:
                    pass
        results.sort(key=lambda item: item['order'])
        return results

    def _save_txt(self, book_title: str, chapters: List[Dict[str, str]], output_path: Path) -> None:
        with output_path.open('w', encoding='utf-8') as handle:
            handle.write(f'{book_title}\n\n')
            for chapter in chapters:
                handle.write(f"{chapter['title']}\n")
                handle.write('=' * 50 + '\n')
                plain = re.sub(r'\[IMAGE_[^\]]+\]', '', chapter['content'])
                handle.write(f'{plain}\n\n')

    def _save_epub(self, book_title: str, chapters: List[Dict[str, str]], output_path: Path, cover_path: Optional[Path]) -> None:
        book = epub.EpubBook()
        book.set_identifier(self._safe_filename(book_title))
        book.set_title(book_title)
        book.set_language('zh')
        book.add_author('novalpie')
        if cover_path and cover_path.exists():
            try:
                book.set_cover(cover_path.name, cover_path.read_bytes())
            except Exception:
                pass
        epub_chapters = []
        spine = ['nav']
        image_items = {}
        for chapter_index, chapter in enumerate(chapters, start=1):
            item = epub.EpubHtml(title=chapter['title'], file_name=f'chapter_{chapter_index:04d}.xhtml', lang='zh')
            image_map = {}
            for image_index, image in enumerate(chapter.get('images', []), start=1):
                image_url = image.get('url', '')
                placeholder = image.get('placeholder', '')
                if not image_url or not placeholder:
                    continue
                image_name = f'img_{chapter_index:04d}_{image_index:03d}.jpg'
                if image_name not in image_items:
                    temp_path = output_path.parent / image_name
                    if self._download_binary(image_url, temp_path, referer=chapter['url']):
                        image_item = epub.EpubItem(uid=image_name, file_name=f'images/{image_name}', media_type='image/jpeg', content=temp_path.read_bytes())
                        book.add_item(image_item)
                        image_items[image_name] = image_item.file_name
                        try:
                            temp_path.unlink()
                        except Exception:
                            pass
                if image_name in image_items:
                    image_map[placeholder] = image_items[image_name]
            content_html = f"<h1>{escape(chapter['title'])}</h1>"
            for line in chapter['content'].split('\n'):
                text = line.strip()
                if not text:
                    continue
                if text in image_map:
                    content_html += f'<p><img src="{escape(image_map[text])}" alt="{escape(chapter["title"])} image"/></p>'
                else:
                    content_html += f'<p>{escape(text)}</p>'
            item.content = content_html
            book.add_item(item)
            epub_chapters.append(item)
            spine.append(item)
        book.toc = epub_chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = spine
        epub.write_epub(str(output_path), book, {})

    def _download_binary(self, url: str, output_path: Path, referer: str) -> bool:
        try:
            response = requests.get(url, headers={'User-Agent': USER_AGENT, 'Referer': referer}, cookies=load_novalpie_cookies(), timeout=30)
            if response.ok and response.content:
                output_path.write_bytes(response.content)
                return True
        except Exception:
            return False
        return False

    def _safe_filename(self, value: str) -> str:
        return (re.sub(r'[\\/:*?"<>|]+', '_', value).strip() or 'novalpie_novel')[:120]

class ScraperApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('小说爬虫 GUI')
        self.root.geometry('1020x780')
        self.log_queue = queue.Queue()
        self.worker = None
        self.url_var = tk.StringVar(value='https://novalpie.cc/book/6/')
        self.output_dir_var = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.expected_chapters_var = tk.IntVar(value=0)
        self.status_var = tk.StringVar(value='等待开始')
        self.token_var = tk.StringVar(value=self._short_token(load_novalpie_auth_token()))
        self.workers_var = tk.IntVar(value=6)
        self.delay_var = tk.DoubleVar(value=0.15)
        self.export_txt_var = tk.BooleanVar(value=True)
        self.export_epub_var = tk.BooleanVar(value=True)
        self.export_json_var = tk.BooleanVar(value=True)
        self.session = NovalpieSession(self._enqueue_log)
        self.scraper = NovalpieScraper(self.session, self._enqueue_log)
        self._build_ui()
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self.root.after(200, self._flush_logs)

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text='书页链接').pack(anchor=tk.W)
        ttk.Entry(frame, textvariable=self.url_var).pack(fill=tk.X, pady=(6, 10))
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row, text='预期章节数').pack(side=tk.LEFT)
        ttk.Spinbox(row, from_=0, to=5000, textvariable=self.expected_chapters_var, width=8).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(row, text='0 表示自动读取页面章节数；不完整就停止，不再抓正文。', foreground='#666').pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(frame, text='导出目录').pack(anchor=tk.W)
        out_row = ttk.Frame(frame)
        out_row.pack(fill=tk.X, pady=(6, 10))
        ttk.Entry(out_row, textvariable=self.output_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(out_row, text='选择目录', command=self._choose_output_dir).pack(side=tk.LEFT, padx=(8, 0))
        token_row = ttk.Frame(frame)
        token_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(token_row, text='当前 token').pack(side=tk.LEFT)
        ttk.Label(token_row, textvariable=self.token_var, foreground='#1f4f99').pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(token_row, text='从浏览器同步 Token', command=self._sync_token).pack(side=tk.LEFT, padx=(12, 0))
        option_row = ttk.Frame(frame)
        option_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Checkbutton(option_row, text='TXT', variable=self.export_txt_var).pack(side=tk.LEFT)
        ttk.Checkbutton(option_row, text='EPUB', variable=self.export_epub_var).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Checkbutton(option_row, text='JSON', variable=self.export_json_var).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(option_row, text='并发线程').pack(side=tk.LEFT, padx=(20, 4))
        ttk.Spinbox(option_row, from_=1, to=16, textvariable=self.workers_var, width=5).pack(side=tk.LEFT)
        ttk.Label(option_row, text='章节延迟(秒)').pack(side=tk.LEFT, padx=(16, 4))
        ttk.Spinbox(option_row, from_=0.0, to=2.0, increment=0.05, textvariable=self.delay_var, width=6).pack(side=tk.LEFT)
        ttk.Label(frame, text='说明: 目录必须完整才会开始正文抓取。封面取详情页真实地址，正文图片尽量写入 EPUB。', foreground='#555').pack(anchor=tk.W, pady=(0, 12))
        button_row = ttk.Frame(frame)
        button_row.pack(fill=tk.X, pady=(0, 12))
        self.open_button = ttk.Button(button_row, text='打开书页浏览器', command=self._open_browser)
        self.open_button.pack(side=tk.LEFT)
        self.start_button = ttk.Button(button_row, text='开始爬取', command=self._start_scrape)
        self.start_button.pack(side=tk.LEFT, padx=8)
        ttk.Button(button_row, text='打开导出目录', command=self._open_output_dir).pack(side=tk.LEFT)
        ttk.Button(button_row, text='关闭浏览器', command=self._close_browser).pack(side=tk.LEFT, padx=8)
        ttk.Label(frame, textvariable=self.status_var).pack(anchor=tk.W, pady=(0, 8))
        self.log_box = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=32)
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.configure(state=tk.DISABLED)

    def _choose_output_dir(self):
        selected = filedialog.askdirectory(initialdir=self.output_dir_var.get() or str(DEFAULT_OUTPUT_DIR))
        if selected:
            self.output_dir_var.set(selected)

    def _open_output_dir(self):
        path = Path(self.output_dir_var.get().strip() or str(DEFAULT_OUTPUT_DIR))
        path.mkdir(parents=True, exist_ok=True)
        import os
        os.startfile(str(path))

    def _open_browser(self):
        try:
            self.session.open_browser(self.url_var.get().strip())
            self.status_var.set('浏览器已打开')
            self._refresh_token_display()
        except Exception as exc:
            messagebox.showerror('打开失败', str(exc))

    def _sync_token(self):
        token = self.session.sync_token_to_file()
        self._refresh_token_display(token)
        if token:
            self.status_var.set('Token 已同步')
        else:
            messagebox.showwarning('未获取到 Token', '当前浏览器 localStorage 里没有 auth_token。')

    def _refresh_token_display(self, token=None):
        current = token if token is not None else load_novalpie_auth_token()
        self.token_var.set(self._short_token(current))

    def _short_token(self, token: str) -> str:
        token = (token or '').strip()
        if not token:
            return '未找到'
        if len(token) <= 20:
            return token
        return f'{token[:16]}...{token[-8:]}'

    def _set_busy(self, busy: bool):
        state = tk.DISABLED if busy else tk.NORMAL
        self.open_button.configure(state=state)
        self.start_button.configure(state=state)

    def _start_scrape(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo('运行中', '当前已有任务在执行。')
            return
        if not (self.export_txt_var.get() or self.export_epub_var.get() or self.export_json_var.get()):
            messagebox.showerror('错误', '至少选择一种导出格式。')
            return
        self._set_busy(True)
        self.status_var.set('正在爬取')
        self.worker = threading.Thread(target=self._run_scrape, daemon=True)
        self.worker.start()

    def _run_scrape(self):
        try:
            paths = self.scraper.scrape(
                detail_url=self.url_var.get().strip(),
                output_dir=Path(self.output_dir_var.get().strip() or str(DEFAULT_OUTPUT_DIR)),
                export_txt=self.export_txt_var.get(),
                export_epub=self.export_epub_var.get(),
                export_json=self.export_json_var.get(),
                workers=max(1, int(self.workers_var.get())),
                delay=max(0.0, float(self.delay_var.get())),
                expected_chapters=max(0, int(self.expected_chapters_var.get())),
                progress=self._enqueue_log,
            )
            self._enqueue_log('导出完成:')
            for path in paths:
                self._enqueue_log(str(path))
            self.root.after(0, lambda: self.status_var.set('已完成'))
            self.root.after(0, lambda: self._refresh_token_display())
            self.root.after(0, lambda: messagebox.showinfo('完成', '导出完成，请看日志中的文件路径。'))
        except Exception as exc:
            self._enqueue_log(f'任务失败: {exc}')
            self.root.after(0, lambda: self.status_var.set('失败'))
            self.root.after(0, lambda: messagebox.showerror('任务失败', str(exc)))
        finally:
            self.root.after(0, lambda: self._set_busy(False))

    def _close_browser(self):
        self.session.close()
        self.status_var.set('浏览器已关闭')
        self._enqueue_log('浏览器已关闭')

    def _enqueue_log(self, message: str):
        self.log_queue.put(f"[{time.strftime('%H:%M:%S')}] {message}")

    def _flush_logs(self):
        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_box.configure(state=tk.NORMAL)
            self.log_box.insert(tk.END, item + '\n')
            self.log_box.see(tk.END)
            self.log_box.configure(state=tk.DISABLED)
        self.root.after(200, self._flush_logs)

    def _on_close(self):
        self.session.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    style = ttk.Style(root)
    if 'vista' in style.theme_names():
        style.theme_use('vista')
    ScraperApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()

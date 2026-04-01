"""
自动获取所有535章的章节列表
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
import time
import json
import config

def get_all_chapters_auto():
    """自动滚动并获取所有章节"""

    options = EdgeOptions()
    # 不使用无头模式，方便观察
    # options.add_argument('--headless')
    options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

    driver = webdriver.Edge(options=options)

    try:
        print("正在访问详情页...")
        driver.get(config.BASE_URL)

        # 添加Cookie
        for name, value in config.COOKIES.items():
            driver.add_cookie({'name': name, 'value': value})

        driver.get(config.DETAIL_URL)

        # 等待页面加载
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-chapter-id]')))
        time.sleep(3)

        print("开始自动滚动收集章节...")

        # 找到章节列表的滚动容器
        print("查找章节列表滚动容器...")
        try:
            # 尝试多种可能的选择器
            scroll_container = None
            selectors = [
                "div.max-h-60vh",  # 从截图中看到的class
                "div[class*='overflow-y-auto']",  # 虚拟滚动容器
                "div[class*='max-h']",
                "div[class*='overflow']",
                "div[class*='chapter']"
            ]

            for selector in selectors:
                try:
                    container = driver.find_element(By.CSS_SELECTOR, selector)
                    if container:
                        scroll_container = container
                        print(f"找到滚动容器: {selector}")
                        break
                except:
                    continue

            if not scroll_container:
                print("未找到特定滚动容器，将滚动整个页面")

        except Exception as e:
            print(f"查找容器时出错: {e}")
            scroll_container = None

        # 边滚动边收集章节
        all_chapters = {}
        last_count = 0
        no_change_count = 0
        max_no_change = 80  # 优化：从150改为80，平衡效率和可靠性
        max_scroll_count = 500  # 新增：防止死循环
        scroll_count = 0

        print("开始边滚动边收集章节ID...")

        while no_change_count < max_no_change:
            # 阶梯式滚动策略：根据滚动次数动态调整参数
            if scroll_count < 50:
                scroll_increment = 800
                delay = 0.3
            elif scroll_count < 200:
                scroll_increment = 500
                delay = 0.5
            else:
                scroll_increment = 300
                delay = 0.6

            # 获取当前可见的所有章节按钮
            buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]')

            # 立即收集当前可见的章节信息
            new_found = 0
            for btn in buttons:
                try:
                    chapter_id = btn.get_attribute('data-chapter-id')
                    if chapter_id and chapter_id not in all_chapters:
                        try:
                            title_elem = btn.find_element(By.CSS_SELECTOR, '.font-medium')
                            title = title_elem.text.strip()
                        except:
                            title = f"第{len(all_chapters) + 1}章"

                        all_chapters[chapter_id] = {
                            'id': chapter_id,
                            'title': title
                        }
                        new_found += 1
                except:
                    continue

            current_count = len(all_chapters)

            # 每10次滚动显示一次进度
            if scroll_count % 10 == 0:
                progress_rate = (current_count / 535) * 100
                print(f"[{scroll_count:3d}] 已收集 {current_count:3d}/535 ({progress_rate:5.1f}%) | "
                      f"本轮新增 {new_found:2d} | 无变化 {no_change_count:2d}/{max_no_change}")

            # 检查是否有新章节（多条件停止判断）
            if current_count == last_count:
                no_change_count += 1
                # 多条件验证：章节数达标 + 滚动到底部
                if no_change_count >= max_no_change and current_count >= 508:
                    if scroll_container:
                        try:
                            scroll_height = driver.execute_script("return arguments[0].scrollHeight", scroll_container)
                            scroll_top = driver.execute_script("return arguments[0].scrollTop", scroll_container)
                            if scroll_top + 1000 >= scroll_height:
                                print(f"\n✓ 已到底部，停止滚动 (收集了 {current_count} 章)")
                                break
                        except:
                            pass
            else:
                no_change_count = 0
                last_count = current_count

            # 滚动策略：多层滚动，确保触发虚拟列表
            if buttons:
                try:
                    # 第1层：滚动到最后一个按钮（关键！触发虚拟列表加载）
                    last_button = buttons[-1]
                    driver.execute_script("arguments[0].scrollIntoView({block: 'end', behavior: 'smooth'});", last_button)
                    time.sleep(delay * 0.5)

                    # 第2层：如果有滚动容器，也滚动容器
                    if scroll_container:
                        driver.execute_script(f"""
                            arguments[0].scrollTop = arguments[0].scrollHeight;
                        """, scroll_container)
                        time.sleep(delay * 0.3)

                    # 第3层：滚动整个页面
                    driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
                    time.sleep(delay * 0.2)
                except Exception as e:
                    print(f"滚动失败: {e}")
                    pass

            scroll_count += 1

            # 检查是否达到最大滚动次数
            if scroll_count >= max_scroll_count:
                print(f"\n⚠ 达到最大滚动次数 {max_scroll_count}，停止")
                break

        # 转换为列表并排序
        chapters = list(all_chapters.values())

        # 按章节号排序
        def get_chapter_num(ch):
            import re
            match = re.search(r'\d+', ch['title'])
            return int(match.group()) if match else 0

        chapters.sort(key=get_chapter_num)

        print(f"\n成功收集到 {len(chapters)} 个章节！")

        # 保存到JSON文件
        with open('all_chapters.json', 'w', encoding='utf-8') as f:
            json.dump(chapters, f, ensure_ascii=False, indent=2)

        print(f"已保存到 all_chapters.json")

        # 转换为爬虫需要的格式
        chapter_list = []
        for ch in chapters:
            chapter_list.append({
                'id': ch['id'],
                'title': ch['title'],
                'url': f"{config.READER_URL}?novel={config.NOVEL_ID}&chapter={ch['id']}"
            })

        return chapter_list

    finally:
        driver.quit()


if __name__ == "__main__":
    chapters = get_all_chapters_auto()
    print(f"\n最终获取到 {len(chapters)} 个章节")

    if chapters:
        print("\n前5章:")
        for ch in chapters[:5]:
            print(f"  {ch['title']} - ID: {ch['id']}")

        print("\n后5章:")
        for ch in chapters[-5:]:
            print(f"  {ch['title']} - ID: {ch['id']}")

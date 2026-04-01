"""
测试滚动加载更多章节
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from bs4 import BeautifulSoup
import time
import config

# 创建浏览器
options = EdgeOptions()
# options.add_argument('--headless')  # 先不用无头模式，方便观察
options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

driver = webdriver.Edge(options=options)

try:
    # 添加Cookie
    driver.get(config.BASE_URL)
    for name, value in config.COOKIES.items():
        driver.add_cookie({'name': name, 'value': value})

    # 访问详情页
    driver.get(config.DETAIL_URL)

    # 等待页面加载
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-chapter-id]')))
    time.sleep(3)

    # 查找"更多"按钮或滚动容器
    html = driver.page_source
    soup = BeautifulSoup(html, 'lxml')

    # 检查章节数量提示
    print("查找章节总数提示...")
    chapter_count_elements = soup.find_all(text=lambda t: t and '章' in str(t) and ('共' in str(t) or '535' in str(t)))
    for elem in chapter_count_elements[:5]:
        print(f"  找到: {elem.strip()}")

    # 查找"更多"或"加载更多"按钮
    print("\n查找加载更多按钮...")
    more_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), '更多') or contains(text(), '加载')]")
    print(f"找到 {len(more_buttons)} 个可能的按钮")
    for btn in more_buttons[:3]:
        print(f"  按钮文本: {btn.text}")
        print(f"  按钮标签: {btn.tag_name}")

    # 查找章节容器
    print("\n查找章节容器...")
    chapter_containers = driver.find_elements(By.CSS_SELECTOR, "div[class*='chapter']")
    print(f"找到 {len(chapter_containers)} 个章节相关容器")

    # 尝试滚动
    print("\n尝试滚动加载...")
    buttons_before = len(driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]'))
    print(f"滚动前章节数: {buttons_before}")

    # 滚动到页面底部
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    buttons_after = len(driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]'))
    print(f"滚动后章节数: {buttons_after}")

    # 多次滚动尝试
    for i in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        buttons_now = len(driver.find_elements(By.CSS_SELECTOR, 'button[data-chapter-id]'))
        print(f"第{i+1}次滚动后: {buttons_now} 章")
        if buttons_now == buttons_after:
            break
        buttons_after = buttons_now

    print(f"\n最终获取到 {buttons_after} 个章节")

    # 保存完整HTML用于分析
    with open('full_page.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print("已保存完整页面到 full_page.html")

    input("\n按回车键关闭浏览器...")

finally:
    driver.quit()

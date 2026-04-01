"""
分析页面，查找章节数据来源
"""

from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re
import config

options = EdgeOptions()
options.add_argument(f'user-agent={config.HEADERS["User-Agent"]}')

driver = webdriver.Edge(options=options)

try:
    driver.get(config.BASE_URL)
    for name, value in config.COOKIES.items():
        driver.add_cookie({'name': name, 'value': value})

    print("访问详情页...")
    driver.get(config.DETAIL_URL)

    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-chapter-id]')))
    time.sleep(3)

    print("\n=== 方法1: 检查页面中的JavaScript变量 ===")

    # 尝试从window对象中获取数据
    try:
        nuxt_data = driver.execute_script("return window.__NUXT__;")
        if nuxt_data:
            print("找到 __NUXT__ 数据")
            with open('nuxt_data.json', 'w', encoding='utf-8') as f:
                json.dump(nuxt_data, f, ensure_ascii=False, indent=2)
            print("已保存到 nuxt_data.json")
    except Exception as e:
        print(f"未找到 __NUXT__: {e}")

    # 检查其他可能的全局变量
    print("\n=== 方法2: 检查Vue组件数据 ===")
    try:
        vue_data = driver.execute_script("""
            // 尝试获取Vue实例的数据
            const app = document.querySelector('#__nuxt');
            if (app && app.__vue_app__) {
                return 'Found Vue app';
            }
            return null;
        """)
        print(f"Vue数据: {vue_data}")
    except Exception as e:
        print(f"检查Vue失败: {e}")

    print("\n=== 方法3: 直接执行浏览器控制台脚本获取所有章节 ===")

    # 使用JavaScript直接获取所有章节（通过滚动）
    print("执行JavaScript收集脚本...")

    all_chapters_js = driver.execute_async_script("""
        const callback = arguments[arguments.length - 1];

        (async function() {
            const allChapters = new Map();
            let lastCount = 0;
            let noChangeCount = 0;

            // 找到滚动容器
            const scrollContainer = document.querySelector('.max-h-60vh') ||
                                   document.querySelector('[class*="overflow-y"]') ||
                                   document.querySelector('[class*="max-h"]');

            console.log('滚动容器:', scrollContainer);

            while (noChangeCount < 50) {
                // 收集当前章节
                const buttons = document.querySelectorAll('button[data-chapter-id]');
                buttons.forEach(btn => {
                    const id = btn.getAttribute('data-chapter-id');
                    const titleDiv = btn.querySelector('.font-medium');
                    const title = titleDiv ? titleDiv.textContent.trim() : '';
                    if (id) {
                        allChapters.set(id, {id, title});
                    }
                });

                const currentCount = allChapters.size;
                console.log(`已收集 ${currentCount} 个章节`);

                if (currentCount === lastCount) {
                    noChangeCount++;
                } else {
                    noChangeCount = 0;
                    lastCount = currentCount;
                }

                // 滚动
                if (scrollContainer) {
                    scrollContainer.scrollTop += 1000;
                } else if (buttons.length > 0) {
                    buttons[buttons.length - 1].scrollIntoView({block: 'end'});
                }

                await new Promise(r => setTimeout(r, 200));
            }

            const result = Array.from(allChapters.values());
            result.sort((a, b) => {
                const numA = parseInt(a.title.match(/\\d+/)?.[0] || '0');
                const numB = parseInt(b.title.match(/\\d+/)?.[0] || '0');
                return numA - numB;
            });

            callback(result);
        })();
    """)

    print(f"\n成功！收集到 {len(all_chapters_js)} 个章节")

    # 保存结果
    with open('all_chapters_complete.json', 'w', encoding='utf-8') as f:
        json.dump(all_chapters_js, f, ensure_ascii=False, indent=2)

    print("已保存到 all_chapters_complete.json")

    print(f"\n前10章:")
    for ch in all_chapters_js[:10]:
        print(f"  {ch['title']} - ID: {ch['id']}")

    print(f"\n后10章:")
    for ch in all_chapters_js[-10:]:
        print(f"  {ch['title']} - ID: {ch['id']}")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("\n完成！")
    driver.quit()

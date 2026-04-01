# Novalpie 章节爬取实现说明

目标：从目录页收集每一章的跳转链接，进入章节页抓取正文，忽略“章节讨论”区域。

## 思路概述
1. **目录页收集章节列表**
   - 访问 `https://novalpie.cc/book/354531/`。
   - 目录列表使用虚拟滚动（`vue-recycle-scroller`），需要持续滚动来触发加载。
   - 页面中每个章节入口是 `button[data-chapter-id]`。
   - 章节标题在按钮内的 `.font-medium` 元素。
   - 章节链接规则：`https://novalpie.cc/book/354531/{chapter_id}`。
   - 将结果保存为 `novalpie_chapters_list.json`（含 `id/title/url`）。

2. **章节页抓取正文**
   - 进入 `https://novalpie.cc/book/354531/{chapter_id}`。
   - 正文所在容器：`div.chapter-item[data-chapter-id="{chapter_id}"]`。
   - 章节讨论区域是 `div.chapter-comments`（或同类 class），不在 `chapter-item` 中，但仍做防御性剔除。
   - 把 `<br>` 转换为换行，再做空行清理。
   - 标题优先使用 `data-chapter-title`，没有则用目录里的标题。

3. **登录（Cookie 或 auth_token 二选一）**
   - 若页面需要登录才能加载完整内容，请提供 Cookie 或 `auth_token`。
   - Cookie 方式：
     - 环境变量 `NOVALPIE_COOKIE`（原始 `a=b; c=d` 形式）
     - 文件 `novalpie_cookies.txt`（同上）
     - 文件 `novalpie_cookies.json`（`{name:value}` 或 `[{name, value}]`）
   - auth_token 方式（LocalStorage）：
     - 环境变量 `NOVALPIE_AUTH_TOKEN`
     - 文件 `novalpie_auth_token.txt`

## 运行步骤
1. 填写 cookie（可选，但推荐）。
2. 运行目录收集脚本生成章节列表。
3. 运行正文抓取脚本生成正文文本。

## 文件产物
- `output/novalpie_chapters_list.json`：章节列表（含 URL）。
- `output/novalpie_scrape_progress.json`：抓取进度（可断点续跑）。
- `output/novalpie_354531.txt`：最终正文输出（默认文件名）。

## 注意事项
1. 仅抓取 `div.chapter-item`，避免“章节讨论”区域。
2. 目录页虚拟滚动需要多次滚动才能收集完整章节。
3. 若章节页一次出现多章内容，按 `data-chapter-id` 精确匹配当前章。

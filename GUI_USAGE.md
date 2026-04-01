# GUI 使用说明

启动方式：

```powershell
python gui_scraper.py
```

或者直接双击：

`启动小说爬虫GUI.bat`

当前主流程：

1. 输入 `novalpie` 书页链接，例如 `https://novalpie.cc/book/6/`
2. 点“打开书页浏览器”
3. 如果浏览器里已经登录，会直接进入书页；如果没有，先在这个窗口里登录
4. 登录后可以点“从浏览器同步 Token”，程序会把 token 保存到 `novalpie_auth_token.txt`
5. 选择导出目录、导出格式、并发线程数
6. 点“开始爬取”

现在支持：

- 导出目录可选
- 导出格式可选：`TXT`、`EPUB`、`JSON`
- `novalpie` 标题优先抓取页面 `h1` 中文标题
- 正文抓取支持并发提速

导出文件默认在：

- `project/output/`

# Novelpia 爬虫 GUI

这是一个 Windows 桌面图形工具，用于在用户自行登录后，把 `novalpie.cc` 可访问的书籍内容导出为 `TXT`、`EPUB` 和 `JSON`。

## 功能

- 打开浏览器并复用当前登录状态
- 优先通过 Novelpia 章节接口读取完整目录，失败时再回退到页面解析
- 支持导出 `TXT`、`EPUB`、`JSON`
- 自动下载详情页封面
- 尝试把正文插图写入 EPUB
- 支持在 GUI 中选择导出目录

## 运行要求

- Windows
- 已安装 Microsoft Edge
- 源码运行模式需要 Python 3.12+

## 源码运行

```powershell
pip install -r requirements.txt
python gui_scraper.py
```

## Windows 免安装版

免安装版请从 GitHub Releases 下载，不建议直接从源码目录运行打包产物。

解压后：

1. 运行 `启动小说爬虫GUI_v2.bat` 或 `小说爬虫GUI_v2.exe`
2. 输入 Novelpia 书页链接，例如 `https://novalpie.cc/book/6/`
3. 点击浏览器按钮并手动登录
4. 开始导出

## 说明

- 不要提交或分享你自己的 token、cookies
- 本工具要求用户使用自己的账号登录
- 导出文件会写入你选择的输出目录

## 免责声明

本项目仅供学习研究和个人用途参考。

使用者必须使用自己的账号登录，并自行确保使用行为符合目标网站的服务条款、版权规则及所在地法律法规。请勿使用本工具传播未授权内容、绕过付费访问限制，或分享任何私人认证信息，例如 token、cookies。

作者不提供任何内置账号、token 或受版权保护的小说内容，也不对使用者的滥用行为承担责任。

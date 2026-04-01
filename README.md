# Novelpia Scraper GUI

A Windows desktop GUI tool for exporting accessible `novalpie.cc` book content to `TXT`, `EPUB`, and `JSON` after user login.

## Features

- Open a browser session and reuse the current login state
- Read chapter lists from the Novelpia chapter API first, then fall back to page parsing if needed
- Export to `TXT`, `EPUB`, and `JSON`
- Download the detail-page cover image
- Embed chapter images into EPUB when available
- Choose export directory from the GUI

## Requirements

- Windows
- Microsoft Edge installed
- Python 3.12+ for source mode

## Source Run

```powershell
pip install -r requirements.txt
python gui_scraper.py
```

## Packaged Windows Build

The packaged Windows build should be downloaded from GitHub Releases, not from the source tree.

After extraction:

1. Run `启动小说爬虫GUI_v2.bat` or `小说爬虫GUI_v2.exe`
2. Enter a Novelpia book URL such as `https://novalpie.cc/book/6/`
3. Click the browser button and log in manually
4. Start export

## Notes

- Do not commit or share your own token or cookies
- This tool expects the user to log in with their own account
- Exported files are written to the selected output directory

## Disclaimer

Use this tool only for content you are allowed to access and export. You are responsible for complying with the target site's terms and applicable laws.

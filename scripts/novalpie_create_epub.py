import argparse
import json
import re
from pathlib import Path
import mimetypes
import requests

from ebooklib import epub


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

DEFAULT_BOOK_ID = "353927"
DEFAULT_BOOK_TITLE = "魔法学院的天才预言家"


def clean_content(content: str) -> str:
    if not content:
        return ""
    patterns = [
        r"章节讨论.*",
        r"写第一条评论.*",
        r"暂无评论.*",
    ]
    for pattern in patterns:
        content = re.sub(pattern, "", content, flags=re.DOTALL)
    return content.strip()


def normalize_title(title: str, index: int) -> str:
    if not title:
        return f"第{index}话"
    if "�" in title or "µ" in title:
        return f"第{index}话"
    return title.strip()


def _find_cover_path(cover_arg: str | None) -> Path | None:
    if cover_arg:
        p = Path(cover_arg)
        if not p.is_absolute():
            p = (Path.cwd() / p)
        if p.exists():
            return p
    candidates = [
        OUTPUT_DIR / "cover.jpg",
        OUTPUT_DIR / "cover.jpeg",
        OUTPUT_DIR / "cover.png",
        BASE_DIR / "cover.jpg",
        BASE_DIR / "cover.jpeg",
        BASE_DIR / "cover.png",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _download_image(url: str, out_path: Path) -> bool:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        return True
    except Exception:
        return False


def create_epub(
    book_id: str,
    book_title: str,
    cover_path: Path | None = None,
    output_path: Path | None = None,
):
    input_json = OUTPUT_DIR / f"novalpie_{book_id}_scrape_progress.json"
    if not input_json.exists():
        raise FileNotFoundError(f"Missing {input_json}")

    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    chapters_content = data.get("chapters_content", [])
    if not chapters_content:
        raise RuntimeError("No chapters_content found in progress JSON")

    # 去重并保持顺序
    seen = set()
    cleaned = []
    for i, ch in enumerate(chapters_content, 1):
        chapter_id = ch.get("id") or str(i)
        if chapter_id in seen:
            continue
        seen.add(chapter_id)

        title = normalize_title(ch.get("title", ""), i)
        content = clean_content(ch.get("content", ""))
        if not content:
            continue
        cleaned.append(
            {
                "title": title,
                "content": content,
                "order": ch.get("order", i),
                "images": ch.get("images", []),
                "id": ch.get("id", str(i)),
            }
        )

    cleaned.sort(key=lambda x: x.get("order", 0))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    book = epub.EpubBook()
    book.set_identifier(f"novalpie_{book_id}")
    book.set_title(book_title)
    book.set_language("zh")
    book.add_author("未知")

    cover_item = None
    if cover_path:
        cover_bytes = cover_path.read_bytes()
        cover_name = cover_path.name
        book.set_cover(cover_name, cover_bytes)
        cover_item = cover_name

    epub_chapters = []
    spine = []

    # Add a cover page as the first spine item so readers show it on page 1
    if cover_item:
        cover_page = epub.EpubHtml(title="封面", file_name="cover_page.xhtml", lang="zh")
        cover_page.content = (
            f"<html><head><title>封面</title></head>"
            f"<body style='margin:0; padding:0; text-align:center;'>"
            f"<img src='{cover_item}' style='max-width:100%; height:auto;' />"
            f"</body></html>"
        )
        book.add_item(cover_page)
        spine.append(cover_page)

    image_items = {}
    for i, ch in enumerate(cleaned, 1):
        chapter = epub.EpubHtml(
            title=ch["title"],
            file_name=f"chapter_{i:04d}.xhtml",
            lang="zh",
        )
        paragraphs = ch["content"].split("\n")
        html_content = f"<h1>{ch['title']}</h1>\n"
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            m = re.fullmatch(r"\[IMG_(\d+)\]", p)
            if m:
                img_idx = int(m.group(1))
                img_list = ch.get("images", [])
                if img_idx < len(img_list):
                    img_url = img_list[img_idx]
                    ext = Path(img_url).suffix.lower()
                    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                        ext = ".jpg"
                    safe_name = f"images/{ch.get('id','ch')}_{img_idx}{ext}"
                    if safe_name not in image_items:
                        image_items[safe_name] = img_url
                    html_content += f"<div><img src='{safe_name}' style='max-width:100%; height:auto;'/></div>\n"
                continue
            html_content += f"<p>{p}</p>\n"
        chapter.content = html_content
        book.add_item(chapter)
        epub_chapters.append(chapter)
        spine.append(chapter)

    # Custom TOC page (two-column list)
    toc_page = epub.EpubHtml(title="目录", file_name="toc.xhtml", lang="zh")
    toc_items = []
    for i, ch in enumerate(epub_chapters, 1):
        toc_items.append(
            f"<li><a href='{ch.file_name}'>{i}. {ch.title}</a></li>"
        )
    toc_page.content = (
        "<html><head><title>目录</title>"
        "<style>"
        "body{font-family:'Microsoft YaHei','SimSun',serif;line-height:1.6;margin:2em;}"
        "h1{text-align:center;margin:0 0 1em 0;}"
        "ol{columns:2;-webkit-columns:2;-moz-columns:2;column-gap:2.5em;}"
        "li{break-inside:avoid;}"
        "a{text-decoration:none;color:#1a4fb3;}"
        "</style></head><body>"
        "<h1>目录</h1>"
        f"<ol>{''.join(toc_items)}</ol>"
        "</body></html>"
    )
    book.add_item(toc_page)

    # Include the custom TOC page as the first item in the book TOC
    # Add downloaded images to book
    img_dir = OUTPUT_DIR / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    for rel_name, url in image_items.items():
        out_path = img_dir / Path(rel_name).name
        if not out_path.exists():
            _download_image(url, out_path)
        if out_path.exists():
            media_type, _ = mimetypes.guess_type(out_path.name)
            if not media_type:
                media_type = "image/jpeg"
            img_item = epub.EpubItem(
                uid=out_path.name,
                file_name=f"images/{out_path.name}",
                media_type=media_type,
                content=out_path.read_bytes(),
            )
            book.add_item(img_item)

    book.toc = [toc_page] + epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    # Ensure cover page and custom TOC appear before nav and content
    book.spine = spine + [toc_page, "nav"] + epub_chapters

    style = """
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
    """
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style,
    )
    book.add_item(nav_css)

    final_output = output_path or (OUTPUT_DIR / f"{book_title}.epub")
    epub.write_epub(str(final_output), book, {})
    print(f"EPUB created: {final_output} (chapters: {len(cleaned)})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cover", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--book-id", default=DEFAULT_BOOK_ID)
    parser.add_argument("--title", default=DEFAULT_BOOK_TITLE)
    args = parser.parse_args()

    cover = _find_cover_path(args.cover if args.cover else None)
    output = Path(args.output) if args.output else None
    create_epub(
        book_id=args.book_id,
        book_title=args.title,
        cover_path=cover,
        output_path=output,
    )

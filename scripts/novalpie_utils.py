import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
)


def _parse_cookie_string(raw: str) -> dict:
    cookies = {}
    if not raw:
        return cookies
    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


def _resolve_path(name: str) -> Path:
    p = Path(name)
    if p.is_absolute():
        return p
    cwd = Path.cwd() / name
    if cwd.exists():
        return cwd
    return BASE_DIR / name


def load_cookies() -> dict:
    env_cookie = os.environ.get("NOVALPIE_COOKIE", "").strip()
    if env_cookie:
        return _parse_cookie_string(env_cookie)

    txt_path = _resolve_path("novalpie_cookies.txt")
    if txt_path.exists():
        with open(txt_path, "r", encoding="utf-8") as f:
            return _parse_cookie_string(f.read().strip())

    json_path = _resolve_path("novalpie_cookies.json")
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            cookies = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                value = item.get("value")
                if name and value is not None:
                    cookies[name] = value
            return cookies

    return {}


def load_auth_token() -> str:
    env_token = os.environ.get("NOVALPIE_AUTH_TOKEN", "").strip()
    if env_token:
        return env_token

    txt_path = _resolve_path("novalpie_auth_token.txt")
    if txt_path.exists():
        with open(txt_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    return ""


def load_local_storage() -> dict:
    """
    Optional localStorage dump to improve auth in reader pages.
    Accepts JSON dict in novalpie_local_storage.json.
    """
    path = _resolve_path("novalpie_local_storage.json")
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            return {}
    return {}


def _inject_auth_token(driver, base_url: str, token: str, extra_ls: dict | None = None):
    if not token:
        return
    driver.get(base_url)
    try:
        driver.execute_script("localStorage.setItem('auth_token', arguments[0]);", token)
        driver.execute_script("localStorage.setItem('openc-enabled', 'false');")
        if extra_ls:
            for k, v in extra_ls.items():
                try:
                    driver.execute_script("localStorage.setItem(arguments[0], arguments[1]);", k, str(v))
                except Exception:
                    continue
        driver.refresh()
    except Exception:
        pass


def create_driver(
    headless: bool,
    base_url: str,
    cookies: dict | None = None,
    auth_token: str | None = None,
    local_storage: dict | None = None,
):
    options = EdgeOptions()
    if headless:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1600,2400")
    options.add_argument("--no-sandbox")
    options.add_argument(f"user-agent={DEFAULT_UA}")
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
    }
    # Only disable images for headless scraping workers.
    if headless:
        prefs["profile.managed_default_content_settings.images"] = 2
    try:
        options.add_experimental_option("prefs", prefs)
    except Exception:
        pass
    options.page_load_strategy = "eager"

    driver = webdriver.Edge(options=options)
    try:
        driver.set_window_size(1600, 2400)
    except Exception:
        pass

    driver.get(base_url)

    if cookies:
        host = urlparse(base_url).hostname or ""
        for name, value in cookies.items():
            try:
                driver.add_cookie(
                    {
                        "name": name,
                        "value": value,
                        "domain": host,
                    }
                )
            except Exception:
                try:
                    driver.add_cookie(
                        {
                            "name": name,
                            "value": value,
                        }
                    )
                except Exception:
                    continue

    if auth_token or local_storage:
        _inject_auth_token(driver, base_url, auth_token or "", local_storage)

    return driver


def normalize_text(raw: str) -> str:
    lines = [line.strip() for line in raw.splitlines()]
    return "\n".join(line for line in lines if line)

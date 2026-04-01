"""
配置文件 - 小说爬虫 (zoolib.cc)
"""

NOVEL_ID = "350009"
BASE_URL = "https://zoolib.cc"
DETAIL_URL = f"{BASE_URL}/book-detail/{NOVEL_ID}"
READER_URL = f"{BASE_URL}/reader"

# Cookie配置
COOKIES = {
    "USERKEY": "764dcbc1fd256de08dc4b0c3aca11f71",
    "LOGINKEY": "21bd5c4305e311628c702d8a13686cb1_f2e5323761d810cfc6961e0bc12d4ea8",
    "AUTH_VIEWER": "2769689",
    "AUTOLOGIN": "3891734",
    "cf_clearance": "MbkaUmO_W0BSTOPXgE0lNAyGArM9Yb0ZrRiLVqx80pc-1766727616-1.2.1.1-n1atXz2l7SrBjflp1BxT9xO7KNcWIaLBaJzrAsgLHZti7Q6topVcqPy2b6ErlJhG99EhjmjTBvon6lepVZlKo3Ko7mMHGMf._VdeLeh93AejIFcCPI89pDwaWxYq7rGF9Kk.O1s_i2wEb_xJmqkFfvWHnfr8ZoDO9I2m59.ViZK6lCkfKge8RM7KTd4zuM9xpw8IumF1zxJfJZXhiDY8QZ.Awi97pBRYtujRExTydV0",
    "LOCALE": "en",
    "lang": "zh-CN",
    "colorMode": "dark",
}

# 请求头配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Referer": BASE_URL,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# 爬取配置
REQUEST_DELAY = 1  # 请求间隔（秒）
MAX_RETRIES = 3    # 最大重试次数
TIMEOUT = 15       # 请求超时时间（秒）

# 输出配置
OUTPUT_FILENAME = "重生路人甲成为天才"
LOG_FILENAME = "scraper.log"

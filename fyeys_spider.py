# -*- coding: utf-8 -*-
import json
import re
from urllib.parse import quote, unquote, urljoin

# 继承官方基类
from base.spider import Spider as BaseSpider

HOST = "https://m.fyeys.com"
DEFAULT_UA = "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36"

CATE_LIST = [
    {"type_id": "1", "type_name": "电影"},
    {"type_id": "2", "type_name": "电视剧"},
    {"type_id": "3", "type_name": "综艺"},
    {"type_id": "4", "type_name": "动漫"},
    {"type_id": "5", "type_name": "短剧"}
]

class Spider(BaseSpider):

    def getName(self):
        return "枫叶影视 (Chaquopy Python)"

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.options = extend
        elif isinstance(extend, str) and extend.strip():
            try:
                self.options = json.loads(extend)
            except Exception:
                self.options = {}
        else:
            self.options = {}
            
        self.site_url = str(self.options.get("host") or HOST).rstrip("/")

    def homeContent(self, filter):
        # 按照规范直接返回 dict 对象
        return {
            "class": CATE_LIST
        }

    def homeVideoContent(self):
        # 默认推荐页抓取电视剧第一页
        return self.categoryContent("2", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        if page <= 1:
            url = f"{self.site_url}/vod/show/id/{tid}"
        else:
            url = f"{self.site_url}/vod/show/id/{tid}/page/{page}"

        html = self._fetch_html(url)
        items = self._parse_list(html)

        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if len(items) >= 10 else page,
            "limit": 30,
            "total": 999
        }

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg or 1))
        keyword = quote(str(key or "").strip())
        if not keyword:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}

        url = f"{self.site_url}/vod/search/{keyword}----------{page}---.html"
        html = self._fetch_html(url)
        items = self._parse_list(html)

        return {
            "list": items,
            "page": page,
            "pagecount": page + 1 if len(items) >= 10 else page,
            "limit": 30,
            "total": 999
        }

    def detailContent(self, ids):
        ident = str(ids[0] if ids else "").removeprefix("vod/").strip()
        if not ident:
            return {"list": []}

        url = f"{self.site_url}/detail/{ident}"
        html = self._fetch_html(url)

        # 提取标题
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.I) or re.search(r'alt="([^"]+)"', html, re.I)
        title = title_match.group(1).strip() if title_match else ident

        # 提取封面
        pic_match = re.search(r'(?:src|data-src|data-original)="(https?://[^"]+)"', html, re.I)
        pic = pic_match.group(1) if pic_match else ""

        # 解析播放剧集
        episodes = self._parse_episodes(html, ident)
        
        # 严格执行规范：清理 $ 与 # 分隔符
        safe_lines = [f"{self._safe_label(ep['name'])}${ep['url']}" for ep in episodes]
        play_url_str = "#".join(safe_lines)

        vod = {
            "vod_id": ident,
            "vod_name": title,
            "vod_pic": pic,
            "vod_play_from": "枫叶云播",
            "vod_play_url": play_url_str
        }

        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        play_page_url = str(id or "").strip()
        if play_page_url.startswith("/"):
            play_page_url = urljoin(self.site_url, play_page_url)

        # 开启网页嗅探模式 (parse=1)
        return {
            "parse": 1,
            "jx": 0,
            "url": play_page_url,
            "header": {
                "User-Agent": DEFAULT_UA,
                "Referer": f"{self.site_url}/"
            }
        }

    def manualVideoCheck(self):
        # 告诉 App 使用 Python 的 isVideoFormat() 函数进行二次过滤拦截
        return True

    def isVideoFormat(self, url):
        u = str(url or "").lower()
        if not u.startswith("http"):
            return False
        # 排除常见广告与干扰资源
        if any(ad in u for ad in ["/ad/", "google", "geetest", "cnzz", "51.la", ".js", ".css"]):
            return False
        return ".m3u8" in u or ".mp4" in u or "m3u8?" in u

    def action(self, action):
        return {"msg": "OK"}

    def destroy(self):
        pass

    # ================= 内部辅助函数 =================

    def _fetch_html(self, url):
        """
        优先调用 Java 原生 OkHttp；若在非 Android 测试环境则降级回 urllib
        """
        try:
            from com.fongmi.android.tv.ui.activity import WebActivity
            from com.github.catvod.net import OkHttp
            from java.util import HashMap
            from java.util.concurrent import TimeUnit

            headers_map = HashMap()
            headers_map.put("User-Agent", DEFAULT_UA)
            headers_map.put("Referer", f"{self.site_url}/")

            call = OkHttp.newCall(url, headers_map)
            call.timeout().timeout(15, TimeUnit.SECONDS)
            response = call.execute()
            try:
                body = response.body()
                return str(body.string()) if body else ""
            finally:
                response.close()
        except Exception:
            # 兼容普通 Python 测试环境 (PC端)
            import urllib.request
            req = urllib.request.Request(url, headers={
                "User-Agent": DEFAULT_UA,
                "Referer": f"{self.site_url}/"
            })
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.read().decode('utf-8', errors='ignore')
            except Exception:
                return ""

    def _parse_list(self, html):
        items = []
        seen = set()
        pattern = re.compile(
            r'href="/detail/(\d+)"[^>]*>[\s\S]*?<img[^>]+(?:src|data-src|data-original)="(https?://[^"]+)"[\s\S]*?alt="([^"]+)"',
            re.IGNORECASE
        )
        for match in pattern.finditer(html):
            vid, pic, name = match.groups()
            if vid not in seen:
                seen.add(vid)
                items.append({
                    "vod_id": f"vod/{vid}",
                    "vod_name": name.strip(),
                    "vod_pic": pic,
                    "vod_remarks": ""
                })
        return items

    def _parse_episodes(self, html, vid):
        eps = []
        seen = set()
        pattern = re.compile(rf'/vod/play/{vid}/[a-zA-Z0-9/._-]+', re.IGNORECASE)
        for match in pattern.finditer(html):
            path = match.group(0)
            if path not in seen:
                seen.add(path)
                full_url = path if path.startswith("http") else urljoin(self.site_url, path)
                eps.append({
                    "name": f"第{len(eps) + 1}集",
                    "url": full_url
                })
        return eps

    @staticmethod
    def _safe_label(value):
        return str(value or "").replace("$", "＄").replace("#", "＃").strip()

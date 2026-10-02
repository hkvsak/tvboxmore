# -*- coding: utf-8 -*-
import html as html_parser
import json
import re
from urllib.parse import quote, urljoin

from base.spider import Spider as BaseSpider

DEFAULT_HOST = "https://m.fyeys.com"
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
        return "枫叶影视 (Chaquopy Python 终极校验版)"

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
            
        self.site_url = str(self.options.get("host") or self.options.get("request_url") or DEFAULT_HOST).rstrip("/")

    def homeContent(self, filter):
        return {"class": CATE_LIST}

    def homeVideoContent(self):
        return self.categoryContent("2", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        if page <= 1:
            url = f"{self.site_url}/vod/show/id/{tid}"
        else:
            url = f"{self.site_url}/vod/show/id/{tid}/page/{page}"

        html_text = self._fetch_html(url)
        items = self._parse_list(html_text)

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

        url = f"{self.site_url}/vod/search/page/{page}/wd/{keyword}"
        html_text = self._fetch_html(url)
        items = self._parse_list(html_text)

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

        url = f"{self.site_url}/vod/detail/{ident}"
        html_text = self._fetch_html(url)

        # 1. 提取标题并反转义 HTML 字符
        title_match = re.search(r'<h[1-3][^>]*>([^<]+)</h[1-3]>', html_text, re.I) or re.search(r'title="([^"]+)"', html_text, re.I)
        raw_title = title_match.group(1).strip() if title_match else ident
        title = html_parser.unescape(raw_title)

        # 2. 提取封面
        pic_match = re.search(r'(?:src|data-src|data-original)="(https?://[^"]+)"', html_text, re.I)
        pic = pic_match.group(1) if pic_match else ""

        # 3. 提取剧集列表
        episodes = self._parse_episodes(html_text, ident)
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
        return True

    def isVideoFormat(self, url):
        u = str(url or "").lower()
        if not u.startswith("http"):
            return False
        
        # 1. 优先放行切片资源与视频流
        if any(v in u for v in [".m3u8", ".mp4", "splitout", "kqgfbs.com", "mime=video"]):
            return True

        # 2. 屏蔽常见广告与无关静态资源
        if any(ad in u for ad in ["/ad/", "google", "geetest", "cnzz", "51.la", ".js", ".css", ".png", ".jpg", ".gif"]):
            return False

        return False

    def action(self, action):
        return {"msg": "OK"}

    def destroy(self):
        pass

    def _fetch_html(self, url):
        # 强装安全网：全局捕获，无论是否引发 BaseException/JavaException 均平滑降级
        try:
            from com.github.catvod.net import OkHttp
            from java.util import HashMap
            from java.util.concurrent import TimeUnit

            headers_map = HashMap()
            headers_map.put("User-Agent", DEFAULT_UA)
            headers_map.put("Referer", f"{self.site_url}/")

            call = OkHttp.newCall(url, headers_map)
            call.timeout().timeout(12, TimeUnit.SECONDS)
            response = call.execute()
            try:
                body = response.body()
                return str(body.string()) if body else ""
            finally:
                response.close()
        except BaseException:
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

    def _parse_list(self, html_text):
        items = []
        seen = set()
        link_pattern = re.compile(r'href="/vod/(?:detail|play)/(\d+)[^"]*"', re.IGNORECASE)
        
        for match in link_pattern.finditer(html_text):
            vid = match.group(1)
            if vid not in seen:
                start = max(0, match.start() - 200)
                end = min(len(html_text), match.end() + 500)
                context = html_text[start:end]

                pic_match = re.search(r'(?:src|data-src|data-original)="(https?://[^"]+)"', context, re.I)
                name_match = re.search(r'alt="([^"]+)"', context, re.I) or re.search(r'title="([^"]+)"', context, re.I) or re.search(r'<h[1-9][^>]*>([^<]+)</h[1-9]>', context, re.I)

                raw_name = name_match.group(1).strip() if name_match else ""
                name = html_parser.unescape(raw_name) if raw_name else ""

                if name and "首页" not in name and "更多" not in name:
                    seen.add(vid)
                    items.append({
                        "vod_id": vid,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": ""
                    })
        return items

    def _parse_episodes(self, html_text, vid):
        eps = []
        seen = set()
        episode_pattern = re.compile(rf'href="(/vod/play/{vid}/\d+/\d+)"[^>]*>([\s\S]*?)</a>', re.IGNORECASE)
        
        for match in episode_pattern.finditer(html_text):
            path = match.group(1)
            raw_content = match.group(2)
            clean_text = re.sub(r'<[^>]+>', '', raw_content).strip()
            clean_name = html_parser.unescape(clean_text)
            
            if path not in seen:
                seen.add(path)
                full_url = path if path.startswith("http") else urljoin(self.site_url, path)
                ep_name = clean_name if clean_name else f"第{len(eps) + 1}集"
                eps.append({
                    "name": ep_name,
                    "url": full_url
                })

        if not eps:
            eps.append({
                "name": "播放页直达",
                "url": f"{self.site_url}/vod/play/{vid}/1/1"
            })
        return eps

    @staticmethod
    def _safe_label(value):
        return str(value or "").replace("$", "＄").replace("#", "＃").strip()

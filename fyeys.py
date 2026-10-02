# -*- coding: utf-8 -*-
# 枫叶影视 fyeys.com - 修复乱码 / 选集 / 播放嗅探
import json
import re
from urllib.parse import quote

from base.spider import Spider as BaseSpider

HOST = "https://fyeys.com"
UA = (
    "Mozilla/5.0 (Linux; Android 13; Mobile) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/129.0.0.0 Mobile Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Referer": HOST + "/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

CATE = [
    {"type_id": "1", "type_name": "电影"},
    {"type_id": "2", "type_name": "电视剧"},
    {"type_id": "3", "type_name": "综艺"},
    {"type_id": "4", "type_name": "动漫"},
    {"type_id": "5", "type_name": "短剧"},
]


class Spider(BaseSpider):
    def init(self, extend=""):
        self.headers = HEADERS.copy()

    def getName(self):
        return "枫叶影视"

    def homeContent(self, filter):
        return {"class": CATE}

    def homeVideoContent(self):
        return self.categoryContent("2", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        tid = str(tid or "1").strip()
        page = max(1, int(pg or 1))
        url = f"{HOST}/vod/show/id/{tid}" if page <= 1 else f"{HOST}/vod/show/id/{tid}/page/{page}"
        html = self._get(url)
        items = self._parse_list(html)
        pagecount = page + 1 if len(items) >= 20 else page
        return {"list": items, "page": page, "pagecount": pagecount, "limit": 30, "total": pagecount * 30}

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg or 1))
        wd = quote(str(key or "").strip())
        if not wd:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}
        html = self._get(f"{HOST}/vod/search/{wd}----------{page}---.html")
        items = self._parse_list(html)
        pagecount = page + 1 if len(items) >= 20 else page
        return {"list": items, "page": page, "pagecount": pagecount, "limit": 30, "total": pagecount * 30}

    def detailContent(self, ids):
        vid = str(ids[0] if ids else "").strip()
        if not vid:
            return {"list": []}
        html = self._get(f"{HOST}/detail/{vid}")

        name = self._field(html, "vodName") or self._alt_title(html) or vid
        pic = self._field(html, "vodPic")
        remarks = self._field(html, "vodRemarks")
        year = self._field(html, "vodYear")
        area = self._field(html, "vodArea")
        director = self._field(html, "vodDirector")
        actor = self._field(html, "vodActor")
        content = self._field(html, "vodContent")

        episodes = self._episodes(html, vid)
        play_url = "#".join(f"{self._safe(e['name'])}${e['url']}" for e in episodes)

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks,
                "vod_year": year,
                "vod_area": area,
                "vod_director": director,
                "vod_actor": actor,
                "vod_content": content,
                "vod_play_from": "枫叶影视",
                "vod_play_url": play_url,
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        url = str(id or "").strip()
        if url.startswith("/"):
            url = HOST + url
        if not url.startswith("http"):
            return {"parse": 0, "msg": "无效播放地址"}
        # 交给 WebView 嗅探真实 m3u8
        return {
            "parse": 1,
            "jx": 0,
            "url": url,
            "header": {"User-Agent": UA, "Referer": HOST + "/"},
        }

    def manualVideoCheck(self):
        return True

    def isVideoFormat(self, url):
        u = str(url or "").lower()
        if not u.startswith("http"):
            return False
        if any(x in u for x in ("google", "doubleclick", "geetest", "cnzz", "51.la", "/ad/")):
            return False
        if ".m3u8" in u and any(x in u for x in ("kqgfbs", "ppvod", "splitout", "index.m3u8")):
            return True
        return u.endswith(".m3u8")

    def destroy(self):
        pass

    # ---------- 网络 ----------
    def _get(self, url):
        try:
            if hasattr(self, "fetch"):
                rsp = self.fetch(url, headers=self.headers)
                if isinstance(rsp, str):
                    return rsp
                text = getattr(rsp, "text", None)
                if text:
                    return text
                content = getattr(rsp, "content", b"") or b""
                if isinstance(content, bytes):
                    return content.decode("utf-8", "ignore")
                return str(content)
        except Exception:
            pass
        try:
            if hasattr(self, "getHtml"):
                return self.getHtml(url) or ""
        except Exception:
            pass
        try:
            import requests
            r = requests.get(url, headers=self.headers, timeout=15)
            r.encoding = "utf-8"
            return r.text
        except Exception:
            return ""

    # ---------- 列表 ----------
    def _parse_list(self, html):
        items, seen = [], set()
        if not html:
            return items
        # movie-card
        for block in re.findall(r'class="[^"]*movie-card[^"]*"[\s\S]*?</a>', html, re.I):
            mid = re.search(r'href="/detail/(\d+)"', block)
            if not mid:
                continue
            vid = mid.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            alt = re.search(r'alt="([^"]+)"', block)
            name = (alt.group(1) if alt else "").strip() or vid
            pic = ""
            pm = re.search(r'(?:src|data-src)="(https?://[^"]+)"', block)
            if pm:
                pic = pm.group(1)
            items.append({"vod_id": vid, "vod_name": name, "vod_pic": pic, "vod_remarks": ""})
        if items:
            return items
        # 兜底
        for vid in re.findall(r'href="/detail/(\d+)"', html):
            if vid in seen:
                continue
            seen.add(vid)
            items.append({"vod_id": vid, "vod_name": vid, "vod_pic": "", "vod_remarks": ""})
        return items

    # ---------- 详情字段（处理 \" 转义，禁止错误 unicode_escape） ----------
    def _field(self, html, key):
        """匹配 vodName\":\"中文  或  "vodName":"中文" """
        patterns = [
            rf'{key}\\":\\"(.*?)\\"',
            rf'"{key}":"(.*?)"',
            rf'{key}":"(.*?)"',
        ]
        for pat in patterns:
            m = re.search(pat, html)
            if not m:
                continue
            raw = m.group(1)
            # 用 json 正确反转义，不要 unicode_escape
            try:
                return json.loads('"' + raw.replace('\n', '\\n') + '"')
            except Exception:
                return (
                    raw.replace("\\n", "\n")
                    .replace("\\/", "/")
                    .replace('\\"', '"')
                    .replace("\\\\", "\\")
                )
        return ""

    def _alt_title(self, html):
        m = re.search(r'alt="([^"]{2,50})"', html)
        if m:
            return m.group(1)
        m = re.search(r"<title>([^<]+)</title>", html)
        if m:
            return m.group(1).split("_")[0].split("-")[0].strip()
        return ""

    # ---------- 选集 ----------
    def _episodes(self, html, vid):
        eps = []
        # 页面里是 episodeList\":[{...}]
        key = "episodeList"
        idx = html.find(key)
        if idx < 0:
            return self._episodes_from_links(html, vid)

        # 找到数组起点 [
        bracket = html.find("[", idx)
        if bracket < 0:
            return self._episodes_from_links(html, vid)

        blob = self._extract_bracket(html, bracket)
        if not blob:
            return self._episodes_from_links(html, vid)

        # 把 \" 变成 " 再 json
        text = blob
        if '\\"' in text or text.startswith("[{\\"):
            text = text.replace('\\"', '"').replace("\\\\", "\\")
        try:
            arr = json.loads(text)
        except Exception:
            try:
                arr = json.loads(blob.encode("utf-8").decode("unicode_escape"))
            except Exception:
                return self._episodes_from_links(html, vid)

        for ep in arr:
            if not isinstance(ep, dict):
                continue
            nid = ep.get("nid")
            if not nid:
                continue
            name = str(ep.get("name") or nid).strip()
            eps.append({"name": name, "url": f"{HOST}/vod/play/{vid}/sid/{nid}"})
        return eps or self._episodes_from_links(html, vid)

    def _episodes_from_links(self, html, vid):
        eps, seen = [], set()
        for m in re.finditer(rf'/vod/play/{re.escape(str(vid))}/(?:sid/)?(\d+)', html):
            nid = m.group(1)
            if nid in seen:
                continue
            seen.add(nid)
            eps.append({"name": str(len(eps) + 1), "url": f"{HOST}/vod/play/{vid}/sid/{nid}"})
        return eps

    @staticmethod
    def _extract_bracket(html, start):
        depth = 0
        for i in range(start, len(html)):
            ch = html[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return html[start : i + 1]
        return ""

    @staticmethod
    def _safe(s):
        return str(s or "").replace("$", "＄").replace("#", "＃").strip()
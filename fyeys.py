# -*- coding: utf-8 -*-
# 枫叶影视 fyeys.com - FongMi Python 爬虫（修正分类串页）
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
        # 正确分页：第1页无 page，第2页起 /page/N（不要 .html）
        if page <= 1:
            url = f"{HOST}/vod/show/id/{tid}"
        else:
            url = f"{HOST}/vod/show/id/{tid}/page/{page}"
        html = self._get(url)
        items = self._parse_list(html)
        pagecount = page + 1 if len(items) >= 20 else page
        return {
            "list": items,
            "page": page,
            "pagecount": pagecount,
            "limit": 30,
            "total": pagecount * 30,
        }

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg or 1))
        wd = quote(str(key or "").strip())
        if not wd:
            return self._empty_page(page)
        url = f"{HOST}/vod/search/{wd}----------{page}---.html"
        html = self._get(url)
        items = self._parse_list(html)
        pagecount = page + 1 if len(items) >= 20 else page
        return {
            "list": items,
            "page": page,
            "pagecount": pagecount,
            "limit": 30,
            "total": pagecount * 30,
        }

    def detailContent(self, ids):
        vid = str(ids[0] if ids else "").strip()
        if not vid:
            return {"list": []}
        html = self._get(f"{HOST}/detail/{vid}")
        name = self._find_vod_name(html, vid)
        pic = self._find_pic(html)
        content = self._meta(html, "vodContent")
        remarks = self._meta(html, "vodRemarks")
        year = self._meta(html, "vodYear")
        area = self._meta(html, "vodArea")
        director = self._meta(html, "vodDirector")
        actor = self._meta(html, "vodActor")

        episodes = self._parse_episodes(html, vid)
        if not episodes:
            episodes = self._parse_episodes_from_links(html, vid)

        play_url = "#".join(f"{self._safe(ep['name'])}${ep['url']}" for ep in episodes)
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
        play_page = str(id or "").strip()
        if play_page.startswith("/"):
            play_page = HOST + play_page
        if not play_page.startswith("http"):
            return {"parse": 0, "msg": "无效播放地址"}
        return {
            "parse": 1,
            "jx": 0,
            "url": play_page,
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
        if ".m3u8" in u and any(x in u for x in ("kqgfbs", "ppvod", "splitout")):
            return True
        return u.endswith(".m3u8") or "index.m3u8" in u

    def destroy(self):
        pass

    # ----- helpers -----

    def _empty_page(self, page=1):
        return {"list": [], "page": page, "pagecount": 1, "limit": 30, "total": 0}

    def _get(self, url):
        try:
            if hasattr(self, "fetch"):
                rsp = self.fetch(url, headers=self.headers)
                if isinstance(rsp, str):
                    return rsp
                return getattr(rsp, "text", None) or str(getattr(rsp, "content", "") or "")
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

    def _parse_list(self, html):
        """只从 movie-card 区域取片，避免导航串页"""
        items = []
        if not html:
            return items
        seen = set()

        # 1) 优先：movie-card 块
        for block in re.findall(
            r'class="[^"]*movie-card[^"]*"[\s\S]*?</a>',
            html,
            re.I,
        ):
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
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": "",
            })

        if items:
            return items

        # 2) 备用：页面里的 vodName + 附近 detail id
        names = re.findall(r'vodName\\?":\\?"([^"\\]+)', html)
        ids = re.findall(r'href="/detail/(\d+)"', html)
        # 去重保序
        uniq_ids = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                uniq_ids.append(i)
        for idx, vid in enumerate(uniq_ids):
            name = names[idx] if idx < len(names) else vid
            name = name.replace("\\", "").strip()
            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": "",
                "vod_remarks": "",
            })
        return items

    def _parse_episodes(self, html, vid):
        eps = []
        m = re.search(r'"episodeList"\s*:\s*(\[[\s\S]*?\])\s*[,}]', html)
        if not m:
            return eps
        try:
            arr = json.loads(m.group(1))
        except Exception:
            return eps
        for ep in arr:
            nid = ep.get("nid")
            if not nid:
                continue
            name = str(ep.get("name") or nid).strip()
            eps.append({
                "name": name,
                "url": f"{HOST}/vod/play/{vid}/sid/{nid}",
            })
        return eps

    def _parse_episodes_from_links(self, html, vid):
        eps, seen = [], set()
        for m in re.finditer(rf'/vod/play/{re.escape(str(vid))}/(?:sid/)?(\d+)', html):
            nid = m.group(1)
            if nid in seen:
                continue
            seen.add(nid)
            eps.append({
                "name": str(len(eps) + 1),
                "url": f"{HOST}/vod/play/{vid}/sid/{nid}",
            })
        return eps

    def _find_vod_name(self, html, vid):
        n = self._meta(html, "vodName")
        if n:
            return n
        m = re.search(r'alt="([^"]+)"', html)
        if m:
            return m.group(1)
        m = re.search(r"<title>([^<]+)</title>", html)
        if m:
            return m.group(1).split("_")[0].split("-")[0].strip()
        return vid

    def _find_pic(self, html):
        p = self._meta(html, "vodPic")
        if p:
            return p
        m = re.search(r'(?:src|data-src)="(https?://obs[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', html, re.I)
        return m.group(1) if m else ""

    def _meta(self, html, key):
        m = re.search(rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"', html)
        if not m:
            m = re.search(rf'{re.escape(key)}\\?":\\?"([^"\\]+)', html)
        if not m:
            return ""
        s = m.group(1)
        try:
            s = bytes(s, "utf-8").decode("unicode_escape")
        except Exception:
            s = s.replace("\\n", "\n")
        return s.strip()

    @staticmethod
    def _safe(s):
        return str(s or "").replace("$", "＄").replace("#", "＃").strip()
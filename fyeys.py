# -*- coding: utf-8 -*-
# 枫叶影视 fyeys.com - FongMi Python 爬虫
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

# 分类：与网站导航一致
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
        # 首页用电视剧第一页
        return self.categoryContent("2", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        url = f"{HOST}/vod/show/id/{tid}/page/{page}.html"
        html = self._get(url)
        items = self._parse_list(html)
        # 粗略分页：有内容就认为还有下一页
        pagecount = page + 1 if len(items) >= 12 else page
        return {
            "list": items,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": pagecount * 24,
        }

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg or 1))
        wd = quote(str(key or "").strip())
        if not wd:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 24, "total": 0}
        # 网站搜索
        url = f"{HOST}/vod/search/{wd}----------{page}---.html"
        html = self._get(url)
        items = self._parse_list(html)
        pagecount = page + 1 if len(items) >= 12 else page
        return {
            "list": items,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": pagecount * 24,
        }

    def detailContent(self, ids):
        vid = str(ids[0] if ids else "").strip()
        if not vid:
            return {"list": []}
        html = self._get(f"{HOST}/detail/{vid}")
        name = self._meta(html, "vodName") or self._title(html) or vid
        pic = self._meta(html, "vodPic") or ""
        content = self._meta(html, "vodContent") or ""
        remarks = self._meta(html, "vodRemarks") or ""
        year = self._meta(html, "vodYear") or ""
        area = self._meta(html, "vodArea") or ""
        director = self._meta(html, "vodDirector") or ""
        actor = self._meta(html, "vodActor") or ""

        episodes = self._parse_episodes(html, vid)
        if not episodes:
            # 兜底：从页面所有 /vod/play/ 链接抽
            episodes = self._parse_episodes_from_links(html, vid)

        play_from = "枫叶影视"
        play_url = "#".join(
            f"{self._safe(ep['name'])}${ep['url']}" for ep in episodes
        )

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
                "vod_play_from": play_from,
                "vod_play_url": play_url,
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        """
        播放页是前端加载 m3u8，这里返回 parse=1，交给 App WebView 嗅探。
        id 形如：https://fyeys.com/vod/play/146562/sid/1313425
        """
        play_page = str(id or "").strip()
        if play_page.startswith("/"):
            play_page = HOST + play_page
        if not play_page.startswith("http"):
            return {"parse": 0, "msg": "无效播放地址"}

        return {
            "parse": 1,          # 打开网页嗅探
            "jx": 0,
            "url": play_page,
            "header": {
                "User-Agent": UA,
                "Referer": HOST + "/",
            },
        }

    def manualVideoCheck(self):
        # 用本站 isVideoFormat 判断嗅探到的地址
        return True

    def isVideoFormat(self, url):
        u = str(url or "").lower()
        if not u.startswith("http"):
            return False
        if any(x in u for x in ("google", "doubleclick", "geetest", "cnzz", "51.la", "/ad/")):
            return False
        # 真实播放域名 + m3u8
        if ".m3u8" in u and any(x in u for x in ("kqgfbs", "ppvod", "splitout", "fyeys")):
            return True
        if u.endswith(".m3u8") or "index.m3u8" in u:
            return True
        return False

    def destroy(self):
        pass

    # ---------- 内部工具 ----------

    def _get(self, url):
        # BaseSpider 通常自带 fetch；不同版本方法名可能是 fetch / getHtml
        try:
            if hasattr(self, "fetch"):
                rsp = self.fetch(url, headers=self.headers)
                if isinstance(rsp, str):
                    return rsp
                return getattr(rsp, "text", None) or str(rsp.content or "")
        except Exception:
            pass
        try:
            if hasattr(self, "getHtml"):
                return self.getHtml(url)
        except Exception:
            pass
        # 最后兜底（部分环境有 requests）
        try:
            import requests
            r = requests.get(url, headers=self.headers, timeout=15)
            r.encoding = "utf-8"
            return r.text
        except Exception:
            return ""

    def _parse_list(self, html):
        items = []
        if not html:
            return items
        # 去重
        seen = set()
        for m in re.finditer(
            r'href="(/detail/(\d+))"[^>]*>[\s\S]*?(?:data-src|src)="([^"]+)"[\s\S]*?(?:title|alt)="([^"]*)"',
            html,
            re.I,
        ):
            path, vid, pic, name = m.group(1), m.group(2), m.group(3), m.group(4)
            if vid in seen:
                continue
            seen.add(vid)
            if pic.startswith("//"):
                pic = "https:" + pic
            elif pic.startswith("/"):
                pic = HOST + pic
            items.append({
                "vod_id": vid,
                "vod_name": name or vid,
                "vod_pic": pic,
                "vod_remarks": "",
            })
        # 备用更宽松匹配
        if not items:
            for m in re.finditer(r'href="(/detail/(\d+))"', html):
                vid = m.group(2)
                if vid in seen:
                    continue
                seen.add(vid)
                items.append({
                    "vod_id": vid,
                    "vod_name": vid,
                    "vod_pic": "",
                    "vod_remarks": "",
                })
        return items

    def _parse_episodes(self, html, vid):
        """从页面嵌入的 episodeList JSON 取选集"""
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
            name = str(ep.get("name") or "").strip() or str(nid)
            if not nid:
                continue
            # 两种播放路径网站都存在，优先 sid 形式
            url = f"{HOST}/vod/play/{vid}/sid/{nid}"
            eps.append({"name": name, "url": url})
        return eps

    def _parse_episodes_from_links(self, html, vid):
        eps = []
        seen = set()
        for m in re.finditer(
            rf'/vod/play/{re.escape(str(vid))}/(?:sid/)?(\d+)',
            html,
        ):
            nid = m.group(1)
            if nid in seen:
                continue
            seen.add(nid)
            eps.append({
                "name": str(len(eps) + 1),
                "url": f"{HOST}/vod/play/{vid}/sid/{nid}",
            })
        return eps

    def _meta(self, html, key):
        m = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]*)"', html)
        if m:
            return m.group(1).replace("\\n", "\n").replace("\\u003c", "<").replace("\\u003e", ">")
        return ""

    def _title(self, html):
        m = re.search(r"<title>([^<]+)</title>", html)
        if m:
            return m.group(1).split("_")[0].split("-")[0].strip()
        return ""

    @staticmethod
    def _safe(s):
        return str(s or "").replace("$", "＄").replace("#", "＃").strip()
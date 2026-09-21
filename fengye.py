# coding: utf-8
import json
import re
import urllib.parse
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "枫叶影视"

    def init(self, extend=""):
        self.siteUrl = "https://fyeys.com"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.siteUrl,
        }

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        return False

    def action_fetch_next_data(self, url):
        """通用方法：提取 Next.js 页面中 __NEXT_DATA__ JSON"""
        try:
            res = self.fetch(url, headers=self.header)
            if res.status_code != 200:
                return {}
            html = res.text
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                html,
                re.S,
            )
            if match:
                return json.loads(match.group(1))
        except Exception as e:
            print(f"Fetch Error: {e}")
        return {}

    def homeContent(self, filter):
        result = {}
        # 分类映射列表
        classes = [
            {"type_id": "movie", "type_name": "电影"},
            {"type_id": "tv", "type_name": "电视剧"},
            {"type_id": "zongyi", "type_name": "综艺"},
            {"type_id": "dongman", "type_name": "动漫"},
        ]
        result["class"] = classes

        next_data = self.action_fetch_next_data(self.siteUrl)
        page_props = next_data.get("props", {}).get("pageProps", {})

        vod_list = []
        raw_list = (
            page_props.get("recommend", [])
            or page_props.get("list", [])
            or page_props.get("data", [])
        )

        for item in raw_list:
            if isinstance(item, dict):
                vod_id = str(item.get("vod_id") or item.get("id") or "")
                vod_name = item.get("vod_name") or item.get("title") or ""
                vod_pic = item.get("vod_pic") or item.get("pic") or ""
                vod_remarks = (
                    item.get("vod_remarks") or item.get("remarks") or ""
                )

                if vod_id and vod_name:
                    vod_list.append(
                        {
                            "vod_id": vod_id,
                            "vod_name": vod_name,
                            "vod_pic": vod_pic,
                            "vod_remarks": vod_remarks,
                        }
                    )

        result["list"] = vod_list
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        # 修正：去除了会导致 404 的 .html 后缀，适配 Next.js 路由
        url = f"{self.siteUrl}/vod/show/id/{tid}/page/{pg}"
        next_data = self.action_fetch_next_data(url)

        page_props = next_data.get("props", {}).get("pageProps", {})
        data_info = page_props.get("data", {})

        raw_list = []
        if isinstance(data_info, dict):
            raw_list = data_info.get("list", [])
        elif isinstance(data_info, list):
            raw_list = data_info

        vod_list = []
        for item in raw_list:
            if isinstance(item, dict):
                vod_id = str(item.get("vod_id") or item.get("id") or "")
                vod_name = item.get("vod_name") or item.get("title") or ""
                vod_pic = item.get("vod_pic") or item.get("pic") or ""
                vod_remarks = (
                    item.get("vod_remarks") or item.get("remarks") or ""
                )

                if vod_id and vod_name:
                    vod_list.append(
                        {
                            "vod_id": vod_id,
                            "vod_name": vod_name,
                            "vod_pic": vod_pic,
                            "vod_remarks": vod_remarks,
                        }
                    )

        result["list"] = vod_list
        result["page"] = int(pg)
        result["pagecount"] = 999
        result["limit"] = 20
        result["total"] = 9999
        return result

    def detailContent(self, ids):
        vod_id = ids[0]
        # 修正：适配详情页路径
        url = f"{self.siteUrl}/vod/detail/{vod_id}"
        next_data = self.action_fetch_next_data(url)

        page_props = next_data.get("props", {}).get("pageProps", {})
        detail = page_props.get("detail", {}) or page_props.get("data", {})

        vod = {
            "vod_id": vod_id,
            "vod_name": detail.get("vod_name") or detail.get("title") or "",
            "vod_pic": detail.get("vod_pic") or detail.get("pic") or "",
            "type_name": detail.get("type_name") or "",
            "vod_year": detail.get("vod_year") or "",
            "vod_area": detail.get("vod_area") or "",
            "vod_remarks": detail.get("vod_remarks") or "",
            "vod_actor": detail.get("vod_actor") or "",
            "vod_director": detail.get("vod_director") or "",
            "vod_content": detail.get("vod_content") or "",
        }

        play_from = []
        play_url = []

        play_list = detail.get("vod_play_list", []) or page_props.get(
            "playList", []
        )

        if isinstance(play_list, list):
            for source in play_list:
                name = (
                    source.get("player_info", {}).get("show")
                    or source.get("name")
                    or "默认线路"
                )
                play_from.append(name)

                urls_data = source.get("urls", [])
                urls_str = ""

                if isinstance(urls_data, list):
                    ep_list = []
                    for ep in urls_data:
                        if isinstance(ep, dict):
                            ep_name = ep.get("name", "")
                            ep_url = ep.get("url", "")
                            if ep_name and ep_url:
                                ep_list.append(f"{ep_name}${ep_url}")
                    urls_str = "#".join(ep_list)
                elif isinstance(urls_data, str):
                    urls_str = urls_data

                play_url.append(urls_str)

        vod["vod_play_from"] = "$$$".join(play_from)
        vod["vod_play_url"] = "$$$".join(play_url)

        return {"list": [vod]}

    def searchContent(self, key, quick):
        # 修正：补全 urllib 编码逻辑
        encoded_key = urllib.parse.quote(key)
        url = f"{self.siteUrl}/vod/search/{encoded_key}"
        next_data = self.action_fetch_next_data(url)

        page_props = next_data.get("props", {}).get("pageProps", {})
        raw_list = (
            page_props.get("data", [])
            or page_props.get("list", [])
            or page_props.get("searchResults", [])
        )

        vod_list = []
        for item in raw_list:
            if isinstance(item, dict):
                vod_id = str(item.get("vod_id") or item.get("id") or "")
                vod_name = item.get("vod_name") or item.get("title") or ""
                vod_pic = item.get("vod_pic") or item.get("pic") or ""
                vod_remarks = (
                    item.get("vod_remarks") or item.get("remarks") or ""
                )

                if vod_id and vod_name:
                    vod_list.append(
                        {
                            "vod_id": vod_id,
                            "vod_name": vod_name,
                            "vod_pic": vod_pic,
                            "vod_remarks": vod_remarks,
                        }
                    )

        return {"list": vod_list}

    def playerContent(self, flag, id, vipFlags):
        result = {}
        # 针对播放链接自动开启嗅探或直链识别
        if (
            id.startswith("http")
            and (".m3u8" in id or ".mp4" in id)
            and "jx" not in id
        ):
            result["parse"] = 0
            result["url"] = id
        else:
            result["parse"] = 1
            result["url"] = id

        result["header"] = self.header
        return result

    def localProxy(self, param):
        pass

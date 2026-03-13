# coding=utf-8
import sys
import re
from urllib.parse import urljoin
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        # 基础域名
        self.host = "https://6180101.xyz"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f"{self.host}/index.php/vod/type/id/40.html"
        }

    def getName(self):
        return "七区-稳定版"

    def homeContent(self, filter):
        # 核心修复：先定义分类，不要放在 try 里面，确保分类列表一定能返回
        result = {}
        classes = [
            {'type_id': '/index.php/vod/type/id/40.html', 'type_name': '最新视频'},
            {'type_id': '/index.php/vod/type/id/43.html', 'type_name': '更新列表'},
            {'type_id': '/index.php/vod/type/id/13.html', 'type_name': '精选内容'}
        ]
        result['class'] = classes
        
        # 尝试抓取首页列表（如果这里报错，分类依然会显示，只是列表为空）
        try:
            res = self.fetch(f"{self.host}/index.php/vod/type/id/40.html", headers=self.headers, timeout=10)
            if res and res.text:
                result['list'] = self._extract_list(res.text)
            else:
                result['list'] = []
        except:
            result['list'] = []
            
        return result

    def _extract_list(self, html):
        vods = []
        # 根据你提供的源码，提取详情页 ID
        # 这种匹配方式不需要图片和标题也能生成列表项
        links = re.findall(r'href="(/index.php/vod/detail/id/(\d+)\.html)"', html)
        
        seen_ids = set()
        for href, vid in links:
            if vid in seen_ids: continue
            seen_ids.add(vid)
            
            vods.append({
                'vod_id': href,
                'vod_name': f"视频ID:{vid}", 
                'vod_pic': "https://img.meituan.net/csc/ea1bb086d18160e6465a4ade60212d6b1150.ico",
                'vod_remarks': '点我进入'
            })
        return vods

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        pg = int(pg) if pg else 1
        url = urljoin(self.host, tid)
        if pg > 1:
            # 兼容该站的分页格式
            url = url.replace('.html', f'/page/{pg}.html')
        try:
            res = self.fetch(url, headers=self.headers, timeout=10)
            result['list'] = self._extract_list(res.text)
            result['page'] = pg
            result['pagecount'] = 99
            result['limit'] = 20
            result['total'] = 999
        except:
            result['list'] = []
        return result

    def detailContent(self, ids):
        href = ids[0]
        url = urljoin(self.host, href)
        vod = {
            'vod_id': href,
            'vod_name': '正在加载...',
            'vod_pic': 'https://img.meituan.net/csc/ea1bb086d18160e6465a4ade60212d6b1150.ico',
            'vod_play_from': '默认线路',
            'vod_play_url': f"点击播放${url}"
        }
        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags):
        # 启用 T3 嗅探模式
        return {'parse': 1, 'url': id, 'header': self.headers}

    def isVideoFormat(self, url): return False
    def manualVideoCheck(self): return False
    def searchContent(self, key, quick): return {"list": []}

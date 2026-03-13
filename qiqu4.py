# coding=utf-8
import sys
import re
from urllib.parse import urljoin
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://6180101.xyz"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.host
        }

    def getName(self):
        return "七区-兼容版"

    # 首页分类 + 默认抓取部分内容
    def homeContent(self, filter):
        result = {
            'class': [
                {'type_id': '/index.php/vod/type/id/40.html', 'type_name': '测试-分类40'},
                {'type_id': '/index.php/vod/type/id/43.html', 'type_name': '测试-分类43'}
            ],
            'list': []
        }
        try:
            res = self.fetch(urljoin(self.host, '/index.php/vod/type/id/40.html'), headers=self.headers)
            result['list'] = self._extract_list(res.text)
        except Exception as e:
            result['list'] = [{'vod_name': f'错误提示: {str(e)}', 'vod_id': 'err', 'vod_pic': ''}]
        
        if not result['list']:
            result['list'] = [{'vod_name': '脚本已运行但源码匹配失败', 'vod_id': 'null', 'vod_pic': ''}]
        
        return result

    # 通用列表解析
    def _extract_list(self, html):
        vods = []
        # 匹配 /vod/detail/id/12345.html 格式
        links = re.findall(r'href="([^"]*/vod/detail/id/(\d+)\.html)"', html)
        for href, vid in links:
            vods.append({
                'vod_id': href,
                'vod_name': f"视频ID {vid} (请点进详情页看真名)",
                'vod_pic': "https://img.meituan.net/csc/ea1bb086d18160e6465a4ade60212d6b1150.ico",
                'vod_remarks': '需嗅探'
            })
        # 去重
        res_list = []
        seen = set()
        for v in vods:
            if v['vod_id'] not in seen:
                res_list.append(v)
                seen.add(v['vod_id'])
        return res_list

    # 分类内容 + 分页
    def categoryContent(self, tid, pg, filter, extend):
        result = {
            'page': int(pg),
            'pagecount': 999,
            'limit': 90,
            'total': 999,
            'list': []
        }
        url = urljoin(self.host, tid)
        try:
            res = self.fetch(url, headers=self.headers)
            result['list'] = self._extract_list(res.text)
        except:
            pass
        return result

    # 详情页
    def detailContent(self, ids):
        vid = ids[0]
        url = urljoin(self.host, vid)
        vod = {
            "vod_id": vid,
            "vod_name": f"视频ID {vid}",
            "vod_pic": "",
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "需嗅探",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "专线",
            "vod_play_url": f"播放${url}"
        }
        return {"list": [vod]}

    # 播放页
    def playerContent(self, flag, id, vipFlags):
        return {'parse': 1, 'url': id, 'header': self.headers}
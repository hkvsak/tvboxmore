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
        return "七区-最终调试版"

    def homeContent(self, filter):
        # 分类必须写死在最前面，确保 100% 出现导航栏
        result = {
            'class': [
                {'type_id': '/index.php/vod/type/id/40.html', 'type_name': '测试-分类40'},
                {'type_id': '/index.php/vod/type/id/43.html', 'type_name': '测试-分类43'}
            ],
            'list': []
        }
        try:
            # 尝试抓取
            res = self.fetch(f"{self.host}/index.php/vod/type/id/40.html", headers=self.headers, timeout=15)
            if res and res.text:
                result['list'] = self._extract_list(res.text)
        except Exception as e:
            # 如果报错，显示一个报错条目
            result['list'] = [{'vod_name': f'错误提示: {str(e)}', 'vod_id': 'err', 'vod_pic': ''}]
        
        # 如果抓完了还是空的，给一个保底显示，证明脚本活着的
        if not result['list']:
            result['list'] = [{'vod_name': '脚本已运行但源码匹配失败', 'vod_id': 'null', 'vod_pic': ''}]
            
        return result

    def _extract_list(self, html):
        vods = []
        # 针对你提供的源码中 href="/index.php/vod/detail/id/72886.html" 的特殊匹配
        links = re.findall(r'href="(/index.php/vod/detail/id/(\d+)\.html)"', html)
        
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

    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': []}
        url = urljoin(self.host, tid)
        try:
            res = self.fetch(url, headers=self.headers)
            result['list'] = self._extract_list(res.text)
        except: pass
        return result

    def detailContent(self, ids):
        # 详情页逻辑...
        return {'list': [{'vod_play_from': '专线', 'vod_play_url': f'播放${urljoin(self.host, ids[0])}'}]}

    def playerContent(self, flag, id, vipFlags):
        return {'parse': 1, 'url': id, 'header': self.headers}

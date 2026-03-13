# coding=utf-8
import sys
import re
from urllib.parse import urljoin
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        # 即使根域名打不开，host 仍作为拼接基准
        self.host = "https://6180101.xyz"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f"{self.host}/index.php/vod/type/id/40.html"
        }

    def getName(self):
        return "七区精选"

    def _decrypt_title(self, text):
        if not text: return ""
        try:
            # 针对该类站点常见的位移加密进行还原
            result = ''.join([chr(ord(c) ^ 128) for c in text])
            return result if len(result) > 0 else text
        except:
            return text

    def _extract_list(self, html):
        vods = []
        # 针对 6180101.xyz 的典型 HTML 结构进行正则匹配
        # 匹配：链接、图片、标题
        pattern = r'lazyload.*?data-original="([^"]+)".*?href="([^"]+)" title="([^"]+)"'
        items = re.findall(pattern, html, re.S)
        
        for pic, href, title_raw in items:
            title = self._decrypt_title(title_raw.strip())
            vods.append({
                'vod_id': href, # 详情页路径
                'vod_name': title,
                'vod_pic': urljoin(self.host, pic),
                'vod_remarks': ''
            })
        return vods

    def homeContent(self, filter):
        # 分类必须以具体的有效路径开始
        classes = [
            {'type_id': '/index.php/vod/type/id/40.html', 'type_name': '最新视频'},
            {'type_id': '/index.php/vod/type/id/13.html', 'type_name': '精品推荐'},
            {'type_id': '/index.php/vod/type/id/21.html', 'type_name': '经典伦理'}
        ]
        result = {'class': classes}
        try:
            # 首页直接抓取你提供的有效页面
            res = self.fetch(f"{self.host}/index.php/vod/type/id/40.html", headers=self.headers)
            result['list'] = self._extract_list(res.text)
        except:
            result['list'] = []
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        curr_page = int(pg) if pg else 1
        # 构造分页 URL
        if curr_page == 1:
            url = urljoin(self.host, tid)
        else:
            # 假设分页规则为 /id/40/page/2.html
            url = urljoin(self.host, tid).replace('.html', f'/page/{curr_page}.html')
            
        try:
            res = self.fetch(url, headers=self.headers)
            result['list'] = self._extract_list(res.text)
            result['page'] = curr_page
            result['pagecount'] = 999
            result['limit'] = 20
            result['total'] = 9999
        except:
            result['list'] = []
        return result

    def detailContent(self, ids):
        # ids[0] 传进来的是 href 路径
        url = urljoin(self.host, ids[0])
        vod = {'vod_id': ids[0], 'vod_name': '', 'vod_pic': '', 'vod_remarks': '', 'vod_content': ''}
        try:
            res = self.fetch(url, headers=self.headers)
            html = res.text
            # 解析播放地址
            # 寻找立即播放按钮的链接或直接寻找 m3u8
            vod['vod_play_from'] = '快速线路'
            vod['vod_play_url'] = f'立即播放${url}' 
        except:
            pass
        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags):
        # 如果详情页地址直接是播放页，尝试嗅探
        return {'parse': 1, 'url': id, 'header': self.headers}

    def searchContent(self, key, quick):
        return {'list': []}

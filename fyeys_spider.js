/**
 * 枫叶影视 QuickJS 爬虫 - 严格基于 FongMi 官方 QuickJS 模板适配
 */

const HOST = "https://m.fyeys.com";
const DEFAULT_UA = "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36";

const CATE_LIST = [
    { type_id: "1", type_name: "电影" },
    { type_id: "2", type_name: "电视剧" },
    { type_id: "3", type_name: "综艺" },
    { type_id: "4", type_name: "动漫" },
    { type_id: "5", type_name: "短剧" }
];

function createSpider(site = {}) {
    let siteUrl = HOST;

    function init(ext) {
        if (typeof ext === "string" && ext.startsWith("http")) {
            siteUrl = ext.replace(/\/+$/, "");
        }
    }

    function home(filter) {
        return output({ class: CATE_LIST });
    }

    function homeVod() {
        return category("2", "1", false, {});
    }

    async function category(tid, pg, filter, extend) {
        void filter;
        void extend;
        const page = Math.max(1, parseInt(pg || "1", 10));
        const url = page <= 1 ? `${siteUrl}/vod/show/id/${tid}` : `${siteUrl}/vod/show/id/${tid}/page/${page}`;
        try {
            const html = await fetchHtml(url);
            const items = parseList(html);
            return output({
                list: items,
                page: page,
                pagecount: items.length >= 10 ? page + 1 : page,
                limit: 30,
                total: 999
            });
        } catch (e) {
            return output({ list: [], page: 1, pagecount: 1, limit: 30, total: 0 });
        }
    }

    async function search(key, quick, pg = "1") {
        void quick;
        const page = Math.max(1, parseInt(pg || "1", 10));
        const keyword = encodeURIComponent(stringValue(key).trim());
        if (!keyword) return output({ list: [], page: 1, pagecount: 1, limit: 30, total: 0 });

        const url = `${siteUrl}/vod/search/${keyword}----------${page}---.html`;
        try {
            const html = await fetchHtml(url);
            const items = parseList(html);
            return output({
                list: items,
                page: page,
                pagecount: items.length >= 10 ? page + 1 : page,
                limit: 30,
                total: 999
            });
        } catch (e) {
            return output({ list: [], page: 1, pagecount: 1, limit: 30, total: 0 });
        }
    }

    async function detail(id) {
        const vid = removePrefix(stringValue(id), "vod/").trim();
        if (!vid) return output({ list: [] });

        const url = `${siteUrl}/detail/${vid}`;
        try {
            const html = await fetchHtml(url);
            
            // 匹配标题
            let name = vid;
            const titleMatch = html.match(/<h1[^>]*>([^<]+)<\/h1>/i) || html.match(/alt="([^"]+)"/i);
            if (titleMatch) name = titleMatch[1].trim();

            // 匹配封面
            let pic = "";
            const picMatch = html.match(/(?:src|data-src|data-original)="(https?:\/\/[^"]+)"/i);
            if (picMatch) pic = picMatch[1];

            // 抓取并拼接剧集
            const episodes = parseEpisodes(html, vid);
            const playUrlStr = episodes.map(e => `${safeLabel(e.name)}$${e.url}`).join("#");

            return output({
                list: [{
                    vod_id: vid,
                    vod_name: name,
                    vod_pic: pic,
                    vod_play_from: "枫叶云播放",
                    vod_play_url: playUrlStr
                }]
            });
        } catch (e) {
            return output({ list: [] });
        }
    }

    async function play(flag, id, vipFlags) {
        void flag;
        void vipFlags;
        let playPageUrl = stringValue(id).trim();
        if (playPageUrl.startsWith("/")) {
            playPageUrl = siteUrl + playPageUrl;
        }

        // 符合官方 play 契约的通用嗅探配置
        return output({
            parse: 1,
            jx: 0,
            url: playPageUrl,
            header: {
                "User-Agent": DEFAULT_UA,
                "Referer": siteUrl + "/"
            }
        });
    }

    function live(url) {
        void url;
        return "[]";
    }

    function proxy(params) {
        void params;
        return [404, "text/plain; charset=utf-8", "Proxy is not configured"];
    }

    function action(value) {
        void value;
        return output({ msg: "OK" });
    }

    function sniffer() {
        return true;
    }

    function isVideo(url) {
        const u = stringValue(url).toLowerCase();
        if (!u.startsWith("http")) return false;
        // 排除干扰链接
        if (["google", "geetest", "cnzz", "51.la", "/ad/", ".js", ".css", ".png", ".jpg"].some(x => u.includes(x))) {
            return false;
        }
        return u.includes(".m3u8") || u.includes(".mp4") || u.includes(".flv") || u.includes("m3u8?");
    }

    function destroy() {}

    // 辅助工具方法
    async function fetchHtml(url) {
        const headers = { 
            "User-Agent": DEFAULT_UA, 
            "Referer": siteUrl + "/" 
        };
        const res = await http(url, { headers, timeout: 10000, redirect: 1 });
        return res ? (res.body || res.content || "") : "";
    }

    function parseList(html) {
        const items = [];
        const seen = new Set();
        const reg = /href="\/detail\/(\d+)"[^>]*>[\s\S]*?<img[^>]+(?:src|data-src|data-original)="(https?:\/\/[^"]+)"[\s\S]*?alt="([^"]+)"/gi;
        let m;
        while ((m = reg.exec(html)) !== null) {
            const vid = m[1];
            if (!seen.has(vid)) {
                seen.add(vid);
                items.push({ 
                    vod_id: `vod/${vid}`, 
                    vod_name: m[3].trim(), 
                    vod_pic: m[2], 
                    vod_remarks: "" 
                });
            }
        }
        return items;
    }

    function parseEpisodes(html, vid) {
        const eps = [];
        const seen = new Set();
        const playLinkRegex = new RegExp(`/vod/play/${vid}/[a-zA-Z0-9/._-]+`, 'gi');
        let m;
        while ((m = playLinkRegex.exec(html)) !== null) {
            const path = m[0];
            if (!seen.has(path)) {
                seen.add(path);
                const fullUrl = path.startsWith("http") ? path : `${siteUrl}${path}`;
                eps.push({
                    name: `第${eps.length + 1}集`,
                    url: fullUrl
                });
            }
        }
        return eps;
    }

    // 遵照官方规范的字符转换与工具函数
    function safeLabel(value) {
        return stringValue(value).replace(/\$/g, "＄").replace(/#/g, "＃").trim();
    }

    function removePrefix(value, prefix) {
        return value.startsWith(prefix) ? value.slice(prefix.length) : value;
    }

    function stringValue(value) {
        return value == null ? "" : String(value);
    }

    function output(value) {
        return JSON.stringify(value);
    }

    return {
        init,
        home,
        homeVod,
        category,
        detail,
        search,
        play,
        live,
        proxy,
        action,
        sniffer,
        isVideo,
        destroy,
    };
}

export default createSpider;

/**
 * 枫叶影视 QuickJS 爬虫 - 终极稳健版
 */

const DEFAULT_HOST = "https://m.fyeys.com";
const DEFAULT_UA = "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36";

const CATE_LIST = [
    { type_id: "1", type_name: "电影" },
    { type_id: "2", type_name: "电视剧" },
    { type_id: "3", type_name: "综艺" },
    { type_id: "4", type_name: "动漫" },
    { type_id: "5", type_name: "短剧" }
];

function createSpider(site = {}) {
    let siteUrl = DEFAULT_HOST;

    function init(ext) {
        if (typeof ext === "string" && ext.startsWith("http")) {
            siteUrl = ext.replace(/\/+$/, "");
        } else if (typeof ext === "object" && ext && (ext.host || ext.request_url)) {
            siteUrl = String(ext.host || ext.request_url).replace(/\/+$/, "");
        }
    }

    function home(filter) { return output({ class: CATE_LIST }); }
    function homeVod() { return category("2", "1", false, {}); }

    async function category(tid, pg, filter, extend) {
        void filter; void extend;
        const page = Math.max(1, parseInt(pg || "1", 10));
        const url = page <= 1 ? `${siteUrl}/vod/show/id/${tid}` : `${siteUrl}/vod/show/id/${tid}/page/${page}`;
        try {
            const html = await fetchHtml(url);
            const items = parseList(html);
            return output({ list: items, page: page, pagecount: items.length >= 10 ? page + 1 : page, limit: 30, total: 999 });
        } catch (e) {
            return output({ list: [], page: 1, pagecount: 1, limit: 30, total: 0 });
        }
    }

    async function search(key, quick, pg = "1") {
        void quick;
        const page = Math.max(1, parseInt(pg || "1", 10));
        const keyword = encodeURIComponent(stringValue(key).trim());
        if (!keyword) return output({ list: [], page: 1, pagecount: 1, limit: 30, total: 0 });

        const url = `${siteUrl}/vod/search/page/${page}/wd/${keyword}`;
        try {
            const html = await fetchHtml(url);
            const items = parseList(html);
            return output({ list: items, page: page, pagecount: items.length >= 10 ? page + 1 : page, limit: 30, total: 999 });
        } catch (e) {
            return output({ list: [], page: 1, pagecount: 1, limit: 30, total: 0 });
        }
    }

    async function detail(id) {
        const vid = removePrefix(stringValue(id), "vod/").trim();
        if (!vid) return output({ list: [] });

        const url = `${siteUrl}/vod/detail/${vid}`;
        try {
            const html = await fetchHtml(url);
            
            // 提取并清理标题
            let name = vid;
            const titleMatch = html.match(/<h[1-3][^>]*>([^<]+)<\/h[1-3]>/i) || html.match(/title="([^"]+)"/i);
            if (titleMatch) name = cleanHtmlEntities(titleMatch[1].trim());

            // 提取封面
            let pic = "";
            const picMatch = html.match(/(?:src|data-src|data-original)="(https?:\/\/[^"]+)"/i);
            if (picMatch) pic = picMatch[1];

            // 提取剧集列表
            const episodes = parseEpisodes(html, vid);
            const playUrlStr = episodes.map(e => `${safeLabel(e.name)}$${e.url}`).join("#");

            return output({
                list: [{
                    vod_id: vid,
                    vod_name: name,
                    vod_pic: pic,
                    vod_play_from: "枫叶云播",
                    vod_play_url: playUrlStr
                }]
            });
        } catch (e) {
            return output({ list: [] });
        }
    }

    async function play(flag, id, vipFlags) {
        void flag; void vipFlags;
        let playPageUrl = stringValue(id).trim();
        if (playPageUrl.startsWith("/")) {
            playPageUrl = siteUrl + playPageUrl;
        }

        return output({
            parse: 1,
            jx: 0,
            url: playPageUrl,
            header: {
                "User-Agent": DEFAULT_UA,
                "Referer": `${siteUrl}/`
            }
        });
    }

    function live(url) { void url; return "[]"; }
    function proxy(params) { void params; return [404, "text/plain", "Not Found"]; }
    function action(value) { void value; return output({ msg: "OK" }); }
    function sniffer() { return true; }

    function isVideo(url) {
        const u = stringValue(url).toLowerCase();
        if (!u.startsWith("http")) return false;
        
        // 1. 优先放行切片资源与视频流
        if ([".m3u8", ".mp4", "splitout", "kqgfbs.com", "mime=video"].some(v => u.includes(v))) {
            return true;
        }

        // 2. 屏蔽常见广告与无关静态资源
        if (["google", "geetest", "cnzz", "51.la", "/ad/", ".js", ".css", ".png", ".jpg", ".gif"].some(x => u.includes(x))) {
            return false;
        }
        return false;
    }

    function destroy() {}

    async function fetchHtml(url) {
        const headers = { "User-Agent": DEFAULT_UA, "Referer": `${siteUrl}/` };
        const res = await http(url, { headers, timeout: 10000, redirect: 1 });
        return res ? (res.body || res.content || "") : "";
    }

    function parseList(html) {
        const items = [];
        const seen = new Set();
        const linkReg = /href="\/vod\/(?:detail|play)\/(\d+)[^"]*"/gi;
        let m;

        while ((m = linkReg.exec(html)) !== null) {
            const vid = m[1];
            if (!seen.has(vid)) {
                const startIndex = Math.max(0, m.index - 200);
                const endIndex = Math.min(html.length, m.index + 500);
                const context = html.substring(startIndex, endIndex);

                const picMatch = context.match(/(?:src|data-src|data-original)="(https?:\/\/[^"]+)"/i);
                const nameMatch = context.match(/alt="([^"]+)"/i) || context.match(/title="([^"]+)"/i) || context.match(/<h[1-9][^>]*>([^<]+)<\/h[1-9]>/i);

                const name = nameMatch ? cleanHtmlEntities(nameMatch[1].trim()) : "";
                const pic = picMatch ? picMatch[1] : "";

                if (name && !name.includes("首页") && !name.includes("更多")) {
                    seen.add(vid);
                    items.push({
                        vod_id: vid,
                        vod_name: name,
                        vod_pic: pic,
                        vod_remarks: ""
                    });
                }
            }
        }
        return items;
    }

    function parseEpisodes(html, vid) {
        const eps = [];
        const seen = new Set();
        const episodeReg = new RegExp(`href="(/vod/play/${vid}/\\d+/\\d+)"[^>]*>([\\s\\S]*?)</a>`, 'gi');
        let m;
        
        while ((m = episodeReg.exec(html)) !== null) {
            const path = m[1];
            const rawContent = m[2];
            const cleanName = cleanHtmlEntities(rawContent.replace(/<[^>]+>/g, '').trim());
            
            if (!seen.has(path)) {
                seen.add(path);
                const fullUrl = `${siteUrl}${path}`;
                const epName = cleanName || `第${eps.length + 1}集`;
                eps.push({
                    name: epName,
                    url: fullUrl
                });
            }
        }

        if (eps.length === 0) {
            eps.push({
                name: "播放页直达",
                url: `${siteUrl}/vod/play/${vid}/1/1`
            });
        }
        return eps;
    }

    function cleanHtmlEntities(str) {
        if (!str) return "";
        return str.replace(/&nbsp;/gi, " ")
                  .replace(/&amp;/gi, "&")
                  .replace(/&lt;/gi, "<")
                  .replace(/&gt;/gi, ">")
                  .replace(/&quot;/gi, '"')
                  .replace(/&#039;/gi, "'");
    }

    function safeLabel(value) { return stringValue(value).replace(/\$/g, "＄").replace(/#/g, "＃").trim(); }
    function removePrefix(value, prefix) { return value.startsWith(prefix) ? value.slice(prefix.length) : value; }
    function stringValue(value) { return value == null ? "" : String(value); }
    function output(value) { return JSON.stringify(value); }

    return { init, home, homeVod, category, detail, search, play, live, proxy, action, sniffer, isVideo, destroy };
}

export default createSpider;

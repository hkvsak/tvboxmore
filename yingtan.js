// 2026 最新 TVBox 异步优化版 JS Spider
const CryptoJS = require('crypto-js');

const Spider = {
    headers: { 'User-Agent': 'okhttp/4.12.0' },
    FIXED_CONFIG: {
        host: 'http://cms.9513tv.vip',
        cmskey: 'ziKv8NzFSwNoBUYRJclwwjRaiTWBb7ON',
        RawPlayUrl: 0
    },
    init: function () {
        this.host = this.FIXED_CONFIG.host;
        this.cmskey = this.FIXED_CONFIG.cmskey || '';
        this.raw_play_url = parseInt(this.FIXED_CONFIG.RawPlayUrl || 0);
        this.homeCache = null;
        this.homeCacheTime = 0;
    },

    // 异步 fetch JSON
    fetchJson: async function(url) {
        let res = await request({ url: url, headers: this.headers });
        return JSON.parse(res);
    },

    // 首页视频，支持缓存
    homeVideoContent: async function () {
        const now = Date.now();
        if (this.homeCache && now - this.homeCacheTime < 30000) return this.homeCache;

        const data = await this.fetchJson(`${this.host}/api.php/app/index_video?token=`);
        let videos = [];
        data.list.forEach(item => videos = videos.concat(item.vlist));

        this.homeCache = { list: videos };
        this.homeCacheTime = now;
        return this.homeCache;
    },

    // 首页分类与 filters
    homeContent: async function () {
        const data = await this.fetchJson(`${this.host}/api.php/app/nav?token=`);
        const keys = ["class", "area", "lang", "year", "letter", "by", "sort"];
        let filters = {}, classes = [];

        data.list.forEach(item => {
            classes.push({ type_name: item.type_name, type_id: item.type_id });
            const type_id = String(item.type_id);
            const type_extend = item.type_extend || {};
            if (keys.some(k => type_extend[k] && type_extend[k].trim() !== "")) {
                filters[type_id] = [];
                keys.forEach(k => {
                    if (type_extend[k] && type_extend[k].trim() !== "") {
                        let values = type_extend[k].split(",").map(v => v.trim()).filter(v => v !== "");
                        filters[type_id].push({
                            key: k,
                            name: k,
                            value: values.map(v => ({ n: v, v: v }))
                        });
                    }
                });
            }
        });

        return { class: classes, filters: filters };
    },

    // 分类内容
    categoryContent: async function (tid, pg, filter, extend) {
        let query = [`tid=${tid}`, `pg=${pg}`, `limit=18`];
        if (extend.class) query.push(`class=${extend.class}`);
        if (extend.area) query.push(`area=${extend.area}`);
        if (extend.lang) query.push(`lang=${extend.lang}`);
        if (extend.year) query.push(`year=${extend.year}`);
        const url = `${this.host}/api.php/app/video?${query.join("&")}`;
        return await this.fetchJson(url);
    },

    // 搜索内容
    searchContent: async function (key, quick, pg = "1") {
        const data = await this.fetchJson(`${this.host}/api.php/app/search?text=${key}&pg=${pg}`);
        data.list.forEach(item => delete item.type);
        return { list: data.list, page: pg };
    },

    // 视频详情，异步解密
    detailContent: async function (ids) {
        const data = (await this.fetchJson(`${this.host}/api.php/app/video_detail?id=${ids[0]}`)).data;
        let show = [], play_urls = [];

        for (const i of data.vod_url_with_player) {
            const urls = i.url.split('#');
            let urls2 = await Promise.all(urls.map(async j => {
                if (!j) return "";
                const parts = j.split('$');
                return parts.length === 2 ? `${parts[0]}$${this.lvdou(parts[1])}` : parts[0];
            }));
            play_urls.push(urls2.join('#'));
            show.push(i.name.trim());
        }

        delete data.vod_url_with_player;
        data.vod_play_from = show.join('$$$');
        data.vod_play_url = play_urls.join('$$$');
        return { list: [data] };
    },

    // 播放器逻辑
    playerContent: function (flag, video_id, vipFlags) {
        let jx = 0;
        if (this.check_paly_url(video_id)) {
            if (this.raw_play_url === 1) video_id = this.raw_url(video_id);
        } else if (/www\.iqiyi|v\.qq|v\.youku|www\.mgtv|www\.bilibili/.test(video_id)) {
            jx = 1;
        }
        return { jx: jx, playUrl: '', parse: 0, url: video_id, header: this.headers };
    },

    // AES 解密
    lvdou: function (text) {
        const keyStr = this.cmskey.slice(0,16);
        const ivStr = this.cmskey.slice(-16);
        const prefix = "lvdou+";
        if (!text.startsWith(prefix)) return text;
        try {
            let ciphertext = CryptoJS.enc.Base64.parse(text.slice(prefix.length));
            let decrypted = CryptoJS.AES.decrypt(
                { ciphertext: ciphertext },
                CryptoJS.enc.Utf8.parse(keyStr),
                { iv: CryptoJS.enc.Utf8.parse(ivStr), mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 }
            );
            return decrypted.toString(CryptoJS.enc.Utf8);
        } catch (e) {
            return text;
        }
    },

    // 原始 URL 跳转
    raw_url: function (original_url) {
        try {
            const res = request({ url: original_url, headers: this.headers, redirect: false });
            if (res.status >= 300 && res.status < 400 && res.headers.Location) {
                const redirect = res.headers.Location;
                return redirect.startsWith("http") ? redirect : new URL(redirect, original_url).href;
            }
            return original_url;
        } catch (e) { return original_url; }
    },

    // URL 校验
    check_paly_url: function (content) {
        const pattern = /https?:\/\/.*(\.(mp4|m3u8|flv|avi|mkv|ts|mov|wmv|webm)|lyyytv\.cn\/)/i;
        return pattern.test(content);
    },

    getName: function(){ return ""; },
    localProxy: function(param){ return param; },
    isVideoFormat: function(url){ return true; },
    manualVideoCheck: function(){ return false; },
    destroy: function(){}
};

Spider.init();
module.exports = Spider;
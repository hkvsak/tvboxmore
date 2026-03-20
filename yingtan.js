// api_server.gs.js
const express = require('express');
const CryptoJS = require('crypto-js');
const axios = require('axios');
const { URL } = require('url');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const CONFIG = {
    host: 'http://cms.9513tv.vip',
    cmskey: 'ziKv8NzFSwNoBUYRJclwwjRaiTWBb7ON',
    RawPlayUrl: 0
};

// ------------------ 工具函数 ------------------
function lvdou(text) {
    const key = CryptoJS.enc.Utf8.parse(CONFIG.cmskey.slice(0,16));
    const iv = CryptoJS.enc.Utf8.parse(CONFIG.cmskey.slice(-16));
    const prefix = "lvdou+";
    if (!text.startsWith(prefix)) return text;
    try {
        const ciphertext = CryptoJS.enc.Base64.parse(text.slice(prefix.length));
        const decrypted = CryptoJS.AES.decrypt(
            { ciphertext: ciphertext },
            key,
            { iv: iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 }
        );
        return decrypted.toString(CryptoJS.enc.Utf8);
    } catch(e) {
        return text;
    }
}

function check_paly_url(content) {
    const pattern = /https?:\/\/.*(\.(mp4|m3u8|flv|avi|mkv|ts|mov|wmv|webm)|lyyytv\.cn\/)/i;
    return pattern.test(content);
}

async function raw_url(original_url) {
    try {
        const res = await axios.get(original_url, { maxRedirects: 0, validateStatus: null });
        if (res.status >= 300 && res.status < 400 && res.headers.location) {
            const redirect = res.headers.location;
            return redirect.startsWith("http") ? redirect : new URL(redirect, original_url).href;
        }
        return original_url;
    } catch(e) {
        return original_url;
    }
}

// ------------------ 接口 ------------------

// 首页视频
app.get('/api.php/app/index_video', async (req, res) => {
    try {
        const resp = await axios.get(`${CONFIG.host}/api.php/app/index_video?token=`, { headers: {'User-Agent':'okhttp/4.12.0'} });
        const data = resp.data;
        let videos = [];
        for (let item of data.list || []) videos = videos.concat(item.vlist || []);
        res.json({ list: videos });
    } catch(e) { res.json({ list: [] }); }
});

// 首页分类
app.get('/api.php/app/nav', async (req, res) => {
    try {
        const resp = await axios.get(`${CONFIG.host}/api.php/app/nav?token=`, { headers: {'User-Agent':'okhttp/4.12.0'} });
        const data = resp.data;
        const keys = ["class","area","lang","year","letter","by","sort"];
        let filters = {};
        let classes = [];
        for (let item of data.list || []) {
            const type_extend = item.type_extend || {};
            let has_non_empty = Object.keys(type_extend).some(k => keys.includes(k) && type_extend[k].trim() !== "");
            classes.push({ type_name: item.type_name, type_id: item.type_id });
            if (has_non_empty) filters[String(item.type_id)] = [];
            for (let dkey in type_extend) {
                if (keys.includes(dkey) && type_extend[dkey].trim() !== "") {
                    const vals = type_extend[dkey].split(",").map(v => v.trim()).filter(v => v!=="");
                    filters[String(item.type_id)].push({ key:dkey, name:dkey, value: vals.map(v=>({n:v,v:v})) });
                }
            }
        }
        res.json({ class: classes, filters: filters });
    } catch(e) { res.json({ class: [], filters: {} }); }
});

// 分类内容
app.get('/api.php/app/video', async (req, res) => {
    try {
        const url = `${CONFIG.host}/api.php/app/video?${new URLSearchParams(req.query).toString()}`;
        const resp = await axios.get(url, { headers: {'User-Agent':'okhttp/4.12.0'} });
        res.json(resp.data);
    } catch(e) { res.json({ list: [] }); }
});

// 搜索
app.get('/api.php/app/search', async (req, res) => {
    try {
        const url = `${CONFIG.host}/api.php/app/search?text=${req.query.text}&pg=${req.query.pg||1}`;
        const resp = await axios.get(url, { headers: {'User-Agent':'okhttp/4.12.0'} });
        const data = resp.data;
        for (let item of data.list || []) delete item.type;
        res.json({ list: data.list, page: req.query.pg||"1" });
    } catch(e) { res.json({ list: [], page: "1" }); }
});

// 视频详情
app.get('/api.php/app/video_detail', async (req, res) => {
    try {
        const url = `${CONFIG.host}/api.php/app/video_detail?id=${req.query.id}`;
        const resp = await axios.get(url, { headers: {'User-Agent':'okhttp/4.12.0'} });
        const data = resp.data.data || {};
        let show=[], play_urls=[];
        for (let i of data.vod_url_with_player || []) {
            const urls = (i.url||"").split('#');
            let urls2 = [];
            for (let j of urls) {
                if (!j) continue;
                const parts = j.split('$',2);
                urls2.push(parts.length==2 ? `${parts[0]}$${lvdou(parts[1])}`:parts[0]);
            }
            play_urls.push(urls2.join('#'));
            show.push((i.name||"").trim());
        }
        delete data.vod_url_with_player;
        data.vod_play_from = show.join('$$$');
        data.vod_play_url = play_urls.join('$$$');
        res.json({ list: [data] });
    } catch(e) { res.json({ list: [] }); }
});

// 启动服务器
const PORT = 9513;
app.listen(PORT, () => console.log(`JS API server running at http://localhost:${PORT}`));
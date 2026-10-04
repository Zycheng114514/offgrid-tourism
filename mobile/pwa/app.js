// Traveller app: download a region pack, then search it with no connection.
// The search rules mirror server/offgrid/search.py; all search words come from the pack,
// so queries work in every language the region lists (including Chinese, matched without spaces).
// The Ask tab answers questions in the traveller's own words: by the server when online, or on this phone,
// where a small downloaded model (assistant-worker.js) only turns the question into search filters.
"use strict";

const $ = id => document.getElementById(id);
const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } },
  del(k) { try { localStorage.removeItem(k); } catch (e) {} },
};
let config = null, pack = null, catFilter = null, smsPhone = "", smsLast = 0, ui = "en";

// ---- interface text ------------------------------------------------------------
const STR = {
  en: {
    banner: "Demo: every business and phone number is invented; village names are real.",
    noPack: "No listings downloaded yet.", download: "Download listings", update: "Update",
    packLine: "{n} listings for {region}", packWhen: "downloaded {when}{kb}", kbOnPhone: " · {kb} KB on this phone",
    offlineFail: "Could not download: no connection. Listings already on this phone still work.",
    tabSearch: "Search (works offline)", tabSms: "Ask by SMS", placeholder: "e.g. cheap room Tomok",
    all: "All", food: "Food", lodging: "Stay", transport: "Transport", guide: "Guide", other: "Other",
    openNow: "Open now", cheapest: "Cheapest first",
    results: "{n} results", result1: "1 result", near: "near {place}", onPhone: "searched on this phone",
    today: "confirmed by host today", daysAgo: "confirmed by host {n} days ago", dayAgo: "confirmed by host 1 day ago",
    stale: "may be out of date", openToday: "open today", closedToday: "closed today", capacity: "capacity {n}",
    call: "Call", sms: "SMS", invented: "(invented)", noPhone: "The host did not agree to show a phone number.",
    nothing: 'Nothing matches. Try a village name, or "food", "room", "boat", "guide".',
    hostWords: "Host's words", online: "Online", offline: "Offline",
    smsIntro: "With phone signal but no mobile data, a traveller texts the service number and gets the top 3 listings back by SMS, in English, Indonesian or Chinese. In this demo the page stands in for the phone's SMS app, so it needs a connection.",
    smsPlaceholder: "SEARCH food Garoga", send: "Send", smsOffline: "(The demo needs a connection for the SMS simulator.)",
    smsElsewhere: "The SMS simulator keeps conversations, so it runs on our own server, not on this host.", open: "Open it",
    // Ask tab
    tabAsk: "Ask", askIntro: "Ask in your own words, in English, Indonesian or Chinese.",
    askPlaceholder: "e.g. Is there a cheap room near Tomok?", askSend: "Ask", askLocal: "Answer on this phone",
    askBusyServer: "Asking the server…", askBusyLoad: "Loading the assistant from this phone's storage…",
    askBusyModel: "The model on this phone is reading the question…",
    whoServerModel: "Answered by the server's model ({model})",
    whoServerSim: "Answered by the server's model (simulated in this demo: the outputs were written in advance)",
    whoServerRules: "Answered by the server's search rules",
    whoPhoneModel: "Answered on this phone by a small model (no connection needed)",
    whoPhoneRulesOffline: "Offline: the assistant is not downloaded, so these are plain search results",
    whoPhoneRules: "The assistant is not downloaded on this phone, so these are plain search results",
    whoPhoneRulesFailed: "The assistant on this phone did not work ({reason}), so these are plain search results",
    fallbackServer: "The server did not answer ({reason}), so this phone answered.",
    reason404: "this server has no question service", reasonNet: "no connection",
    reasonTimeout: "no reply within {s} seconds", reasonStatus: "error {status}", reasonBad: "a reply this app cannot read",
    noteChecksFailed: "The model's answer failed a check, so the answer was built from the listings by rules.",
    noteNoModel: "The model gave no answer, so the answer was built from the listings by rules.",
    noteNothing: "Nothing in the listings matches the question.",
    detailsServer: "How the server answered", checkFailed: "Check failed: {check} ({detail})",
    rejectedAnswer: "The model's answer that was rejected", modelOutput: "What the model wrote", serverSaid: "Server note",
    filtersTitle: "Filters chosen by the model:", fCategory: "category: {c}", fCheap: "cheap", fNow: "open now",
    fKeywords: "words: {w}", fNone: "none", fIgnored: "Ignored because not allowed: {what}",
    fUnreadable: "the model's reply was not valid JSON, so no filters were used",
    placeByRules: "Place (found by the search rules, not by the model): {place}",
    placeNone: "No village named (the search rules look for village names).",
    modelTime: "The model took {s} s on the {device}.", loadTime: "Loading it from storage took {s} s.",
    ansNone: "No listing on this phone matches{near}.", ansOne: "1 place matches{near}: {list}.",
    ansFew: "{n} places match{near}: {list}.", ansMany: "{n} places match{near}. The first 3: {list}.",
    ansNear: " near {place}", showAll: "Show all {n}", askNoPack: "Download the listings first (button at the top).",
    assistTitle: "Offline assistant", assistDownload: "Download offline assistant (about {mb} MB)",
    assistAbout: "A small language model (Qwen2.5-0.5B-Instruct, Apache-2.0 licence), downloaded from Hugging Face. It runs inside this browser, and questions answered on this phone never leave the phone. The model only turns your question into search filters; the answer is built from the listings.",
    assistNotYet: "Not downloaded. Without it, questions asked offline get plain search results.",
    assistStarting: "Starting the download…", assistDownloading: "Downloading from Hugging Face: {done} of {total} MB",
    assistPreparing: "Downloaded. Preparing the model…", assistLoading: "Loading the assistant from this phone's storage: {pct}%",
    assistReady: "Downloaded: {mb} MB on this phone. Runs on the {device}, with no connection.",
    assistOffline: "Downloading needs a connection.", assistFailed: "Download failed: {msg}", assistNotStored: "The browser could not keep the model on this phone ({files}), so it would not work offline.",
    assistGpuFailed: "This phone's graphics chip could not run the model. Tap download again to get the version for the main processor (about 520 MB).",
    assistMissing: "The assistant's files are no longer on this phone (the browser may have removed them). Download it again to use it offline.",
    assistNoSpace: "Not enough free space: about {need} MB needed, {free} MB free.",
    assistNoWorker: "This browser cannot run the assistant.", assistRemove: "Remove from this phone",
    assistRemoveConfirm: "Remove the offline assistant ({mb} MB) from this phone?",
    deviceGpu: "graphics chip (WebGPU)", deviceCpu: "main processor (WebAssembly)",
  },
  id: {
    banner: "Demo: semua usaha dan nomor telepon adalah rekaan; nama desa asli.",
    noPack: "Belum ada data yang diunduh.", download: "Unduh daftar", update: "Perbarui",
    packLine: "{n} usaha di {region}", packWhen: "diunduh {when}{kb}", kbOnPhone: " · {kb} KB di ponsel ini",
    offlineFail: "Gagal mengunduh: tidak ada koneksi. Data yang sudah ada di ponsel tetap bisa dipakai.",
    tabSearch: "Cari (tanpa internet)", tabSms: "Tanya lewat SMS", placeholder: "mis. kamar murah Tomok",
    all: "Semua", food: "Makan", lodging: "Inap", transport: "Transportasi", guide: "Pemandu", other: "Lainnya",
    openNow: "Buka sekarang", cheapest: "Termurah dulu",
    results: "{n} hasil", result1: "1 hasil", near: "dekat {place}", onPhone: "dicari di ponsel ini",
    today: "dikonfirmasi pemilik hari ini", daysAgo: "dikonfirmasi pemilik {n} hari lalu", dayAgo: "dikonfirmasi pemilik 1 hari lalu",
    stale: "mungkin sudah tidak berlaku", openToday: "buka hari ini", closedToday: "tutup hari ini", capacity: "kapasitas {n}",
    call: "Telepon", sms: "SMS", invented: "(rekaan)", noPhone: "Pemilik tidak setuju nomornya ditampilkan.",
    nothing: 'Tidak ada hasil. Coba nama desa, atau "makan", "kamar", "kapal", "pemandu".',
    hostWords: "Kata pemilik", online: "Online", offline: "Offline",
    smsIntro: "Ada sinyal tapi tidak ada data? Kirim SMS ke nomor layanan dan dapatkan 3 hasil teratas lewat SMS. Di demo ini halaman ini menggantikan aplikasi SMS, jadi perlu koneksi.",
    smsPlaceholder: "CARI makan Garoga", send: "Kirim", smsOffline: "(Simulator SMS di demo ini perlu koneksi.)",
    smsElsewhere: "Simulator SMS menyimpan percakapan, jadi berjalan di server kami sendiri, bukan di sini.", open: "Buka",
    // Ask tab
    tabAsk: "Tanya", askIntro: "Bertanyalah dengan kata-kata sendiri, dalam bahasa Inggris, Indonesia, atau Mandarin.",
    askPlaceholder: "mis. Ada kamar murah dekat Tomok?", askSend: "Tanya", askLocal: "Jawab di ponsel ini",
    askBusyServer: "Bertanya ke server…", askBusyLoad: "Memuat asisten dari penyimpanan ponsel…",
    askBusyModel: "Model di ponsel ini sedang membaca pertanyaan…",
    whoServerModel: "Dijawab oleh model di server ({model})",
    whoServerSim: "Dijawab oleh model di server (disimulasikan dalam demo ini: jawabannya sudah ditulis sebelumnya)",
    whoServerRules: "Dijawab oleh aturan pencarian di server",
    whoPhoneModel: "Dijawab di ponsel ini oleh model kecil (tanpa koneksi)",
    whoPhoneRulesOffline: "Offline: asisten belum diunduh, jadi ini hasil pencarian biasa",
    whoPhoneRules: "Asisten belum diunduh di ponsel ini, jadi ini hasil pencarian biasa",
    whoPhoneRulesFailed: "Asisten di ponsel ini tidak berjalan ({reason}), jadi ini hasil pencarian biasa",
    fallbackServer: "Server tidak menjawab ({reason}), jadi ponsel ini yang menjawab.",
    reason404: "server ini tidak punya layanan tanya-jawab", reasonNet: "tidak ada koneksi",
    reasonTimeout: "tidak ada balasan dalam {s} detik", reasonStatus: "galat {status}", reasonBad: "balasan yang tidak bisa dibaca aplikasi ini",
    noteChecksFailed: "Jawaban model gagal dalam pemeriksaan, jadi jawaban disusun dari daftar usaha dengan aturan.",
    noteNoModel: "Model tidak memberi jawaban, jadi jawaban disusun dari daftar usaha dengan aturan.",
    noteNothing: "Tidak ada usaha dalam daftar yang cocok dengan pertanyaan.",
    detailsServer: "Cara server menjawab", checkFailed: "Pemeriksaan gagal: {check} ({detail})",
    rejectedAnswer: "Jawaban model yang ditolak", modelOutput: "Yang ditulis model", serverSaid: "Catatan server",
    filtersTitle: "Filter yang dipilih model:", fCategory: "kategori: {c}", fCheap: "murah", fNow: "buka sekarang",
    fKeywords: "kata: {w}", fNone: "tidak ada", fIgnored: "Diabaikan karena tidak diizinkan: {what}",
    fUnreadable: "balasan model bukan JSON yang sah, jadi tidak ada filter yang dipakai",
    placeByRules: "Tempat (ditemukan oleh aturan pencarian, bukan oleh model): {place}",
    placeNone: "Tidak ada nama desa (aturan pencarian mencari nama desa).",
    modelTime: "Model butuh {s} detik di {device}.", loadTime: "Memuatnya dari penyimpanan butuh {s} detik.",
    ansNone: "Tidak ada usaha di ponsel ini yang cocok{near}.", ansOne: "1 tempat cocok{near}: {list}.",
    ansFew: "{n} tempat cocok{near}: {list}.", ansMany: "{n} tempat cocok{near}. 3 teratas: {list}.",
    ansNear: " dekat {place}", showAll: "Tampilkan semua {n}", askNoPack: "Unduh daftar usaha dulu (tombol di atas).",
    assistTitle: "Asisten offline", assistDownload: "Unduh asisten offline (sekitar {mb} MB)",
    assistAbout: "Model bahasa kecil (Qwen2.5-0.5B-Instruct, lisensi Apache-2.0) yang diunduh dari Hugging Face. Model ini berjalan di dalam browser ini, dan pertanyaan yang dijawab di ponsel ini tidak pernah keluar dari ponsel. Model hanya mengubah pertanyaan menjadi filter pencarian; jawabannya disusun dari daftar usaha.",
    assistNotYet: "Belum diunduh. Tanpa asisten, pertanyaan saat offline mendapat hasil pencarian biasa.",
    assistStarting: "Mulai mengunduh…", assistDownloading: "Mengunduh dari Hugging Face: {done} dari {total} MB",
    assistPreparing: "Sudah diunduh. Menyiapkan model…", assistLoading: "Memuat asisten dari penyimpanan ponsel: {pct}%",
    assistReady: "Sudah diunduh: {mb} MB di ponsel ini. Berjalan di {device}, tanpa koneksi.",
    assistOffline: "Mengunduh perlu koneksi.", assistFailed: "Gagal mengunduh: {msg}", assistNotStored: "Browser tidak bisa menyimpan model di ponsel ini ({files}), jadi model tidak akan berjalan offline.",
    assistGpuFailed: "Chip grafis ponsel ini tidak bisa menjalankan model. Ketuk unduh lagi untuk versi prosesor utama (sekitar 520 MB).",
    assistMissing: "File asisten sudah tidak ada di ponsel ini (mungkin dihapus oleh browser). Unduh lagi untuk memakainya offline.",
    assistNoSpace: "Ruang kosong tidak cukup: perlu sekitar {need} MB, tersedia {free} MB.",
    assistNoWorker: "Browser ini tidak bisa menjalankan asisten.", assistRemove: "Hapus dari ponsel ini",
    assistRemoveConfirm: "Hapus asisten offline ({mb} MB) dari ponsel ini?",
    deviceGpu: "chip grafis (WebGPU)", deviceCpu: "prosesor utama (WebAssembly)",
  },
  zh: {
    banner: "演示：所有商户和电话号码都是虚构的；村名是真实的。",
    noPack: "还没有下载任何信息。", download: "下载信息", update: "更新",
    packLine: "{region}：{n} 家商户", packWhen: "下载于 {when}{kb}", kbOnPhone: " · 占用本机 {kb} KB",
    offlineFail: "下载失败：没有网络。手机里已有的信息仍然可以用。",
    tabSearch: "搜索（可离线）", tabSms: "短信查询", placeholder: "例如：便宜 住宿 Tomok",
    all: "全部", food: "吃饭", lodging: "住宿", transport: "交通", guide: "向导", other: "其他",
    openNow: "现在营业", cheapest: "价格从低到高",
    results: "{n} 条结果", result1: "1 条结果", near: "{place} 附近", onPhone: "在本机搜索",
    today: "店主今天确认过", daysAgo: "店主 {n} 天前确认过", dayAgo: "店主 1 天前确认过",
    stale: "信息可能过时", openToday: "今天营业", closedToday: "今天不营业", capacity: "可容纳 {n}",
    call: "打电话", sms: "发短信", invented: "（虚构）", noPhone: "店主没有同意公开电话号码。",
    nothing: "没有结果。试试村名，或“吃”“住宿”“船”“向导”。",
    hostWords: "店主原话", online: "在线", offline: "离线",
    smsIntro: "有手机信号但没有流量时，游客可以发短信到服务号码，收到前 3 条结果。演示里这个页面代替手机短信，所以需要联网。",
    smsPlaceholder: "搜索 吃 Garoga", send: "发送", smsOffline: "（演示的短信模拟需要联网。）",
    smsElsewhere: "短信模拟需要保存对话，所以放在我们自己的服务器上，不在这个网站。", open: "打开",
    // Ask tab
    tabAsk: "提问", askIntro: "用自己的话提问，可以用英文、印尼文或中文。",
    askPlaceholder: "例如：Tomok 附近有便宜的住处吗？", askSend: "提问", askLocal: "在本机回答",
    askBusyServer: "正在问服务器…", askBusyLoad: "正在从本机存储加载助手…",
    askBusyModel: "本机的模型正在读问题…",
    whoServerModel: "由服务器上的模型回答（{model}）",
    whoServerSim: "由服务器上的模型回答（本演示为模拟：输出是事先写好的）",
    whoServerRules: "由服务器上的搜索规则回答",
    whoPhoneModel: "由本机上的小模型回答（不需要网络）",
    whoPhoneRulesOffline: "离线：助手还没有下载，所以这里是普通搜索结果",
    whoPhoneRules: "本机还没有下载助手，所以这里是普通搜索结果",
    whoPhoneRulesFailed: "本机的助手没能运行（{reason}），所以这里是普通搜索结果",
    fallbackServer: "服务器没有回答（{reason}），所以由本机回答。",
    reason404: "这个服务器没有问答服务", reasonNet: "没有网络",
    reasonTimeout: "{s} 秒内没有回复", reasonStatus: "错误 {status}", reasonBad: "回复无法读取",
    noteChecksFailed: "模型的回答没有通过检查，所以答案是按规则从商户信息生成的。",
    noteNoModel: "模型没有给出回答，所以答案是按规则从商户信息生成的。",
    noteNothing: "商户信息里没有和问题相符的。",
    detailsServer: "服务器是怎么回答的", checkFailed: "未通过的检查：{check}（{detail}）",
    rejectedAnswer: "被拒绝的模型回答", modelOutput: "模型的原始输出", serverSaid: "服务器说明",
    filtersTitle: "模型选择的筛选条件：", fCategory: "类别：{c}", fCheap: "便宜", fNow: "现在营业",
    fKeywords: "关键词：{w}", fNone: "无", fIgnored: "不允许的值，已忽略：{what}",
    fUnreadable: "模型的回复不是有效的 JSON，所以没有使用筛选条件",
    placeByRules: "地点（由搜索规则找到，不是模型）：{place}",
    placeNone: "没有提到村名（搜索规则会查找村名）。",
    modelTime: "模型在{device}上用时 {s} 秒。", loadTime: "从本机存储加载用时 {s} 秒。",
    ansNone: "本机的信息里没有符合的商户{near}。", ansOne: "有 1 家符合{near}：{list}。",
    ansFew: "有 {n} 家符合{near}：{list}。", ansMany: "有 {n} 家符合{near}，前 3 家：{list}。",
    ansNear: "（{place} 附近）", showAll: "显示全部 {n} 条", askNoPack: "请先下载商户信息（上方的按钮）。",
    assistTitle: "离线助手", assistDownload: "下载离线助手（约 {mb} MB）",
    assistAbout: "一个小型语言模型（Qwen2.5-0.5B-Instruct，Apache-2.0 许可），从 Hugging Face 下载，在这个浏览器里运行。在本机回答的问题不会离开手机。模型只负责把问题变成搜索条件，答案由商户信息生成。",
    assistNotYet: "还没有下载。没有助手时，离线提问只会得到普通搜索结果。",
    assistStarting: "开始下载…", assistDownloading: "正在从 Hugging Face 下载：{done} / {total} MB",
    assistPreparing: "已下载，正在准备模型…", assistLoading: "正在从本机存储加载助手：{pct}%",
    assistReady: "已下载：本机占用 {mb} MB。在{device}上运行，不需要网络。",
    assistOffline: "下载需要联网。", assistFailed: "下载失败：{msg}", assistNotStored: "浏览器没能把模型保存在本机（{files}），所以离线时无法使用。",
    assistGpuFailed: "这台手机的图形芯片无法运行模型。再点一次下载，改用主处理器版本（约 520 MB）。",
    assistMissing: "助手的文件已经不在本机（可能被浏览器清除了）。要离线使用，请重新下载。",
    assistNoSpace: "空间不够：大约需要 {need} MB，现在只有 {free} MB。",
    assistNoWorker: "这个浏览器无法运行助手。", assistRemove: "从本机删除",
    assistRemoveConfirm: "从本机删除离线助手（{mb} MB）？",
    deviceGpu: "图形芯片（WebGPU）", deviceCpu: "主处理器（WebAssembly）",
  },
};
const t = (key, vars = {}) => (STR[ui][key] ?? STR.en[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");

function applyText() {
  document.documentElement.lang = ui;
  document.querySelectorAll("[data-t]").forEach(el => { el.textContent = t(el.dataset.t); });
  $("q").placeholder = t("placeholder"); $("smsText").placeholder = t("smsPlaceholder");
  $("askText").placeholder = t("askPlaceholder");
  $("uiLang").value = ui; setNet(); showPack(); renderCats(); render(); smsAvailability(); renderAsk(); renderAssist();
}

// On hosts that keep no state (e.g. Vercel) the SMS simulator is not available here; point to our own server.
function smsAvailability() {
  const off = config && config.simulator === false;
  ["thread", "smsExamples"].forEach(id => { $(id).hidden = off; });
  document.querySelector("#paneSms .compose").hidden = off;
  $("smsElsewhere").hidden = !off;
  if (off) {
    const live = config.live_server_url;
    $("smsElsewhere").innerHTML = esc(t("smsElsewhere")) + (live ? ` <a href="${esc(live)}/app/">${esc(t("open"))}</a>` : "");
  }
}

// ---- text helpers (same rules as the server) ------------------------------------
const CJK = /[぀-ヿ㐀-䶿一-鿿가-힯]/;
const norm = s => (s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()
  .replace(/[^\p{L}\p{N}?？]+/gu, " ")
  .replace(/([぀-ヿ㐀-䶿一-鿿가-힯])(?=[^\s぀-ヿ㐀-䶿一-鿿가-힯])/g, "$1 ")
  .replace(/([^\s぀-ヿ㐀-䶿一-鿿가-힯])(?=[぀-ヿ㐀-䶿一-鿿가-힯])/g, "$1 ")
  .replace(/\s+/g, " ").trim();
function termPos(textNorm, word) {
  const w = norm(word); if (!w) return -1;
  if (CJK.test(w)) return textNorm.replace(/ /g, "").indexOf(w.replace(/ /g, ""));
  return (" " + textNorm + " ").indexOf(" " + w + " ");
}
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function km(a, b) {
  const r = Math.PI / 180, dLat = (b[0] - a[0]) * r, dLon = (b[1] - a[1]) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLon / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

function langs() { return Object.keys(pack.region.words); }
function wordsFor(key) { return langs().flatMap(l => pack.region.words[l][key] || []); }

function categoryOf(q) {
  const tn = norm(q); let best = null;
  for (const l of langs()) for (const [cat, ws] of Object.entries(pack.region.words[l].category || {}))
    for (const w of ws) { const pos = termPos(tn, w); if (pos >= 0 && (!best || pos < best.pos)) best = { pos, cat }; }
  return best ? best.cat : null;
}
function hasWord(q, key) { const tn = norm(q); return wordsFor(key).some(w => termPos(tn, w) >= 0); }

let aliasIndex = null;
function matchPlace(q) {
  if (!aliasIndex) {
    aliasIndex = new Map();
    const rank = { town: 0, village: 0, suburb: 1, hamlet: 2 };
    for (const v of pack.villages) for (const a of new Set([norm(v.name), norm(v.name).replace(/ /g, "")]))
      if (a.length >= 3) { const cur = aliasIndex.get(a); if (!cur || (rank[v.place] ?? 9) < (rank[cur.place] ?? 9)) aliasIndex.set(a, v); }
  }
  const tok = norm(q).split(" ").filter(Boolean);
  for (let n = 4; n >= 1; n--) for (let i = 0; i + n <= tok.length; i++) {
    const g = tok.slice(i, i + n).join(" ");
    for (const k of [g, g.replace(/ /g, "")]) if (aliasIndex.has(k)) return aliasIndex.get(k);
  }
  // Close spelling, as on the server (difflib.get_close_matches, cutoff 0.85): "garoga?" or "Tomuk" still count.
  for (const n of [2, 1]) for (let i = 0; i + n <= tok.length; i++) {
    const c = tok.slice(i, i + n).join(" ");
    if ([...c].length < 5 || CJK.test(c)) continue;
    let best = null;
    for (const k of aliasIndex.keys()) {
      const r = similarity(k, c);
      if (r >= 0.85 && (!best || r > best.r || (r === best.r && k > best.k))) best = { r, k };
    }
    if (best) return aliasIndex.get(best.k);
  }
  return null;
}
// difflib.SequenceMatcher(None, a, b).ratio(): 2 * matching characters / total length, where matching blocks are
// found by repeatedly taking the longest common substring (no junk heuristics: they only apply to 200+ characters).
function similarity(a, b) {
  a = [...a]; b = [...b];
  const b2j = new Map();
  b.forEach((ch, j) => { if (!b2j.has(ch)) b2j.set(ch, []); b2j.get(ch).push(j); });
  let matches = 0;
  const queue = [[0, a.length, 0, b.length]];
  while (queue.length) {
    const [alo, ahi, blo, bhi] = queue.pop();
    let bi = alo, bj = blo, bk = 0, j2len = new Map();
    for (let i = alo; i < ahi; i++) {
      const next = new Map();
      for (const j of b2j.get(a[i]) || []) {
        if (j < blo) continue;
        if (j >= bhi) break;
        const k = (j2len.get(j - 1) || 0) + 1;
        next.set(j, k);
        if (k > bk) { bi = i - k + 1; bj = j - k + 1; bk = k; }
      }
      j2len = next;
    }
    if (!bk) continue;
    matches += bk;
    if (alo < bi && blo < bj) queue.push([alo, bi, blo, bj]);
    if (bi + bk < ahi && bj + bk < bhi) queue.push([bi + bk, ahi, bj + bk, bhi]);
  }
  return a.length + b.length ? 2 * matches / (a.length + b.length) : 1;
}

function relevance(q, l) {
  const hay = norm([l.name, l.offer_original, l.offer_en, l.landmark].join(" "));
  return [...new Set(norm(q).split(" "))].filter(w => w.length >= 3 && termPos(hay, w) >= 0).length;
}

function localNow() {
  const tz = pack?.region?.timezone || config?.timezone || "UTC";
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date());
  const p = Object.fromEntries(parts.map(x => [x.type, x.value]));
  return { date: `${p.year}-${p.month}-${p.day}`, hhmm: `${p.hour}:${p.minute}` };
}
function openNow(l) {
  const now = localNow();
  if (l.open_today_date === now.date && l.open_today === false) return false;
  if (!l.hours) return l.open_today_date === now.date ? l.open_today : null;
  return l.hours.open <= now.hhmm && now.hhmm < l.hours.close;
}

// The Search tab: filters from the question's words plus the tab's own buttons.
function find(q) {
  return search(q, { cat: catFilter || categoryOf(q), place: matchPlace(q),
    cheap: $("cheap").checked || hasWord(q, "cheap"), nowOnly: $("openNow").checked || hasWord(q, "now") });
}
// The rule search itself, also used by the Ask tab's answers on this phone (with the model's filters).
// `words` are extra words for ranking by relevance (the model's keywords); the Search tab passes none.
function search(q, { cat = null, place = null, cheap = false, nowOnly = false, words = [] } = {}) {
  const rq = [q, ...words].join(" ");
  let items = pack.listings.slice();
  if (cat) items = items.filter(l => l.category === cat);
  // ties are broken by freshness: the most recently confirmed listing comes first (sorts below are stable)
  items.sort((a, b) => (b.last_confirmed_at || "").localeCompare(a.last_confirmed_at || ""));
  if (nowOnly) items = items.filter(l => openNow(l) !== false);
  if (place) {
    const here = [place.lat, place.lon];
    const dist = l => l.location ? km(here, [l.location.lat, l.location.lon]) : 9e9;
    items = items.filter(l => dist(l) <= 15);
    items.sort((a, b) => ((a.village === place.name ? 0 : 1) - (b.village === place.name ? 0 : 1))
      || (relevance(rq, b) - relevance(rq, a)) || (dist(a) - dist(b)));
  } else if (rq.trim()) {
    items.sort((a, b) => relevance(rq, b) - relevance(rq, a));
    if (!cat && items.some(l => relevance(rq, l) > 0)) items = items.filter(l => relevance(rq, l) > 0);
  }
  if (cheap) items.sort((a, b) => (a.price?.min ?? 9e18) - (b.price?.min ?? 9e18));
  return { items, cat, place };
}

// ---- formatting -------------------------------------------------------------------
// Listings shown before any pack is downloaded (server answers) still need a currency: fall back to its code.
function money(n, code) {
  const c = pack?.region?.currency;
  if (!c) return `${Math.round(n).toLocaleString("en-US")} ${code || ""}`.trim();
  return c.display.replace("{amount}", Math.round(n).toLocaleString("en-US").replace(/,/g, c.thousands_separator || ","));
}
function price(p) {
  if (!p) return "";
  const units = pack?.region?.unit_labels || {};
  const labels = units[ui] || units.en || {};
  return money(p.min, p.currency) + (p.max ? "–" + money(p.max, p.currency).replace(/^[^\d]*/, "") : "") + (labels[p.unit || "other"] || "");
}
function ago(iso) {
  if (!iso) return { text: t("stale"), stale: true };
  const days = Math.floor((Date.now() - Date.parse(iso)) / 86400000);
  return { text: days <= 0 ? t("today") : days === 1 ? t("dayAgo") : t("daysAgo", { n: days }), stale: days > 14 };
}
// Show the host's own words if the reader shares their language, otherwise the English translation.
function offer(l) {
  if (ui === l.language || !l.offer_en) return { main: l.offer_original, orig: null };
  return { main: l.offer_en, orig: l.offer_original };
}

function card(l) {
  const f = ago(l.last_confirmed_at), now = localNow(), o = offer(l);
  const today = l.open_today_date === now.date && l.open_today !== null
    ? `<span class="tag ${l.open_today ? "open" : "closed"}">${l.open_today ? t("openToday") : t("closedToday")}</span>` : "";
  const phone = l.phone ? `<div class="actions"><a href="tel:${esc(l.phone)}">${t("call")}</a><a href="sms:${esc(l.phone)}">${t("sms")}</a>
    <span class="small muted">${esc(l.phone)} ${t("invented")}</span></div>` : `<div class="small muted" style="margin-top:6px">${t("noPhone")}</div>`;
  return `<article class="result">
    <h3>${esc(l.name)} <span class="tag">${t(l.category)}</span></h3>
    <div class="where">${esc(l.village)}${l.landmark ? " · " + esc(l.landmark) : ""}</div>
    <div class="offer">${esc(o.main)}</div>
    ${o.orig ? `<div class="orig">${t("hostWords")}: “${esc(o.orig)}”</div>` : ""}
    <div class="facts">${price(l.price) ? `<span>${esc(price(l.price))}</span>` : ""}
      ${l.hours ? `<span>${esc(l.hours.open)}–${esc(l.hours.close)}</span>` : ""}
      ${l.capacity ? `<span>${t("capacity", { n: l.capacity })}</span>` : ""}
      <span class="tag ${f.stale ? "stale" : ""}">${f.text}${f.stale && l.last_confirmed_at ? " · " + t("stale") : ""}</span>${today}</div>
    ${phone}</article>`;
}

function render() {
  if (!pack) { $("results").innerHTML = ""; $("count").textContent = ""; return; }
  const q = $("q").value;
  const { items, cat, place } = find(q);
  $("count").textContent = (items.length === 1 ? t("result1") : t("results", { n: items.length })) +
    (cat ? ` · ${t(cat)}` : "") + (place ? ` · ${t("near", { place: place.name })}` : "") + ` · ${t("onPhone")}`;
  $("results").innerHTML = items.map(card).join("") || `<p class="muted">${t("nothing")}</p>`;
}

// ---- pack download -----------------------------------------------------------------
function showPack() {
  if (!pack) { $("packInfo").textContent = t("noPack"); $("update").textContent = t("download"); return; }
  const kb = Math.round((store.get("pack:" + pack.region.id) || "").length / 1024);
  const when = new Date(pack.generated_at).toLocaleString(ui === "zh" ? "zh-CN" : ui === "id" ? "id-ID" : "en-GB");
  $("packInfo").innerHTML = `<strong>${esc(t("packLine", { n: pack.listings.length, region: pack.region.display_name }))}</strong>` +
    `<br><span class="muted">${esc(t("packWhen", { when, kb: kb ? t("kbOnPhone", { kb }) : "" }))}</span>`;
  $("regionName").textContent = pack.region.display_name;
  $("update").textContent = t("update");
}
async function downloadPack() {
  $("update").disabled = true;
  try {
    const id = (config && config.region_id) || (pack && pack.region.id);
    const data = await (await fetch(`/api/regions/${id}/pack.json`, { cache: "no-store" })).json();
    pack = data; aliasIndex = null;
    store.set("pack:" + data.region.id, JSON.stringify(data)); store.set("packRegion", data.region.id);
    showPack(); renderCats(); render();
  } catch (e) {
    $("packInfo").textContent = t("offlineFail");
  } finally { $("update").disabled = false; }
}

function renderCats() {
  $("cats").innerHTML = "";
  [null, "food", "lodging", "transport", "guide"].forEach(c => {
    const b = document.createElement("button");
    b.className = "chip" + (catFilter === c ? " on" : ""); b.textContent = c ? t(c) : t("all");
    b.onclick = () => { catFilter = c; renderCats(); render(); };
    $("cats").appendChild(b);
  });
}

// ---- Ask tab -------------------------------------------------------------------------
// Three ways to answer:
// 1. Online: the server answers (POST /api/chat) with its own model or rules, and says which.
// 2. On this phone with the assistant downloaded: the small model only turns the question into search filters
//    (JSON); the village comes from matchPlace() (rules), the search is search() (rules), and the answer text is
//    built from the listing rows by a fixed template, so it cannot name a place that is not in the listings.
// 3. On this phone without the assistant: plain rule search on the question.
// (2) or (3) are used offline, when "Answer on this phone" is on, or when the server does not answer.
const CHAT_TIMEOUT_S = 25;
const CATEGORIES = ["food", "lodging", "transport", "guide"];
// A 0.5B model needs the cue words spelled out; the examples differ in "cheap" and "open_now" on purpose
// (with two "cheap" examples it answered cheap: true for almost everything).
const FILTER_PROMPT = [
  "Turn the traveller's question into search filters. Reply with one line of JSON only, for example:",
  '{"category": "food", "cheap": false, "open_now": false, "keywords": []}',
  "category is one of:",
  '- "food": eating, drinking, hungry, meal, breakfast, restaurant (makan, lapar, sarapan, warung; 吃, 饭, 饿, 早餐)',
  '- "lodging": a room or a bed for the night, sleep, stay, homestay, hotel (kamar, inap, penginapan, tidur; 住, 房间, 民宿, 酒店)',
  '- "transport": boat, ferry, motorbike, ride, taxi (kapal, ojek, motor, sewa; 船, 车, 摩托)',
  '- "guide": guide, tour, hike (pemandu, tur; 导游, 向导)',
  "- null if none of these.",
  '"cheap": true only if the question says cheap, cheaply, budget, murah or 便宜; otherwise false.',
  '"open_now": true only if the question says now, tonight, today, sekarang, malam ini, 现在, 今晚 or 今天; otherwise false.',
  '"keywords": up to 3 English words for a specific dish, drink or destination in the question, such as "fish" or "coffee"; [] if none.',
].join("\n");
const FILTER_EXAMPLES = [
  ["I'm hungry, anything cheap near Garoga?", '{"category": "food", "cheap": true, "open_now": false, "keywords": []}'],
  ["kamar dengan sarapan di Tomok", '{"category": "lodging", "cheap": false, "open_now": false, "keywords": ["breakfast"]}'],
  ["今晚有船去吗", '{"category": "transport", "cheap": false, "open_now": true, "keywords": []}'],
];
let lastAsk = null, asking = false;

function filterMessages(q) {
  return [{ role: "system", content: FILTER_PROMPT },
    ...FILTER_EXAMPLES.flatMap(([u, a]) => [{ role: "user", content: u }, { role: "assistant", content: a }]),
    { role: "user", content: q }];
}

// Strict reading of the model's reply: it must parse as a JSON object (a code fence around it is tolerated);
// each value that is not allowed is ignored, i.e. that filter is not used.
function readFilters(text) {
  const f = { ok: false, category: null, cheap: false, open_now: false, keywords: [], ignored: [] };
  const raw = String(text || "").trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  let data;
  try { data = JSON.parse(raw); } catch (e) { return f; }
  if (!data || typeof data !== "object" || Array.isArray(data)) return f;
  f.ok = true;
  const bad = (k, v) => f.ignored.push(`${k} = ${JSON.stringify(v)}`);
  for (const [k, v] of Object.entries(data)) {
    if (k === "category") { if (v === null || CATEGORIES.includes(v)) f.category = v; else bad(k, v); }
    else if (k === "cheap" || k === "open_now") { if (typeof v === "boolean") f[k] = v; else bad(k, v); }
    else if (k === "keywords") {
      const ok = Array.isArray(v) && v.length <= 3 && v.every(w => typeof w === "string" && w.trim() && w.length <= 30);
      if (ok) f.keywords = v.map(w => w.trim()); else bad(k, v);
    } else bad(k, v);
  }
  return f;
}

// Rule search on this phone with the given filters. As on the server, a question with nothing to search for
// (no category, cheap/now, village or word found in a listing) gets no results rather than every listing.
function phoneSearch(q, f) {
  const place = matchPlace(q), words = f.keywords || [];
  const { items } = search(q, { cat: f.category, place, cheap: f.cheap, nowOnly: f.open_now, words });
  const rq = [q, ...words].join(" ");
  const target = f.category || f.cheap || f.open_now || place || items.some(l => relevance(rq, l) > 0);
  return { items: target ? items : [], place };
}
function ruleFilters(q) {
  return { ok: true, category: categoryOf(q), cheap: hasWord(q, "cheap"), open_now: hasWord(q, "now"), keywords: [], ignored: [] };
}

// The answer text from the listing rows, in the interface language.
function answerText(items, place) {
  const zh = ui === "zh";
  const list = items.slice(0, 3).map(l => {
    const bits = [l.village, price(l.price), l.hours ? `${l.hours.open}–${l.hours.close}` : ""].filter(Boolean);
    return zh ? `${l.name}（${bits.join("，")}）` : `${l.name} (${bits.join(", ")})`;
  }).join(zh ? "；" : "; ");
  const n = items.length, near = place ? t("ansNear", { place: place.name }) : "";
  return t(n === 0 ? "ansNone" : n === 1 ? "ansOne" : n <= 3 ? "ansFew" : "ansMany", { n, near, list });
}

async function askServer(question) {
  const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), CHAT_TIMEOUT_S * 1000);
  try {
    let res;
    try {
      res = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, lang: ui }), signal: ctl.signal, cache: "no-store" });
    } catch (e) {
      throw { why: e.name === "AbortError" ? { key: "reasonTimeout", vars: { s: CHAT_TIMEOUT_S } } : { key: "reasonNet" } };
    }
    if (res.status === 404) throw { why: { key: "reason404" } };
    if (!res.ok) throw { why: { key: "reasonStatus", vars: { status: res.status } } };
    let data;
    try { data = await res.json(); } catch (e) {
      throw { why: e.name === "AbortError" ? { key: "reasonTimeout", vars: { s: CHAT_TIMEOUT_S } } : { key: "reasonBad" } };
    }
    if (!data || typeof data.answer !== "string") throw { why: { key: "reasonBad" } };
    return data;
  } finally { clearTimeout(timer); }
}

async function askPhone(q, why) {
  if (!pack) return { kind: "nopack", q, why };
  const rules = extra => ({ kind: "phoneRules", q, why, offline: !navigator.onLine, ...phoneSearch(q, ruleFilters(q)), ...extra });
  const saved = assistantSaved();
  if (!saved) return rules();
  try {
    let loadMs = 0;
    if (assistant.state !== "ready") {
      setAskBusy(t("askBusyLoad"));
      const t0 = performance.now();
      await assistantStart(saved);
      loadMs = Math.round(performance.now() - t0);
    }
    setAskBusy(t("askBusyModel"));
    const out = await assistantRun(filterMessages(q));
    const filters = readFilters(out.text);
    return { kind: "phoneModel", q, why, filters, raw: out.text, genMs: out.ms, tokens: out.tokens, loadMs,
             device: assistant.device, dtype: assistant.dtype, ...phoneSearch(q, filters) };
  } catch (e) {
    return rules({ failed: String(e?.message || e) });
  }
}

async function ask(text) {
  const q = String(text ?? $("askText").value).trim();
  if (!q || asking) return;
  asking = true; $("askSend").disabled = true;
  const t0 = performance.now();
  let result = null;
  try {
    let why = null;
    if (!$("askLocal").checked && navigator.onLine) {
      setAskBusy(t("askBusyServer"));
      try { result = { kind: "server", q, res: await askServer(q) }; }
      catch (e) { why = e?.why || { key: "reasonNet" }; }
    }
    if (!result) result = await askPhone(q, why);
  } catch (e) {
    result = { kind: "phoneRules", q, failed: String(e?.message || e), items: [], place: null };
  } finally {
    if (result) result.ms = Math.round(performance.now() - t0);
    lastAsk = result; asking = false; $("askSend").disabled = false; renderAsk();
  }
}

function setAskBusy(text) { lastAsk = { busy: text }; renderAsk(); }

function serverNote(r) {
  if ((r.checks_failed || []).length) return t("noteChecksFailed");
  if (r.method === "rules" && r.model && !r.model_output) return t("noteNoModel");
  if (r.method === "rules" && !(r.listing_ids || []).length) return t("noteNothing");
  return r.note || "";
}
function serverDetails(r) {
  let body = (r.checks_failed || []).map(c => `<div class="warn">${esc(t("checkFailed", { check: c.check, detail: c.detail }))}</div>`).join("");
  if (r.model_output) body += `<div>${esc(t((r.checks_failed || []).length ? "rejectedAnswer" : "modelOutput"))}:</div>` +
    `<pre>${esc(JSON.stringify(r.model_output, null, 2))}</pre>`;
  if (r.note && r.note !== serverNote(r)) body += `<div class="muted">${esc(t("serverSaid"))}: ${esc(r.note)}</div>`;
  return body ? `<details class="small"><summary>${esc(t("detailsServer"))}</summary>${body}</details>` : "";
}
function filtersBlock(a) {
  const f = a.filters, parts = [];
  if (!f.ok) parts.push(t("fUnreadable"));
  else {
    if (f.category) parts.push(t("fCategory", { c: t(f.category) }));
    if (f.cheap) parts.push(t("fCheap"));
    if (f.open_now) parts.push(t("fNow"));
    if (f.keywords.length) parts.push(t("fKeywords", { w: f.keywords.join(", ") }));
    if (!parts.length) parts.push(t("fNone"));
  }
  const s = n => (n / 1000).toFixed(1);
  const device = t(a.device === "webgpu" ? "deviceGpu" : "deviceCpu");
  return `<div class="filters small">
      <div>${esc(t("filtersTitle"))} ${parts.map(p => `<span class="tag">${esc(p)}</span>`).join(" ")}</div>
      ${f.ignored.length ? `<div class="warn">${esc(t("fIgnored", { what: f.ignored.join("; ") }))}</div>` : ""}
      <div>${esc(a.place ? t("placeByRules", { place: a.place.name }) : t("placeNone"))}</div>
      <div class="muted">${esc(t("modelTime", { s: s(a.genMs), device }))}${a.loadMs ? " " + esc(t("loadTime", { s: s(a.loadMs) })) : ""}</div>
    </div>
    <details class="small"><summary>${esc(t("modelOutput"))}</summary><pre>${esc(a.raw)}</pre></details>`;
}

function renderAsk() {
  const out = $("askOut"), a = lastAsk;
  if (!a) { out.innerHTML = ""; return; }
  if (a.busy) { out.innerHTML = `<p class="small muted">${esc(a.busy)}</p>`; return; }
  if (a.kind === "nopack") { out.innerHTML = `<p class="small">${esc(t("askNoPack"))}</p>`; return; }
  let who, cls, text, notes = [], extra = "", listings;
  if (a.kind === "server") {
    const r = a.res;
    who = r.method === "model" ? t("whoServerModel", { model: r.model || "" })
      : r.method === "simulated" ? t("whoServerSim") : t("whoServerRules");
    cls = r.method === "rules" ? "rules" : "model";
    text = r.answer; listings = r.listings || [];
    const note = serverNote(r); if (note) notes.push(note);
    extra = serverDetails(r);
  } else {
    listings = a.items; text = answerText(a.items, a.place);
    if (a.why) notes.push(t("fallbackServer", { reason: t(a.why.key, a.why.vars) }));
    if (a.kind === "phoneModel") { who = t("whoPhoneModel"); cls = "model"; extra = filtersBlock(a); }
    else {
      cls = "rules";
      who = a.failed ? t("whoPhoneRulesFailed", { reason: a.failed }) : a.offline ? t("whoPhoneRulesOffline") : t("whoPhoneRules");
      if (!a.failed && !assistantSaved()) extra = `<button class="primary assist-download" data-act="download">${esc(t("assistDownload", { mb: assistant.plan.mb }))}</button>`;
    }
  }
  const cards = listings.map(card);
  out.innerHTML = `<div class="answer">
      <div class="who ${cls}">${esc(who)}</div>
      <p class="answer-text">${esc(text)}</p>
      ${notes.map(n => `<p class="small note">${esc(n)}</p>`).join("")}
      ${extra}
    </div>
    ${cards.slice(0, 3).join("")}
    ${cards.length > 3 ? `<div id="askMore" hidden>${cards.slice(3).join("")}</div>
      <button class="chip" data-act="more">${esc(t("showAll", { n: cards.length }))}</button>` : ""}`;
}

// ---- offline assistant (small model in assistant-worker.js) ----------------------------------
const MODEL_ID = "onnx-community/Qwen2.5-0.5B-Instruct";
// Which weights each device gets, the ONNX file and the download size in MB (the ONNX file + 7 MB tokenizer).
// Not "q4f16" (16-bit maths) on WebGPU: in testing it gave garbage answers; "q4" (32-bit maths) works.
const PLANS = { webgpu: { device: "webgpu", dtype: "q4", file: "onnx/model_q4.onnx", mb: 790 },
                wasm: { device: "wasm", dtype: "q8", file: "onnx/model_quantized.onnx", mb: 520 } };
const MODEL_CACHE = "transformers-cache";  // Cache Storage name used for the model files (see assistant-worker.js)
const CDN_CACHE = "offgrid-cdn-v1";        // same name as in sw.js
const assistant = { state: "absent", worker: null, ready: null, device: null, dtype: null, chosen: null, plan: PLANS.wasm,
                    progress: null, note: null, missing: false, pending: new Map(), seq: 0 };

function assistantSaved() { try { return JSON.parse(store.get("assistant") || "null"); } catch (e) { return null; } }
// The graphics chip when the browser offers WebGPU, else the main processor (or after the GPU failed once).
async function assistantPlan() {
  if (store.get("assistantForceWasm") !== "1") {
    try { if (navigator.gpu && await navigator.gpu.requestAdapter()) return PLANS.webgpu; } catch (e) { /* no GPU */ }
  }
  return PLANS.wasm;
}
// Stored for offline use = the file's entry and every one of its parts are in the cache (see assistant-worker.js).
async function modelStored(dtype) {
  const plan = Object.values(PLANS).find(p => p.dtype === dtype);
  if (!plan) return false;
  const c = await caches.open(MODEL_CACHE), key = `https://huggingface.co/${MODEL_ID}/resolve/main/${plan.file}`;
  const hit = await c.match(key);
  if (!hit) return false;
  const parts = Number(hit.headers.get("x-offgrid-parts") || 0);
  for (let i = 0; i < parts; i++) if (!(await c.match(`${key}?offgrid-part=${i}`))) return false;
  return true;
}

// Start the worker and load the model: from Hugging Face the first time, from this browser's cache afterwards.
// opts: {device, dtype} of an earlier download (so the same files are used), or {} to choose for this browser.
function assistantStart(opts = {}) {
  if (assistant.ready) return assistant.ready;
  if (assistant.state !== "downloading") assistant.state = "loading";
  assistant.progress = null; renderAssist();
  assistant.ready = new Promise((resolve, reject) => {
    let w;
    try { w = new Worker("assistant-worker.js", { type: "module" }); }
    catch (e) { reject(new Error(t("assistNoWorker"))); return; }
    assistant.worker = w;
    const fail = err => {
      reject(err);
      for (const p of assistant.pending.values()) p.reject(err);
      assistant.pending.clear(); w.terminate();
      if (assistant.worker === w) { assistant.worker = null; assistant.ready = null; assistant.state = assistantSaved() ? "saved" : "absent"; renderAssist(); }
    };
    w.onmessage = e => {
      const m = e.data || {};
      if (m.type === "chosen") assistant.chosen = m;
      else if (m.type === "progress") { assistant.progress = m; renderAssist(); }
      else if (m.type === "loaded") {
        Object.assign(assistant, { state: "ready", device: m.device, dtype: m.dtype });
        renderAssist(); resolve(m);
      } else if (m.type === "generated" || (m.type === "error" && m.id)) {
        const p = assistant.pending.get(m.id); assistant.pending.delete(m.id);
        if (p) { if (m.type === "generated") p.resolve(m); else p.reject(new Error(m.message)); }
      } else if (m.type === "error") fail(new Error(m.message));
    };
    w.onerror = e => { e.preventDefault(); fail(new Error(e.message || "the assistant stopped")); };
    w.postMessage({ type: "load", ...opts });
  });
  return assistant.ready;
}

function assistantRun(messages) {
  return new Promise((resolve, reject) => {
    if (!assistant.worker) { reject(new Error("the model is not loaded")); return; }
    const id = ++assistant.seq;
    assistant.pending.set(id, { resolve, reject });
    assistant.worker.postMessage({ type: "generate", id, messages, max_new_tokens: 64 });
  });
}

async function assistantDownload() {
  if (assistant.state === "downloading" || assistant.state === "loading" || assistantSaved()) return;
  assistant.note = null;
  if (!navigator.onLine) { assistant.note = { key: "assistOffline" }; renderAssist(); return; }
  const plan = assistant.plan = await assistantPlan(), need = plan.mb + 100;
  try {
    const est = await navigator.storage?.estimate?.();
    const free = est && est.quota ? Math.floor((est.quota - est.usage) / 1e6) : Infinity;
    if (free < need) { assistant.note = { key: "assistNoSpace", vars: { need, free } }; renderAssist(); return; }
  } catch (e) { /* no estimate: try anyway */ }
  try { await navigator.storage?.persist?.(); } catch (e) { /* asking the browser not to evict it is optional */ }
  const forceWasm = plan.device === "wasm";
  assistant.state = "downloading"; assistant.chosen = null;
  const t0 = performance.now();
  try {
    const m = await assistantStart({ device: plan.device, dtype: plan.dtype });
    if (m.missing && m.missing.length) {  // loaded, but the browser did not keep every file: not usable offline
      assistant.note = { key: "assistNotStored", vars: { files: m.missing.join(", ") } };
      assistantStop(); renderAssist(); return;
    }
    const p = assistant.progress;
    store.set("assistant", JSON.stringify({ model: m.model, device: m.device, dtype: m.dtype, bytes: p?.total || null,
      seconds: Math.round((performance.now() - t0) / 100) / 10, at: new Date().toISOString() }));
    store.del("assistantForceWasm"); assistant.missing = false;
    keepRuntime(m.runtime);
  } catch (e) {
    const p = assistant.progress, downloaded = p && p.total && p.loaded >= p.total;
    if (!forceWasm && assistant.chosen?.device === "webgpu" && downloaded) {
      store.set("assistantForceWasm", "1"); assistant.note = { key: "assistGpuFailed" };
    } else assistant.note = { key: "assistFailed", vars: { msg: String(e?.message || e) } };
  }
  renderAssist(); renderAsk();
}

// sw.js stores the library and runtime files as the worker fetches them; this also covers a download made
// before sw.js controlled the page.
async function keepRuntime(urls) {
  try {
    const c = await caches.open(CDN_CACHE);
    for (const u of urls || []) if (!(await c.match(u))) await c.add(u);
  } catch (e) { /* sw.js will store them on the next use */ }
}

// A download is remembered in localStorage; check that the browser still has the model file.
async function assistantCheck() {
  const s = assistantSaved();
  if (s && assistant.state === "absent") {
    assistant.state = "saved"; assistant.device = s.device; assistant.dtype = s.dtype;
    try {
      if (!(await modelStored(s.dtype))) { store.del("assistant"); assistant.state = "absent"; assistant.missing = true; }
    } catch (e) { /* cannot check: keep the record */ }
  }
  assistant.plan = await assistantPlan();
  renderAssist(); renderAsk();
}

// Load the model ahead of the first question when answers will come from this phone.
function assistantWarm() {
  const s = assistantSaved();
  if (s && assistant.state === "saved" && ($("askLocal").checked || !navigator.onLine)) assistantStart(s).catch(() => {});
}

function assistantStop() {
  if (assistant.worker) assistant.worker.terminate();
  for (const p of assistant.pending.values()) p.reject(new Error("the assistant was stopped"));
  assistant.pending.clear();
  Object.assign(assistant, { worker: null, ready: null, state: assistantSaved() ? "saved" : "absent", progress: null });
}

async function assistantRemove() {
  const s = assistantSaved();
  if (!confirm(t("assistRemoveConfirm", { mb: s && s.bytes ? Math.round(s.bytes / 1e6) : "?" }))) return;
  store.del("assistant");
  assistantStop();
  Object.assign(assistant, { note: null, missing: false });
  try { await caches.delete(MODEL_CACHE); } catch (e) {}
  store.del("assistantForceWasm");
  renderAssist(); renderAsk();
}

function renderAssist() {
  const s = assistantSaved(), st = assistant.state, p = assistant.progress;
  const mb = b => Math.round(b / 1e6);
  let text;
  if (st === "downloading") {
    text = !p || !p.total ? t("assistStarting")
      : p.loaded >= p.total ? t("assistPreparing") : t("assistDownloading", { done: mb(p.loaded), total: mb(p.total) });
  } else if (st === "loading" && p && p.total) {
    text = t("assistLoading", { pct: Math.floor(100 * p.loaded / p.total) });
  } else if (s) {
    text = t("assistReady", { mb: s.bytes ? mb(s.bytes) : "?", device: t(s.device === "webgpu" ? "deviceGpu" : "deviceCpu") });
  } else text = t(assistant.missing ? "assistMissing" : "assistNotYet");
  if (assistant.note) text = t(assistant.note.key, assistant.note.vars) + " " + text;
  $("assistState").textContent = text;
  const bar = $("assistBar"), busy = (st === "downloading" || st === "loading") && p && p.total;
  bar.hidden = !busy;
  if (busy) bar.value = p.loaded / p.total;
  $("assistDownload").textContent = t("assistDownload", { mb: assistant.plan.mb });
  $("assistDownload").hidden = !!s;
  $("assistDownload").disabled = st === "downloading" || st === "loading";
  $("assistRemove").hidden = !s || st === "downloading" || st === "loading";
}

// ---- SMS tab (simulated in the demo) --------------------------------------------------
function bubble(m) {
  const d = document.createElement("div"); d.className = "msg " + (m.direction === "in" ? "in" : "out");
  d.textContent = m.text; $("thread").appendChild(d); $("thread").scrollTop = $("thread").scrollHeight;
}
async function smsPoll() {
  if ($("paneSms").hidden || !navigator.onLine) return;
  try {
    const msgs = await (await fetch(`/api/messages?phone=${encodeURIComponent(smsPhone)}&after=${smsLast}`)).json();
    msgs.forEach(m => { bubble(m); smsLast = Math.max(smsLast, m.id); });
  } catch (e) {}
}
async function smsSend(text) {
  text = (text ?? $("smsText").value).trim(); if (!text) return;
  try {
    await fetch("/api/simulate", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from: smsPhone, text }) });
    $("smsText").value = ""; setTimeout(smsPoll, 300);
  } catch (e) { bubble({ direction: "out", text: t("smsOffline") }); }
}

// ---- setup ---------------------------------------------------------------------------
function setNet() {
  const on = navigator.onLine;
  $("net").textContent = on ? t("online") : t("offline"); $("net").className = "badge " + (on ? "online" : "offline");
}
function tab(which) {
  [["search", "tabSearch", "paneSearch"], ["ask", "tabAsk", "paneAsk"], ["sms", "tabSms", "paneSms"]].forEach(([name, b, p]) => {
    $(b).setAttribute("aria-selected", which === name); $(p).hidden = which !== name;
  });
  if (which === "sms") smsPoll();
  if (which === "ask") assistantWarm();
}
function chips(el, list, onClick) {
  el.innerHTML = ""; list.forEach(x => { const b = document.createElement("button"); b.className = "chip"; b.textContent = x; b.onclick = () => onClick(x); el.appendChild(b); });
}

async function init() {
  const saved = store.get("uiLang"), nav = (navigator.language || "en").slice(0, 2);
  ui = STR[saved] ? saved : STR[nav] ? nav : "en";
  addEventListener("online", setNet); addEventListener("offline", setNet);
  const regionId = store.get("packRegion");
  if (regionId) { try { pack = JSON.parse(store.get("pack:" + regionId)); } catch (e) { pack = null; } }
  $("askLocal").checked = store.get("askLocal") === "1";
  applyText();
  assistantCheck();
  try { config = await (await fetch("/api/config", { cache: "no-store" })).json(); } catch (e) { config = null; }
  if (config && !pack) $("regionName").textContent = config.display_name;
  smsAvailability();
  let ex = { sms: [], offline: [], chat: [] };
  try {
    const all = await (await fetch("/api/examples")).json();
    ex = { ...ex, ...(all.traveller_examples || {}),
           chat: (all.traveller_chat_examples || []).map(x => x && x.question).filter(Boolean) };
    store.set("examples", JSON.stringify(ex));
  } catch (e) { try { ex = { ...ex, ...JSON.parse(store.get("examples")) }; } catch (e2) {} }
  chips($("qExamples"), ex.offline || [], x => { $("q").value = x; render(); });
  chips($("smsExamples"), ex.sms || [], x => smsSend(x));
  chips($("askExamples"), ex.chat || [], x => { $("askText").value = x; ask(x); });
  try { smsPhone = sessionStorage.getItem("travellerPhone") || ""; } catch (e) {}
  if (!smsPhone) { smsPhone = "+1555000" + Math.floor(1000 + Math.random() * 9000); try { sessionStorage.setItem("travellerPhone", smsPhone); } catch (e) {} }
  $("uiLang").onchange = () => { ui = $("uiLang").value; store.set("uiLang", ui); applyText(); };
  $("update").onclick = downloadPack;
  $("q").addEventListener("input", render); $("cheap").onchange = render; $("openNow").onchange = render;
  $("tabSearch").onclick = () => tab("search"); $("tabAsk").onclick = () => tab("ask"); $("tabSms").onclick = () => tab("sms");
  $("smsSend").onclick = () => smsSend(); $("smsText").addEventListener("keydown", e => { if (e.key === "Enter") smsSend(); });
  $("askSend").onclick = () => ask(); $("askText").addEventListener("keydown", e => { if (e.key === "Enter") ask(); });
  $("askLocal").onchange = () => { store.set("askLocal", $("askLocal").checked ? "1" : "0"); assistantWarm(); };
  $("assistDownload").onclick = assistantDownload; $("assistRemove").onclick = assistantRemove;
  $("askOut").addEventListener("click", e => {
    const act = e.target.closest("[data-act]")?.dataset.act;
    if (act === "download") { assistantDownload(); $("assist").scrollIntoView({ behavior: "smooth", block: "nearest" }); }
    if (act === "more") { $("askMore").hidden = false; e.target.remove(); }
  });
  setInterval(smsPoll, 1500);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
}
init();

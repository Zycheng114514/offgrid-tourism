// Traveller app: download a region pack, then search it with no connection.
// The search rules mirror server/offgrid/search.py; all search words come from the pack,
// so queries work in every language the region lists (including Chinese, matched without spaces).
"use strict";

const $ = id => document.getElementById(id);
const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } },
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
  },
};
const t = (key, vars = {}) => (STR[ui][key] ?? STR.en[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");

function applyText() {
  document.documentElement.lang = ui;
  document.querySelectorAll("[data-t]").forEach(el => { el.textContent = t(el.dataset.t); });
  $("q").placeholder = t("placeholder"); $("smsText").placeholder = t("smsPlaceholder");
  $("uiLang").value = ui; setNet(); showPack(); renderCats(); render(); smsAvailability();
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
  return null;
}

function relevance(q, l) {
  const hay = norm([l.name, l.offer_original, l.offer_en, l.landmark].join(" "));
  return [...new Set(norm(q).split(" "))].filter(w => w.length >= 3 && termPos(hay, w) >= 0).length;
}

function localNow() {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: pack.region.timezone, year: "numeric", month: "2-digit",
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

function find(q) {
  const cat = catFilter || categoryOf(q), place = matchPlace(q);
  const cheap = $("cheap").checked || hasWord(q, "cheap"), nowOnly = $("openNow").checked || hasWord(q, "now");
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
      || (relevance(q, b) - relevance(q, a)) || (dist(a) - dist(b)));
  } else if (q.trim()) {
    items.sort((a, b) => relevance(q, b) - relevance(q, a));
    if (!cat && items.some(l => relevance(q, l) > 0)) items = items.filter(l => relevance(q, l) > 0);
  }
  if (cheap) items.sort((a, b) => (a.price?.min ?? 9e18) - (b.price?.min ?? 9e18));
  return { items, cat, place };
}

// ---- formatting -------------------------------------------------------------------
function money(n) {
  const c = pack.region.currency;
  return c.display.replace("{amount}", Math.round(n).toLocaleString("en-US").replace(/,/g, c.thousands_separator || ","));
}
function price(p) {
  if (!p) return "";
  const labels = pack.region.unit_labels[ui] || pack.region.unit_labels.en || {};
  return money(p.min) + (p.max ? "–" + money(p.max).replace(/^[^\d]*/, "") : "") + (labels[p.unit || "other"] || "");
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

function render() {
  if (!pack) { $("results").innerHTML = ""; $("count").textContent = ""; return; }
  const q = $("q").value;
  const { items, cat, place } = find(q);
  $("count").textContent = (items.length === 1 ? t("result1") : t("results", { n: items.length })) +
    (cat ? ` · ${t(cat)}` : "") + (place ? ` · ${t("near", { place: place.name })}` : "") + ` · ${t("onPhone")}`;
  $("results").innerHTML = items.map(l => {
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
  }).join("") || `<p class="muted">${t("nothing")}</p>`;
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
  $("tabSearch").setAttribute("aria-selected", which === "search"); $("tabSms").setAttribute("aria-selected", which === "sms");
  $("paneSearch").hidden = which !== "search"; $("paneSms").hidden = which !== "sms";
  if (which === "sms") smsPoll();
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
  applyText();
  try { config = await (await fetch("/api/config", { cache: "no-store" })).json(); } catch (e) { config = null; }
  if (config && !pack) $("regionName").textContent = config.display_name;
  smsAvailability();
  let ex = { sms: [], offline: [] };
  try { ex = (await (await fetch("/api/examples")).json()).traveller_examples || ex; store.set("examples", JSON.stringify(ex)); }
  catch (e) { try { ex = JSON.parse(store.get("examples")) || ex; } catch (e2) {} }
  chips($("qExamples"), ex.offline || [], x => { $("q").value = x; render(); });
  chips($("smsExamples"), ex.sms || [], x => smsSend(x));
  try { smsPhone = sessionStorage.getItem("travellerPhone") || ""; } catch (e) {}
  if (!smsPhone) { smsPhone = "+1555000" + Math.floor(1000 + Math.random() * 9000); try { sessionStorage.setItem("travellerPhone", smsPhone); } catch (e) {} }
  $("uiLang").onchange = () => { ui = $("uiLang").value; store.set("uiLang", ui); applyText(); };
  $("update").onclick = downloadPack;
  $("q").addEventListener("input", render); $("cheap").onchange = render; $("openNow").onchange = render;
  $("tabSearch").onclick = () => tab("search"); $("tabSms").onclick = () => tab("sms");
  $("smsSend").onclick = () => smsSend(); $("smsText").addEventListener("keydown", e => { if (e.key === "Enter") smsSend(); });
  setInterval(smsPoll, 1500);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
}
init();

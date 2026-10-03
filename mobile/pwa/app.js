// Traveller app: download a region pack, then search it with no connection.
// The search rules mirror server/offgrid/search.py; all words come from the pack.
"use strict";

const $ = id => document.getElementById(id);
const store = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } },
};
let config = null, pack = null, catFilter = null, smsPhone = "", smsLast = 0;

// ---- text helpers ---------------------------------------------------------
const norm = s => (s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase()
  .replace(/[^a-z0-9?]+/g, " ").trim();
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function km(a, b) {
  const r = Math.PI / 180, dLat = (b[0] - a[0]) * r, dLon = (b[1] - a[1]) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLon / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

function langs() { return Object.keys(pack.region.words); }
function wordsFor(key) { return langs().flatMap(l => pack.region.words[l][key] || []); }

function categoryOf(q) {
  const t = " " + norm(q) + " "; let best = null;
  for (const l of langs()) for (const [cat, ws] of Object.entries(pack.region.words[l].category || {}))
    for (const w of ws) { const pos = t.indexOf(" " + norm(w) + " "); if (pos >= 0 && (!best || pos < best.pos)) best = { pos, cat }; }
  return best ? best.cat : null;
}
function hasWord(q, key) { const t = " " + norm(q) + " "; return wordsFor(key).some(w => t.includes(" " + norm(w) + " ")); }

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
  const hay = " " + norm([l.name, l.offer_original, l.offer_en, l.landmark].join(" ")) + " ";
  return [...new Set(norm(q).split(" "))].filter(w => w.length >= 3 && hay.includes(" " + w + " ")).length;
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
  if (nowOnly) items = items.filter(l => openNow(l) !== false);
  if (place) {
    const here = [place.lat, place.lon];
    const dist = l => l.location ? km(here, [l.location.lat, l.location.lon]) : 9e9;
    items = items.filter(l => dist(l) <= 15);
    items.sort((a, b) => ((a.village === place.name ? 0 : 1) - (b.village === place.name ? 0 : 1))
      || (relevance(q, b) - relevance(q, a)) || (dist(a) - dist(b)));
  } else if (q.trim()) {
    items.sort((a, b) => relevance(q, b) - relevance(q, a));
    const anyHit = items.some(l => relevance(q, l) > 0);
    if (anyHit && !cat) items = items.filter(l => relevance(q, l) > 0);
  }
  if (cheap) items.sort((a, b) => (a.price?.min ?? 9e18) - (b.price?.min ?? 9e18));
  return { items, cat, place };
}

// ---- formatting -----------------------------------------------------------
function money(n) {
  const c = pack.region.currency;
  return c.display.replace("{amount}", Math.round(n).toLocaleString("en-US").replace(/,/g, c.thousands_separator || ","));
}
function price(p) {
  if (!p) return "";
  const unit = (pack.region.unit_labels[pack.region.traveller_language] || {})[p.unit || "other"] || "";
  return money(p.min) + (p.max ? "–" + money(p.max).replace(/^[^\d]*/, "") : "") + unit;
}
function ago(iso) {
  if (!iso) return { text: "never confirmed", stale: true };
  const days = Math.floor((Date.now() - Date.parse(iso)) / 86400000);
  return { text: days <= 0 ? "confirmed by host today" : `confirmed by host ${days} day${days > 1 ? "s" : ""} ago`, stale: days > 14 };
}
const CAT_LABEL = { food: "Food", lodging: "Stay", transport: "Transport", guide: "Guide", other: "Other" };

function render() {
  if (!pack) { $("results").innerHTML = ""; $("count").textContent = ""; return; }
  const q = $("q").value;
  const { items, cat, place } = find(q);
  $("count").textContent = `${items.length} result${items.length === 1 ? "" : "s"}` +
    (cat ? ` · ${CAT_LABEL[cat]}` : "") + (place ? ` · near ${place.name}` : "") + " · searched on this phone";
  $("results").innerHTML = items.map(l => {
    const f = ago(l.last_confirmed_at), now = localNow();
    const today = l.open_today_date === now.date && l.open_today !== null
      ? `<span class="tag ${l.open_today ? "open" : "closed"}">${l.open_today ? "open today" : "closed today"}</span>` : "";
    const phone = l.phone ? `<div class="actions"><a href="tel:${esc(l.phone)}">Call</a><a href="sms:${esc(l.phone)}">SMS</a>
      <span class="small muted">${esc(l.phone)} (invented)</span></div>` : `<div class="small muted" style="margin-top:6px">Host did not agree to show a phone number.</div>`;
    return `<article class="result">
      <h3>${esc(l.name)} <span class="tag">${CAT_LABEL[l.category] || l.category}</span></h3>
      <div class="where">${esc(l.village)}${l.landmark ? " · " + esc(l.landmark) : ""}</div>
      <div class="offer">${esc(l.offer_en || l.offer_original)}</div>
      ${l.offer_en ? `<div class="orig">"${esc(l.offer_original)}"</div>` : ""}
      <div class="facts">${price(l.price) ? `<span>${esc(price(l.price))}</span>` : ""}
        ${l.hours ? `<span>${esc(l.hours.open)}–${esc(l.hours.close)}</span>` : ""}
        ${l.capacity ? `<span>capacity ${l.capacity}</span>` : ""}
        <span class="tag ${f.stale ? "stale" : ""}">${f.text}${f.stale ? " · may be out of date" : ""}</span>${today}</div>
      ${phone}</article>`;
  }).join("") || `<p class="muted">Nothing matches. Try a village name or "food", "room", "boat", "guide".</p>`;
}

// ---- pack download -----------------------------------------------------------
function showPack() {
  if (!pack) { $("packInfo").textContent = "No listings downloaded yet."; return; }
  const kb = Math.round((store.get("pack:" + pack.region.id) || "").length / 1024);
  const when = new Date(pack.generated_at).toLocaleString();
  $("packInfo").innerHTML = `<strong>${pack.listings.length} listings</strong> for ${esc(pack.region.display_name)}` +
    `<br><span class="muted">downloaded ${esc(when)}${kb ? ` · ${kb} KB on this phone` : ""}</span>`;
  $("regionName").textContent = pack.region.display_name;
  $("update").textContent = "Update";
  renderCats();
}
async function downloadPack() {
  $("update").disabled = true;
  try {
    const id = (config && config.region_id) || (pack && pack.region.id);
    const res = await fetch(`/api/regions/${id}/pack.json`, { cache: "no-store" });
    const data = await res.json();
    pack = data; aliasIndex = null;
    store.set("pack:" + data.region.id, JSON.stringify(data)); store.set("packRegion", data.region.id);
    showPack(); render();
  } catch (e) {
    $("packInfo").textContent = "Could not download: no connection. Listings already on this phone still work.";
  } finally { $("update").disabled = false; }
}

function renderCats() {
  $("cats").innerHTML = "";
  [null, "food", "lodging", "transport", "guide"].forEach(c => {
    const b = document.createElement("button");
    b.className = "chip" + (catFilter === c ? " on" : ""); b.textContent = c ? CAT_LABEL[c] : "All";
    b.onclick = () => { catFilter = c; renderCats(); render(); };
    $("cats").appendChild(b);
  });
}

// ---- SMS tab (simulated in the demo) -------------------------------------------
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
  } catch (e) { bubble({ direction: "out", text: "(Demo needs a connection for the SMS simulator.)" }); }
}

// ---- setup ------------------------------------------------------------------
function setNet() {
  const on = navigator.onLine;
  $("net").textContent = on ? "Online" : "Offline"; $("net").className = "badge " + (on ? "online" : "offline");
}
function tab(which) {
  $("tabSearch").setAttribute("aria-selected", which === "search"); $("tabSms").setAttribute("aria-selected", which === "sms");
  $("paneSearch").hidden = which !== "search"; $("paneSms").hidden = which !== "sms";
  if (which === "sms") smsPoll();
}
function chips(el, list, onClick) {
  el.innerHTML = ""; list.forEach(t => { const b = document.createElement("button"); b.className = "chip"; b.textContent = t; b.onclick = () => onClick(t); el.appendChild(b); });
}

async function init() {
  setNet(); addEventListener("online", setNet); addEventListener("offline", setNet);
  const regionId = store.get("packRegion");
  if (regionId) { try { pack = JSON.parse(store.get("pack:" + regionId)); } catch (e) { pack = null; } }
  showPack(); renderCats(); render();
  try { config = await (await fetch("/api/config", { cache: "no-store" })).json(); } catch (e) { config = null; }
  if (config && !pack) $("regionName").textContent = config.display_name;
  let ex = { sms: [], offline: [] };
  try { ex = (await (await fetch("/api/examples")).json()).traveller_examples || ex; store.set("examples", JSON.stringify(ex)); }
  catch (e) { try { ex = JSON.parse(store.get("examples")) || ex; } catch (e2) {} }
  chips($("qExamples"), ex.offline || [], t => { $("q").value = t; render(); });
  chips($("smsExamples"), ex.sms || [], t => smsSend(t));
  try { smsPhone = sessionStorage.getItem("travellerPhone") || ""; } catch (e) {}
  if (!smsPhone) { smsPhone = "+1555000" + Math.floor(1000 + Math.random() * 9000); try { sessionStorage.setItem("travellerPhone", smsPhone); } catch (e) {} }
  $("update").onclick = downloadPack;
  $("q").addEventListener("input", render); $("cheap").onchange = render; $("openNow").onchange = render;
  $("tabSearch").onclick = () => tab("search"); $("tabSms").onclick = () => tab("sms");
  $("smsSend").onclick = () => smsSend(); $("smsText").addEventListener("keydown", e => { if (e.key === "Enter") smsSend(); });
  setInterval(smsPoll, 1500);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
}
init();

// Offline assistant: runs a small language model in a background thread so the page stays responsive.
// The model only turns a question into search filters (JSON); app.js does the search and writes the answer.
//
// Library: transformers.js, pinned version, from the jsDelivr CDN. sw.js keeps a copy of it and of the
// ONNX runtime files it loads (also from jsDelivr), so they load with no connection.
// Model files: downloaded from Hugging Face directly (never through our server) and kept in the browser's
// Cache Storage ("transformers-cache"); later loads read them from there.
const LIB_URL = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.0/dist/transformers.min.js";
const MODEL_ID = "onnx-community/Qwen2.5-0.5B-Instruct";
const MODEL_FILES = ["config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json"];
const ONNX_FILE = { q4: "onnx/model_q4.onnx", q8: "onnx/model_quantized.onnx" };
const CACHE_NAME = "transformers-cache";
const PART = 32 * 1024 * 1024;

// transformers.js 4.3.0 stores each file with a single Cache.put() of the whole file. Chromium refused that for
// the 483 MB model ("UnknownError: Unexpected internal error"), so the model was not kept for offline use.
// This cache (given to transformers.js through env.customCache) stores small files whole and large ones in
// 32 MB parts; the entry under the file's own URL is written last, so a half-written file is never used, and a
// file with a part missing (a browser may drop entries) counts as not stored.
const partKey = (key, i) => `${key}?offgrid-part=${i}`;
const splitCache = {
  async match(key) {
    const c = await caches.open(CACHE_NAME);
    const hit = await c.match(key);
    if (!hit || !hit.headers.has("x-offgrid-parts")) return hit;
    const parts = Number(hit.headers.get("x-offgrid-parts"));
    for (let j = 0; j < parts; j++) if (!(await c.match(partKey(key, j)))) return undefined;
    let i = 0;
    const body = new ReadableStream({
      async pull(ctl) {
        if (i >= parts) { ctl.close(); return; }
        const r = await c.match(partKey(key, i++));
        if (!r) { ctl.error(new Error(`part ${i - 1} of ${key} is missing`)); return; }
        ctl.enqueue(new Uint8Array(await r.arrayBuffer()));
      },
    });
    const headers = new Headers(hit.headers);
    headers.set("content-length", hit.headers.get("x-offgrid-size"));
    headers.delete("x-offgrid-parts"); headers.delete("x-offgrid-size");
    return new Response(body, { status: 200, headers });
  },
  async put(key, response) {
    const c = await caches.open(CACHE_NAME);
    const size = Number(response.headers.get("content-length")) || 0;
    if (size <= PART) return c.put(key, response);
    const reader = response.body.getReader();
    const nextSize = done => (size - done > 0 ? Math.min(PART, size - done) : PART);
    let n = 0, written = 0, fill = 0, part = new Uint8Array(nextSize(0));
    const flush = async () => {
      await c.put(partKey(key, n++), new Response(part.subarray(0, fill)));
      written += fill; fill = 0; part = new Uint8Array(nextSize(written));
    };
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (let off = 0; off < value.length;) {
        const k = Math.min(part.length - fill, value.length - off);
        part.set(value.subarray(off, off + k), fill); fill += k; off += k;
        if (fill === part.length) await flush();
      }
    }
    if (fill) await flush();
    const headers = new Headers(response.headers);
    headers.delete("content-length");
    headers.set("x-offgrid-parts", String(n)); headers.set("x-offgrid-size", String(written));
    await c.put(key, new Response(null, { status: 200, headers }));
  },
};

let generator = null, loading = null;

// The page chooses the device and weights (app.js, assistantPlan) and passes them in; this is only a fallback.
// Graphics chip (WebGPU) with 4-bit weights and 32-bit maths ("q4"); otherwise the main processor (WebAssembly)
// with 8-bit weights ("q8" = model_quantized.onnx). Not "q4f16": with 16-bit maths this model's answers were
// garbage in testing (it could not name the capital of France), while q4 and q8 answered normally.
async function pickDevice() {
  try {
    if (self.navigator.gpu && await self.navigator.gpu.requestAdapter()) return { device: "webgpu", dtype: "q4" };
  } catch (e) { /* no usable GPU */ }
  return { device: "wasm", dtype: "q8" };
}

async function load({ device, dtype } = {}) {
  const t0 = performance.now();
  const { env, pipeline } = await import(LIB_URL);
  env.allowLocalModels = false;   // model files come from Hugging Face or this browser's cache, nothing else
  env.useCustomCache = true;      // Cache Storage, with large files split (see splitCache)
  env.customCache = splitCache;
  env.useWasmCache = false;       // the runtime files are kept once, by sw.js, not twice
  let networkFetches = 0;         // transformers.js requests that went past its cache (0 when everything is stored)
  const baseFetch = env.fetch;
  env.fetch = (...args) => { networkFetches++; return baseFetch(...args); };
  const chosen = device && dtype ? { device, dtype } : await pickDevice();
  postMessage({ type: "chosen", ...chosen });
  let last = 0;
  generator = await pipeline("text-generation", MODEL_ID, {
    ...chosen,
    progress_callback: p => {
      if (p.status !== "progress_total") return;
      const now = performance.now();
      if (now - last < 250 && p.loaded < p.total) return;
      last = now;
      postMessage({ type: "progress", loaded: p.loaded, total: p.total });
    },
  });
  // Are all files really stored for offline use? (A failed write is only logged by transformers.js.)
  const base = `${env.remoteHost}${MODEL_ID}/resolve/main/`;
  const missing = [];
  for (const f of [...MODEL_FILES, ONNX_FILE[chosen.dtype]]) if (!(await splitCache.match(base + f))) missing.push(f);
  const wasm = env.backends?.onnx?.wasm?.wasmPaths || {};
  const runtime = [LIB_URL, wasm.mjs, wasm.wasm].filter(u => typeof u === "string" && u.startsWith("https://"));
  return { ...chosen, ms: Math.round(performance.now() - t0), networkFetches, missing, runtime, model: MODEL_ID };
}

// Greedy decoding: the model's own generation_config.json asks for sampling, so switch it off explicitly.
async function generate({ messages, max_new_tokens = 64 }) {
  const t0 = performance.now();
  const out = await generator(messages, { max_new_tokens, do_sample: false, repetition_penalty: 1.0 });
  const text = out[0].generated_text.at(-1).content;
  let tokens = null;
  try { tokens = generator.tokenizer.encode(text).length; } catch (e) { /* only for the timing note */ }
  return { text, tokens, ms: Math.round(performance.now() - t0) };
}

self.onmessage = async e => {
  const m = e.data || {};
  if (m.type === "load") {
    loading = loading || load(m);
    try { postMessage({ type: "loaded", ...(await loading) }); }
    catch (err) { loading = null; generator = null; postMessage({ type: "error", stage: "load", message: String(err?.message || err) }); }
  } else if (m.type === "generate") {
    try {
      if (!generator) throw new Error("the model is not loaded");
      postMessage({ type: "generated", id: m.id, ...(await generate(m)) });
    } catch (err) { postMessage({ type: "error", stage: "generate", id: m.id, message: String(err?.message || err) }); }
  }
};

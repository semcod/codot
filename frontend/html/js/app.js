// UI glue. Keeps state minimal: the JWT lives in sessionStorage via api.js.

const $ = (id) => document.getElementById(id);

function showAuthed(role) {
  $("login-section").hidden = true;
  $("catalog-section").hidden = false;
  $("runner-section").hidden = false;
  $("query-section").hidden = false;
  $("logout-btn").hidden = false;
  $("user-label").textContent = `role: ${role}`;
}

function showAnonymous() {
  $("login-section").hidden = false;
  $("catalog-section").hidden = true;
  $("runner-section").hidden = true;
  $("query-section").hidden = true;
  $("logout-btn").hidden = true;
  $("user-label").textContent = "not logged in";
}

$("login-btn").addEventListener("click", async () => {
  const u = $("username").value.trim();
  const p = $("password").value;
  const msg = $("login-msg");
  msg.textContent = ""; msg.className = "msg";
  try {
    const r = await API.login(u, p);
    msg.textContent = `logged in as ${u} (role: ${r.role})`;
    msg.classList.add("ok");
    showAuthed(r.role);
    loadCatalog();
  } catch (e) {
    msg.textContent = `login failed: ${e.message}`;
    msg.classList.add("err");
  }
});

$("logout-btn").addEventListener("click", () => {
  API.clearToken();
  showAnonymous();
});

$("refresh-catalog").addEventListener("click", loadCatalog);

async function loadCatalog() {
  const box = $("catalog-box");
  box.textContent = "loading...";
  try {
    const cat = await API.catalog();
    const cmdSel = $("command-select");
    const qrySel = $("query-select");
    cmdSel.innerHTML = "";
    qrySel.innerHTML = "";

    for (const c of cat.commands) {
      const o = document.createElement("option");
      o.value = c.name; o.textContent = c.name;
      cmdSel.appendChild(o);
    }
    for (const q of cat.queries) {
      const o = document.createElement("option");
      o.value = q.name; o.textContent = q.name;
      qrySel.appendChild(o);
    }

    box.innerHTML = `
      <div class="catalog-group"><b>Protocols:</b> ${cat.protocols.map(p => `<code>${p}</code>`).join(" ")}</div>
      <div class="catalog-group"><b>Commands:</b>
        ${cat.commands.map(c => `<div class="catalog-item"><code>PUT /commands/${c.name}</code> — ${c.description}</div>`).join("")}
      </div>
      <div class="catalog-group"><b>Queries:</b>
        ${cat.queries.map(q => `<div class="catalog-item"><code>POST /queries/${q.name}</code> — ${q.description}</div>`).join("")}
      </div>`;
  } catch (e) {
    box.textContent = `failed: ${e.message}`;
  }
}

function parseMeta() {
  const raw = $("meta").value.trim() || "{}";
  try { return JSON.parse(raw); }
  catch (e) { throw new Error("meta is not valid JSON: " + e.message); }
}

function decodeB64(b64) {
  const bin = atob(b64 || "");
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

function renderDecoded(mime, b64) {
  const box = $("decoded");
  box.innerHTML = "";
  if (!b64) { box.textContent = "(no payload)"; return; }
  const bytes = decodeB64(b64);
  if (!mime) mime = "application/octet-stream";

  if (mime.startsWith("text/html")) {
    const iframe = document.createElement("iframe");
    iframe.sandbox = "";
    iframe.style = "width:100%;height:360px;border:1px solid #d0d7de;border-radius:6px;background:#fff";
    iframe.srcdoc = new TextDecoder().decode(bytes);
    box.appendChild(iframe);
  } else if (mime.startsWith("image/")) {
    const blob = new Blob([bytes], { type: mime });
    const img = document.createElement("img");
    img.src = URL.createObjectURL(blob);
    img.style = "max-width:100%;border:1px solid #d0d7de;border-radius:6px";
    box.appendChild(img);
  } else if (mime.includes("json") || mime.startsWith("text/") || mime.includes("xml") || mime.includes("csv")) {
    const pre = document.createElement("pre");
    pre.textContent = new TextDecoder().decode(bytes);
    box.appendChild(pre);
  } else {
    box.textContent = `binary payload (${bytes.length} bytes, ${mime})`;
  }
}

$("run-btn").addEventListener("click", async () => {
  const name = $("command-select").value;
  const respEl = $("response");
  respEl.textContent = "running...";
  $("decoded").innerHTML = "";
  try {
    const body = {
      input_uri: $("input-uri").value.trim() || null,
      schema_uri: $("schema-uri").value.trim() || null,
      meta: parseMeta(),
    };
    const r = await API.runCommand(name, body);
    respEl.textContent = JSON.stringify({ ok: r.ok, mime: r.mime, meta: r.meta }, null, 2);
    renderDecoded(r.mime, r.payload_b64);
  } catch (e) {
    respEl.textContent = `ERROR ${e.status || ""}: ${e.message}`;
  }
});

// Presets - illustrate common patterns
$("preset-csv").addEventListener("click", () => {
  $("command-select").value = "converttojson";
  $("input-uri").value = "http://data/products.csv";
  $("schema-uri").value = "http://schemas/public-products.json";
  $("meta").value = JSON.stringify({ mode: "csv" }, null, 2);
});

$("preset-render").addEventListener("click", () => {
  $("command-select").value = "render";
  $("input-uri").value = "http://data/posts.json";
  $("schema-uri").value = "";
  $("meta").value = JSON.stringify({ title: "Posts" }, null, 2);
});

$("preset-pipeline").addEventListener("click", () => {
  $("command-select").value = "pipeline";
  $("input-uri").value = "";
  $("schema-uri").value = "";
  $("meta").value = JSON.stringify({
    steps: [
      { command: "converttojson", request: { input_uri: "http://data/products.csv", meta: { mode: "csv" } } },
      { command: "render", request: { input_uri: "$previous.output", meta: { title: "Products" } } },
    ],
  }, null, 2);
});

$("run-query-btn").addEventListener("click", async () => {
  const name = $("query-select").value;
  const respEl = $("query-response");
  respEl.textContent = "running...";
  try {
    const uris = $("query-uris").value.split("\n").map(s => s.trim()).filter(Boolean);
    const r = await API.runQuery(name, { source_uris: uris });
    respEl.textContent = JSON.stringify(r, null, 2);
  } catch (e) {
    respEl.textContent = `ERROR ${e.status || ""}: ${e.message}`;
  }
});

// Boot
if (API.getToken()) {
  showAuthed(API.getRole() || "?");
  loadCatalog();
} else {
  showAnonymous();
}

// Tiny fetch wrapper that stores the JWT and adds Authorization headers.
const API = (() => {
  const TOKEN_KEY = "codot.token";
  const ROLE_KEY = "codot.role";

  function getToken() { return sessionStorage.getItem(TOKEN_KEY); }
  function setToken(t) { sessionStorage.setItem(TOKEN_KEY, t); }
  function clearToken() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(ROLE_KEY);
  }
  function getRole() { return sessionStorage.getItem(ROLE_KEY); }
  function setRole(r) { sessionStorage.setItem(ROLE_KEY, r); }

  async function request(path, { method = "GET", body = null, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth && getToken()) headers["Authorization"] = `Bearer ${getToken()}`;
    const resp = await fetch(`/api${path}`, {
      method,
      headers,
      body: body === null ? null : JSON.stringify(body),
    });
    let data;
    const ct = resp.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      data = await resp.json();
    } else {
      data = { raw: await resp.text() };
    }
    if (!resp.ok) {
      const err = new Error(data.detail || data.error || resp.statusText);
      err.status = resp.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  async function login(username, password) {
    const data = await request("/auth/token", {
      method: "POST",
      body: { username, password },
      auth: false,
    });
    setToken(data.access_token);
    setRole(data.role);
    return data;
  }

  async function catalog() { return request("/catalog", { auth: false }); }

  async function runCommand(name, body) {
    return request(`/commands/${name}`, { method: "PUT", body });
  }

  async function runQuery(name, body) {
    return request(`/queries/${name}`, { method: "POST", body });
  }

  return { login, catalog, runCommand, runQuery, getToken, clearToken, getRole };
})();

const API = "/api/v1";
const KEY_ACCESS = "coreauth_access";
const KEY_REFRESH = "coreauth_refresh";

const $ = (id) => document.getElementById(id);

function getTokens() {
  return {
    access: localStorage.getItem(KEY_ACCESS),
    refresh: localStorage.getItem(KEY_REFRESH),
  };
}

function setTokens(access, refresh) {
  localStorage.setItem(KEY_ACCESS, access);
  localStorage.setItem(KEY_REFRESH, refresh);
}

function clearTokens() {
  localStorage.removeItem(KEY_ACCESS);
  localStorage.removeItem(KEY_REFRESH);
}

async function request(path, { auth = false, method = "GET", body } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth) {
    const { access } = getTokens();
    if (access) headers.Authorization = `Bearer ${access}`;
  }

  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!res.ok) {
    const d = data?.detail;
    const msg =
      typeof d === "string"
        ? d
        : Array.isArray(d)
          ? d.map((e) => e.msg || e.message).join(", ")
          : res.statusText;
    throw new Error(msg || "Request failed");
  }
  return data;
}

const api = {
  register: (email, password) => request("/auth/register", { method: "POST", body: { email, password } }),
  login: (email, password) => request("/auth/login", { method: "POST", body: { email, password } }),
  me: () => request("/auth/me", { auth: true }),
  refresh: (token) => request("/auth/refresh", { method: "POST", body: { refresh_token: token } }),
  logout: () => request("/auth/logout", { method: "POST", auth: true }),
  health: () => fetch(`${API}/health`).then((r) => r.ok),
};

function showAlert(el, msg, type = "error") {
  el.textContent = msg;
  el.className = `alert alert-${type}`;
  el.hidden = false;
}

function hideAlert(el) {
  el.hidden = true;
}

function showGuest() {
  $("view-guest").hidden = false;
  $("view-dashboard").hidden = true;
  hideAlert($("alert"));
}

function showDashboard() {
  $("view-guest").hidden = true;
  $("view-dashboard").hidden = false;
  hideAlert($("alert-dash"));
}

function switchTab(name) {
  const login = name === "login";
  $("tab-login").classList.toggle("active", login);
  $("tab-register").classList.toggle("active", !login);
  $("panel-login").hidden = !login;
  $("panel-register").hidden = login;
  hideAlert($("alert"));
}

function renderProfile(user) {
  $("profile-email").textContent = user.email;
  $("profile-id").textContent = user.id;
  $("profile-created").textContent = new Date(user.created_at).toLocaleString();
  $("profile-role").textContent = user.is_superuser ? "Superuser" : "User";
  const pill = $("status-pill");
  pill.textContent = user.is_active ? "Active" : "Inactive";
  pill.className = user.is_active ? "pill pill-ok" : "pill pill-off";
}

async function loadProfile() {
  renderProfile(await api.me());
  showDashboard();
}

async function restoreSession() {
  if (!localStorage.getItem(KEY_ACCESS)) {
    showGuest();
    return;
  }
  try {
    await loadProfile();
  } catch {
    const { refresh } = getTokens();
    if (refresh) {
      try {
        const t = await api.refresh(refresh);
        setTokens(t.access_token, t.refresh_token);
        await loadProfile();
        return;
      } catch {}
    }
    clearTokens();
    showGuest();
  }
}

$("tab-login").onclick = () => switchTab("login");
$("tab-register").onclick = () => switchTab("register");

$("panel-login").onsubmit = async (e) => {
  e.preventDefault();
  hideAlert($("alert"));
  const fd = new FormData(e.target);
  const btn = e.target.querySelector("button");
  btn.disabled = true;
  try {
    const t = await api.login(fd.get("email"), fd.get("password"));
    setTokens(t.access_token, t.refresh_token);
    await loadProfile();
    e.target.reset();
  } catch (err) {
    showAlert($("alert"), err.message);
  } finally {
    btn.disabled = false;
  }
};

$("panel-register").onsubmit = async (e) => {
  e.preventDefault();
  hideAlert($("alert"));
  const fd = new FormData(e.target);
  const btn = e.target.querySelector("button");
  btn.disabled = true;
  try {
    await api.register(fd.get("email"), fd.get("password"));
    showAlert($("alert"), "Account created. Sign in below.", "success");
    switchTab("login");
    $("panel-login").querySelector('[name="email"]').value = fd.get("email");
    e.target.reset();
  } catch (err) {
    showAlert($("alert"), err.message);
  } finally {
    btn.disabled = false;
  }
};

$("btn-refresh").onclick = async () => {
  hideAlert($("alert-dash"));
  $("btn-refresh").disabled = true;
  try {
    const { refresh } = getTokens();
    const t = await api.refresh(refresh);
    setTokens(t.access_token, t.refresh_token);
    await loadProfile();
    showAlert($("alert-dash"), "Tokens refreshed.", "success");
  } catch (err) {
    showAlert($("alert-dash"), err.message);
  } finally {
    $("btn-refresh").disabled = false;
  }
};

$("btn-logout").onclick = async () => {
  $("btn-logout").disabled = true;
  try {
    await api.logout();
  } catch {}
  clearTokens();
  showGuest();
  $("btn-logout").disabled = false;
};

(async () => {
  $("loading").hidden = false;
  try {
    const ok = await api.health();
    $("health-status").textContent = ok ? "API online" : "API offline";
    $("health-status").className = ok ? "ok" : "err";
  } catch {
    $("health-status").textContent = "API offline";
    $("health-status").className = "err";
  }
  await restoreSession();
  $("loading").hidden = true;
})();

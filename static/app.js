// Shared Alpine components for Quorum.
// Forms post to the existing JSON API; JWT cookie is set by the server on login.

const API = "";

// Paths that must NEVER trigger a refresh/retry loop on 401.
const AUTH_PATHS = new Set(["/accounts/login", "/accounts/refresh", "/accounts/logout"]);

// Shared promise so parallel 401s only call /accounts/refresh once.
let _refreshing = null;

async function _rawFetch(path, options) {
    return fetch(API + path, {
        credentials: "include",
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    });
}

async function _refreshTokens() {
    if (!_refreshing) {
        _refreshing = (async () => {
            try {
                const r = await _rawFetch("/accounts/refresh", { method: "POST" });
                return r.ok;
            } catch (_) {
                return false;
            } finally {
                // Clear after a tick so simultaneous callers all see the same result.
                setTimeout(() => { _refreshing = null; }, 0);
            }
        })();
    }
    return _refreshing;
}

function _onPublicPage() {
    const p = window.location.pathname;
    return p === "/login" || p === "/register";
}

async function apiFetch(path, options = {}) {
    let res = await _rawFetch(path, options);

    // On 401 for any non-auth endpoint, try one refresh + retry.
    if (res.status === 401 && !AUTH_PATHS.has(path)) {
        const ok = await _refreshTokens();
        if (ok) {
            res = await _rawFetch(path, options);
        } else if (!_onPublicPage()) {
            // Can't recover; send the user to login with return path.
            const next = encodeURIComponent(window.location.pathname + window.location.search);
            window.location.href = `/login?next=${next}`;
            throw new Error("Session expired");
        }
    }

    let data = null;
    try { data = await res.json(); } catch (_) { /* empty body */ }
    if (!res.ok) {
        const detail = (data && (data.detail || data.message)) || `HTTP ${res.status}`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
}

// --- Client-side cache (sessionStorage, TTL in ms) ---------------------------
const cache = {
    get(key) {
        try {
            const raw = sessionStorage.getItem(key);
            if (!raw) return null;
            const { expires, value } = JSON.parse(raw);
            if (Date.now() > expires) {
                sessionStorage.removeItem(key);
                return null;
            }
            return value;
        } catch (_) { return null; }
    },
    set(key, value, ttlMs) {
        try {
            sessionStorage.setItem(key, JSON.stringify({
                expires: Date.now() + ttlMs,
                value,
            }));
        } catch (_) { /* storage full / disabled */ }
    },
    clear(prefix = "") {
        for (const k of Object.keys(sessionStorage)) {
            if (!prefix || k.startsWith(prefix)) sessionStorage.removeItem(k);
        }
    },
};

// Fetch with cache + stale-while-revalidate. Returns cached immediately if
// present; if stale, refetches in the background and calls onFresh(value).
async function cachedFetch(path, ttlMs = 5 * 60 * 1000, onFresh = null) {
    const key = `cache:${path}`;
    const cached = cache.get(key);
    if (cached != null) {
        // optional background refresh when more than half the TTL has elapsed
        try {
            const raw = JSON.parse(sessionStorage.getItem(key));
            const age = Date.now() - (raw.expires - ttlMs);
            if (age > ttlMs / 2 && onFresh) {
                apiFetch(path).then(v => { cache.set(key, v, ttlMs); onFresh(v); }).catch(() => {});
            }
        } catch (_) {}
        return cached;
    }
    const value = await apiFetch(path);
    cache.set(key, value, ttlMs);
    return value;
}

// --- Formatters -------------------------------------------------------------
function fmtNum(n, digits = 5) {
    if (n == null || Number.isNaN(n)) return "—";
    return Number(n).toLocaleString(undefined, { maximumFractionDigits: digits });
}
function fmtPct(n, digits = 2) {
    if (n == null || Number.isNaN(n)) return "—";
    const sign = n > 0 ? "+" : "";
    return `${sign}${Number(n).toFixed(digits)}%`;
}
function toneForChange(n) {
    if (n == null) return "text-slate-300";
    if (n > 0) return "text-emerald-400";
    if (n < 0) return "text-red-400";
    return "text-slate-300";
}
function toneForQuality(q) {
    return ({
        modest: "text-emerald-400",
        weak: "text-amber-400",
        no_edge_detected: "text-slate-500",
    }[q] || "text-slate-300");
}

// --- Alpine components ------------------------------------------------------
document.addEventListener("alpine:init", () => {
    Alpine.data("loginForm", () => ({
        email: "", password: "", loading: false, error: "",
        async submit() {
            this.loading = true; this.error = "";
            try {
                await apiFetch("/accounts/login", {
                    method: "POST",
                    body: JSON.stringify({ email: this.email, password: this.password }),
                });
                cache.clear();  // reset per-user cache on login
                const next = new URLSearchParams(window.location.search).get("next") || "/";
                window.location.href = next;
            } catch (e) { this.error = e.message; }
            finally { this.loading = false; }
        },
    }));

    Alpine.data("registerForm", () => ({
        name: "", email: "", password: "", loading: false, error: "",
        async submit() {
            this.loading = true; this.error = "";
            try {
                await apiFetch("/accounts", {
                    method: "POST",
                    body: JSON.stringify({ name: this.name, email: this.email, password: this.password }),
                });
                await apiFetch("/accounts/login", {
                    method: "POST",
                    body: JSON.stringify({ email: this.email, password: this.password }),
                });
                cache.clear();
                window.location.href = "/";
            } catch (e) { this.error = e.message; }
            finally { this.loading = false; }
        },
    }));

    Alpine.data("auth", () => ({
        user: null,
        _timer: null,
        async init() {
            try {
                this.user = await cachedFetch("/accounts/me", 60 * 1000, v => this.user = v);
            } catch (_) { this.user = null; }
            // Proactive refresh: access tokens live for JWT_ACCESS_EXPIRY minutes.
            // Refresh every 10 min so an idle tab stays logged in without a 401.
            if (this.user && !_onPublicPage()) {
                this._timer = setInterval(() => { _refreshTokens(); }, 10 * 60 * 1000);
            }
        },
        destroy() {
            if (this._timer) clearInterval(this._timer);
        },
        async logout() {
            if (this._timer) clearInterval(this._timer);
            try { await apiFetch("/accounts/logout", { method: "POST" }); } catch (_) {}
            cache.clear();
            this.user = null;
            window.location.href = "/login";
        },
    }));

    Alpine.data("dashboard", () => ({
        loading: true, error: "", signals: null, news: null,
        async init() {
            await Promise.all([this.loadSignals(), this.loadNews()]);
            this.loading = false;
        },
        async loadSignals() {
            try {
                this.signals = await cachedFetch(
                    "/api/signals/current?pair=GBPUSD&interval=1h",
                    5 * 60 * 1000,
                    v => this.signals = v,
                );
            } catch (e) { this.error = e.message; }
        },
        async loadNews() {
            try {
                this.news = await cachedFetch(
                    "/api/news/digest?max_items=5",
                    10 * 60 * 1000,
                    v => this.news = v,
                );
            } catch (e) { console.warn("news load failed:", e.message); }
        },
        get price() { return this.signals?.snapshot?.price; },
        get change1d() { return this.signals?.snapshot?.change_1d_pct; },
        get trend() { return this.signals?.regime?.trend ?? "—"; },
        get volState() { return this.signals?.regime?.vol_state ?? "—"; },
        get pUp() { return this.signals?.model?.p_up; },
        get quality() { return this.signals?.model?.signal_quality ?? "—"; },
        get topHeadlines() { return (this.news?.items ?? []).slice(0, 5); },
        get topPriority() { return this.topHeadlines[0]?.priority ?? null; },
        fmtNum, fmtPct, toneForChange, toneForQuality,
    }));

    Alpine.data("signalsPage", () => ({
        loading: true, error: "", signals: null,
        async init() {
            try {
                this.signals = await cachedFetch(
                    "/api/signals/current?pair=GBPUSD&interval=1h",
                    5 * 60 * 1000,
                    v => this.signals = v,
                );
            } catch (e) { this.error = e.message; }
            finally { this.loading = false; }
        },
        fmtNum, fmtPct, toneForChange, toneForQuality,
    }));

    Alpine.data("newsPage", () => ({
        loading: true, error: "", digest: null,
        async init() {
            try {
                this.digest = await cachedFetch(
                    "/api/news/digest",
                    10 * 60 * 1000,
                    v => this.digest = v,
                );
            } catch (e) { this.error = e.message; }
            finally { this.loading = false; }
        },
    }));

    Alpine.data("chat", () => ({
        messages: [],
        input: "",
        loading: false,
        error: "",
        suggestions: [
            "What's your read on GBP/USD right now?",
            "Show my account summary and open positions.",
            "Any high-priority news for GBP/USD in the last 24h?",
            "Would you buy 1000 units of GBPUSD now? Explain.",
        ],
        STORE_KEY: "chat:messages:v1",
        init() {
            try {
                const raw = sessionStorage.getItem(this.STORE_KEY);
                if (raw) this.messages = JSON.parse(raw);
            } catch (_) { this.messages = []; }
            this.$nextTick(() => this.scrollDown());
        },
        persist() {
            try { sessionStorage.setItem(this.STORE_KEY, JSON.stringify(this.messages)); } catch (_) {}
        },
        scrollDown() {
            const el = this.$refs.scroller;
            if (el) el.scrollTop = el.scrollHeight;
        },
        reset() {
            this.messages = [];
            this.error = "";
            this.persist();
        },
        async send() {
            const text = this.input.trim();
            if (!text || this.loading) return;
            this.error = "";
            this.messages.push({ role: "user", content: text });
            this.input = "";
            this.persist();
            this.$nextTick(() => this.scrollDown());
            this.loading = true;
            try {
                const res = await apiFetch("/api/chat/message", {
                    method: "POST",
                    body: JSON.stringify({ messages: this.messages }),
                });
                this.messages.push(res.message);
                this.persist();
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
                this.$nextTick(() => this.scrollDown());
            }
        },
    }));
});

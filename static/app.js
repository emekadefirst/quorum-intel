// Shared Alpine components for Quorum.
// Forms post to the existing JSON API; JWT cookie is set by the server on login.

const API = "";

async function apiFetch(path, options = {}) {
    const res = await fetch(API + path, {
        credentials: "include",
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    });
    let data = null;
    try { data = await res.json(); } catch (_) { /* empty body */ }
    if (!res.ok) {
        const detail = (data && (data.detail || data.message)) || `HTTP ${res.status}`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
}

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
    return (
        {
            modest: "text-emerald-400",
            weak: "text-amber-400",
            no_edge_detected: "text-slate-500",
        }[q] || "text-slate-300"
    );
}

document.addEventListener("alpine:init", () => {
    Alpine.data("loginForm", () => ({
        email: "",
        password: "",
        loading: false,
        error: "",
        async submit() {
            this.loading = true;
            this.error = "";
            try {
                await apiFetch("/accounts/login", {
                    method: "POST",
                    body: JSON.stringify({ email: this.email, password: this.password }),
                });
                window.location.href = "/";
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },
    }));

    Alpine.data("registerForm", () => ({
        name: "",
        email: "",
        password: "",
        loading: false,
        error: "",
        async submit() {
            this.loading = true;
            this.error = "";
            try {
                await apiFetch("/accounts", {
                    method: "POST",
                    body: JSON.stringify({
                        name: this.name,
                        email: this.email,
                        password: this.password,
                    }),
                });
                await apiFetch("/accounts/login", {
                    method: "POST",
                    body: JSON.stringify({ email: this.email, password: this.password }),
                });
                window.location.href = "/";
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },
    }));

    Alpine.data("auth", () => ({
        user: null,
        async init() {
            try {
                this.user = await apiFetch("/accounts/me");
            } catch (_) {
                this.user = null;
            }
        },
        async logout() {
            try { await apiFetch("/accounts/logout", { method: "POST" }); } catch (_) {}
            this.user = null;
            window.location.href = "/login";
        },
    }));

    Alpine.data("dashboard", () => ({
        loading: true,
        error: "",
        signals: null,
        news: null,
        async init() {
            await Promise.all([this.loadSignals(), this.loadNews()]);
            this.loading = false;
        },
        async loadSignals() {
            try {
                this.signals = await apiFetch("/api/signals/current?pair=GBPUSD&interval=1h");
            } catch (e) {
                this.error = e.message;
            }
        },
        async loadNews() {
            try {
                this.news = await apiFetch("/api/news/digest?max_items=5");
            } catch (e) {
                // non-fatal; the dashboard still shows signals
                console.warn("news load failed:", e.message);
            }
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
        loading: true,
        error: "",
        signals: null,
        async init() {
            try {
                this.signals = await apiFetch("/api/signals/current?pair=GBPUSD&interval=1h");
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },
        fmtNum, fmtPct, toneForChange, toneForQuality,
    }));

    Alpine.data("newsPage", () => ({
        loading: true,
        error: "",
        digest: null,
        async init() {
            try {
                this.digest = await apiFetch("/api/news/digest");
            } catch (e) {
                this.error = e.message;
            } finally {
                this.loading = false;
            }
        },
    }));
});

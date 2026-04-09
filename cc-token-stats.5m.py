#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>

"""
cc-token-status — Claude Code usage dashboard in your menu bar.
https://github.com/echowonderfulworld/cc-token-status
"""

VERSION = "2.1.0"
REPO_URL = "https://raw.githubusercontent.com/echowonderfulworld/cc-token-status/main"

import json, os, glob, socket, subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────

CONFIG_FILE = Path.home() / ".config" / "cc-token-stats" / "config.json"
ICLOUD_SYNC_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "cc-token-stats"

DEFAULTS = {
    "claude_dir": str(Path.home() / ".claude"),
    "sync_repo": "", "sync_mode": "auto",
    "subscription": 0, "subscription_label": "",
    "language": "auto", "machine_labels": {},
    "menu_bar_icon": "sfSymbol=sparkles.rectangle.stack",
}

def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.is_file():
        try:
            with open(CONFIG_FILE) as f: cfg.update(json.load(f))
        except: pass
    for ek, ck in [("CC_STATS_CLAUDE_DIR","claude_dir"),("CC_STATS_SYNC_REPO","sync_repo"),("CC_STATS_LANG","language")]:
        if os.environ.get(ek): cfg[ck] = os.environ[ek]
    if os.environ.get("CC_STATS_SUBSCRIPTION"):
        try: cfg["subscription"] = float(os.environ["CC_STATS_SUBSCRIPTION"])
        except: pass
    if cfg["language"] == "auto":
        try:
            out = subprocess.check_output(["defaults","read",".GlobalPreferences","AppleLanguages"], stderr=subprocess.DEVNULL, text=True)
            cfg["language"] = "zh" if "zh" in out.lower() else "en"
        except: cfg["language"] = "en"
    return cfg

CFG = load_config()
ZH = CFG["language"] == "zh"
MACHINE = socket.gethostname().split(".")[0]
CLAUDE_DIR = os.path.expanduser(CFG["claude_dir"])

def resolve_sync():
    mode = CFG.get("sync_mode", "auto")
    if mode == "off": return None, None
    if mode in ("icloud","auto"):
        r = Path.home()/"Library"/"Mobile Documents"/"com~apple~CloudDocs"
        if r.is_dir(): return str(ICLOUD_SYNC_DIR), "icloud"
    if mode in ("custom","auto"):
        c = CFG.get("sync_repo","")
        if c:
            e = os.path.expanduser(c)
            if os.path.isdir(e) or os.path.isdir(os.path.dirname(e)): return e, "custom"
    return None, None

SYNC_DIR, SYNC_TYPE = resolve_sync()

# ─── Pricing / Formatting ────────────────────────────────────────

# Per-model pricing (USD per 1M tokens) — https://docs.anthropic.com/en/docs/about-claude/models
# Opus 4.5/4.6: $5/$25, cache_write $6.25(5m)/$10(1h), cache_read $0.50
# Opus 4.0/4.1: $15/$75 (legacy)
# Sonnet 4.5/4.6: $3/$15
# Haiku 4.5: $1/$5
PRICING = {
    "opus_new":  {"input": 5,    "output": 25, "cache_write": 10,    "cache_read": 0.50},
    "opus_old":  {"input": 15,   "output": 75, "cache_write": 18.75, "cache_read": 1.50},
    "sonnet":    {"input": 3,    "output": 15, "cache_write": 3.75,  "cache_read": 0.30},
    "haiku":     {"input": 1,    "output": 5,  "cache_write": 1.25,  "cache_read": 0.10},
}
MODEL_SHORT = {
    "claude-opus-4-6":"Opus 4.6","claude-opus-4-5-20250918":"Opus 4.5",
    "claude-sonnet-4-6":"Sonnet 4.6","claude-sonnet-4-5-20250929":"Sonnet 4.5",
    "claude-haiku-4-5-20251001":"Haiku 4.5",
}

def dw(s):
    return sum(2 if ord(c)>0x2E7F else 1 for c in s)

def tk(n):
    if ZH:
        if n>=1e8: return f"{n/1e8:.2f} 亿"
        if n>=1e4: return f"{n/1e4:.1f} 万"
    else:
        if n>=1e9: return f"{n/1e9:.2f}B"
        if n>=1e6: return f"{n/1e6:.1f}M"
        if n>=1e3: return f"{n/1e3:.1f}K"
    return f"{n:,}"

def fc(n):
    return f"${n:,.0f}" if n>=10000 else f"${n:,.2f}"

def tier(m):
    ml = m.lower()
    if "opus" in ml:
        # Opus 4.5+ uses new (cheaper) pricing
        if "4-5" in m or "4-6" in m or "4.5" in m or "4.6" in m:
            return "opus_new"
        return "opus_old"
    if "haiku" in ml: return "haiku"
    return "sonnet"

def mlabel(h):
    labels = CFG.get("machine_labels",{})
    if h in labels: return labels[h]
    hl = h.lower()
    if "mac" in hl and ("mini" in hl or "home" in hl): return "🏠 Home" if not ZH else "🏠 家里"
    if any(x in hl for x in ["office","work","corp"]): return "🏢 Office" if not ZH else "🏢 办公室"
    return f"💻 {h}"

def bar(val, maxval, width=12):
    """Render a mini bar chart using block characters."""
    if maxval <= 0: return " " * width
    filled = round(val / maxval * width)
    empty = "░" if DARK else "▁"
    return "█" * filled + empty * (width - filled)

# ─── Auto-update (once per day, silent) ──────────────────────────

UPDATE_CHECK_FILE = Path.home() / ".config" / "cc-token-stats" / ".last_update_check"

def auto_update():
    """Check for updates once per day. Downloads new version silently."""
    try:
        # Check at most once per day
        if UPDATE_CHECK_FILE.is_file():
            last = float(UPDATE_CHECK_FILE.read_text().strip())
            if datetime.now().timestamp() - last < 86400:  # 24h
                return
    except: pass

    try:
        import urllib.request
        # Fetch remote version line
        req = urllib.request.Request(f"{REPO_URL}/cc-token-stats.5m.py",
                                     headers={"Range": "bytes=0-500"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            head = resp.read(500).decode("utf-8", errors="ignore")
        # Parse VERSION from remote
        for line in head.splitlines():
            if line.startswith("VERSION"):
                remote_ver = line.split('"')[1]
                if remote_ver != VERSION:
                    # Download full file
                    plugin_path = None
                    try:
                        plugin_dir = subprocess.run(
                            ["defaults", "read", "com.ameba.SwiftBar", "PluginDirectory"],
                            capture_output=True, text=True, timeout=3
                        ).stdout.strip()
                        if plugin_dir:
                            plugin_path = os.path.join(plugin_dir, "cc-token-stats.5m.py")
                    except: pass
                    if not plugin_path:
                        plugin_path = os.path.join(
                            str(Path.home()), "Library", "Application Support",
                            "SwiftBar", "plugins", "cc-token-stats.5m.py")

                    urllib.request.urlretrieve(f"{REPO_URL}/cc-token-stats.5m.py", plugin_path)
                    os.chmod(plugin_path, 0o755)
                break

        # Record check time
        UPDATE_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        UPDATE_CHECK_FILE.write_text(str(datetime.now().timestamp()))
    except: pass

# ─── Usage API (official rate limits) ────────────────────────────

def get_oauth_token():
    """Read Claude Code OAuth token from macOS Keychain."""
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-g"],
            capture_output=True, text=True, timeout=5
        )
        # Extract password field from stderr (security outputs it there)
        for line in out.stderr.splitlines():
            if line.startswith("password: "):
                pw = line[len("password: "):]
                if pw.startswith('"') and pw.endswith('"'):
                    pw = pw[1:-1]
                creds = json.loads(pw)
                oauth = creds.get("claudeAiOauth", {})
                return oauth.get("accessToken"), oauth.get("subscriptionType"), oauth.get("rateLimitTier")
    except Exception:
        pass
    return None, None, None

def fetch_usage():
    """Fetch official plan usage from Anthropic API. Returns dict or None."""
    token, sub_type, tier = get_oauth_token()
    if not token:
        return None
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.anthropic.com/api/oauth/usage",
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-beta": "oauth-2025-04-20",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        data["_sub_type"] = sub_type
        data["_tier"] = tier
        return data
    except Exception:
        return None

USAGE_CACHE = Path.home() / ".config" / "cc-token-stats" / ".usage_cache.json"

def get_usage():
    """Get usage with local cache to avoid rate limits."""
    # Try cache first (valid for 4 minutes, plugin runs every 5)
    if USAGE_CACHE.is_file():
        try:
            cached = json.loads(USAGE_CACHE.read_text())
            age = datetime.now().timestamp() - cached.get("_ts", 0)
            if age < 240:  # 4 minutes
                return cached
        except Exception:
            pass
    # Fetch fresh
    data = fetch_usage()
    if data:
        data["_ts"] = datetime.now().timestamp()
        try:
            USAGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
            USAGE_CACHE.write_text(json.dumps(data))
        except Exception:
            pass
        return data
    # Fallback to stale cache
    if USAGE_CACHE.is_file():
        try: return json.loads(USAGE_CACHE.read_text())
        except: pass
    return None

# ─── Data ────────────────────────────────────────────────────────

def scan():
    base = os.path.join(CLAUDE_DIR, "projects")
    today_str = datetime.now().strftime("%Y-%m-%d")
    # 7-day date keys
    day_keys = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    now_dt = datetime.now()
    cutoff_5h = now_dt - timedelta(hours=5)
    cutoff_7d = now_dt - timedelta(days=7)

    s = {
        "machine": MACHINE, "sessions": 0,
        "inp": 0, "out": 0, "cw": 0, "cr": 0,
        "cost": 0.0, "d_min": None, "d_max": None,
        "models": {},
        # Today
        "today": {"tokens": 0, "cost": 0.0, "msgs": 0, "inp": 0, "out": 0, "cw": 0, "cr": 0, "models": {}},
        # Rolling windows
        "window_5h": {"tokens": 0, "cost": 0.0, "msgs": 0, "out": 0},
        "window_7d": {"tokens": 0, "cost": 0.0, "msgs": 0, "out": 0},
        # Daily (last 7 days)
        "daily": {d: {"tokens": 0, "cost": 0.0, "msgs": 0} for d in day_keys},
        # Hourly (24h)
        "hourly": defaultdict(int),
        # Per-project
        "projects": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0}),
    }

    if not os.path.isdir(base):
        return s

    for pd in glob.glob(os.path.join(base, "*")):
        if not os.path.isdir(pd): continue
        proj = os.path.basename(pd)
        # Extract readable project name
        parts = proj.replace("-", "/").split("/")
        proj_name = parts[-1] if parts else proj[:20]

        for jf in glob.glob(os.path.join(pd, "*.jsonl")):
            has = False
            try: fd = datetime.fromtimestamp(os.path.getmtime(jf)).strftime("%Y-%m-%d")
            except: fd = None
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            d = json.loads(line)
                            if d.get("type") != "assistant": continue
                            msg = d.get("message", {})
                            if not isinstance(msg, dict): continue
                            u = msg.get("usage")
                            if not u: continue
                            i, o, w, r = u.get("input_tokens", 0), u.get("output_tokens", 0), u.get("cache_creation_input_tokens", 0), u.get("cache_read_input_tokens", 0)
                            s["inp"] += i; s["out"] += o; s["cw"] += w; s["cr"] += r; has = True
                            total_t = i + o + w + r
                            m = msg.get("model", "")
                            p = PRICING.get(tier(m), PRICING["sonnet"])
                            mc = (i * p["input"] + o * p["output"] + w * p["cache_write"] + r * p["cache_read"]) / 1e6
                            s["cost"] += mc

                            # Model breakdown
                            if m and m != "<synthetic>":
                                if m not in s["models"]: s["models"][m] = {"msgs": 0, "tokens": 0, "cost": 0.0}
                                s["models"][m]["msgs"] += 1; s["models"][m]["tokens"] += total_t; s["models"][m]["cost"] += mc

                            # Per-message date
                            ts_str = d.get("timestamp", "")
                            msg_date = ts_str[:10] if ts_str and len(ts_str) >= 10 else None

                            # Today
                            if msg_date == today_str:
                                t = s["today"]
                                t["tokens"] += total_t; t["cost"] += mc; t["msgs"] += 1
                                t["inp"] += i; t["out"] += o; t["cw"] += w; t["cr"] += r
                                if m and m != "<synthetic>":
                                    if m not in t["models"]: t["models"][m] = {"msgs": 0, "cost": 0.0}
                                    t["models"][m]["msgs"] += 1; t["models"][m]["cost"] += mc

                            # Daily (last 7 days)
                            if msg_date and msg_date in s["daily"]:
                                dd = s["daily"][msg_date]
                                dd["tokens"] += total_t; dd["cost"] += mc; dd["msgs"] += 1

                            # Hourly
                            if ts_str and len(ts_str) >= 13:
                                try: s["hourly"][int(ts_str[11:13])] += 1
                                except: pass

                            # Rolling windows (5h / 7d)
                            if ts_str:
                                try:
                                    msg_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
                                    if msg_dt >= cutoff_5h:
                                        s["window_5h"]["tokens"] += total_t; s["window_5h"]["cost"] += mc
                                        s["window_5h"]["msgs"] += 1; s["window_5h"]["out"] += o
                                    if msg_dt >= cutoff_7d:
                                        s["window_7d"]["tokens"] += total_t; s["window_7d"]["cost"] += mc
                                        s["window_7d"]["msgs"] += 1; s["window_7d"]["out"] += o
                                except: pass

                            # Project
                            s["projects"][proj_name]["tokens"] += total_t
                            s["projects"][proj_name]["cost"] += mc
                            s["projects"][proj_name]["msgs"] += 1

                        except: pass
                if has:
                    s["sessions"] += 1
                    if fd:
                        if not s["d_min"] or fd < s["d_min"]: s["d_min"] = fd
                        if not s["d_max"] or fd > s["d_max"]: s["d_max"] = fd
            except: pass
    return s

def save_sync(st):
    if not SYNC_DIR: return
    d = os.path.join(SYNC_DIR, "machines", MACHINE)
    try:
        os.makedirs(d, exist_ok=True)
        mb = {m: {**v, "cost": round(v["cost"], 2)} for m, v in st.get("models", {}).items()}
        json.dump({"machine": MACHINE, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "session_count": st["sessions"], "input_tokens": st["inp"], "output_tokens": st["out"],
            "cache_write_tokens": st["cw"], "cache_read_tokens": st["cr"],
            "total_cost": round(st["cost"], 2), "date_range": {"min": st["d_min"], "max": st["d_max"]},
            "model_breakdown": mb}, open(os.path.join(d, "token-stats.json"), "w"), indent=2)
    except: pass

def recalc_remote_cost(data):
    """Recalculate remote machine cost using current pricing (not cached total_cost)."""
    total = 0.0
    mb = data.get("model_breakdown", {})
    if mb:
        # Has per-model breakdown — recalc from tokens
        inp = data.get("input_tokens", 0)
        out = data.get("output_tokens", 0)
        cw = data.get("cache_write_tokens", 0)
        cr = data.get("cache_read_tokens", 0)
        # Estimate per-model share by message ratio, apply correct pricing
        total_msgs = max(sum(v.get("msgs", 0) for v in mb.values()), 1)
        for model, mdata in mb.items():
            ratio = mdata.get("msgs", 0) / total_msgs
            p = PRICING.get(tier(model), PRICING["sonnet"])
            total += (inp * ratio * p["input"] + out * ratio * p["output"] +
                      cw * ratio * p["cache_write"] + cr * ratio * p["cache_read"]) / 1e6
        # Also recalc per-model costs
        for model, mdata in mb.items():
            ratio = mdata.get("msgs", 0) / total_msgs
            p = PRICING.get(tier(model), PRICING["sonnet"])
            mdata["cost"] = round((inp * ratio * p["input"] + out * ratio * p["output"] +
                                   cw * ratio * p["cache_write"] + cr * ratio * p["cache_read"]) / 1e6, 2)
    else:
        # Fallback: assume sonnet pricing
        inp = data.get("input_tokens", 0)
        out = data.get("output_tokens", 0)
        cw = data.get("cache_write_tokens", 0)
        cr = data.get("cache_read_tokens", 0)
        p = PRICING["sonnet"]
        total = (inp * p["input"] + out * p["output"] + cw * p["cache_write"] + cr * p["cache_read"]) / 1e6
    data["total_cost"] = round(total, 2)
    return data

def load_remotes():
    remotes = []
    if not SYNC_DIR: return remotes
    md = os.path.join(SYNC_DIR, "machines")
    if not os.path.isdir(md): return remotes
    for m in os.listdir(md):
        if m == MACHINE: continue
        sf = os.path.join(md, m, "token-stats.json")
        if os.path.isfile(sf):
            try: remotes.append(recalc_remote_cost(json.load(open(sf))))
            except: pass
    return remotes

# ─── Render ──────────────────────────────────────────────────────

# Styles — auto-detect dark/light mode
def _is_dark():
    try:
        r = subprocess.run(["defaults","read","-g","AppleInterfaceStyle"],
                           capture_output=True, text=True, timeout=3)
        return "dark" in r.stdout.lower()
    except: return True  # default to dark

DARK = _is_dark()

if DARK:
    H1   = "color=#4EC9B0 size=14"
    H2   = "color=#4EC9B0 size=13"
    ROW  = "color=#E0D8C8 size=13 font=Menlo"
    ROW2 = "color=#E0D8C8 size=12 font=Menlo"
    DIM  = "color=#9B9080 size=11 font=Menlo"
    DIM2 = "color=#9B9080 size=10 font=Menlo"
    META = "color=#6B6560 size=10"
    SEC  = "color=#7AAFCF size=13"
    SEC2 = "color=#7AAFCF size=12"
    MODL = "color=#8B8578 size=12 font=Menlo"
    BAR  = "color=#4EC9B0 size=11 font=Menlo"
    WARN = "color=#E8A838 size=12"
else:
    # Light mode: NO color attr → SwiftBar uses system native black text
    # Only accent items get explicit color (green title, blue links)
    H1   = "color=#0B6B50 size=14"
    H2   = "color=#0B6B50 size=13"
    ROW  = "size=13 font=Menlo"
    ROW2 = "size=12 font=Menlo"
    DIM  = "size=12 font=Menlo"
    DIM2 = "size=11 font=Menlo"
    META = "size=11"
    SEC  = "color=#14507A size=13"
    SEC2 = "color=#14507A size=12"
    MODL = "size=12 font=Menlo"
    BAR  = "color=#0B6B50 size=12 font=Menlo"
    WARN = "color=#A05A10 size=12"

def main():
    auto_update()
    local = scan()
    save_sync(local)
    remotes = load_remotes()

    # Build machine list
    machines = [{
        "label": mlabel(MACHINE), "name": MACHINE, "sessions": local["sessions"],
        "inp": local["inp"], "out": local["out"], "cw": local["cw"], "cr": local["cr"],
        "cost": local["cost"], "d_min": local["d_min"], "d_max": local["d_max"],
        "local": True, "at": None, "models": local.get("models", {}),
    }]
    for r in remotes:
        dr = r.get("date_range", {})
        machines.append({
            "label": mlabel(r.get("machine", "?")), "name": r.get("machine", "?"),
            "sessions": r.get("session_count", 0),
            "inp": r.get("input_tokens", 0), "out": r.get("output_tokens", 0),
            "cw": r.get("cache_write_tokens", 0), "cr": r.get("cache_read_tokens", 0),
            "cost": r.get("total_cost", 0), "d_min": dr.get("min"), "d_max": dr.get("max"),
            "local": False, "at": r.get("generated_at"), "models": r.get("model_breakdown", {}),
        })

    ti = sum(m["inp"] for m in machines); to = sum(m["out"] for m in machines)
    tw = sum(m["cw"] for m in machines); tr = sum(m["cr"] for m in machines)
    tc = sum(m["cost"] for m in machines); ts = sum(m["sessions"] for m in machines)
    ta = ti + to + tw + tr
    now = datetime.now().strftime("%H:%M:%S")
    icon = CFG.get("menu_bar_icon", "sfSymbol=sparkles.rectangle.stack")
    today = local["today"]
    machine_count = len(machines)

    daily = local["daily"]
    week_total_cost = sum(v["cost"] for v in daily.values())
    week_total_msgs = sum(v["msgs"] for v in daily.values())

    # Aggregate models across all machines
    all_models = {}
    for m in machines:
        for model, data in m.get("models", {}).items():
            if model not in all_models:
                all_models[model] = {"msgs": 0, "tokens": 0, "cost": 0.0}
            all_models[model]["msgs"] += data["msgs"]
            all_models[model]["tokens"] += data["tokens"]
            all_models[model]["cost"] += data["cost"]
    total_model_msgs = max(sum(v["msgs"] for v in all_models.values()), 1)

    # ─── Menu bar line ───
    if today["msgs"] > 0:
        print(f"CC: {'今日' if ZH else 'Today'} {fc(today['cost'])} | {icon}")
    else:
        print(f"CC: {tk(ta)} | {icon}")
    print("---")

    # ═══════════════════════════════════════════════════════════════
    # OVERVIEW — 一级菜单，一眼看到全貌
    # ═══════════════════════════════════════════════════════════════
    title = "Claude Code 用量看板" if ZH else "Claude Code Usage Dashboard"
    print(f"{title} | {H1}")
    print("---")

    # ── Key numbers: pure ASCII labels, values pushed to right edge ──
    cost_s = fc(tc); sess_s = f"{ts:,}"; tok_s = tk(ta)
    W = 36  # total line display width — pushes values to right edge of panel
    def rj(label, val):
        pad = W - len(label) - dw(val)
        return f"{label}{' ' * max(pad, 1)}{val}"
    print(f"{rj('Cost:', cost_s)} | {ROW}")
    print(f"{rj('Sessions:', sess_s)} | {ROW}")
    print(f"{rj('Tokens:', tok_s)} | {ROW}")

    # ── Official usage limits (top-level, most important) ──
    usage = get_usage()
    if usage:
        def _reset_label(reset_str):
            if not reset_str: return ""
            try:
                # Parse as timezone-aware, convert to local
                rt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
                now_aware = datetime.now().astimezone()
                diff = rt - now_aware
                secs = diff.total_seconds()
                if secs <= 0: return "now" if not ZH else "即将"
                hrs = int(secs // 3600); mins = int((secs % 3600) // 60)
                if hrs >= 48: return f"{hrs // 24}d" if not ZH else f"{hrs // 24}天"
                if hrs >= 24: return f"1d{hrs-24}h" if not ZH else f"1天{hrs-24}时"
                if hrs > 0: return f"{hrs}h{mins}m" if not ZH else f"{hrs}时{mins}分"
                return f"{mins}m" if not ZH else f"{mins}分"
            except: return ""

        def _reset_time_local(reset_str):
            try:
                rt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
                return rt.astimezone().strftime("%m-%d %H:%M")
            except: return ""

        def _gauge(pct):
            p = min(max(pct, 0), 100)
            filled = round(p / 100 * 10)
            return "▰" * filled + "▱" * (10 - filled)

        # Each gauge gets a distinct color
        if DARK:
            LINE_COLORS = ["#4EC9B0", "#7AAFCF", "#E0D8C8", "#E8A838"]
        else:
            LINE_COLORS = ["#0B6B50", "#14507A", None, "#A05A10"]  # None = system default
        _color_idx = [0]

        def _danger_color(pct):
            """Override color when usage is critical."""
            if pct >= 80: return "#D03020" if not DARK else "#E85838"
            if pct >= 60: return "#C07820" if not DARK else "#E8A838"
            return None

        LW = 8
        def _usage_line(label, obj):
            if not obj or obj.get("utilization") is None: return
            p = obj["utilization"]
            rst = _reset_label(obj.get("resets_at"))
            rst_s = f"↻{rst}" if rst else ""
            padded = f"{label:<{LW}}"
            pct_s = f"{p:.0f}%"
            # Fixed-width: pct 4 chars, reset 8 chars → always aligned
            col = _danger_color(p) or LINE_COLORS[_color_idx[0] % len(LINE_COLORS)]
            _color_idx[0] += 1
            col_attr = f"color={col} " if col else ""
            print(f"{padded}{_gauge(p)}  {pct_s:>4}  {rst_s:<8} | {col_attr}size=13 font=Menlo")
            # Submenu: reset time
            rt_local = _reset_time_local(obj.get("resets_at", ""))
            if rt_local:
                if ZH:
                    print(f"--重置：{rt_local} | {DIM}")
                else:
                    print(f"--Resets: {rt_local} | {DIM}")

        print("---")
        _usage_line("Session", usage.get("five_hour"))
        _usage_line("Weekly ", usage.get("seven_day"))
        ss = usage.get("seven_day_sonnet")
        if ss and ss.get("utilization") is not None:
            _usage_line("Sonnet ", ss)
        so = usage.get("seven_day_opus")
        if so and so.get("utilization") is not None:
            _usage_line("Opus   ", so)

    # ── Subscription ROI ──
    sub = CFG.get("subscription", 0)
    if sub > 0:
        lbl = CFG.get("subscription_label", "")
        prefix = f"{lbl} " if lbl else ""
        savings = tc - sub
        multiplier = tc / sub if sub > 0 else 0
        print("---")
        if ZH:
            print(f"💰 {prefix}${sub:.0f}/月 → 已节省 {fc(savings)} ({multiplier:.0f}x) | {SEC}")
        else:
            print(f"💰 {prefix}${sub:.0f}/mo → saved {fc(savings)} ({multiplier:.0f}x) | {SEC}")
        # Submenu: details
        if ZH:
            print(f"--等价 API 费用：{fc(tc)} | {ROW2}")
        else:
            print(f"--API equivalent: {fc(tc)} | {ROW2}")
        if week_total_cost > 0:
            daily_avg = week_total_cost / 7
            monthly_proj = daily_avg * 30
            if ZH:
                print(f"--日均：{fc(daily_avg)} · 月估：{fc(monthly_proj)} | {DIM}")
            else:
                print(f"--Daily: {fc(daily_avg)} · Monthly: {fc(monthly_proj)} | {DIM}")

    print("---")

    # ── Token breakdown ──
    if ZH:
        print(f"输入：{tk(ti):>10}   输出：{tk(to):>10} | {DIM}")
        print(f"缓存写：{tk(tw):>8}   缓存读：{tk(tr):>8} | {DIM}")
    else:
        print(f"Input: {tk(ti):>10}   Output: {tk(to):>10} | {DIM}")
        print(f"Cache W: {tk(tw):>8}   Cache R: {tk(tr):>8} | {DIM}")

    print("---")

    # ── Today (if active) ──
    if today["msgs"] > 0:
        if ZH:
            print(f"⚡ 今日：{fc(today['cost'])} · {tk(today['tokens'])} · {today['msgs']} 条 | {SEC}")
        else:
            print(f"⚡ Today: {fc(today['cost'])} · {tk(today['tokens'])} · {today['msgs']} msgs | {SEC}")
        # Submenu: today details
        if ZH:
            print(f"--输入: {tk(today['inp'])}   输出: {tk(today['out'])} | {DIM}")
            print(f"--缓存写: {tk(today['cw'])}   缓存读: {tk(today['cr'])} | {DIM}")
        else:
            print(f"--Input: {tk(today['inp'])}   Output: {tk(today['out'])} | {DIM}")
            print(f"--Cache W: {tk(today['cw'])}   Cache R: {tk(today['cr'])} | {DIM}")
        if today["models"]:
            print("-----")
            tm_total = max(sum(v["msgs"] for v in today["models"].values()), 1)
            for model, data in sorted(today["models"].items(), key=lambda x: -x[1]["cost"]):
                short = MODEL_SHORT.get(model, model)
                pct = data["msgs"] / tm_total * 100
                print(f"--{short}: {data['msgs']:,} ({pct:.0f}%) {fc(data['cost'])} | {MODL}")

    # ── Machines — top level summary, details in submenu ──
    for m in machines:
        ma = m["inp"] + m["out"] + m["cw"] + m["cr"]
        if m["local"]:
            suf = " (实时)" if ZH else " (live)"
        else:
            suf = (f" (同步 {m['at'][5:16]})" if ZH else f" (synced {m['at'][5:16]})") if m.get("at") else ""
        print(f"{m['label']}{suf}  {fc(m['cost'])} | {SEC}")

        # Submenu: machine details
        print(f"--Token: {tk(ma)} · Sessions: {m['sessions']} | {ROW2}")
        if ZH:
            print(f"--输入: {tk(m['inp'])}   输出: {tk(m['out'])} | {DIM}")
            print(f"--缓存写: {tk(m['cw'])}   缓存读: {tk(m['cr'])} | {DIM}")
        else:
            print(f"--Input: {tk(m['inp'])}   Output: {tk(m['out'])} | {DIM}")
            print(f"--Cache W: {tk(m['cw'])}   Cache R: {tk(m['cr'])} | {DIM}")
        mb = m.get("models", {})
        if mb:
            print("-----")
            mtotal = max(sum(v["msgs"] for v in mb.values()), 1)
            for model, data in sorted(mb.items(), key=lambda x: -x[1]["cost"]):
                short = MODEL_SHORT.get(model, model)
                pct = data["msgs"] / mtotal * 100
                print(f"--{short}: {pct:.0f}% · {fc(data['cost'])} | {MODL}")
        dr = f"{m['d_min'][5:]} ~ {m['d_max'][5:]}" if m["d_min"] and m["d_max"] else "N/A"
        print(f"--{dr} | {META}")

    print("---")

    # ═══════════════════════════════════════════════════════════════
    # DRILL-DOWN SECTIONS — 子菜单，按需展开
    # ═══════════════════════════════════════════════════════════════

    # ── 7-Day Trend ──
    max_cost = max((v["cost"] for v in daily.values()), default=1) or 1
    trend_title = "📈 最近 7 天" if ZH else "📈 Last 7 Days"
    print(f"{trend_title} | {H2}")
    for date, data in daily.items():
        dd = date[5:]
        b = bar(data["cost"], max_cost, 10)
        if data["msgs"] > 0:
            print(f"--{dd}  {fc(data['cost']):>8}  {b} | {ROW2}")
            print(f"----{tk(data['tokens'])} tokens · {data['msgs']} msgs | {DIM}")
        else:
            empty_bar = '░' * 10 if DARK else '▁' * 10
            print(f"--{dd}  {'—':>8}  {empty_bar} | {DIM}")
    print("-----")
    if ZH:
        print(f"--合计: {fc(week_total_cost)} · {week_total_msgs} 条 | {DIM}")
    else:
        print(f"--Total: {fc(week_total_cost)} · {week_total_msgs} msgs | {DIM}")

    # ── Models ──
    model_title = "🧩 模型分布" if ZH else "🧩 Models"
    print(f"{model_title} | {H2}")
    for model, data in sorted(all_models.items(), key=lambda x: -x[1]["cost"]):
        short = MODEL_SHORT.get(model, model)
        pct = data["msgs"] / total_model_msgs * 100
        b = bar(data["msgs"], total_model_msgs, 8)
        print(f"--{short} {pct:.0f}% · {fc(data['cost'])} | {ROW2}")
        if ZH:
            print(f"----{data['msgs']:,} 条 · {tk(data['tokens'])} tokens | {DIM}")
        else:
            print(f"----{data['msgs']:,} msgs · {tk(data['tokens'])} tokens | {DIM}")
        print(f"----{b} | {BAR}")

    # ── Hourly Activity ──
    hourly = local["hourly"]
    if hourly:
        hour_title = "⏰ 活跃时段" if ZH else "⏰ Active Hours"
        print(f"{hour_title} | {H2}")
        max_h = max(hourly.values()) if hourly else 1
        block_ranges = [
            ("🌅 早上 6-12" if ZH else "🌅 Morning 6-12", range(6, 12)),
            ("☀️ 下午 12-18" if ZH else "☀️ Afternoon 12-18", range(12, 18)),
            ("🌙 晚上 18-24" if ZH else "🌙 Evening 18-24", range(18, 24)),
            ("🌑 凌晨 0-6" if ZH else "🌑 Night 0-6", range(0, 6)),
        ]
        for label, hours in block_ranges:
            block_count = sum(hourly.get(h, 0) for h in hours)
            if block_count == 0: continue
            cells = ""
            for h in hours:
                c = hourly.get(h, 0)
                if c == 0: cells += "░" if DARK else "▁"
                elif c < max_h * 0.25: cells += "▒" if DARK else "▃"
                elif c < max_h * 0.6: cells += "▓" if DARK else "▅"
                else: cells += "█"
            msgs_label = "条" if ZH else "msgs"
            print(f"--{label}  {cells}  {block_count} {msgs_label} | {ROW2}")
            for h in hours:
                c = hourly.get(h, 0)
                if c > 0:
                    print(f"----{h:02d}:00  {bar(c, max_h, 8)}  {c:,} | {DIM}")

    # ── Top Projects ──
    projects = dict(local["projects"])
    if projects:
        proj_title = "📁 项目排行" if ZH else "📁 Top Projects"
        print(f"{proj_title} | {H2}")
        top = sorted(projects.items(), key=lambda x: -x[1]["cost"])[:8]
        max_proj_cost = top[0][1]["cost"] if top else 1
        for name, data in top:
            short_name = name[:18] + "…" if len(name) > 18 else name
            b = bar(data["cost"], max_proj_cost, 8)
            print(f"--{short_name}  {fc(data['cost'])} | {ROW2}")
            print(f"----{tk(data['tokens'])} · {data['msgs']} msgs  {b} | {DIM}")

    # ═══════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════
    print("---")
    dmin = min((m["d_min"] for m in machines if m["d_min"]), default="N/A")
    dmax = max((m["d_max"] for m in machines if m["d_max"]), default="N/A")
    rng = f"{dmin[5:]} ~ {dmax[5:]}" if dmin != "N/A" else "N/A"
    sync_str = {"icloud": "iCloud", "custom": "Custom"}.get(SYNC_TYPE, "")
    parts = [rng, f"{machine_count}{'台' if ZH else ' machines'}"]
    if sync_str: parts.append(sync_str)
    parts.append(now)
    print(f"{' · '.join(parts)} | {META}")

    print("---")
    print("Refresh | refresh=true")
    quit_label = "退出 SwiftBar" if ZH else "Quit SwiftBar"
    print(f"{quit_label} | bash='osascript' param1='-e' param2='quit app \"SwiftBar\"' terminal=false")

if __name__ == "__main__":
    main()

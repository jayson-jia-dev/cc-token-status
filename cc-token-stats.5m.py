#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>

"""
cc-token-status — Claude Code usage dashboard in your menu bar.
https://github.com/jayson-jia-dev/cc-token-status
"""

VERSION = "2.1.0"
REPO_URL = "https://raw.githubusercontent.com/jayson-jia-dev/cc-token-status/main"

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
    "notifications": True,
}
NOTIFY_STATE_FILE = Path.home() / ".config" / "cc-token-stats" / ".notify_state.json"

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
            langs = [l.strip().strip('"').strip('",') for l in out.split("\n") if l.strip() and l.strip() not in ("(", ")")]
            if langs:
                fl = langs[0].lower().split("-")[0]  # "en-CN" → "en", "zh-Hans-CN" → "zh"
                supported = {"en","zh","es","fr","pt","de","ru","ja","ko","hi","ar"}
                cfg["language"] = fl if fl in supported else "en"
            else:
                cfg["language"] = "en"
        except: cfg["language"] = "en"
    return cfg

CFG = load_config()
LANG = CFG["language"]
ZH = LANG == "zh"  # kept for backward compat
MACHINE = socket.gethostname().split(".")[0]

# ─── i18n: 10 languages covering 95%+ world population ─────────
STRINGS = {
    "title":       {"en":"Claude Code Usage Dashboard","zh":"Claude Code 用量看板","es":"Panel de uso de Claude Code","fr":"Tableau de bord Claude Code","pt":"Painel de uso Claude Code","de":"Claude Code Nutzungs-Dashboard","ru":"Панель Claude Code","ja":"Claude Code 使用状況","ko":"Claude Code 사용 현황","hi":"Claude Code उपयोग डैशबोर्ड","ar":"لوحة استخدام Claude Code"},
    "today":       {"en":"Today","zh":"今日","es":"Hoy","fr":"Aujourd'hui","pt":"Hoje","de":"Heute","ru":"Сегодня","ja":"今日","ko":"오늘","hi":"आज","ar":"اليوم"},
    "live":        {"en":"live","zh":"实时","es":"en vivo","fr":"en direct","pt":"ao vivo","de":"live","ru":"живой","ja":"ライブ","ko":"실시간","hi":"लाइव","ar":"مباشر"},
    "synced":      {"en":"synced","zh":"同步","es":"sincronizado","fr":"synchronisé","pt":"sincronizado","de":"synchronisiert","ru":"синхр.","ja":"同期","ko":"동기화","hi":"सिंक","ar":"متزامن"},
    "daily":       {"en":"Daily Details","zh":"每日明细","es":"Detalles diarios","fr":"Détails quotidiens","pt":"Detalhes diários","de":"Tagesdetails","ru":"По дням","ja":"日別詳細","ko":"일별 상세","hi":"दैनिक विवरण","ar":"التفاصيل اليومية"},
    "older":       {"en":"Older","zh":"更早","es":"Anteriores","fr":"Plus ancien","pt":"Anteriores","de":"Älter","ru":"Ранее","ja":"過去","ko":"이전","hi":"पुराने","ar":"أقدم"},
    "total":       {"en":"Total","zh":"合计","es":"Total","fr":"Total","pt":"Total","de":"Gesamt","ru":"Итого","ja":"合計","ko":"합계","hi":"कुल","ar":"المجموع"},
    "models":      {"en":"Models","zh":"模型分布","es":"Modelos","fr":"Modèles","pt":"Modelos","de":"Modelle","ru":"Модели","ja":"モデル","ko":"모델","hi":"मॉडल","ar":"النماذج"},
    "hours":       {"en":"Active Hours","zh":"活跃时段","es":"Horas activas","fr":"Heures actives","pt":"Horas ativas","de":"Aktive Stunden","ru":"Активность","ja":"活動時間","ko":"활동 시간","hi":"सक्रिय समय","ar":"ساعات النشاط"},
    "projects":    {"en":"Top Projects","zh":"项目排行","es":"Proyectos","fr":"Projets","pt":"Projetos","de":"Projekte","ru":"Проекты","ja":"プロジェクト","ko":"프로젝트","hi":"परियोजनाएं","ar":"المشاريع"},
    "saved":       {"en":"saved","zh":"省","es":"ahorrado","fr":"économisé","pt":"economizado","de":"gespart","ru":"экономия","ja":"節約","ko":"절약","hi":"बचत","ar":"وفر"},
    "msgs":        {"en":"msgs","zh":"条","es":"msgs","fr":"msgs","pt":"msgs","de":"Nachr.","ru":"сообщ.","ja":"件","ko":"건","hi":"संदेश","ar":"رسالة"},
    "refresh":     {"en":"Refresh","zh":"Refresh","es":"Actualizar","fr":"Actualiser","pt":"Atualizar","de":"Aktualisieren","ru":"Обновить","ja":"更新","ko":"새로고침","hi":"रिफ्रेश","ar":"تحديث"},
    "quit":        {"en":"Quit SwiftBar","zh":"退出 SwiftBar","es":"Salir de SwiftBar","fr":"Quitter SwiftBar","pt":"Sair do SwiftBar","de":"SwiftBar beenden","ru":"Выйти","ja":"SwiftBar 終了","ko":"SwiftBar 종료","hi":"SwiftBar बंद करें","ar":"إنهاء SwiftBar"},
    "notify":      {"en":"Notifications","zh":"通知提醒","es":"Notificaciones","fr":"Notifications","pt":"Notificações","de":"Benachrichtigungen","ru":"Уведомления","ja":"通知","ko":"알림","hi":"सूचनाएं","ar":"الإشعارات"},
    "login":       {"en":"Launch at Login","zh":"开机自启","es":"Iniciar con el sistema","fr":"Lancer au démarrage","pt":"Iniciar com o sistema","de":"Beim Login starten","ru":"Автозапуск","ja":"ログイン時に起動","ko":"로그인 시 실행","hi":"लॉगिन पर लॉन्च","ar":"تشغيل عند الدخول"},
    "subscription":{"en":"Subscription","zh":"订阅方案","es":"Suscripción","fr":"Abonnement","pt":"Assinatura","de":"Abonnement","ru":"Подписка","ja":"サブスクリプション","ko":"구독","hi":"सदस्यता","ar":"الاشتراك"},
    "limit_warn":  {"en":"Approaching usage limit","zh":"用量接近上限","es":"Acercándose al límite","fr":"Proche de la limite","pt":"Aproximando do limite","de":"Limit fast erreicht","ru":"Приближение к лимиту","ja":"上限に近づいています","ko":"한도에 가까워지고 있습니다","hi":"सीमा के करीब पहुँच रहे हैं","ar":"اقتراب من الحد"},
    "limit_crit":  {"en":"Rate limit imminent!","zh":"即将限速！","es":"¡Límite inminente!","fr":"Limite imminente !","pt":"Limite iminente!","de":"Limit erreicht!","ru":"Скоро лимит!","ja":"制限間近！","ko":"제한 임박!","hi":"सीमा निकट!","ar":"!الحد وشيك"},
    "am":          {"en":"AM","zh":"早上","es":"Mañana","fr":"Matin","pt":"Manhã","de":"Morgen","ru":"Утро","ja":"午前","ko":"오전","hi":"सुबह","ar":"صباحاً"},
    "pm":          {"en":"PM","zh":"下午","es":"Tarde","fr":"Après-midi","pt":"Tarde","de":"Nachmittag","ru":"День","ja":"午後","ko":"오후","hi":"दोपहर","ar":"ظهراً"},
    "eve":         {"en":"Eve","zh":"晚上","es":"Noche","fr":"Soir","pt":"Noite","de":"Abend","ru":"Вечер","ja":"夜","ko":"저녁","hi":"शाम","ar":"مساءً"},
    "late":        {"en":"Late","zh":"凌晨","es":"Madrugada","fr":"Nuit","pt":"Madrugada","de":"Nacht","ru":"Ночь","ja":"深夜","ko":"심야","hi":"रात","ar":"متأخر"},
    "reset":       {"en":"Resets","zh":"重置","es":"Reinicia","fr":"Réinit.","pt":"Reinicia","de":"Reset","ru":"Сброс","ja":"リセット","ko":"리셋","hi":"रीसेट","ar":"إعادة"},
    "api_equiv":   {"en":"API equiv","zh":"等价 API","es":"Equiv. API","fr":"Equiv. API","pt":"Equiv. API","de":"API Äquiv.","ru":"API экв.","ja":"API相当","ko":"API 환산","hi":"API समकक्ष","ar":"معادل API"},
}

def t(key):
    """Get translated string for current language."""
    s = STRINGS.get(key, {})
    return s.get(LANG, s.get("en", key))
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
# Using 1h cache write prices (Claude Code uses 1h cache ~90% of the time)
# Opus 4.0/4.1: $15/$75 (legacy)
# Sonnet 4.5/4.6: $3/$15
# Haiku 4.5: $1/$5
PRICING = {
    "opus_new":  {"input": 5,    "output": 25, "cache_write": 10,    "cache_read": 0.50},
    "opus_old":  {"input": 15,   "output": 75, "cache_write": 18.75, "cache_read": 1.50},
    "sonnet":    {"input": 3,    "output": 15, "cache_write": 6,     "cache_read": 0.30},
    "haiku":     {"input": 1,    "output": 5,  "cache_write": 2,     "cache_read": 0.10},
}
MODEL_SHORT = {
    "claude-opus-4-6":"Opus 4.6","claude-opus-4-5-20250918":"Opus 4.5",
    "claude-sonnet-4-6":"Sonnet 4.6","claude-sonnet-4-5-20250929":"Sonnet 4.5",
    "claude-haiku-4-5-20251001":"Haiku 4.5",
}

def dw(s):
    return sum(2 if ord(c)>0x2E7F else 1 for c in s)

def tk(n):
    if LANG == "zh":
        if n>=1e8: return f"{n/1e8:.2f} 亿"
        if n>=1e4: return f"{n/1e4:.1f} 万"
    elif LANG == "ja":
        if n>=1e8: return f"{n/1e8:.2f} 億"
        if n>=1e4: return f"{n/1e4:.1f} 万"
    elif LANG == "ko":
        if n>=1e8: return f"{n/1e8:.2f} 억"
        if n>=1e4: return f"{n/1e4:.1f} 만"
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
    # Truncate long hostnames
    return h[:16] + "…" if len(h) > 16 else h

def bar(val, maxval, width=12):
    """Render a mini bar chart — ▰▱ works in both dark and light mode."""
    if maxval <= 0: return "▱" * width
    filled = round(val / maxval * width)
    return "▰" * filled + "▱" * (width - filled)

# ─── Notifications ───────────────────────────────────────────────

def check_and_notify(usage):
    """Send macOS notification when limits cross 80% or 95%. Once per threshold per reset cycle."""
    if not CFG.get("notifications", True) or not usage:
        return
    # Load state
    state = {}
    try:
        if NOTIFY_STATE_FILE.is_file():
            state = json.loads(NOTIFY_STATE_FILE.read_text())
    except: pass

    thresholds = [80, 95]
    checks = [
        ("Session", "five_hour"),
        ("Weekly", "seven_day"),
    ]
    changed = False
    for name, key in checks:
        obj = usage.get(key)
        if not obj or obj.get("utilization") is None: continue
        util = obj["utilization"]
        reset = obj.get("resets_at", "")
        for t in thresholds:
            state_key = f"{key}_{t}_{reset}"
            if util >= t and state_key not in state:
                # Send notification
                if t >= 95:
                    title = f"⛔ {name} {util:.0f}%"
                    msg = t("limit_crit")
                else:
                    title = f"⚠️ {name} {util:.0f}%"
                    msg = t("limit_warn")
                try:
                    subprocess.run([
                        "osascript", "-e",
                        f'display notification "{msg}" with title "{title}" subtitle "cc-token-status"'
                    ], timeout=5)
                except: pass
                state[state_key] = datetime.now().isoformat()
                changed = True

    # Cleanup old entries and save
    if changed:
        # Keep only entries from current reset cycles
        try:
            NOTIFY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            NOTIFY_STATE_FILE.write_text(json.dumps(state))
            NOTIFY_STATE_FILE.chmod(0o600)
        except: pass

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

                    # Atomic update: download to temp file, then rename
                    tmp_path = plugin_path + ".tmp"
                    urllib.request.urlretrieve(f"{REPO_URL}/cc-token-stats.5m.py", tmp_path)
                    os.chmod(tmp_path, 0o755)
                    os.rename(tmp_path, plugin_path)  # atomic on same filesystem
                break

        # Record check time
        UPDATE_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        UPDATE_CHECK_FILE.write_text(str(datetime.now().timestamp()))
        UPDATE_CHECK_FILE.chmod(0o600)
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
            USAGE_CACHE.chmod(0o600)  # protect cached OAuth data
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
        # Daily (ALL dates, collected dynamically)
        "daily": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0}),
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

                            # Daily (all dates) + date range from message timestamps
                            if msg_date:
                                dd = s["daily"][msg_date]
                                dd["tokens"] += total_t; dd["cost"] += mc; dd["msgs"] += 1
                                if not s["d_min"] or msg_date < s["d_min"]: s["d_min"] = msg_date
                                if not s["d_max"] or msg_date > s["d_max"]: s["d_max"] = msg_date

                            # Hourly (convert to local timezone)
                            if ts_str:
                                try:
                                    local_h = datetime.fromisoformat(ts_str.replace("Z","+00:00")).astimezone().hour
                                    s["hourly"][local_h] += 1
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

# ── Color System ──
# Brand: teal green · Info: blue · Warn: amber · Danger: red
# Light mode: all colors must have hue saturation (pure gray/black renders transparent on frosted glass)

if DARK:
    # ── Dark mode: soft, warm tones on dark background ──
    H1   = "color=#5CC6A7 size=14"                # teal — title/section headers
    H2   = "color=#5CC6A7 size=13"
    ROW  = "color=#D4CDC0 size=13 font=Menlo"     # warm white — primary data
    ROW2 = "color=#D4CDC0 size=12 font=Menlo"
    DIM  = "color=#9E9589 size=11 font=Menlo"     # warm gray — secondary info
    DIM2 = "color=#9E9589 size=10 font=Menlo"
    META = "color=#6B6560 size=10"                 # muted — footer/timestamps
    SEC  = "color=#6BA4C9 size=13"                 # soft blue — interactive items
    SEC2 = "color=#6BA4C9 size=12"
    MODL = "color=#9E9589 size=12 font=Menlo"     # warm gray — model details
    BAR  = "color=#5CC6A7 size=11 font=Menlo"     # teal — bar charts
    WARN = "color=#E8A838 size=12"                 # amber — warnings
else:
    # ── Light mode: dark saturated tones (avoid pure gray → SwiftBar makes it transparent) ──
    H1   = "color=#0E1018 size=14"                # near-black with subtle blue tint — title
    H2   = "color=#0E1018 size=13"
    ROW  = "color=#1C2030 size=13 font=Menlo"     # dark navy — primary data (reads as near-black)
    ROW2 = "color=#1C2030 size=12 font=Menlo"
    DIM  = "color=#2C3040 size=12 font=Menlo"     # navy — secondary info
    DIM2 = "color=#2C3040 size=11 font=Menlo"
    META = "color=#3C4050 size=11"                 # slate — footer
    SEC  = "color=#1B5A85 size=13"                 # deep blue — interactive items
    SEC2 = "color=#1B5A85 size=12"
    MODL = "color=#2C3040 size=12 font=Menlo"     # navy — model details
    BAR  = "color=#1A5C4C size=12 font=Menlo"     # rich dark teal — bar charts
    WARN = "color=#B86E1A size=12"                 # dark amber — warnings

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
    now = datetime.now().strftime("%H:%M")
    icon = CFG.get("menu_bar_icon", "sfSymbol=sparkles.rectangle.stack")
    today = local["today"]
    machine_count = len(machines)

    daily = dict(local["daily"])  # convert from defaultdict
    # Sort by date
    daily_sorted = sorted(daily.items(), key=lambda x: x[0])
    # Last 7 days for quick stats
    last_7d = [(d, v) for d, v in daily_sorted if d >= (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")]
    week_total_cost = sum(v["cost"] for _, v in last_7d)
    week_total_msgs = sum(v["msgs"] for _, v in last_7d)

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
    usage = get_usage()

    # Get limits for panel display
    _5h_util = 0; _7d_util = 0
    if usage:
        _fh = usage.get("five_hour")
        if _fh and _fh.get("utilization") is not None: _5h_util = _fh["utilization"]
        _sd = usage.get("seven_day")
        if _sd and _sd.get("utilization") is not None: _7d_util = _sd["utilization"]

    print("CC")
    print("---")

    # ═══════════════════════════════════════════════════════════════
    # LAYOUT: Limits → Today → Overview → ROI → Details → Machines
    # ═══════════════════════════════════════════════════════════════
    title = t("title")
    print(f"{title} | {H1}")

    W = 30  # total line display width for aligned rows
    def rj(label, val):
        pad = W - len(label) - dw(val)
        return f"{label}{' ' * max(pad, 1)}{val}"

    # ═══ 1. LIMITS (most urgent) ═══
    # usage already fetched above for menu bar line
    check_and_notify(usage)
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
            LINE_COLORS = ["#5CC6A7", "#E07850", "#6BA4C9", "#D4CDC0"]   # teal, coral, blue, warm white
        else:
            LINE_COLORS = ["#1A5C4C", "#A04030", "#1B5A85", "#2C3040"]   # rich teal, deep coral, deep blue, navy
        _color_idx = [0]

        def _danger_color(pct):
            """Override color when usage is critical."""
            if pct >= 80: return "#C03020" if not DARK else "#E85838"
            if pct >= 60: return "#B86E1A" if not DARK else "#E8A838"
            return None

        LW = 8

        def _reset_short(reset_str):
            """Short reset label — ASCII only for uniform monospace width."""
            if not reset_str: return ""
            try:
                rt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
                now_aware = datetime.now().astimezone()
                secs = (rt - now_aware).total_seconds()
                if secs <= 0: return "now"
                hrs = int(secs // 3600); mins = int((secs % 3600) // 60)
                if hrs >= 48: return f"{hrs // 24}d"
                if hrs >= 24: return f"1d{hrs-24}h"
                # Use fixed-length format: "Xh" or "XhYm" or "Xm"
                if hrs > 0 and mins > 0: return f"{hrs}h{mins}m"
                if hrs > 0: return f"{hrs}h"
                return f"{mins}m"
            except: return ""

        gauge_items = [
            ("Session", usage.get("five_hour")),
            ("Weekly ", usage.get("seven_day")),
        ]
        ss = usage.get("seven_day_sonnet")
        if ss and ss.get("utilization") is not None:
            gauge_items.append(("Sonnet ", ss))
        so = usage.get("seven_day_opus")
        if so and so.get("utilization") is not None:
            gauge_items.append(("Opus   ", so))

        # Build lines with uniform ASCII formatting
        gauge_lines = []
        for label, obj in gauge_items:
            if not obj or obj.get("utilization") is None: continue
            p = obj["utilization"]
            rst = _reset_short(obj.get("resets_at"))
            col = _danger_color(p) or LINE_COLORS[_color_idx[0] % len(LINE_COLORS)]
            _color_idx[0] += 1
            rt_local = _reset_time_local(obj.get("resets_at", ""))
            # All ASCII: label(8) + gauge(10) + pct(5) + reset(6) = fixed total
            line = f"{label:<{LW}}{_gauge(p)} {p:>3.0f}%  ↻{rst:<5}"
            gauge_lines.append((line, col, rt_local))

        if gauge_lines:
            # Pad only to longest gauge line (NOT to W — that adds too much trailing space)
            max_len = max(len(t) for t, _, _ in gauge_lines)
            print("---")
            for text, col, rt_local in gauge_lines:
                padded = text.ljust(max_len)
                col_attr = f"color={col} " if col else ""
                print(f"{padded} | {col_attr}size=13 font=Menlo")
                if rt_local:
                    print(f"--{t('reset')}: {rt_local} | {DIM}")

    # ═══ 2. TODAY + trend comparison ═══
    if today["msgs"] > 0:
        print("---")
        print(f"⚡ {t('today')}: {fc(today['cost'])} · {tk(today['tokens'])} · {today['msgs']} {t('msgs')} | {SEC}")
        print(f"--Input: {tk(today['inp'])}   Output: {tk(today['out'])} | {DIM}")
        print(f"--Cache W: {tk(today['cw'])}   Cache R: {tk(today['cr'])} | {DIM}")
        if today["models"]:
            print("-----")
            tm_total = max(sum(v["msgs"] for v in today["models"].values()), 1)
            for model, data in sorted(today["models"].items(), key=lambda x: -x[1]["cost"]):
                short = MODEL_SHORT.get(model, model)
                pct = data["msgs"] / tm_total * 100
                print(f"--{short}: {data['msgs']:,} ({pct:.0f}%) {fc(data['cost'])} | {MODL}")

    # ═══ 3. OVERVIEW ═══
    print("---")
    print(f"{rj('Cost:', fc(tc))} | {ROW}")
    print(f"{rj('Sessions:', f'{ts:,}')} | {ROW}")
    print(f"{rj('Tokens:', tk(ta))} | {ROW}")
    print(f"Input: {tk(ti):>10}   Output: {tk(to):>10} | {DIM}")
    print(f"Cache W: {tk(tw):>8}   Cache R: {tk(tr):>8} | {DIM}")

    # ═══ 4. SUBSCRIPTION ROI ═══
    sub = CFG.get("subscription", 0)
    if sub > 0:
        lbl = CFG.get("subscription_label", "")
        prefix = f"{lbl} " if lbl else ""
        savings = tc - sub
        multiplier = tc / sub if sub > 0 else 0
        GOLD = "color=#D4A04A size=13" if DARK else "color=#8B6914 size=13"
        print(f"💰 {prefix}${sub:.0f}/mo · {t('saved')} {fc(savings)} ({multiplier:.0f}x) | {GOLD}")
        print(f"--{t('api_equiv')}: {fc(tc)} | {ROW2}")
        if week_total_cost > 0:
            daily_avg = week_total_cost / 7
            monthly_proj = daily_avg * 30
            print(f"--Daily: {fc(daily_avg)} · Monthly: {fc(monthly_proj)} | {DIM}")

    # ═══ 5. MACHINES ═══
    print("---")

    # ── Machines — top level summary, details in submenu ──
    for m in machines:
        ma = m["inp"] + m["out"] + m["cw"] + m["cr"]
        if machine_count == 1:
            icon_m = "💻"
        else:
            icon_m = "●" if m["local"] else "○"
        print(f"{icon_m} {m['label']}  {fc(m['cost'])} | {SEC}")

        # Submenu: machine details
        if m["local"]:
            print(f"--{t('live')} | {DIM}")
        elif m.get("at"):
            print(f"--{t('synced')} {m['at']} | {DIM}")
        print(f"--Token: {tk(ma)} · Sessions: {m['sessions']} | {ROW2}")
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
    # DRILL-DOWN — clean, minimal, data-focused
    # ═══════════════════════════════════════════════════════════════

    # Section header style
    SH = "color=#5CC6A7 size=12" if DARK else "color=#1A5C4C size=12"

    # ── Daily Details (newest first, max 15 visible, older folded) ──
    all_total_cost = sum(v["cost"] for v in daily.values())
    all_total_msgs = sum(v["msgs"] for v in daily.values())
    active_days = [(d, v) for d, v in reversed(daily_sorted) if v["msgs"] > 0]
    day_count = len(active_days)
    print(f"{t('daily')} | {SH}")
    # Show recent 15
    for date, data in active_days[:15]:
        dd = date[5:]
        print(f"--{dd}   {fc(data['cost']):>8}   {data['msgs']:>5} msgs | {ROW2}")
    # Older days folded into submenu
    if len(active_days) > 15:
        older = active_days[15:]
        older_cost = sum(v["cost"] for _, v in older)
        older_msgs = sum(v["msgs"] for _, v in older)
        print(f"--{t('older')} ({len(older)}d) {fc(older_cost)} · {older_msgs} msgs | {DIM}")
        for date, data in older:
            dd = date[5:]
            print(f"----{dd}   {fc(data['cost']):>8}   {data['msgs']:>5} msgs | {ROW2}")
    print("-----")
    total_label = t("total")
    print(f"--{total_label}   {fc(all_total_cost):>8}   {all_total_msgs:>5} msgs | {DIM}")

    # ── Models ──
    print(f"{t('models')} | {SH}")
    for model, data in sorted(all_models.items(), key=lambda x: -x[1]["cost"]):
        short = MODEL_SHORT.get(model, model)
        pct = data["msgs"] / total_model_msgs * 100
        print(f"--{short:<12} {pct:>3.0f}%   {fc(data['cost']):>8}   {data['msgs']:>6,} msgs | {ROW2}")

    # ── Hourly Activity ──
    hourly = local["hourly"]
    if hourly:
        print(f"{t('hours')} | {SH}")
        total_hourly = max(sum(hourly.values()), 1)
        max_h = max(hourly.values()) if hourly else 1
        # Spark bars: ▁▂▃▄▅▆▇█ — each char = 1 hour, height = relative activity
        sparks = " ▁▂▃▄▅▆▇█"
        def spark(h):
            v = hourly.get(h, 0)
            if v == 0: return "▁"
            level = min(int(v / max_h * 8) + 1, 8)
            return sparks[level]

        block_defs = [
            (t("am"),   "06–12", range(6, 12)),
            (t("pm"),   "12–18", range(12, 18)),
            (t("eve"),  "18–24", range(18, 24)),
            (t("late"), "00–06", range(0, 6)),
        ]
        for label, time_str, hours in block_defs:
            count = sum(hourly.get(h, 0) for h in hours)
            if count == 0: continue
            pct = count / total_hourly * 100
            sparkline = "".join(spark(h) for h in hours)
            msgs_u = t("msgs")
            print(f"--{label} {time_str}  {sparkline}  {count:>5,} {msgs_u} {pct:>2.0f}% | {ROW2}")

    # ── Top Projects ──
    projects = dict(local["projects"])
    if projects:
        print(f"{t('projects')} | {SH}")
        top = sorted(projects.items(), key=lambda x: -x[1]["cost"])[:8]
        for name, data in top:
            short_name = f"{name[:14]:<14}" if len(name) <= 14 else f"{name[:13]}…"
            print(f"--{short_name}  {fc(data['cost']):>8}   {data['msgs']:>5} msgs | {ROW2}")

    # ═══════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════
    print("---")
    dmin = min((m["d_min"] for m in machines if m["d_min"]), default="N/A")
    dmax = max((m["d_max"] for m in machines if m["d_max"]), default="N/A")
    rng = f"{dmin[5:]}~{dmax[5:]}" if dmin != "N/A" else "N/A"
    sync_str = {"icloud": "iCloud", "custom": "Custom"}.get(SYNC_TYPE, "")
    parts = [rng, f"{machine_count} mac"]
    if sync_str: parts.append(sync_str)
    parts.append(now)
    print(f"{' · '.join(parts)} | {META}")

    # ═══ SETTINGS ═══
    print("---")

    # Helper script path
    helper = str(Path.home() / ".config" / "cc-token-stats" / ".toggle.sh")

    # Notification toggle
    notify_on = CFG.get("notifications", True)
    notify_icon = "✓ " if notify_on else "  "
    notify_label = f"{notify_icon} {t('notify')}"
    toggle_val = "False" if notify_on else "True"  # Python bool, not JSON
    # Write a tiny helper script for SwiftBar to execute
    try:
        Path(helper).parent.mkdir(parents=True, exist_ok=True)
        Path(helper).write_text(f"""#!/bin/bash
case "$1" in
  notify)
    python3 -c "
import json, pathlib
p = pathlib.Path('{CONFIG_FILE}')
c = json.loads(p.read_text())
c['notifications'] = {toggle_val}
p.write_text(json.dumps(c, indent=2))
"
    ;;
  login-add)
    osascript -e 'tell application "System Events" to make login item at end with properties {{path:"/Applications/SwiftBar.app", hidden:false}}'
    ;;
  login-remove)
    osascript -e 'tell application "System Events" to delete login item "SwiftBar"'
    ;;
  sub)
    # $2=price $3=label
    python3 -c "
import json, pathlib
p = pathlib.Path('{CONFIG_FILE}')
c = json.loads(p.read_text())
c['subscription'] = int('$2')
c['subscription_label'] = '$3'
p.write_text(json.dumps(c, indent=2))
"
    ;;
esac
""")
        os.chmod(helper, 0o755)
    except: pass

    print(f"{notify_label} | bash={helper} param1=notify terminal=false refresh=true")

    # Launch at login toggle
    try:
        login_items = subprocess.run(["osascript", "-e", 'tell application "System Events" to get the name of every login item'], capture_output=True, text=True, timeout=5).stdout
        login_on = "SwiftBar" in login_items
    except: login_on = False
    login_icon = "✓ " if login_on else "  "
    login_label = f"{login_icon} {t('login')}"
    login_action = "login-remove" if login_on else "login-add"
    print(f"{login_label} | bash={helper} param1={login_action} terminal=false refresh=true")

    # Subscription plan selector
    cur_sub = CFG.get("subscription", 0)
    plans = [("Pro", 20), ("Max 5x", 100), ("Max 20x", 200), ("Team", 30), ("API / None", 0)]
    plan_title = t("subscription")
    cur_name = next((name for name, price in plans if price == cur_sub), f"${cur_sub}")
    print(f"{'  '}{plan_title}: {cur_name} | size=13")
    for name, price in plans:
        check = "✓ " if price == cur_sub else "  "
        label_short = name.split(" ")[0] if " " in name else name
        print(f"--{check}{name} (${price}/mo) | bash={helper} param1=sub param2={price} param3={label_short} terminal=false refresh=true")

    print("---")
    print("Refresh | refresh=true")
    quit_label = t("quit")
    print(f"{quit_label} | bash='osascript' param1='-e' param2='quit app \"SwiftBar\"' terminal=false")

if __name__ == "__main__":
    main()

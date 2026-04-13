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

VERSION = "1.0.1.1"
REPO_URL = "https://raw.githubusercontent.com/jayson-jia-dev/cc-token-status/main"

import json, os, glob, shlex, socket, subprocess
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
    "auto_update": True,
}
NOTIFY_STATE_FILE = Path.home() / ".config" / "cc-token-stats" / ".notify_state.json"
SCAN_CACHE_FILE = Path.home() / ".config" / "cc-token-stats" / ".scan_cache.json"

def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.is_file():
        try:
            with open(CONFIG_FILE) as f: cfg.update(json.load(f))
        except Exception: pass
    for ek, ck in [("CC_STATS_CLAUDE_DIR","claude_dir"),("CC_STATS_SYNC_REPO","sync_repo"),("CC_STATS_LANG","language")]:
        if os.environ.get(ek): cfg[ck] = os.environ[ek]
    if os.environ.get("CC_STATS_SUBSCRIPTION"):
        try: cfg["subscription"] = float(os.environ["CC_STATS_SUBSCRIPTION"])
        except Exception: pass
    if cfg["language"] == "auto":
        try:
            out = subprocess.check_output(["defaults","read",".GlobalPreferences","AppleLanguages"], stderr=subprocess.DEVNULL, text=True)
            langs = [l.strip().strip('"').strip('",') for l in out.split("\n") if l.strip() and l.strip() not in ("(", ")")]
            if langs:
                fl = langs[0].lower().split("-")[0]  # "en-CN" → "en", "zh-Hans-CN" → "zh"
                supported = {"en","zh","es","fr","ja"}
                cfg["language"] = fl if fl in supported else "en"
            else:
                cfg["language"] = "en"
        except Exception: cfg["language"] = "en"
    return cfg

CFG = load_config()
LANG = CFG["language"]
MACHINE = socket.gethostname().split(".")[0]

# ─── i18n: 5 languages (EN, ZH, ES, FR, JA) ───────────────────
STRINGS = {
    "title":       {"en":"Claude Code Usage Dashboard","zh":"Claude Code 用量看板","es":"Panel de uso de Claude Code","fr":"Tableau de bord Claude Code","ja":"Claude Code 使用状況"},
    "today":       {"en":"Today","zh":"今日","es":"Hoy","fr":"Aujourd'hui","ja":"今日"},
    "live":        {"en":"live","zh":"实时","es":"en vivo","fr":"en direct","ja":"ライブ"},
    "synced":      {"en":"synced","zh":"同步","es":"sincronizado","fr":"synchronisé","ja":"同期"},
    "daily":       {"en":"Daily Details","zh":"每日明细","es":"Detalles diarios","fr":"Détails quotidiens","ja":"日別詳細"},
    "older":       {"en":"Older","zh":"更早","es":"Anteriores","fr":"Plus ancien","ja":"過去"},
    "total":       {"en":"Total","zh":"合计","es":"Total","fr":"Total","ja":"合計"},
    "models":      {"en":"Models","zh":"模型分布","es":"Modelos","fr":"Modèles","ja":"モデル"},
    "hours":       {"en":"Active Hours","zh":"活跃时段","es":"Horas activas","fr":"Heures actives","ja":"活動時間"},
    "projects":    {"en":"Top Projects","zh":"项目排行","es":"Proyectos","fr":"Projets","ja":"プロジェクト"},
    "saved":       {"en":"saved","zh":"省","es":"ahorrado","fr":"économisé","ja":"節約"},
    "msgs":        {"en":"msgs","zh":"条","es":"msgs","fr":"msgs","ja":"件"},
    "quit":        {"en":"Quit","zh":"退出","es":"Salir","fr":"Quitter","ja":"終了"},
    "refresh":     {"en":"Refresh","zh":"刷新","es":"Actualizar","fr":"Rafraîchir","ja":"更新"},
    "settings":    {"en":"Settings","zh":"设置","es":"Ajustes","fr":"Réglages","ja":"設定"},
    "notify":      {"en":"Notifications","zh":"通知提醒","es":"Notificaciones","fr":"Notifications","ja":"通知"},
    "login":       {"en":"Launch at Login","zh":"开机自启","es":"Inicio automático","fr":"Lancer au démarrage","ja":"ログイン時に起動"},
    "subscription":{"en":"Subscription","zh":"订阅方案","es":"Suscripción","fr":"Abonnement","ja":"サブスクリプション"},
    "limit_warn":  {"en":"Approaching usage limit","zh":"用量接近上限","es":"Acercándose al límite","fr":"Proche de la limite","ja":"上限に近づいています"},
    "limit_crit":  {"en":"Rate limit imminent!","zh":"即将限速！","es":"¡Límite inminente!","fr":"Limite imminente !","ja":"制限間近！"},
    "am":          {"en":"AM","zh":"早上","es":"Mañana","fr":"Matin","ja":"午前"},
    "pm":          {"en":"PM","zh":"下午","es":"Tarde","fr":"Après-midi","ja":"午後"},
    "eve":         {"en":"Eve","zh":"晚上","es":"Noche","fr":"Soir","ja":"夜"},
    "late":        {"en":"Late","zh":"凌晨","es":"Madrugada","fr":"Nuit","ja":"深夜"},
    "reset":       {"en":"Resets","zh":"重置","es":"Reinicia","fr":"Réinit.","ja":"リセット"},
    "api_equiv":   {"en":"API equiv","zh":"等价 API","es":"Equiv. API","fr":"Equiv. API","ja":"API相当"},
    "auto_upd":    {"en":"Auto Update","zh":"自动更新","es":"Auto actualizar","fr":"Mise à jour auto","ja":"自動更新"},
    "input":       {"en":"Input","zh":"输入","es":"Entrada","fr":"Entrée","ja":"入力"},
    "output":      {"en":"Output","zh":"输出","es":"Salida","fr":"Sortie","ja":"出力"},
    "cache_w":     {"en":"Cache W","zh":"缓存写","es":"Caché E","fr":"Cache É","ja":"Cache書"},
    "cache_r":     {"en":"Cache R","zh":"缓存读","es":"Caché L","fr":"Cache L","ja":"Cache読"},
    "overview":    {"en":"Total","zh":"累计","es":"Total","fr":"Total","ja":"累計"},
    "devices":     {"en":"Devices","zh":"设备","es":"Dispositivos","fr":"Appareils","ja":"デバイス"},
    "details":     {"en":"Details","zh":"详情","es":"Detalles","fr":"Détails","ja":"詳細"},
    "level":       {"en":"Level","zh":"等级","es":"Nivel","fr":"Niveau","ja":"レベル"},
    "next_level":  {"en":"Next","zh":"下一级","es":"Siguiente","fr":"Suivant","ja":"次"},
    "no_token":    {"en":"⚠ No OAuth token — log in to Claude Code","zh":"⚠ 未找到 OAuth token — 请登录 Claude Code","es":"⚠ Sin token OAuth — inicie sesión en Claude Code","fr":"⚠ Pas de token OAuth — connectez-vous à Claude Code","ja":"⚠ OAuthトークンなし — Claude Codeにログイン"},
    "api_error":   {"en":"⚠ Cannot reach Anthropic API","zh":"⚠ 无法连接 Anthropic API","es":"⚠ No se puede conectar a la API","fr":"⚠ API Anthropic inaccessible","ja":"⚠ Anthropic APIに接続できません"},
    "first_use":   {"en":"Start a Claude Code session to see stats","zh":"启动 Claude Code 会话以查看统计","es":"Inicie una sesión de Claude Code","fr":"Démarrez une session Claude Code","ja":"Claude Codeセッションを開始してください"},
    "dim_usage":   {"en":"Usage","zh":"使用深度","es":"Uso","fr":"Utilisation","ja":"使用量"},
    "dim_context": {"en":"Context","zh":"上下文","es":"Contexto","fr":"Contexte","ja":"コンテキスト"},
    "dim_tools":   {"en":"Tools","zh":"工具生态","es":"Herramientas","fr":"Outils","ja":"ツール"},
    "dim_auto":    {"en":"Automation","zh":"自动化","es":"Automatización","fr":"Automatisation","ja":"自動化"},
    "dim_scale":   {"en":"Scale","zh":"规模化","es":"Escala","fr":"Échelle","ja":"スケール"},
    "burn_rate":   {"en":"~{0}min to rate limit","zh":"约{0}分钟后限速","es":"~{0}min al límite","fr":"~{0}min avant limite","ja":"約{0}分で制限"},
    "extra":       {"en":"Extra","zh":"额外用量","es":"Extra","fr":"Extra","ja":"追加"},
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
        # Only legacy Opus (4.0/4.1) uses old pricing; all newer default to opus_new
        if "4-0" in m or "4-1" in m or "4.0" in ml or "4.1" in ml:
            return "opus_old"
        return "opus_new"
    if "haiku" in ml: return "haiku"
    return "sonnet"

# ─── User Level System ────────────────────────────────────────────

LEVELS = [
    (0,  "🌑", "Starter",      "练气期"),
    (13, "🌒", "Planner",      "筑基期"),
    (31, "🌓", "Engineer",     "金丹期"),
    (51, "🌔", "Integrator",   "元婴期"),
    (71, "🌕", "Architect",    "化神期"),
    (86, "👑", "Orchestrator", "大乘期"),
]

LEVEL_CACHE_FILE = Path.home() / ".config" / "cc-token-stats" / ".level_cache.json"

def calc_user_level():
    """Calculate user level from local data. Returns (score, level_idx, details).
    Cached for 24 hours since level changes very slowly."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        if LEVEL_CACHE_FILE.is_file():
            _lc = json.loads(LEVEL_CACHE_FILE.read_text())
            if _lc.get("date") == today_str and _lc.get("ver") == VERSION:
                return _lc["score"], _lc["level"], _lc["details"]
    except Exception: pass

    import glob as _g
    _home = os.path.expanduser("~")
    _cd = os.path.join(_home, ".claude")
    details = {}

    # 1. Usage maturity (20pts): median session length + density
    _sessions = []
    _dates = set()
    for jf in _g.glob(os.path.join(_cd, "projects/*/*.jsonl")):
        cnt = 0
        try:
            with open(jf) as f:
                for line in f:
                    d = json.loads(line)
                    if d.get("type") == "assistant": cnt += 1
                    ts = d.get("timestamp", "")
                    if ts: _dates.add(ts[:10])
        except Exception: pass
        if cnt > 0: _sessions.append(cnt)
    _sessions.sort()
    med = _sessions[len(_sessions)//2] if _sessions else 0
    _ad = len(_dates)
    if _dates:
        _fd, _ld = min(_dates), max(_dates)
        _td = (datetime.strptime(_ld, "%Y-%m-%d") - datetime.strptime(_fd, "%Y-%m-%d")).days + 1
    else:
        _td = 1
    _dens = _ad / max(_td, 1)
    s1 = 16 if med >= 80 else 10 if med >= 50 else 6 if med >= 30 else 2 if med >= 10 else 0
    s1 += 4 if _dens >= 0.6 else 2 if _dens >= 0.4 else 0
    s1 = min(s1, 20)
    details["usage"] = s1

    # 2. Context management (20pts)
    s2 = 0
    _cm = os.path.join(_cd, "CLAUDE.md")
    if os.path.isfile(_cm):
        with open(_cm) as _f: s2 += 4 if len(_f.readlines()) > 50 else 2
    _pcm = _g.glob(os.path.join(_home, "Downloads/*/CLAUDE.md"))
    s2 += 4 if len(_pcm) >= 3 else 2 if len(_pcm) >= 1 else 0
    _md = os.path.join(_cd, "projects/-Users-" + os.path.basename(_home), "memory")
    _mf = [f for f in _g.glob(os.path.join(_md, "*.md")) if "MEMORY.md" not in f] if os.path.isdir(_md) else []
    _sm = [f for f in _mf if os.path.getsize(f) > 200]
    _mr = any((datetime.now().timestamp() - os.path.getmtime(f)) < 7*86400 for f in _sm) if _sm else False
    s2 += 4 if len(_sm) >= 5 and _mr else 2 if len(_sm) >= 2 else 0
    _rd = [os.path.join(_cd, "rules"), os.path.join(_cd, ".claude/rules")]
    _rc = sum(len(_g.glob(os.path.join(d, "*"))) for d in _rd if os.path.isdir(d))
    if _rc > 0: s2 += 4
    s2 = min(s2, 20)
    details["context"] = s2

    # 3. Tool ecosystem (20pts)
    s3 = 0
    _wm = {"zentao","gitlab","jira","confluence","jenkins"}
    _pm = 0; _mc = 0
    _mf2 = os.path.join(_cd, "mcp.json")
    if os.path.isfile(_mf2):
        try:
            with open(_mf2) as _f: _md2 = json.load(_f)
            _svs = _md2.get("mcpServers", {})
            _mc = len(_svs)
            _pm = sum(1 for n in _svs if not any(w in n.lower() for w in _wm))
        except Exception: pass
    _em = _pm + (_mc - _pm) * 0.5
    s3 += 14 if _em >= 4 else 10 if _em >= 3 else 7 if _em >= 2 else 4 if _em >= 1 else 0
    _pl = _g.glob(os.path.join(_cd, "plugins/cache/*/"))
    s3 += 4 if len(_pl) >= 3 else 2 if len(_pl) >= 1 else 0
    s3 = min(s3, 20)
    details["tools"] = s3

    # 4. Automation (20pts) — self-built weighted
    _fp = ("gsd","jjx","rn-","claude-","commit-","code-review","pr-review","understand","smart-",
           "mem-","workflow-","using-","test-","systematic","verification","receiving-","requesting-",
           "writing-","log-","dispatching","executing-","finishing-","subagent","brainstorming","planning-")
    _cmddir = os.path.join(_cd, "commands")
    _ac = [f for f in os.listdir(_cmddir) if f.endswith(".md")] if os.path.isdir(_cmddir) else []
    _sc2 = [c for c in _ac if not any(c.startswith(p) for p in _fp)]
    _skdir = os.path.join(_cd, "skills")
    _ask = os.listdir(_skdir) if os.path.isdir(_skdir) else []
    _ssk = [s for s in _ask if not any(s.startswith(p) for p in _fp)]
    _hc = 0
    _sf = os.path.join(_cd, "settings.json")
    if os.path.isfile(_sf):
        try:
            with open(_sf) as _f: _sd = json.load(_f)
            for v in _sd.get("hooks", {}).values():
                if isinstance(v, list): _hc += len(v)
        except Exception: pass
    _raw = 0
    _nsc = len(_sc2)
    _raw += 14 if _nsc >= 10 else 10 if _nsc >= 5 else 6 if _nsc >= 3 else 3 if _nsc >= 1 else 0
    _raw += 6 if _hc >= 3 else 3 if _hc >= 1 else 0
    _raw = min(_raw, 20)
    _ta = len(_ac) + len(_ask)
    _sa = len(_sc2) + len(_ssk)
    _sr = _sa / max(_ta, 1)
    s4 = int(_raw * (0.3 + 0.7 * _sr))
    s4 = min(s4, 20)
    details["automation"] = s4

    # 5. Scale (20pts) — substantial projects only
    s5 = 0
    _pdir = os.path.join(_cd, "projects")
    _ps = {}
    for pd in _g.glob(os.path.join(_pdir, "*")):
        if os.path.isdir(pd):
            _ps[os.path.basename(pd)] = len(_g.glob(os.path.join(pd, "*.jsonl")))
    _sp = sum(1 for c in _ps.values() if c >= 5)
    s5 += 10 if _sp >= 8 else 7 if _sp >= 5 else 4 if _sp >= 3 else 2 if _sp >= 1 else 0
    # worktree detection (simplified)
    try:
        _dl = Path(_home) / "Downloads"
        if any(_dl.glob("*/.git/worktrees")) or any(_dl.glob("*/*/.git/worktrees")):
            s5 += 4
    except Exception: pass
    s5 += 4 if _td >= 90 else 3 if _td >= 60 else 2 if _td >= 30 else 1 if _td >= 14 else 0
    s5 = min(s5, 20)
    details["scale"] = s5

    total = s1 + s2 + s3 + s4 + s5
    lvl = 0
    for i, (threshold, *_) in enumerate(LEVELS):
        if total >= threshold: lvl = i
    try:
        LEVEL_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LEVEL_CACHE_FILE.write_text(json.dumps({"date": today_str, "ver": VERSION, "score": total, "level": lvl, "details": details}))
    except Exception: pass
    return total, lvl, details

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

def _notify(title, msg):
    """Send a macOS notification."""
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{msg}" with title "{title}" subtitle "cc-token-status"'
        ], timeout=5)
    except Exception: pass

def check_and_notify(usage):
    """Send macOS notification when limits cross 80% or 95%. Once per threshold per reset cycle."""
    if not CFG.get("notifications", True) or not usage:
        return
    # Load state
    state = {}
    try:
        if NOTIFY_STATE_FILE.is_file():
            state = json.loads(NOTIFY_STATE_FILE.read_text())
    except Exception: pass

    thresholds = [80, 95]
    checks = [
        ("Session", "five_hour"),
        ("Weekly", "seven_day"),
        ("Sonnet", "seven_day_sonnet"),
        ("Opus", "seven_day_opus"),
    ]
    current_keys = set()
    changed = False
    for name, key in checks:
        obj = usage.get(key)
        if not obj or obj.get("utilization") is None: continue
        util = obj["utilization"]
        # Truncate reset time to minute — avoid microsecond differences creating duplicate keys
        reset_raw = obj.get("resets_at", "")
        reset = reset_raw[:16] if reset_raw else ""  # "2026-04-11T06:00"
        for thresh in thresholds:
            state_key = f"{key}_{thresh}_{reset}"
            current_keys.add(state_key)
            if util >= thresh and state_key not in state:
                if thresh >= 95:
                    _notify(f"⛔ {name} {util:.0f}%", t("limit_crit"))
                else:
                    _notify(f"⚠️ {name} {util:.0f}%", t("limit_warn"))
                state[state_key] = datetime.now().isoformat()
                changed = True

    # Burn rate warning: if session >50% and will hit 100% within 30 min at current pace
    fh = usage.get("five_hour")
    if fh and fh.get("utilization") is not None and fh["utilization"] >= 50:
        try:
            reset_str = fh.get("resets_at", "")
            if reset_str:
                rt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
                now_aware = datetime.now().astimezone()
                remaining_min = (rt - now_aware).total_seconds() / 60
                util = fh["utilization"]
                # Estimate time to 100%: if util% used in (300-remaining) minutes,
                # rate = util / elapsed, time_to_100 = (100-util) / rate
                elapsed_min = max(300 - remaining_min, 1)  # 5h = 300min
                rate = util / elapsed_min  # % per minute
                if rate > 0:
                    min_to_full = (100 - util) / rate
                    burn_key = f"burn_{reset_str[:16]}"
                    if min_to_full <= 30 and burn_key not in state:
                        _notify(
                            f"🔥 Session {util:.0f}%",
                            t("burn_rate").format(int(min_to_full))
                        )
                        state[burn_key] = datetime.now().isoformat()
                        changed = True
                    current_keys.add(burn_key)
        except Exception: pass

    # Cleanup: remove entries whose reset time has passed (not just missing from current check)
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    old_keys = [k for k in state if k not in current_keys and not k.startswith("burn_")]
    # For non-burn keys: only remove if the reset time in the key is in the past
    for k in list(state.keys()):
        if k in current_keys: continue
        # Extract reset timestamp from key (last 16 chars after last _)
        parts = k.rsplit("_", 1)
        if len(parts) == 2 and len(parts[1]) >= 16:
            if parts[1] < now_str:
                del state[k]
                changed = True
        elif k.startswith("burn_") and k not in current_keys:
            # Burn key from past cycle
            burn_reset = k[5:]  # "burn_2026-04-11T06:00"
            if burn_reset < now_str:
                del state[k]
                changed = True

    if changed:
        try:
            NOTIFY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            NOTIFY_STATE_FILE.write_text(json.dumps(state))
            NOTIFY_STATE_FILE.chmod(0o600)
        except Exception: pass

# ─── Auto-update (once per day, silent) ──────────────────────────

UPDATE_CHECK_FILE = Path.home() / ".config" / "cc-token-stats" / ".last_update_check"

def auto_update():
    """Check for updates once per day. Downloads new version silently."""
    if not CFG.get("auto_update", True):
        return
    try:
        # Check at most once per day
        if UPDATE_CHECK_FILE.is_file():
            last = float(UPDATE_CHECK_FILE.read_text().strip())
            if datetime.now().timestamp() - last < 86400:  # 24h
                return
    except Exception: pass

    try:
        import urllib.request, hashlib
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
                    # Resolve plugin path
                    plugin_path = None
                    try:
                        plugin_dir = subprocess.run(
                            ["defaults", "read", "com.ameba.SwiftBar", "PluginDirectory"],
                            capture_output=True, text=True, timeout=3
                        ).stdout.strip()
                        if plugin_dir:
                            plugin_path = os.path.join(plugin_dir, "cc-token-stats.5m.py")
                    except Exception: pass
                    if not plugin_path:
                        plugin_path = os.path.join(
                            str(Path.home()), "Library", "Application Support",
                            "SwiftBar", "plugins", "cc-token-stats.5m.py")

                    # Download to temp file
                    tmp_path = plugin_path + ".tmp"
                    urllib.request.urlretrieve(f"{REPO_URL}/cc-token-stats.5m.py", tmp_path)

                    # Verify SHA256 checksum
                    with open(tmp_path, "rb") as f:
                        actual_hash = hashlib.sha256(f.read()).hexdigest()
                    with urllib.request.urlopen(f"{REPO_URL}/checksum.sha256", timeout=5) as resp:
                        expected_hash = resp.read().decode().strip().split()[0]
                    if actual_hash != expected_hash:
                        try: os.remove(tmp_path)
                        except Exception: pass
                        return  # checksum mismatch — don't record, retry next cycle

                    os.chmod(tmp_path, 0o755)
                    os.rename(tmp_path, plugin_path)  # atomic on same filesystem
                break

        # Record check time — only reached on success or same-version
        UPDATE_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        UPDATE_CHECK_FILE.write_text(str(datetime.now().timestamp()))
        UPDATE_CHECK_FILE.chmod(0o600)
    except Exception: pass

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
    """Fetch official plan usage from Anthropic API. Returns (data, error_hint).
    error_hint is None on success, or a short string describing the failure."""
    token, sub_type, tier = get_oauth_token()
    if not token:
        return None, "no_token"
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
        return data, None
    except Exception:
        return None, "api_error"

USAGE_CACHE = Path.home() / ".config" / "cc-token-stats" / ".usage_cache.json"

def get_usage():
    """Get usage with local cache. Returns (data_or_None, error_hint_or_None)."""
    # Try cache first (valid for 4 minutes, plugin runs every 5)
    if USAGE_CACHE.is_file():
        try:
            cached = json.loads(USAGE_CACHE.read_text())
            age = datetime.now().timestamp() - cached.get("_ts", 0)
            if age < 240:  # 4 minutes
                return cached, None
        except Exception:
            pass
    # Fetch fresh
    data, err = fetch_usage()
    if data:
        data["_ts"] = datetime.now().timestamp()
        try:
            USAGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
            USAGE_CACHE.write_text(json.dumps(data))
            USAGE_CACHE.chmod(0o600)  # protect cached OAuth data
        except Exception:
            pass
        return data, None
    # Fallback to stale cache — max 30 minutes to avoid showing yesterday's data
    if USAGE_CACHE.is_file():
        try:
            stale = json.loads(USAGE_CACHE.read_text())
            stale_age = datetime.now().timestamp() - stale.get("_ts", 0)
            if stale_age < 1800:  # 30 minutes
                return stale, None  # has data, suppress error hint
        except Exception: pass
    return None, err

# ─── Data ────────────────────────────────────────────────────────

def _file_fingerprints(base):
    """Collect {path: mtime} for all JSONL files under base."""
    fps = {}
    if not os.path.isdir(base):
        return fps
    for pd in glob.glob(os.path.join(base, "*")):
        if not os.path.isdir(pd): continue
        for jf in glob.glob(os.path.join(pd, "*.jsonl")):
            try: fps[jf] = os.path.getmtime(jf)
            except Exception: pass
    return fps

def _load_scan_cache(base, today_str):
    """Return cached scan result if all files unchanged and same day."""
    try:
        if not SCAN_CACHE_FILE.is_file():
            return None
        cache = json.loads(SCAN_CACHE_FILE.read_text())
        if cache.get("date") != today_str:
            return None  # day boundary crossed, need re-scan for today stats
        current_fps = _file_fingerprints(base)
        cached_fps = cache.get("file_mtimes", {})
        if current_fps == cached_fps:
            # Restore defaultdicts from cached plain dicts
            s = cache["result"]
            s["daily"] = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0}, s.get("daily", {}))
            s["hourly"] = defaultdict(int, {int(k): v for k, v in s.get("hourly", {}).items()})
            s["projects"] = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0}, s.get("projects", {}))
            return s
    except Exception: pass
    return None

def _save_scan_cache(base, today_str, s):
    """Save scan result and file fingerprints to cache."""
    try:
        cache = {
            "date": today_str,
            "file_mtimes": _file_fingerprints(base),
            "result": {k: (dict(v) if isinstance(v, defaultdict) else v) for k, v in s.items()},
        }
        SCAN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCAN_CACHE_FILE.write_text(json.dumps(cache))
    except Exception: pass

def scan():
    base = os.path.join(CLAUDE_DIR, "projects")
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Incremental: return cached result if no files changed
    cached = _load_scan_cache(base, today_str)
    if cached is not None:
        return cached

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
        parts = [p for p in proj.replace("-", "/").split("/") if p]
        proj_name = parts[-1] if parts else proj[:20]

        for jf in glob.glob(os.path.join(pd, "*.jsonl")):
            has = False
            try: fd = datetime.fromtimestamp(os.path.getmtime(jf)).strftime("%Y-%m-%d")
            except Exception: fd = None
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
                                td = s["today"]
                                td["tokens"] += total_t; td["cost"] += mc; td["msgs"] += 1
                                td["inp"] += i; td["out"] += o; td["cw"] += w; td["cr"] += r
                                if m and m != "<synthetic>":
                                    if m not in td["models"]: td["models"][m] = {"msgs": 0, "cost": 0.0}
                                    td["models"][m]["msgs"] += 1; td["models"][m]["cost"] += mc

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
                                except Exception: pass

                            # Rolling windows (5h / 7d)
                            if ts_str:
                                try:
                                    msg_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
                                    if msg_dt >= cutoff_5h:
                                        s["window_5h"]["tokens"] += total_t; s["window_5h"]["cost"] += mc
                                        s["window_5h"]["msgs"] += 1; s["window_5h"]["out"] += o
                                    if msg_dt >= cutoff_7d:
                                        s["window_7d"]["tokens"] += total_t; s["window_7d"]["cost"] += mc
                                        s["window_7d"]["msgs"] += 1; s["window_7d"]["out"] += o
                                except Exception: pass

                            # Project
                            s["projects"][proj_name]["tokens"] += total_t
                            s["projects"][proj_name]["cost"] += mc
                            s["projects"][proj_name]["msgs"] += 1

                        except Exception: pass
                if has:
                    s["sessions"] += 1
            except Exception: pass

    _save_scan_cache(base, today_str, s)
    return s

def save_sync(st):
    if not SYNC_DIR: return
    d = os.path.join(SYNC_DIR, "machines", MACHINE)
    try:
        os.makedirs(d, exist_ok=True)
        mb = {m: {**v, "cost": round(v["cost"], 2)} for m, v in st.get("models", {}).items()}
        with open(os.path.join(d, "token-stats.json"), "w") as f:
            json.dump({"machine": MACHINE, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_count": st["sessions"], "input_tokens": st["inp"], "output_tokens": st["out"],
                "cache_write_tokens": st["cw"], "cache_read_tokens": st["cr"],
                "total_cost": round(st["cost"], 2), "date_range": {"min": st["d_min"], "max": st["d_max"]},
                "model_breakdown": mb}, f, indent=2)
    except Exception: pass

def recalc_remote_cost(data):
    """Recalculate remote machine cost using current pricing (not cached total_cost)."""
    total = 0.0
    mb = data.get("model_breakdown", {})
    if mb:
        # Has per-model breakdown — use token ratio (not msg ratio, since
        # Opus messages have far more tokens per msg than Haiku)
        inp = data.get("input_tokens", 0)
        out = data.get("output_tokens", 0)
        cw = data.get("cache_write_tokens", 0)
        cr = data.get("cache_read_tokens", 0)
        total_tokens = max(sum(v.get("tokens", 0) for v in mb.values()), 1)
        for model, mdata in mb.items():
            ratio = mdata.get("tokens", 0) / total_tokens
            p = PRICING.get(tier(model), PRICING["sonnet"])
            model_cost = (inp * ratio * p["input"] + out * ratio * p["output"] +
                          cw * ratio * p["cache_write"] + cr * ratio * p["cache_read"]) / 1e6
            total += model_cost
            mdata["cost"] = round(model_cost, 2)
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
            try:
                with open(sf) as f: remotes.append(recalc_remote_cost(json.load(f)))
            except Exception: pass
    return remotes

# ─── Render ──────────────────────────────────────────────────────

# Styles — auto-detect dark/light mode
def _is_dark():
    try:
        r = subprocess.run(["defaults","read","-g","AppleInterfaceStyle"],
                           capture_output=True, text=True, timeout=3)
        return "dark" in r.stdout.lower()
    except Exception: return True  # default to dark

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
    # Last 7 days for quick stats (today + 6 preceding days)
    last_7d = [(d, v) for d, v in daily_sorted if d >= (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")]
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
    usage, usage_err = get_usage()

    # Get limits for panel display
    _5h_util = 0; _7d_util = 0
    if usage:
        _fh = usage.get("five_hour")
        if _fh and _fh.get("utilization") is not None: _5h_util = _fh["utilization"]
        _sd = usage.get("seven_day")
        if _sd and _sd.get("utilization") is not None: _7d_util = _sd["utilization"]

    _max_util = max(_5h_util, _7d_util)
    if _max_util >= 100:
        print(f"CC 100%")
    elif _5h_util > 0:
        print(f"CC {_5h_util:.0f}%")
    else:
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
        def _reset_time_local(reset_str):
            try:
                rt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
                return rt.astimezone().strftime("%m-%d %H:%M")
            except Exception: return ""

        def _gauge(pct):
            p = min(max(pct, 0), 100)
            filled = round(p / 100 * 10)
            return "▰" * filled + "▱" * (10 - filled)

        # Each gauge gets a distinct base color; danger overrides at 60%/80%
        if DARK:
            LINE_COLORS = ["#5CC6A7", "#E07850", "#6BA4C9", "#D4CDC0"]   # teal, coral, blue, warm white
        else:
            LINE_COLORS = ["#1A5C4C", "#A04030", "#1B5A85", "#2C3040"]   # rich teal, deep coral, deep blue, navy
        _color_idx = [0]

        def _gauge_color(pct):
            """Base color by position, overridden by danger at high utilization."""
            if pct >= 80: return "#E85838" if DARK else "#C03020"   # red
            if pct >= 60: return "#E8A838" if DARK else "#B86E1A"   # amber
            col = LINE_COLORS[_color_idx[0] % len(LINE_COLORS)]
            _color_idx[0] += 1
            return col

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
            except Exception: return ""

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
        eu = usage.get("extra_usage")
        if eu and eu.get("used_credits") is not None:
            eu_obj = {"utilization": eu.get("utilization") or 0, "resets_at": eu.get("resets_at", "")}
            gauge_items.append(("Extra  ", eu_obj))

        # Build lines with uniform ASCII formatting
        gauge_lines = []
        for label, obj in gauge_items:
            if not obj or obj.get("utilization") is None: continue
            p = obj["utilization"]
            rst = _reset_short(obj.get("resets_at"))
            col = _gauge_color(p)
            rt_local = _reset_time_local(obj.get("resets_at", ""))
            # All ASCII: label(8) + gauge(10) + pct(5) + optional reset
            reset_part = f"  ↻{rst}" if rst else ""
            line = f"{label:<{LW}}{_gauge(p)} {p:>3.0f}%{reset_part}"
            is_extra = label.strip() == "Extra"
            gauge_lines.append((line, col, rt_local, is_extra))

        if gauge_lines:
            # Pad only to longest gauge line (NOT to W — that adds too much trailing space)
            max_len = max(len(text) for text, _, _, _ in gauge_lines)
            print("---")
            for text, col, rt_local, is_extra in gauge_lines:
                padded = text.ljust(max_len)
                col_attr = f"color={col} " if col else ""
                print(f"{padded} | {col_attr}size=13 font=Menlo")
                if is_extra and eu:
                    spent = eu.get("used_credits")
                    limit = eu.get("monthly_limit")
                    enabled = eu.get("is_enabled", False)
                    status = "ON" if enabled else "OFF"
                    if spent is not None:
                        print(f"--Spent: ${spent:.2f} | {ROW2}")
                    if limit is not None:
                        print(f"--Limit: ${limit:.2f}/mo | {DIM}")
                    print(f"--Status: {status} | {DIM}")
                elif rt_local:
                    print(f"--{t('reset')}: {rt_local} | {DIM}")

    # ═══ 1b. USAGE STATUS HINTS ═══
    HINT = "color=#888888 size=11"
    if not usage and usage_err:
        hint = t("no_token") if usage_err == "no_token" else t("api_error")
        print(f"{hint} | {HINT}")

    # ═══ 1c. FIRST-USE GUIDE ═══
    if ts == 0:
        print(f"{t('first_use')} | {HINT}")

    # Section title style
    ST = "color=#6B6560 size=11" if DARK else "color=#3C4050 size=11"

    # ═══ 2. TODAY ═══
    if today["msgs"] > 0:
        print("---")
        today_label = t("today")
        # Trend vs recent average (active days in last 30d, excluding today)
        today_str_local = datetime.now().strftime("%Y-%m-%d")
        recent_days = [(d, v) for d, v in daily_sorted
                       if d != today_str_local
                       and d >= (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                       and v["cost"] > 0]
        trend = ""
        if recent_days:
            avg_cost = sum(v["cost"] for _, v in recent_days) / len(recent_days)
            avg_msgs = sum(v["msgs"] for _, v in recent_days) / len(recent_days)
            # Suppress trend when today's activity < 30% of daily average
            if avg_cost > 0 and (avg_msgs <= 0 or today["msgs"] / avg_msgs >= 0.3):
                pct_change = (today["cost"] - avg_cost) / avg_cost * 100
                if abs(pct_change) >= 1:
                    if pct_change >= 0:
                        trend = f" ↑{pct_change:.0f}%"
                    else:
                        trend = f" ↓{abs(pct_change):.0f}%"
        print(f"── {today_label} ── | {ST}")
        print(f"⚡ {fc(today['cost'])} · {today['msgs']} {t('msgs')}{trend} | {SEC}")
        # Token details in submenu
        print(f"--{t('input')}: {tk(today['inp'])}   {t('output')}: {tk(today['out'])} | {DIM}")
        print(f"--{t('cache_w')}: {tk(today['cw'])}   {t('cache_r')}: {tk(today['cr'])} | {DIM}")
        if today["models"]:
            print("-----")
            tm_total = max(sum(v["msgs"] for v in today["models"].values()), 1)
            for model, data in sorted(today["models"].items(), key=lambda x: -x[1]["cost"]):
                short = MODEL_SHORT.get(model, model)
                pct = data["msgs"] / tm_total * 100
                print(f"--{short}: {data['msgs']:,} ({pct:.0f}%) {fc(data['cost'])} | {MODL}")

    # ═══ 3. OVERVIEW ═══
    print("---")
    dmin_all = min((m["d_min"] for m in machines if m["d_min"]), default=None)
    dmax_all = max((m["d_max"] for m in machines if m["d_max"]), default=None)
    rng_label = f"{dmin_all[5:]}~{dmax_all[5:]}" if dmin_all and dmax_all else ""
    overview_title = t("overview")
    if rng_label:
        print(f"── {overview_title} ({rng_label}) ── | {ST}")
    else:
        print(f"── {overview_title} ── | {ST}")
    print(f"{rj('Cost:', fc(tc))} | {ROW}")
    print(f"{rj('Sessions:', f'{ts:,}')} | {ROW}")
    print(f"{rj('Tokens:', tk(ta))} | {ROW}")
    print(f"--{t('input')}: {tk(ti):>10}   {t('output')}: {tk(to):>10} | {DIM}")
    print(f"--{t('cache_w')}: {tk(tw):>8}   {t('cache_r')}: {tk(tr):>8} | {DIM}")

    # ═══ 4. SUBSCRIPTION ROI (stays as one line) ═══
    sub = CFG.get("subscription", 0)
    if sub > 0:
        lbl = CFG.get("subscription_label", "")
        prefix = f"{lbl} " if lbl else ""
        if dmin_all:
            first = datetime.strptime(dmin_all, "%Y-%m-%d")
            months_active = max((datetime.now() - first).days / 30.0, 1)
        else:
            months_active = 1
        total_paid = sub * months_active
        savings = tc - total_paid
        multiplier = tc / total_paid
        GOLD = "color=#D4A04A size=13" if DARK else "color=#8B6914 size=13"
        print(f"💰 {prefix}${sub:.0f}/mo · {t('saved')} {fc(savings)} ({multiplier:.0f}x) | {GOLD}")
        print(f"--{t('api_equiv')}: {fc(tc)} | {ROW2}")
        if daily_sorted:
            cutoff_30d = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
            last_30d = [(d, v) for d, v in daily_sorted if d >= cutoff_30d]
            if last_30d:
                n_days = max((datetime.now() - datetime.strptime(last_30d[0][0], "%Y-%m-%d")).days + 1, 1)
                cost_30d = sum(v["cost"] for _, v in last_30d)
                daily_avg = cost_30d / n_days
                monthly_proj = daily_avg * 30
                print(f"--Daily: {fc(daily_avg)} · Monthly: {fc(monthly_proj)} | {DIM}")

    # ═══ 5. MACHINES ═══
    print("---")
    devices_label = t("devices")
    if machine_count > 1:
        sync_str = {"icloud": "iCloud", "custom": "Custom"}.get(SYNC_TYPE, "")
        suffix = f" ({machine_count} mac · {sync_str})" if sync_str else f" ({machine_count} mac)"
        print(f"── {devices_label}{suffix} ── | {ST}")

    for m in machines:
        ma = m["inp"] + m["out"] + m["cw"] + m["cr"]
        if machine_count == 1:
            icon_m = "💻"
        else:
            icon_m = "●" if m["local"] else "○"
        print(f"{icon_m} {m['label']}  {fc(m['cost'])} | {SEC}")

        # Submenu: machine details + stale detection
        if m["local"]:
            print(f"--{t('live')} | {DIM}")
        elif m.get("at"):
            stale_tag = ""
            try:
                _sync_dt = datetime.strptime(m["at"], "%Y-%m-%d %H:%M:%S")
                _sync_age = (datetime.now() - _sync_dt).days
                if _sync_age >= 7:
                    stale_tag = f" ({_sync_age}d)"
            except Exception: pass
            print(f"--{t('synced')} {m['at']}{stale_tag} | {DIM}")
        print(f"--Token: {tk(ma)} · Sessions: {m['sessions']} | {ROW2}")
        print(f"--{t('input')}: {tk(m['inp'])}   {t('output')}: {tk(m['out'])} | {DIM}")
        print(f"--{t('cache_w')}: {tk(m['cw'])}   {t('cache_r')}: {tk(m['cr'])} | {DIM}")
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
    details_label = t("details")
    print(f"── {details_label} ── | {ST}")

    # ── Daily Details (newest first, max 15 visible, older folded) ──
    all_total_cost = sum(v["cost"] for v in daily.values())
    all_total_msgs = sum(v["msgs"] for v in daily.values())
    active_days = [(d, v) for d, v in reversed(daily_sorted) if v["msgs"] > 0]
    day_count = len(active_days)
    print(f"{t('daily')} | {SH}")
    all_total_tokens = sum(v["tokens"] for v in daily.values())
    # Show recent 15
    for date, data in active_days[:15]:
        dd = date[5:]
        print(f"--{dd}   {fc(data['cost']):>8}   {tk(data['tokens']):>8}   {data['msgs']:>5} msgs | {ROW2}")
    # Older days folded into submenu
    if len(active_days) > 15:
        older = active_days[15:]
        older_cost = sum(v["cost"] for _, v in older)
        older_tokens = sum(v["tokens"] for _, v in older)
        older_msgs = sum(v["msgs"] for _, v in older)
        print(f"--{t('older')} ({len(older)}d) {fc(older_cost)} · {tk(older_tokens)} · {older_msgs} msgs | {DIM}")
        for date, data in older:
            dd = date[5:]
            print(f"----{dd}   {fc(data['cost']):>8}   {tk(data['tokens']):>8}   {data['msgs']:>5} msgs | {ROW2}")
    print("-----")
    total_label = t("total")
    print(f"--{total_label}   {fc(all_total_cost):>8}   {tk(all_total_tokens):>8}   {all_total_msgs:>5} msgs | {DIM}")

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
            print(f"--{short_name}  {fc(data['cost']):>8}   {tk(data['tokens']):>8}   {data['msgs']:>5} msgs | {ROW2}")

    # ═══ USER LEVEL ═══
    print("---")
    level_title = t("level")
    print(f"── {level_title} ── | {ST}")
    try:
        _score, _lvl, _det = calc_user_level()
        _icon = LEVELS[_lvl][1]
        _en_name = LEVELS[_lvl][2]
        _zh_name = LEVELS[_lvl][3]
        _name = _zh_name if LANG == "zh" else _en_name
        _next_threshold = LEVELS[_lvl + 1][0] if _lvl < len(LEVELS) - 1 else None

        # Experience bar within current level
        _cur_threshold = LEVELS[_lvl][0]
        _next_t = LEVELS[_lvl + 1][0] if _lvl < len(LEVELS) - 1 else 100
        _progress = (_score - _cur_threshold) / max(_next_t - _cur_threshold, 1)
        _exp_bar = bar(_progress * 10, 10, 8)
        print(f"{_icon} Lv.{_lvl+1} {_name} {_exp_bar} | {SEC}")

        # Submenu: dimension breakdown
        dim_names = {"usage": t("dim_usage"), "context": t("dim_context"),
                     "tools": t("dim_tools"), "automation": t("dim_auto"),
                     "scale": t("dim_scale")}
        for k, label in dim_names.items():
            v = _det.get(k, 0)
            b = bar(v, 20, 5)
            print(f"--{label:<10} {b} {v:>2}/20 | {ROW2}")

        if _next_threshold:
            _gap = _next_threshold - _score
            _next_icon = LEVELS[_lvl + 1][1]
            _next_name = LEVELS[_lvl + 1][3] if LANG == "zh" else LEVELS[_lvl + 1][2]
            next_label = t("next_level")
            print(f"--{next_label}: {_next_icon} Lv.{_lvl+2} {_next_name} (+{_gap}) | {DIM}")
    except Exception: pass

    # ═══════════════════════════════════════════════════════════════
    # OPERATIONS (separated from data by ---)
    # ═══════════════════════════════════════════════════════════════
    print("---")

    # Helper script path
    helper = str(Path.home() / ".config" / "cc-token-stats" / ".toggle.sh")

    # Notification toggle
    notify_on = CFG.get("notifications", True)
    notify_icon = "✓ " if notify_on else "  "
    notify_label = f"{notify_icon} {t('notify')}"
    toggle_val = "False" if notify_on else "True"  # Python bool, not JSON
    # Write a tiny helper script for SwiftBar to execute
    # Find plugin path for touch-refresh
    _plugin_path = ""
    try:
        _pd = subprocess.run(["defaults","read","com.ameba.SwiftBar","PluginDirectory"],
                             capture_output=True, text=True, timeout=3).stdout.strip()
        if _pd: _plugin_path = os.path.join(_pd, "cc-token-stats.5m.py")
    except Exception: pass
    if not _plugin_path:
        _plugin_path = os.path.join(str(Path.home()), "Library", "Application Support",
                                    "SwiftBar", "plugins", "cc-token-stats.5m.py")

    try:
        Path(helper).parent.mkdir(parents=True, exist_ok=True)
        _escaped_plugin = shlex.quote(_plugin_path)
        _escaped_config = str(CONFIG_FILE).replace("'", "'\\''")
        Path(helper).write_text(f"""#!/bin/bash
PLUGIN={_escaped_plugin}

case "$1" in
  notify)
    python3 - <<'PYEOF'
import json, pathlib
p = pathlib.Path('{_escaped_config}')
c = json.loads(p.read_text())
c["notifications"] = {toggle_val}
p.write_text(json.dumps(c, indent=2))
PYEOF
    ;;
  login-add)
    osascript -e 'tell application "System Events" to make login item at end with properties {{path:"/Applications/SwiftBar.app", hidden:false}}'
    sleep 1
    ;;
  login-remove)
    osascript -e 'tell application "System Events" to delete login item "SwiftBar"'
    sleep 1
    ;;
  autoupdate)
    python3 - <<'PYEOF'
import json, pathlib
p = pathlib.Path('{_escaped_config}')
c = json.loads(p.read_text())
c["auto_update"] = not c.get("auto_update", True)
p.write_text(json.dumps(c, indent=2))
PYEOF
    ;;
  sub)
    python3 - "$2" "$3" <<'PYEOF'
import json, pathlib, sys
p = pathlib.Path('{_escaped_config}')
c = json.loads(p.read_text())
c["subscription"] = int(sys.argv[1])
c["subscription_label"] = sys.argv[2]
p.write_text(json.dumps(c, indent=2))
PYEOF
    ;;
esac
""")
        os.chmod(helper, 0o755)
    except Exception: pass

    # ⚙️ Settings — all toggles collapsed into one submenu
    settings_label = t("settings")
    print(f"{settings_label} | size=13")

    # Notification toggle
    print(f"--{notify_label} | bash={helper} param1=notify terminal=false refresh=true")

    # Launch at login toggle
    try:
        login_items = subprocess.run(["osascript", "-e", 'tell application "System Events" to get the name of every login item'], capture_output=True, text=True, timeout=5).stdout
        login_on = "SwiftBar" in login_items
    except Exception: login_on = False
    login_icon = "✓ " if login_on else "  "
    login_label = f"{login_icon} {t('login')}"
    login_action = "login-remove" if login_on else "login-add"
    print(f"--{login_label} | bash={helper} param1={login_action} terminal=false refresh=true")

    # Auto-update toggle
    update_on = CFG.get("auto_update", True)
    update_icon = "✓ " if update_on else "  "
    update_label = f"{update_icon} {t('auto_upd')}"
    print(f"--{update_label} | bash={helper} param1=autoupdate terminal=false refresh=true")

    # Subscription plan selector
    cur_sub = CFG.get("subscription", 0)
    plans = [("Pro", 20), ("Max 5x", 100), ("Max 20x", 200), ("Team", 30), ("API / None", 0)]
    plan_title = t("subscription")
    cur_name = next((name for name, price in plans if price == cur_sub), f"${cur_sub}")
    print(f"--{plan_title}: {cur_name} | size=13")
    for name, price in plans:
        check = "✓ " if price == cur_sub else "  "
        label_short = name.split(" ")[0] if " " in name else name
        print(f"----{check}{name} (${price}/mo) | bash={helper} param1=sub param2={price} param3={label_short} terminal=false refresh=true")

    # Refresh and Quit — same level as settings, below separator
    print("---")
    print(f"{t('refresh')} | refresh=true")
    quit_label = t("quit")
    print(f"{quit_label} | bash='osascript' param1='-e' param2='quit app \"SwiftBar\"' terminal=false")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never crash — show basic menu bar item on any error
        print("CC")
        print("---")
        print("Error occurred | color=red")
        print("Click Refresh to retry | refresh=true")

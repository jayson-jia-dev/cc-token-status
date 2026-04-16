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

VERSION = "1.3.0.0"
REPO_URL = "https://raw.githubusercontent.com/jayson-jia-dev/cc-token-status/main"

import json, os, glob, shlex, socket, subprocess, sys
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
    "roi_note":    {"en":"{m:.1f}mo × ${s:.0f} = ${p:.0f} paid → {tc} ÷ ${p:.0f} = {x:.0f}x","zh":"{m:.1f}月 × ${s:.0f} = ${p:.0f} 已付 → {tc} ÷ ${p:.0f} = {x:.0f}x","es":"{m:.1f}m × ${s:.0f} = ${p:.0f} pagado → {tc} ÷ ${p:.0f} = {x:.0f}x","fr":"{m:.1f}m × ${s:.0f} = ${p:.0f} payé → {tc} ÷ ${p:.0f} = {x:.0f}x","ja":"{m:.1f}月 × ${s:.0f} = ${p:.0f} 支払 → {tc} ÷ ${p:.0f} = {x:.0f}x"},
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
    "report":      {"en":"View Full Report","zh":"查看完整报告","es":"Ver informe","fr":"Voir le rapport","ja":"レポートを見る"},
    "trend_vs":    {"en":"vs 30d avg","zh":"对比 30 天均值","es":"vs prom. 30d","fr":"vs moy. 30j","ja":"30日平均比"},
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

def _detect_macos_proxy():
    """Read HTTPS proxy from macOS system settings via scutil.
    Returns 'http://host:port' or None."""
    try:
        out = subprocess.run(["scutil", "--proxy"], capture_output=True, text=True, timeout=3)
        d = {}
        for line in out.stdout.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                d[k.strip()] = v.strip()
        if d.get("HTTPSEnable") == "1" and d.get("HTTPSProxy") and d.get("HTTPSPort"):
            return f"http://{d['HTTPSProxy']}:{d['HTTPSPort']}"
        if d.get("HTTPEnable") == "1" and d.get("HTTPProxy") and d.get("HTTPPort"):
            return f"http://{d['HTTPProxy']}:{d['HTTPPort']}"
    except Exception:
        pass
    return None

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
        import urllib.request, urllib.error
        url = "https://api.anthropic.com/api/oauth/usage"
        headers = {
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Content-Type": "application/json",
        }
        # Try 1: default behavior (auto-detects env vars + macOS system proxy)
        # Try 2: if that fails, read macOS system proxy via scutil (SwiftBar
        #         strips env vars and _scproxy may not work in its sandbox)
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers=headers)
                if attempt == 0:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                else:
                    proxy = _detect_macos_proxy()
                    if not proxy:
                        break  # no system proxy found, don't retry
                    handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
                    opener = urllib.request.build_opener(handler)
                    with opener.open(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                data["_sub_type"] = sub_type
                data["_tier"] = tier
                return data, None
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    # Pass Retry-After hint if server provides one
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    return None, f"rate_limit:{retry_after}" if retry_after else "rate_limit"
                if attempt == 0:
                    continue
            except Exception:
                if attempt == 0:
                    continue
        return None, "api_error"
    except Exception:
        return None, "api_error"

USAGE_CACHE = Path.home() / ".config" / "cc-token-stats" / ".usage_cache.json"
BACKOFF_STATE_FILE = Path.home() / ".config" / "cc-token-stats" / ".backoff_state.json"

def _load_backoff():
    try:
        if BACKOFF_STATE_FILE.is_file():
            s = json.loads(BACKOFF_STATE_FILE.read_text())
            return s.get("until", 0), s.get("count", 0)
    except Exception: pass
    return 0, 0

def _save_backoff(until_ts, count):
    try:
        BACKOFF_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        BACKOFF_STATE_FILE.write_text(json.dumps({"until": until_ts, "count": count}))
    except Exception: pass

def _clear_backoff():
    try: BACKOFF_STATE_FILE.unlink(missing_ok=True)
    except Exception: pass

def _read_synced_usage():
    """Try to read fresh usage data from another machine via sync directory."""
    if not SYNC_DIR:
        return None
    try:
        shared = os.path.join(SYNC_DIR, "shared_usage.json")
        if not os.path.isfile(shared):
            return None
        data = json.loads(Path(shared).read_text())
        return data
    except Exception:
        return None

def _write_synced_usage(data):
    """Share fresh usage data for other machines via sync directory."""
    if not SYNC_DIR:
        return
    try:
        shared = os.path.join(SYNC_DIR, "shared_usage.json")
        os.makedirs(os.path.dirname(shared), exist_ok=True)
        Path(shared).write_text(json.dumps(data))
    except Exception:
        pass

def get_usage():
    """Get usage with multi-layer cache: local → synced → API (with backoff)."""
    now_ts = datetime.now().timestamp()

    # Layer 1: local cache (< 9 minutes)
    if USAGE_CACHE.is_file():
        try:
            cached = json.loads(USAGE_CACHE.read_text())
            age = now_ts - cached.get("_ts", 0)
            if age < 540:  # 9 minutes
                return cached, None
        except Exception: pass

    # Layer 2: synced usage from another machine (< 9 minutes)
    synced = _read_synced_usage()
    if synced:
        synced_age = now_ts - synced.get("_ts", 0)
        if synced_age < 540:
            # Save to local cache so we don't re-read sync dir every run
            try:
                USAGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
                USAGE_CACHE.write_text(json.dumps(synced))
                USAGE_CACHE.chmod(0o600)
            except Exception: pass
            return synced, None

    # Layer 3: check backoff — if in cooldown, use whatever cache we have
    backoff_until, backoff_count = _load_backoff()
    if backoff_until > now_ts:
        return _best_cached(now_ts), None  # silent — data is just slightly stale

    # Layer 4: fetch from API
    data, err = fetch_usage()
    if data:
        data["_ts"] = now_ts
        try:
            USAGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
            USAGE_CACHE.write_text(json.dumps(data))
            USAGE_CACHE.chmod(0o600)
        except Exception: pass
        _write_synced_usage(data)  # share with other machines
        _clear_backoff()
        return data, None

    # On 429: backoff (10m → 20m → 40m → 60m cap), respect Retry-After
    if err and err.startswith("rate_limit"):
        new_count = backoff_count + 1
        retry_after_secs = None
        if ":" in err:
            try: retry_after_secs = int(err.split(":")[1])
            except (ValueError, IndexError): pass
        delay = min(retry_after_secs, 3600) if retry_after_secs and retry_after_secs > 0 \
            else min(600 * (2 ** (new_count - 1)), 3600)
        _save_backoff(now_ts + delay, new_count)
        return _best_cached(now_ts), None  # silent fallback

    # Other errors (no_token, api_error): only show if no data at all
    cached = _best_cached(now_ts)
    if cached:
        return cached, None
    return None, err

def _best_cached(now_ts):
    """Return best available cached data (local or synced), up to 2h stale."""
    for source in [USAGE_CACHE]:
        try:
            if source.is_file():
                data = json.loads(source.read_text())
                if now_ts - data.get("_ts", 0) < 7200:
                    return data
        except Exception: pass
    synced = _read_synced_usage()
    if synced and now_ts - synced.get("_ts", 0) < 7200:
        return synced
    return None

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
            s["daily"] = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0, "sessions": 0}, s.get("daily", {}))
            s["hourly"] = defaultdict(int, {int(k): v for k, v in s.get("hourly", {}).items()})
            s["projects"] = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0}, s.get("projects", {}))
            s.setdefault("daily_models", {})
            s.setdefault("daily_hourly", {})
            s.setdefault("sessions_by_day", {})
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
        "daily": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0, "sessions": 0}),
        # Hourly (24h)
        "hourly": defaultdict(int),
        # Per-project
        "projects": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "msgs": 0}),
        # v3: per-day per-model breakdown
        "daily_models": defaultdict(lambda: defaultdict(lambda: {"cost": 0.0, "msgs": 0})),
        # v3: per-day per-hour (for heatmap)
        "daily_hourly": defaultdict(lambda: defaultdict(int)),
        # v3: session-level detail per day
        "sessions_by_day": defaultdict(list),
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
            sess_cost = 0.0; sess_msgs = 0; sess_first_date = None; sess_model_counts = {}
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
                            # v3: session-level tracking
                            sess_cost += mc; sess_msgs += 1
                            if m and m != "<synthetic>":
                                sess_model_counts[m] = sess_model_counts.get(m, 0) + 1

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

                            # v3: track first message date for session
                            if msg_date and not sess_first_date:
                                sess_first_date = msg_date

                            # Daily (all dates) + date range from message timestamps
                            if msg_date:
                                dd = s["daily"][msg_date]
                                dd["tokens"] += total_t; dd["cost"] += mc; dd["msgs"] += 1
                                if not s["d_min"] or msg_date < s["d_min"]: s["d_min"] = msg_date
                                if not s["d_max"] or msg_date > s["d_max"]: s["d_max"] = msg_date
                                # v3: per-day per-model
                                if m and m != "<synthetic>":
                                    short_m = MODEL_SHORT.get(m, m.split("-")[-1] if "-" in m else m[:15])
                                    dm = s["daily_models"][msg_date][short_m]
                                    dm["cost"] += mc; dm["msgs"] += 1

                            # Hourly (convert to local timezone)
                            if ts_str:
                                try:
                                    local_dt = datetime.fromisoformat(ts_str.replace("Z","+00:00")).astimezone()
                                    local_h = local_dt.hour
                                    s["hourly"][local_h] += 1
                                    # v3: per-day per-hour for heatmap
                                    if msg_date:
                                        local_weekday = local_dt.weekday()  # 0=Mon, 6=Sun
                                        s["daily_hourly"][local_weekday][local_h] += 1
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
                    # v3: record session detail + count sessions per day
                    if sess_first_date:
                        s["daily"][sess_first_date]["sessions"] = s["daily"][sess_first_date].get("sessions", 0) + 1
                        sess_list = s["sessions_by_day"][sess_first_date]
                        if len(sess_list) < 30:  # cap per day
                            dom_model = max(sess_model_counts, key=sess_model_counts.get) if sess_model_counts else ""
                            short_dm = MODEL_SHORT.get(dom_model, dom_model.split("-")[-1] if "-" in dom_model else dom_model[:15])
                            sess_list.append({"project": proj_name, "cost": round(sess_cost, 2),
                                              "msgs": sess_msgs, "model": short_dm})
            except Exception: pass

    _save_scan_cache(base, today_str, s)
    return s

def save_sync(st):
    if not SYNC_DIR: return
    d = os.path.join(SYNC_DIR, "machines", MACHINE)
    try:
        os.makedirs(d, exist_ok=True)
        mb = {m: {**v, "cost": round(v["cost"], 2)} for m, v in st.get("models", {}).items()}
        # Daily: {date: {cost, msgs, tokens}}
        daily = {k: {"cost": round(v["cost"], 2), "msgs": v["msgs"], "tokens": v["tokens"]}
                 for k, v in st.get("daily", {}).items() if v.get("cost", 0) > 0 or v.get("msgs", 0) > 0}
        # Hourly: {hour: count}
        hourly = {str(k): v for k, v in st.get("hourly", {}).items() if v > 0}
        # Projects: {name: {cost, msgs, tokens}}
        projects = {k: {"cost": round(v["cost"], 2), "msgs": v["msgs"], "tokens": v["tokens"]}
                    for k, v in st.get("projects", {}).items() if v.get("cost", 0) > 0}
        # Today snapshot
        td = st.get("today", {})
        today = {"cost": round(td.get("cost", 0), 2), "msgs": td.get("msgs", 0),
                 "tokens": td.get("tokens", 0)}
        with open(os.path.join(d, "token-stats.json"), "w") as f:
            json.dump({"machine": MACHINE, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_count": st["sessions"], "input_tokens": st["inp"], "output_tokens": st["out"],
                "cache_write_tokens": st["cw"], "cache_read_tokens": st["cr"],
                "total_cost": round(st["cost"], 2), "date_range": {"min": st["d_min"], "max": st["d_max"]},
                "model_breakdown": mb, "daily": daily, "hourly": hourly,
                "projects": projects, "today": today}, f, indent=2)
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
                with open(sf) as f:
                    data = recalc_remote_cost(json.load(f))
                # Normalize field names to match local scan() output
                data["cost"] = data.get("total_cost", 0)
                data["sessions"] = data.get("session_count", 0)
                data["d_min"] = data.get("date_range", {}).get("min")
                data["d_max"] = data.get("date_range", {}).get("max")
                data.setdefault("models", data.get("model_breakdown", {}))
                data.setdefault("daily", {})
                data.setdefault("hourly", {})
                data.setdefault("projects", {})
                data.setdefault("today", {"cost": 0, "msgs": 0, "tokens": 0})
                data.setdefault("daily_models", {})
                data.setdefault("daily_hourly", {})
                data.setdefault("sessions_by_day", {})
                remotes.append(data)
            except Exception: pass
    return remotes

DASHBOARD_FILE = Path.home() / ".config" / "cc-token-stats" / "dashboard.html"

def _build_level_data():
    """Build level data dict for dashboard payload."""
    try:
        score, lvl, details = calc_user_level()
        icon = LEVELS[lvl][1]
        en_name = LEVELS[lvl][2]
        zh_name = LEVELS[lvl][3]
        cur_threshold = LEVELS[lvl][0]
        next_threshold = LEVELS[lvl + 1][0] if lvl < len(LEVELS) - 1 else 100
        next_icon = LEVELS[lvl + 1][1] if lvl < len(LEVELS) - 1 else ""
        next_en = LEVELS[lvl + 1][2] if lvl < len(LEVELS) - 1 else ""
        next_zh = LEVELS[lvl + 1][3] if lvl < len(LEVELS) - 1 else ""
        gap = next_threshold - score
        dims_sorted = sorted(details.items(), key=lambda x: x[1])
        tips = []
        tip_map = {
            "usage": {"en": "Use longer sessions (50+ messages per session)", "zh": "进行更深度的对话（单次会话 50+ 消息）"},
            "context": {"en": "Create CLAUDE.md, add memory files, set up rules", "zh": "创建 CLAUDE.md，添加记忆文件，配置 rules"},
            "tools": {"en": "Set up MCP servers and install plugins", "zh": "配置 MCP 服务器，安装插件"},
            "automation": {"en": "Create custom commands, skills, or hooks", "zh": "创建自定义 commands、skills 或 hooks"},
            "scale": {"en": "Work on more projects, use worktrees", "zh": "在更多项目中使用，尝试 worktrees"},
        }
        for dim, val in dims_sorted[:2]:
            if val < 16:
                tips.append({"dim": dim, "score": val, "max": 20,
                             "tip_en": tip_map.get(dim, {}).get("en", ""),
                             "tip_zh": tip_map.get(dim, {}).get("zh", "")})
        return {
            "score": score, "lvl": lvl + 1, "icon": icon,
            "en_name": en_name, "zh_name": zh_name,
            "details": details, "max_score": 100,
            "cur_threshold": cur_threshold, "next_threshold": next_threshold,
            "gap": gap, "next_icon": next_icon, "next_en": next_en, "next_zh": next_zh,
            "tips": tips,
        }
    except Exception:
        return {}

def generate_dashboard():
    """Generate a self-contained HTML dashboard and open in browser."""
    local = scan()
    usage, _ = get_usage()
    remotes = load_remotes()
    machines = [local] + [r for r in remotes]
    sub = CFG.get("subscription", 0)

    tc = sum(m.get("cost", 0) for m in machines)
    ts = sum(m.get("sessions", 0) for m in machines)

    # Merge today across all machines
    today = dict(local.get("today", {}))
    for r in remotes:
        rt = r.get("today", {})
        today["cost"] = today.get("cost", 0) + rt.get("cost", 0)
        today["msgs"] = today.get("msgs", 0) + rt.get("msgs", 0)

    # Merge daily across all machines
    daily = {}
    for m in machines:
        for date, v in m.get("daily", {}).items():
            if date not in daily:
                daily[date] = {"cost": 0.0, "msgs": 0, "tokens": 0}
            daily[date]["cost"] += v.get("cost", 0)
            daily[date]["msgs"] += v.get("msgs", 0)
            daily[date]["tokens"] += v.get("tokens", 0)

    # Merge hourly across all machines
    hourly = {}
    for m in machines:
        for h, cnt in m.get("hourly", {}).items():
            h_str = str(h)
            hourly[h_str] = hourly.get(h_str, 0) + cnt

    # Merge models across all machines
    models = {}
    for m in machines:
        for model, data in m.get("models", {}).items():
            if model not in models:
                models[model] = {"msgs": 0, "tokens": 0, "cost": 0.0}
            models[model]["msgs"] += data.get("msgs", 0)
            models[model]["tokens"] += data.get("tokens", 0)
            models[model]["cost"] += data.get("cost", 0)

    # Merge projects across all machines
    projects = {}
    for m in machines:
        for proj, v in m.get("projects", {}).items():
            if proj not in projects:
                projects[proj] = {"cost": 0.0, "msgs": 0, "tokens": 0}
            projects[proj]["cost"] += v.get("cost", 0)
            projects[proj]["msgs"] += v.get("msgs", 0)
            projects[proj]["tokens"] += v.get("tokens", 0)

    machine_data = [{"name": m.get("machine", "?"), "cost": round(m.get("cost", 0), 2),
                     "sessions": m.get("sessions", 0)} for m in machines]
    model_display = {}
    model_msgs = {}
    for k, v in models.items():
        short = MODEL_SHORT.get(k, k.split("-")[-1] if "-" in k else k[:15])
        model_display[short] = round(v["cost"], 2)
        model_msgs[short] = v["msgs"]

    # Token composition
    total_inp = sum(m.get("inp", 0) + m.get("input_tokens", 0) for m in machines)
    total_out = sum(m.get("out", 0) + m.get("output_tokens", 0) for m in machines)
    total_cw = sum(m.get("cw", 0) + m.get("cache_write_tokens", 0) for m in machines)
    total_cr = sum(m.get("cr", 0) + m.get("cache_read_tokens", 0) for m in machines)
    total_tokens = total_inp + total_out + total_cw + total_cr

    # Date range across all machines
    dmin_all = local.get("d_min")
    for r in remotes:
        rd = r.get("d_min") or r.get("date_range", {}).get("min")

    # Daily average based on calendar span
    active_days = len([v for v in daily.values() if v.get("cost", 0) > 0])
    if dmin_all:
        span_days = (datetime.now() - datetime.strptime(dmin_all, "%Y-%m-%d")).days + 1
    else:
        span_days = max(active_days, 1)
    daily_avg = round(tc / max(span_days, 1), 2)
    limits = {}
    if usage:
        for key in ["five_hour", "seven_day", "seven_day_sonnet", "seven_day_opus"]:
            obj = usage.get(key)
            if obj and obj.get("utilization") is not None:
                limits[key] = {"util": obj["utilization"], "resets_at": obj.get("resets_at", "")}
        if rd and (not dmin_all or rd < dmin_all): dmin_all = rd
    roi = {}
    if sub > 0 and dmin_all:
        first = datetime.strptime(dmin_all, "%Y-%m-%d")
        months = max((datetime.now() - first).days / 30.0, 1)
        paid = sub * months
        roi = {"sub": sub, "months": round(months, 1), "paid": round(paid, 0),
               "cost": round(tc, 2), "multiplier": round(tc / paid, 1)}

    # v3: Merge daily_models across machines
    daily_models = {}
    for m in machines:
        for date, models_d in m.get("daily_models", {}).items():
            if date not in daily_models:
                daily_models[date] = {}
            for model, v in models_d.items():
                if model not in daily_models[date]:
                    daily_models[date][model] = {"cost": 0.0, "msgs": 0}
                daily_models[date][model]["cost"] += v.get("cost", 0)
                daily_models[date][model]["msgs"] += v.get("msgs", 0)

    # v3: Merge daily_hourly (weekday × hour heatmap)
    heatmap = {}  # {weekday: {hour: count}}
    for m in machines:
        for wd, hours_d in m.get("daily_hourly", {}).items():
            wd_s = str(wd)
            if wd_s not in heatmap:
                heatmap[wd_s] = {}
            for h, cnt in hours_d.items():
                h_s = str(h)
                heatmap[wd_s][h_s] = heatmap[wd_s].get(h_s, 0) + cnt

    # v3: Merge sessions_by_day
    sessions_by_day = {}
    for m in machines:
        for date, sess_list in m.get("sessions_by_day", {}).items():
            if date not in sessions_by_day:
                sessions_by_day[date] = []
            sessions_by_day[date].extend(sess_list)
    # Cap and sort by cost desc
    for date in sessions_by_day:
        sessions_by_day[date] = sorted(sessions_by_day[date], key=lambda x: -x.get("cost", 0))[:30]

    # v3: Forecast — project current month total based on 7-day average
    forecast = {}
    sorted_dates = sorted(daily.keys())
    if len(sorted_dates) >= 3:
        recent_7 = [daily[d]["cost"] for d in sorted_dates[-7:]]
        avg_7d = sum(recent_7) / len(recent_7)
        today_dt = datetime.now()
        days_in_month = 30  # simplified
        try:
            import calendar
            days_in_month = calendar.monthrange(today_dt.year, today_dt.month)[1]
        except Exception: pass
        month_prefix = today_dt.strftime("%Y-%m")
        month_actual = sum(daily[d]["cost"] for d in daily if d[:7] == month_prefix)
        days_left = days_in_month - today_dt.day
        projected = month_actual + (avg_7d * max(days_left, 0))
        forecast = {"projected": round(projected, 0), "avg_7d": round(avg_7d, 2),
                    "days_left": days_left, "month_actual": round(month_actual, 2)}

    # v3: Anomaly detection — days where cost > 2x trailing 30-day average
    anomaly_dates = []
    for idx, date in enumerate(sorted_dates):
        window = [daily[d]["cost"] for d in sorted_dates[max(0, idx-30):idx]]
        if len(window) >= 3:
            avg = sum(window) / len(window)
            if avg > 0 and daily[date]["cost"] > avg * 2:
                anomaly_dates.append(date)

    # v3: daily_models for payload (round costs)
    dm_payload = {}
    for date, models_d in sorted(daily_models.items()):
        dm_payload[date] = {m: round(v["cost"], 2) for m, v in models_d.items()}

    payload = json.dumps({
        "daily": {k: {"cost": round(v["cost"], 2), "msgs": v["msgs"], "tokens": v["tokens"],
                       "sessions": v.get("sessions", 0)}
                  for k, v in sorted(daily.items()) if v.get("cost", 0) > 0 or v.get("msgs", 0) > 0},
        "hourly": {str(k): v for k, v in sorted(hourly.items())},
        "models": model_display, "model_msgs": model_msgs,
        "projects": {k: {"cost": round(v["cost"], 2), "msgs": v["msgs"]}
                     for k, v in sorted(projects.items(), key=lambda x: -x[1]["cost"])[:15]},
        "machines": machine_data, "limits": limits, "roi": roi,
        "today": {"cost": round(today.get("cost", 0), 2), "msgs": today.get("msgs", 0)},
        "total": {"cost": round(tc, 2), "sessions": ts, "tokens": total_tokens,
                  "inp": total_inp, "out": total_out, "cw": total_cw, "cr": total_cr},
        "daily_avg": daily_avg, "active_days": active_days, "span_days": span_days,
        "daily_models": dm_payload,
        "heatmap": heatmap,
        "sessions_by_day": sessions_by_day,
        "forecast": forecast,
        "anomaly_dates": anomaly_dates,
        "level": _build_level_data(),
        "lang": LANG, "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)

    html = _build_dashboard_html(payload)
    # Atomic file write: tmp + rename to avoid race condition
    DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = DASHBOARD_FILE.with_suffix(".tmp")
    tmp_path.write_text(html)
    os.rename(str(tmp_path), str(DASHBOARD_FILE))
    return str(DASHBOARD_FILE)

def _build_dashboard_html(payload):
    """Build self-contained HTML string for dashboard. All data comes from trusted local caches.
    Uses string.replace() instead of f-string to avoid brace escaping nightmares with JS."""
    template = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Claude Code Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif}
.header{padding:24px 32px 8px;display:flex;justify-content:space-between;align-items:baseline}
.header h1{font-size:22px;color:#e6edf3;font-weight:600}.header .meta{color:#8b949e;font-size:12px}
.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px;padding:14px 32px 32px;max-width:1440px;margin:0 auto}
.card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px}
.s2{grid-column:span 2}.s3{grid-column:span 3}.s4{grid-column:span 4}.s6{grid-column:span 6}.s8{grid-column:span 8}.s12{grid-column:span 12}
.kpi{text-align:center;padding:12px 8px}.kpi .v{font-size:24px;font-weight:700;color:#e6edf3;margin:6px 0 3px}
.kpi .l{font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:.5px}
.kpi .u{font-size:11px;color:#8b949e;margin-top:2px}
.kpi.c1 .v{color:#58d4ab}.kpi.c2 .v{color:#58a6ff}.kpi.c3 .v{color:#d4a04a}
.kpi.c4 .v{color:#3fb950}.kpi.c5 .v{color:#a371f7}.kpi.c6 .v{color:#d2a8ff}
.ch{width:100%;height:300px}.cht{width:100%;height:300px}
h3{font-size:12px;color:#8b949e;font-weight:500;margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px}
.empty{color:#484f58;text-align:center;padding-top:80px;font-size:13px}
@media(max-width:900px){.grid{grid-template-columns:repeat(6,1fr)}.s2{grid-column:span 3}.s8,.s6,.s4{grid-column:span 6}}
@media(max-width:600px){.grid{grid-template-columns:1fr;padding:12px}[class*="s"]{grid-column:span 1}}
</style></head><body>
<div class="header"><h1 id="T"></h1><span class="meta" id="G"></span></div>
<div class="grid">
<!-- 6 KPI cards -->
<div class="card s2 kpi c1"><div class="l" id="k1l"></div><div class="v" id="k1v"></div><div class="u" id="k1u"></div></div>
<div class="card s2 kpi c2"><div class="l" id="k2l"></div><div class="v" id="k2v"></div><div class="u" id="k2u"></div></div>
<div class="card s2 kpi c3"><div class="l" id="k3l"></div><div class="v" id="k3v"></div><div class="u" id="k3u"></div></div>
<div class="card s2 kpi c4"><div class="l" id="k4l"></div><div class="v" id="k4v"></div><div class="u" id="k4u"></div></div>
<div class="card s2 kpi c5"><div class="l" id="k5l"></div><div class="v" id="k5v"></div><div class="u" id="k5u"></div></div>
<div class="card s2 kpi c6"><div class="l" id="k6l"></div><div class="v" id="k6v"></div><div class="u" id="k6u"></div></div>
<!-- Row 2: Daily trend (dual axis) full width -->
<div class="card s12"><h3 id="h1"></h3><div id="c1" class="ch"></div></div>
<!-- Row 3: Model + Token composition + Rate limits -->
<div class="card s4"><h3 id="h2"></h3><div id="c2" class="ch"></div></div>
<div class="card s4"><h3 id="h7"></h3><div id="c7" class="ch"></div></div>
<div class="card s4"><h3 id="h5"></h3><div id="c5" class="ch"></div></div>
<!-- Row 4: Hourly + Projects -->
<div class="card s6"><h3 id="h3"></h3><div id="c3" class="ch"></div></div>
<div class="card s6"><h3 id="h4"></h3><div id="c4" class="ch"></div></div>
<!-- Row 5: Machines + Daily detail table -->
<div class="card s4" id="card6"><h3 id="h6"></h3><div id="c6" class="ch"></div></div>
<div class="card s8" id="card8"><h3 id="h8"></h3><div id="c8" style="max-height:400px;overflow-y:auto"></div></div>
<!-- Level Panel -->
<div class="card s12" id="cardLevel" style="display:none"><div id="levelPanel"></div></div>
<!-- Fun panels -->
<div class="card s12" id="cardBurn" style="text-align:center;padding:16px"><div id="burnCounter"></div></div>
<div class="card s6" id="cardWrapped"><div id="wrappedPanel"></div></div>
<div class="card s6" id="cardEquiv"><div id="equivPanel"></div></div>
<div class="card s12" id="cardBadges"><div id="badgesPanel"></div></div>
</div>
<script>
const D=__DATA__;
const zh=D.lang==='zh';
const t=k=>({title:zh?'Claude Code 用量看板详情':'Claude Code Usage Dashboard',
today:zh?'今日':'Today',total:zh?'累计费用':'Total Cost',sessions:zh?'会话':'Sessions',
roi:'ROI',tokens:zh?'总 Tokens':'Total Tokens',avg:zh?'日均费用':'Daily Avg',
daily:zh?'每日费用 & 消息趋势':'Daily Cost & Message Trend',
model:zh?'模型费用分布':'Model Cost Distribution',
token_comp:zh?'Token 构成':'Token Composition',
hourly:zh?'24 小时活跃分布':'24-Hour Activity',project:zh?'项目费用排行':'Project Cost Ranking',
limits:zh?'用量限额':'Rate Limits',machines:zh?'设备费用对比':'Machine Cost Comparison',
detail:zh?'每日明细':'Daily Breakdown',
cost:zh?'费用':'Cost',msgs:zh?'消息':'Msgs',days:zh?'天':'days',
input:zh?'输入':'Input',output:zh?'输出':'Output',cache_w:zh?'缓存写':'Cache W',cache_r:zh?'缓存读':'Cache R'
})[k]||k;
const fc=n=>n>=1e4?'$'+n.toLocaleString('en',{maximumFractionDigits:0}):'$'+n.toFixed(2);
const fk=n=>{if(zh){if(n>=1e8)return(n/1e8).toFixed(1)+' \u4ebf';if(n>=1e4)return(n/1e4).toFixed(0)+' \u4e07';return n.toLocaleString();}return n>=1e9?(n/1e9).toFixed(1)+'B':n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(0)+'K':n;};
const C={p:'#58a6ff',t:'#58d4ab',g:'#d4a04a',d:'#f85149',w:'#d29922',op:'#a371f7',sn:'#58a6ff',hk:'#3fb950',m:'#484f58'};
const tt={backgroundColor:'#1c2128',borderColor:'#30363d',textStyle:{color:'#c9d1d9'}};
const ax={axisLine:{lineStyle:{color:'#30363d'}},splitLine:{lineStyle:{color:'#21262d'}},axisLabel:{color:'#8b949e',fontSize:10}};
const $=id=>document.getElementById(id);

// Header
$('T').textContent=t('title');$('G').textContent=D.generated;

// 6 KPI Cards
$('k1l').textContent=t('today');$('k1v').textContent=fc(D.today.cost);$('k1u').textContent=D.today.msgs+' '+t('msgs');
$('k2l').textContent=t('total');$('k2v').textContent=fc(D.total.cost);$('k2u').textContent=D.span_days+' '+t('days');
$('k3l').textContent=t('roi');
if(D.roi.multiplier){$('k3v').textContent=D.roi.multiplier+'x';$('k3u').textContent=fc(D.roi.cost)+' / $'+D.roi.paid;}
else{$('k3v').textContent='\u2014';$('k3u').textContent='';}
$('k4l').textContent=t('sessions');$('k4v').textContent=D.total.sessions.toLocaleString();$('k4u').textContent=D.machines.length+' machines';
$('k5l').textContent=t('tokens');$('k5v').textContent=fk(D.total.tokens);$('k5u').textContent='in+out+cache';
$('k6l').textContent=t('avg');$('k6v').textContent=fc(D.daily_avg);$('k6u').textContent='/day';

// 1. Daily Cost + Messages (dual Y axis, full width)
$('h1').textContent=t('daily');
const dd=Object.keys(D.daily),dCost=dd.map(d=>D.daily[d].cost),dMsgs=dd.map(d=>D.daily[d].msgs);
echarts.init($('c1')).setOption({
tooltip:{...tt,trigger:'axis',formatter:p=>{let s=p[0].name;p.forEach(x=>{s+='<br/>'+x.marker+x.seriesName+': '+(x.seriesIndex===0?fc(x.value):x.value);});return s;}},
legend:{data:[t('cost'),t('msgs')],textStyle:{color:'#8b949e'},top:0,right:60},
xAxis:{type:'category',data:dd,...ax,axisLabel:{...ax.axisLabel,formatter:v=>v.slice(5)}},
yAxis:[{type:'value',...ax,axisLabel:{...ax.axisLabel,formatter:v=>'$'+v}},
{type:'value',...ax,axisLabel:{...ax.axisLabel},splitLine:{show:false}}],
series:[
{name:t('cost'),type:'bar',data:dCost,barWidth:'60%',itemStyle:{color:C.t,borderRadius:[3,3,0,0]},yAxisIndex:0},
{name:t('msgs'),type:'line',data:dMsgs,smooth:true,symbol:'none',lineStyle:{color:C.p,width:2},yAxisIndex:1}],
dataZoom:[{type:'inside'},{type:'slider',height:18,bottom:0,borderColor:'#30363d',backgroundColor:'#161b22',
fillerColor:'rgba(88,212,171,0.1)',handleStyle:{color:'#58d4ab'},textStyle:{color:'#8b949e'}}],
grid:{left:55,right:55,top:30,bottom:38}});

// 2. Model Distribution (auto: donut if balanced, bars if one dominates)
$('h2').textContent=t('model');
const mClr={};Object.keys(D.models).forEach(k=>{const l=k.toLowerCase();mClr[k]=l.includes('opus')?C.op:l.includes('haiku')?C.hk:C.sn;});
const mTotal=Object.values(D.models).reduce((a,b)=>a+b,0)||1;
const mMax=Math.max(...Object.values(D.models));
if(mMax/mTotal>0.9){
// One model dominates >90% — use horizontal bars with labels for readability
const mEntries=Object.entries(D.models).sort((a,b)=>b[1]-a[1]);
const mMsgs=D.model_msgs||{};
let mHtml='';
mEntries.forEach(([k,v])=>{const pct=v/mTotal*100;const msgs=mMsgs[k]||0;
mHtml+='<div style="margin:12px 0"><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px">'
+'<span style="color:'+(mClr[k]||C.m)+';font-weight:600">'+k+'</span>'
+'<span style="color:#8b949e">'+fc(v)+' \u00b7 '+msgs.toLocaleString()+' msgs \u00b7 '+pct.toFixed(1)+'%</span></div>'
+'<div style="background:#21262d;border-radius:4px;height:8px;overflow:hidden">'
+'<div style="background:'+(mClr[k]||C.m)+';height:100%;border-radius:4px;width:'+Math.max(pct,0.8)+'%"></div>'
+'</div></div>';});
$('c2').style.cssText='padding:5px 0';$('c2').className='';
$('c2').insertAdjacentHTML('beforeend',mHtml);
}else{
echarts.init($('c2')).setOption({
tooltip:{...tt,formatter:p=>p.name+': '+fc(p.value)+' ('+p.percent+'%)'},
series:[{type:'pie',radius:['40%','68%'],center:['50%','55%'],
label:{color:'#c9d1d9',fontSize:10,formatter:'{b}\n{d}%'},
data:Object.entries(D.models).map(([k,v])=>({name:k,value:v,itemStyle:{color:mClr[k]||C.m}}))}]});
}

// 7. Token Composition (progress bars via DOM)
$('h7').textContent=t('token_comp');
const tk=D.total,tkAll=tk.inp+tk.out+tk.cw+tk.cr||1;
const tkItems=[{l:t('cache_r'),v:tk.cr,c:'#a371f7'},{l:t('cache_w'),v:tk.cw,c:'#d4a04a'},
{l:t('output'),v:tk.out,c:'#58d4ab'},{l:t('input'),v:tk.inp,c:'#58a6ff'}];
let tkHtml='';
tkItems.forEach(x=>{const pct=(x.v/tkAll*100);
tkHtml+='<div style="margin:10px 0"><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:11px">'
+'<span style="color:#c9d1d9">'+x.l+'</span><span style="color:#8b949e">'+fk(x.v)+' ('+pct.toFixed(1)+'%)</span></div>'
+'<div style="background:#21262d;border-radius:4px;height:8px;overflow:hidden">'
+'<div style="background:'+x.c+';height:100%;border-radius:4px;width:'+Math.max(pct,0.5)+'%"></div>'
+'</div></div>';});
$('c7').style.cssText='padding:5px 0';$('c7').className='';
$('c7').insertAdjacentHTML('beforeend',tkHtml);

// 5. Rate Limits (battery-style progress bars)
$('h5').textContent=t('limits');
const ln={five_hour:'Session (5h)',seven_day:'Weekly (7d)',seven_day_sonnet:'Sonnet',seven_day_opus:'Opus'};
const le=Object.entries(D.limits);
if(le.length>0){
let limHtml='';
le.forEach(([k,v])=>{
const name=ln[k]||k;const pct=Math.round(v.util);
const barColor=pct>=80?C.d:pct>=60?C.w:C.t;
const rst=v.resets_at;let rstLabel='';
if(rst){try{const rt=new Date(rst);const now=new Date();const diff=Math.max(0,rt-now);
const h=Math.floor(diff/3600000);const m=Math.floor((diff%3600000)/60000);
rstLabel=h>0?(h+'h'+m+'m'):(m+'m');}catch(e){}}
limHtml+='<div style="margin:14px 0">'
+'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px">'
+'<span style="color:#e6edf3;font-size:13px;font-weight:600">'+name+'</span>'
+'<span style="font-size:11px;color:#8b949e">'
+'<span style="color:'+barColor+';font-weight:700;font-size:16px">'+pct+'%</span>'
+(rstLabel?(' \u00b7 \u21bb '+rstLabel):'')+'</span></div>'
+'<div style="background:#21262d;border-radius:5px;height:14px;overflow:hidden;position:relative">'
+'<div style="background:linear-gradient(90deg,'+barColor+','+barColor+'cc);height:100%;border-radius:5px;width:'+Math.max(pct,1)+'%;'
+'box-shadow:0 0 8px '+barColor+'30"></div>'
+(pct<80?'<div style="position:absolute;left:80%;top:0;bottom:0;width:1px;background:#484f58" title="80%"></div>':'')
+'</div></div>';});
$('c5').style.cssText='padding:8px 0';$('c5').className='';
$('c5').insertAdjacentHTML('beforeend',limHtml);
}else{$('c5').textContent='No data';$('c5').className='empty';}

// 3. Activity Heatmap (7x24)
$('h3').textContent=zh?'活动热力图':'Activity Heatmap';
(function(){
var hm=D.heatmap||{};
var wdays=zh?['周一','周二','周三','周四','周五','周六','周日']:['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
var hrs=[];for(var h=0;h<24;h++)hrs.push(String(h).padStart(2,'0'));
var data=[],mx=0;
for(var wd=0;wd<7;wd++){var wdD=hm[String(wd)]||{};for(var hr=0;hr<24;hr++){var v=wdD[String(hr)]||0;data.push([hr,wd,v]);if(v>mx)mx=v;}}
echarts.init($('c3')).setOption({
tooltip:{backgroundColor:'#1c2128',borderColor:'#30363d',textStyle:{color:'#c9d1d9'},formatter:function(p){return wdays[p.value[1]]+' '+hrs[p.value[0]]+':00 — '+p.value[2]+(zh?' 条消息':' msgs');}},
grid:{left:50,right:30,top:10,bottom:55},
xAxis:{type:'category',data:hrs,axisLabel:{color:'#8b949e',fontSize:10,interval:2},axisLine:{lineStyle:{color:'#30363d'}}},
yAxis:{type:'category',data:wdays,axisLabel:{color:'#8b949e',fontSize:11},axisLine:{lineStyle:{color:'#30363d'}}},
visualMap:{min:0,max:mx||1,calculable:false,orient:'horizontal',left:'center',bottom:4,itemWidth:12,itemHeight:360,textStyle:{color:'#8b949e',fontSize:9},inRange:{color:['#161b22','#0e4429','#006d32','#26a641','#39d353']}},
series:[{type:'heatmap',data:data,label:{show:false},itemStyle:{borderColor:'#0d1117',borderWidth:2,borderRadius:2},emphasis:{itemStyle:{borderColor:'#58a6ff'}}}]});
})();

// 4. Project Ranking (horizontal bar)
$('h4').textContent=t('project');
const pe=Object.entries(D.projects).slice(0,10).map(([k,v])=>[k,v.cost]);
const pn=pe.map(e=>e[0]).reverse(),pc=pe.map(e=>e[1]).reverse();
echarts.init($('c4')).setOption({
tooltip:{...tt,formatter:p=>p.name+': '+fc(p.value)},
xAxis:{type:'value',...ax,axisLabel:{...ax.axisLabel,formatter:v=>'$'+v}},
yAxis:{type:'category',data:pn,...ax,axisLabel:{...ax.axisLabel,width:75,overflow:'truncate'}},
series:[{type:'bar',data:pc,barWidth:'55%',itemStyle:{color:C.g,borderRadius:[0,4,4,0]},
label:{show:true,position:'right',color:'#8b949e',fontSize:9,formatter:p=>fc(p.value)}}],
grid:{left:85,right:55,top:8,bottom:28}});

// 6. Machines — hide if single, expand table to full width
if(D.machines.length>1){
$('h6').textContent=t('machines');
echarts.init($('c6')).setOption({
tooltip:{...tt},
xAxis:{type:'category',data:D.machines.map(m=>m.name),...ax,axisLabel:{...ax.axisLabel,fontSize:9}},
yAxis:{type:'value',...ax,axisLabel:{...ax.axisLabel,formatter:v=>'$'+v}},
series:[{type:'bar',data:D.machines.map(m=>({value:m.cost,itemStyle:{color:C.t,borderRadius:[4,4,0,0]}})),
barWidth:'45%',label:{show:true,position:'top',color:'#8b949e',fontSize:10,formatter:p=>fc(p.value)}}],
grid:{left:50,right:12,top:25,bottom:28}});
}else{$('card6').style.display='none';$('card8').style.gridColumn='span 12';}

// 8. Daily Detail Table — all dates filled, all expandable, no sessions column
$('h8').textContent=zh?'每日明细':'Daily Details';
(function(){
var daily=D.daily||{};var sessions=D.sessions_by_day||{};
// Fill all dates from d_min to today (no gaps)
var allDates=Object.keys(daily);
var minD=allDates.length?allDates.sort()[0]:null;
if(minD){var cur=new Date(minD+'T00:00:00');var today=new Date();today.setHours(0,0,0,0);
while(cur<=today){var ds=cur.toISOString().slice(0,10);if(!daily[ds])daily[ds]={cost:0,msgs:0,tokens:0};
cur.setDate(cur.getDate()+1);}}
var dates=Object.keys(daily).sort().reverse();
var tbl=document.createElement('table');
tbl.style.cssText='width:100%;border-collapse:collapse;font-size:12px;font-family:Menlo,monospace';
var thead=tbl.createTHead();var hdr=thead.insertRow();
[zh?'日期':'Date',zh?'费用':'Cost',zh?'消息':'Msgs','Tokens'].forEach(function(h){
var th=document.createElement('th');th.textContent=h;
th.style.cssText='text-align:right;padding:6px 8px;color:#8b949e;border-bottom:1px solid #30363d;font-weight:500';
if(h===(zh?'日期':'Date'))th.style.textAlign='left';hdr.appendChild(th);});
var tbody=tbl.createTBody();
var noData=zh?'当天没有消耗 Token':'No token usage this day';
dates.forEach(function(d){
var row=daily[d];var isEmpty=(row.cost||0)===0&&(row.msgs||0)===0;
var hasSess=sessions[d]&&sessions[d].length>0;
var tr=tbody.insertRow();
tr.setAttribute('data-date',d);
tr.style.cssText='cursor:pointer';
tr.onmouseenter=function(){this.style.background='rgba(88,166,255,0.06)';};
tr.onmouseleave=function(){this.style.background='';};
if(isEmpty){
[{v:'\u25b6 '+d.slice(5),a:'left'},{v:'\u2014',a:'right'},{v:'\u2014',a:'right'},{v:'\u2014',a:'right'}].forEach(function(c){
var td=tr.insertCell();td.textContent=c.v;td.style.cssText='padding:5px 8px;border-bottom:1px solid #21262d;color:#484f58;text-align:'+c.a;});
var emptyRow=tbody.insertRow();emptyRow.style.display='none';emptyRow.setAttribute('data-parent',d);
var etd=emptyRow.insertCell();etd.colSpan=4;etd.textContent=noData;
etd.style.cssText='padding:8px 8px 8px 24px;color:#484f58;font-style:italic;border-bottom:1px solid #1a1f26;font-size:11px';
}else{
[{v:'\u25b6 '+d.slice(5),a:'left'},{v:fc(row.cost||0),a:'right'},{v:(row.msgs||0).toLocaleString(),a:'right'},{v:fk(row.tokens||0),a:'right'}].forEach(function(c){
var td=tr.insertCell();td.textContent=c.v;td.style.cssText='padding:5px 8px;border-bottom:1px solid #21262d;color:#c9d1d9;text-align:'+c.a;});
if(hasSess){sessions[d].forEach(function(s){
var sr=tbody.insertRow();sr.style.display='none';sr.setAttribute('data-parent',d);
[{v:'  '+(s.project||'\u2014'),a:'left'},{v:fc(s.cost||0),a:'right'},{v:s.msgs||0,a:'right'},{v:s.model||'\u2014',a:'right'}].forEach(function(c){
var td=sr.insertCell();td.textContent=c.v;td.style.cssText='padding:3px 8px;border-bottom:1px solid #1a1f26;color:#8b949e;text-align:'+c.a+';font-size:11px';});});}
else{var nr=tbody.insertRow();nr.style.display='none';nr.setAttribute('data-parent',d);
var ntd=nr.insertCell();ntd.colSpan=4;ntd.textContent=zh?'无 Session 明细（来自远程同步）':'No session details (from remote sync)';
ntd.style.cssText='padding:6px 8px 6px 24px;color:#484f58;font-style:italic;border-bottom:1px solid #1a1f26;font-size:11px';}}});
tbody.addEventListener('click',function(e){
var tr=e.target.closest('tr[data-date]');if(!tr||tr.getAttribute('data-parent'))return;
var d=tr.getAttribute('data-date');var subs=tbody.querySelectorAll('tr[data-parent="'+d+'"]');
if(!subs.length)return;
var hidden=subs[0].style.display==='none';
subs.forEach(function(s){s.style.display=hidden?'':'none';});
tr.cells[0].textContent=(hidden?'\u25bc ':'\u25b6 ')+d.slice(5);});
$('c8').appendChild(tbl);
})();

// 9. Level Panel (radar + progress bars + tips)
(function(){
var L=D.level;if(!L||!L.score&&L.score!==0)return;
$('cardLevel').style.display='';
var name=zh?L.zh_name:L.en_name;
var nextName=zh?L.next_zh:L.next_en;
var dimLabels={usage:zh?'使用深度':'Usage',context:zh?'上下文':'Context',tools:zh?'工具生态':'Tools',automation:zh?'自动化':'Automation',scale:zh?'规模化':'Scale'};
var dimOrder=['usage','context','tools','automation','scale'];
var det=L.details||{};

// Build layout: left radar (40%) + right details (60%)
var html='<div style="display:flex;gap:20px;flex-wrap:wrap">';

// Left: title + radar + progress
html+='<div style="flex:0 0 38%;min-width:260px">';
html+='<div style="font-size:16px;color:#e6edf3;font-weight:700;margin-bottom:4px">'+L.icon+' Lv.'+L.lvl+' '+name+'</div>';
html+='<div style="color:#8b949e;font-size:12px;margin-bottom:12px">'+L.score+' / '+L.max_score+(zh?' 分':' pts')+'</div>';
html+='<div id="radarChart" style="width:100%;height:220px"></div>';
// XP progress bar to next level
var progress=L.next_threshold>L.cur_threshold?((L.score-L.cur_threshold)/(L.next_threshold-L.cur_threshold)*100):100;
html+='<div style="margin-top:8px">';
html+='<div style="display:flex;justify-content:space-between;font-size:11px;color:#8b949e;margin-bottom:4px">';
html+='<span>'+L.icon+' Lv.'+L.lvl+'</span>';
if(L.next_icon)html+='<span>'+L.next_icon+' Lv.'+(L.lvl+1)+' '+nextName+'</span>';
else html+='<span>MAX</span>';
html+='</div>';
html+='<div style="background:#21262d;border-radius:6px;height:10px;overflow:hidden">';
html+='<div style="background:linear-gradient(90deg,#58d4ab,#58a6ff);height:100%;border-radius:6px;width:'+Math.min(progress,100)+'%"></div>';
html+='</div>';
if(L.gap>0)html+='<div style="color:#8b949e;font-size:11px;margin-top:4px;text-align:center">'+(zh?'还差 '+L.gap+' 分升级':''+L.gap+' pts to next level')+'</div>';
html+='</div>';
html+='</div>';

// Right: dimension bars + tips
html+='<div style="flex:1;min-width:280px">';
html+='<div style="font-size:13px;color:#8b949e;font-weight:500;text-transform:uppercase;letter-spacing:.5px;margin-bottom:12px">'+(zh?'五维评分':'Dimension Scores')+'</div>';
dimOrder.forEach(function(dim){
var val=det[dim]||0;var pct=val/20*100;
var barColor=val>=16?'#58d4ab':val>=10?'#58a6ff':val>=6?'#d29922':'#f85149';
html+='<div style="margin:10px 0">';
html+='<div style="display:flex;justify-content:space-between;margin-bottom:3px;font-size:12px">';
html+='<span style="color:#c9d1d9">'+(dimLabels[dim]||dim)+'</span>';
html+='<span style="color:'+barColor+';font-weight:600">'+val+'/20</span></div>';
html+='<div style="background:#21262d;border-radius:4px;height:8px;overflow:hidden">';
html+='<div style="background:'+barColor+';height:100%;border-radius:4px;width:'+pct+'%"></div>';
html+='</div></div>';});

// Upgrade tips
if(L.tips&&L.tips.length>0){
html+='<div style="margin-top:16px;padding:12px;background:#1c2128;border-radius:8px;border:1px solid #30363d">';
html+='<div style="font-size:12px;color:#d4a04a;font-weight:600;margin-bottom:8px">'+(zh?'💡 升级建议':'💡 Upgrade Tips')+'</div>';
L.tips.forEach(function(tip){
html+='<div style="font-size:11px;color:#c9d1d9;margin:6px 0">';
html+='<span style="color:#8b949e">'+(dimLabels[tip.dim]||tip.dim)+' ('+tip.score+'/'+tip.max+')</span> → ';
html+=(zh?tip.tip_zh:tip.tip_en);
html+='</div>';});
html+='</div>';}
html+='</div></div>';

$('levelPanel').insertAdjacentHTML('beforeend',html);

// Render radar chart
var chart=echarts.init($('radarChart'));
chart.setOption({
radar:{indicator:dimOrder.map(function(d){return{name:dimLabels[d]||d,max:20};}),
shape:'polygon',radius:'70%',center:['50%','55%'],
axisName:{color:'#8b949e',fontSize:10},
axisLine:{lineStyle:{color:'#30363d'}},splitLine:{lineStyle:{color:'#21262d'}},splitArea:{areaStyle:{color:['transparent','rgba(88,212,171,0.03)']}}},
series:[{type:'radar',symbol:'circle',symbolSize:6,
lineStyle:{color:'#58d4ab',width:2},
areaStyle:{color:'rgba(88,212,171,0.15)'},
itemStyle:{color:'#58d4ab',borderColor:'#161b22',borderWidth:2},
data:[{value:dimOrder.map(function(d){return det[d]||0;})}]}]});
window.addEventListener('resize',function(){chart.resize();});
})();

// ═══ FUN FEATURES ═══

// F1. Live Burn Counter (taxi-meter style)
(function(){
var dailyVals=Object.values(D.daily).map(function(d){return d.cost||0;});
var avg7=dailyVals.slice(-7).reduce(function(a,b){return a+b;},0)/Math.max(dailyVals.slice(-7).length,1);
var perSec=avg7/86400;
if(perSec<=0){$('cardBurn').style.display='none';return;}
var base=D.total.cost;var startTime=Date.now();
var el=$('burnCounter');
el.insertAdjacentHTML('beforeend','<div style="font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">'+(zh?'\u5b9e\u65f6\u71c3\u70e7\u8ba1\u6570\u5668':'LIVE BURN COUNTER')+'</div><div id="burnNum" style="font-size:36px;font-weight:700;color:#58d4ab;font-family:Menlo,monospace"></div><div style="font-size:11px;color:#484f58;margin-top:4px">'+(zh?'\u57fa\u4e8e\u8fd1 7 \u5929\u65e5\u5747 '+fc(avg7)+' \u7684\u6d88\u8017\u901f\u7387':'Based on 7-day avg of '+fc(avg7)+'/day')+'</div>');
var numEl=document.getElementById('burnNum');
setInterval(function(){var elapsed=(Date.now()-startTime)/1000;numEl.textContent=fc(base+perSec*elapsed);},80);
})();

// F2. Monthly Wrapped (Spotify-style insights)
(function(){
var daily=D.daily||{};var dates=Object.keys(daily).sort();
if(dates.length<3){$('cardWrapped').style.display='none';return;}
var hourly=D.hourly||{};var projects=D.projects||{};
// Find peak hour
var peakH=0,peakV=0;for(var h in hourly){if(hourly[h]>peakV){peakV=hourly[h];peakH=h;}}
// Find most expensive day
var maxDay='',maxCost=0;dates.forEach(function(d){if(daily[d].cost>maxCost){maxCost=daily[d].cost;maxDay=d;}});
// Find top project
var topProj='';var topProjCost=0;for(var p in projects){if(projects[p].cost>topProjCost){topProjCost=projects[p].cost;topProj=p;}}
// Consecutive days streak
var streak=0,cur=0;
for(var i=dates.length-1;i>=0;i--){
if(i===dates.length-1||(new Date(dates[i+1])-new Date(dates[i]))/(86400000)<=1.5){cur++;}
else break;}
streak=cur;
// Output tokens → approx code lines (1 token ≈ 4 chars, 1 line ≈ 60 chars → ~15 tokens/line)
var codeLines=Math.round(D.total.out/15);
var codeLinesStr=codeLines>=10000?(codeLines/1000).toFixed(0)+'K':codeLines.toLocaleString();
// Total messages
var totalMsgs=Object.values(daily).reduce(function(a,d){return a+d.msgs;},0);
// Build wrapped
var html='<div style="font-size:14px;color:#e6edf3;font-weight:700;margin-bottom:14px">'+(zh?'\ud83c\udf81 \u4f7f\u7528\u62a5\u544a':'🎁 Usage Wrapped')+'</div>';
var items=[
{icon:'\u23f0',text:zh?'\u4f60\u6700\u6d3b\u8dc3\u7684\u65f6\u6bb5\u662f <b>'+peakH+':00</b>':'Your peak hour is <b>'+peakH+':00</b>'},
{icon:'\ud83d\udcb8',text:zh?'\u6700\u70e7\u94b1\u7684\u4e00\u5929\u662f <b>'+maxDay+'</b>\uff08'+fc(maxCost)+'\uff09':'Most expensive day: <b>'+maxDay+'</b> ('+fc(maxCost)+')'},
{icon:'\ud83c\udfc6',text:zh?'\u6700\u8017 Token \u7684\u9879\u76ee\u662f <b>'+topProj+'</b>':'Top project: <b>'+topProj+'</b> ('+fc(topProjCost)+')'},
{icon:'\ud83d\udd25',text:zh?'\u8fde\u7eed\u4f7f\u7528 <b>'+streak+' \u5929</b>':'Current streak: <b>'+streak+' days</b>'},
{icon:'\ud83d\udcbb',text:zh?'Claude \u5e2e\u4f60\u751f\u6210\u4e86\u7ea6 <b>'+codeLinesStr+' \u884c\u4ee3\u7801</b>':'Claude generated ~<b>'+codeLinesStr+' lines</b> of code'},
{icon:'\ud83d\udcac',text:zh?'\u603b\u5171\u5bf9\u8bdd <b>'+totalMsgs.toLocaleString()+' \u6761\u6d88\u606f</b>':'Total <b>'+totalMsgs.toLocaleString()+' messages</b>'},
];
items.forEach(function(it){
html+='<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #21262d">';
html+='<span style="font-size:18px;width:28px;text-align:center">'+it.icon+'</span>';
html+='<span style="font-size:12px;color:#c9d1d9">'+it.text+'</span></div>';});
$('wrappedPanel').insertAdjacentHTML('beforeend',html);
})();

// F3. Cost Equivalents (fun conversions)
(function(){
var cost=D.total.cost;if(cost<=0){$('cardEquiv').style.display='none';return;}
var html='<div style="font-size:14px;color:#e6edf3;font-weight:700;margin-bottom:14px">'+(zh?'\u2615 \u8d39\u7528\u7b49\u4ef7\u7269':'☕ Cost Equivalents')+'</div>';
var equivs=zh?[
{v:Math.round(cost/5),u:'\u676f\u661f\u5df4\u514b',icon:'\u2615'},
{v:Math.round(cost/30),u:'\u987f\u5916\u5356',icon:'\ud83c\udf5c'},
{v:Math.round(cost/1299),u:'\u53f0 MacBook Air',icon:'\ud83d\udcbb'},
{v:Math.round(cost/15),u:'\u6708 Netflix',icon:'\ud83c\udfac'},
{v:(cost/500).toFixed(1),u:'\u4e2a\u521d\u7ea7\u5de5\u7a0b\u5e08\u00b7\u5929',icon:'\ud83d\udc68\u200d\ud83d\udcbb'},
{v:Math.round(cost*7500/1e6*1000),u:'\u9875 A4 \u7eb8\u6253\u5370',icon:'\ud83d\udcc4'},
]:[
{v:Math.round(cost/5),u:'Starbucks lattes',icon:'\u2615'},
{v:Math.round(cost/15),u:'lunches',icon:'\ud83c\udf5c'},
{v:Math.round(cost/1299),u:'MacBook Airs',icon:'\ud83d\udcbb'},
{v:Math.round(cost/15),u:'months of Netflix',icon:'\ud83c\udfac'},
{v:(cost/500).toFixed(1),u:'junior dev days',icon:'\ud83d\udc68\u200d\ud83d\udcbb'},
];
equivs.forEach(function(e){
html+='<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #21262d">';
html+='<span style="font-size:18px;width:28px;text-align:center">'+e.icon+'</span>';
html+='<span style="font-size:12px;color:#c9d1d9"><b style="color:#d4a04a;font-size:16px">'+e.v+'</b> '+e.u+'</span></div>';});
$('equivPanel').insertAdjacentHTML('beforeend',html);
})();

// F4. Achievement Badges
(function(){
var daily=D.daily||{};var dates=Object.keys(daily).sort();
var hourly=D.hourly||{};var models=D.models||{};var projects=D.projects||{};
var cost=D.total.cost;var sessions=D.total.sessions;
// Late night usage (0-4)
var lateCount=0;for(var h=0;h<=4;h++)lateCount+=(hourly[String(h)]||0);
// Opus percentage
var modelTotal=Object.values(models).reduce(function(a,b){return a+b;},0)||1;
var opusPct=0;for(var m in models){if(m.toLowerCase().indexOf('opus')>=0)opusPct=models[m]/modelTotal*100;}
// Max session msgs (from sessions_by_day)
var maxSessMsgs=0;var sbd=D.sessions_by_day||{};
for(var d in sbd){sbd[d].forEach(function(s){if(s.msgs>maxSessMsgs)maxSessMsgs=s.msgs;});}
// Max single day cost
var maxDayCost=0;dates.forEach(function(d){if(daily[d].cost>maxDayCost)maxDayCost=daily[d].cost;});
// Consecutive days
var streak=0;for(var i=dates.length-1;i>=0;i--){
if(i===dates.length-1||(new Date(dates[i+1])-new Date(dates[i]))/(86400000)<=1.5)streak++;else break;}
// Project count
var projCount=Object.keys(projects).length;
// Define badges: [id, icon, name_zh, name_en, condition, unlocked]
var badges=[
['cost100','\ud83d\udcb0','\u767e\u5200\u65a9','$100 Club',cost>=100],
['cost1k','\ud83d\udcb5','\u5343\u5200\u65a9','$1K Club',cost>=1000],
['cost3k','\ud83d\udc8e','\u4e09\u5343\u5200\u65a9','$3K Club',cost>=3000],
['night','\ud83c\udf19','\u591c\u732b\u5b50','Night Owl',lateCount>=50],
['night100','\ud83e\udddb','\u5f7b\u591c\u8005','Vampire Coder',lateCount>=200],
['opus90','\ud83d\udc9c','Opus \u4fe1\u5f92','Opus Devotee',opusPct>=90],
['marathon','\ud83c\udfaf','\u4e00\u955c\u5230\u5e95','Marathon Session',maxSessMsgs>=200],
['streak7','\ud83d\udd25','\u4e03\u65e5\u8fde\u51fb','7-Day Streak',streak>=7],
['streak30','\u26a1','\u6708\u5ea6\u8fbe\u4eba','30-Day Streak',streak>=30],
['multi5','\ud83d\udc19','\u591a\u680f\u52a8\u7269','Multi-Project',projCount>=5],
['bigday','\ud83d\udca5','\u5927\u624b\u7b14','Big Spender Day',maxDayCost>=200],
['sess100','\ud83c\udfc5','\u767e\u4f1a\u8fbe\u4eba','100 Sessions',sessions>=100],
];
var unlocked=badges.filter(function(b){return b[4];});
var locked=badges.filter(function(b){return !b[4];});
if(unlocked.length===0&&locked.length===0){$('cardBadges').style.display='none';return;}
var html='<div style="font-size:14px;color:#e6edf3;font-weight:700;margin-bottom:14px">'+(zh?'\ud83c\udfc6 \u6210\u5c31\u5fbd\u7ae0 ('+unlocked.length+'/'+badges.length+')':'🏆 Achievements ('+unlocked.length+'/'+badges.length+')')+'</div>';
html+='<div style="display:flex;flex-wrap:wrap;gap:10px">';
unlocked.forEach(function(b){
html+='<div style="background:#1c2128;border:1px solid #30363d;border-radius:10px;padding:10px 14px;text-align:center;min-width:90px">';
html+='<div style="font-size:24px">'+b[1]+'</div>';
html+='<div style="font-size:10px;color:#58d4ab;margin-top:2px;font-weight:600">'+(zh?b[2]:b[3])+'</div></div>';});
locked.forEach(function(b){
html+='<div style="background:#161b22;border:1px solid #21262d;border-radius:10px;padding:10px 14px;text-align:center;min-width:90px;opacity:0.35">';
html+='<div style="font-size:24px;filter:grayscale(1)">'+b[1]+'</div>';
html+='<div style="font-size:10px;color:#484f58;margin-top:2px">'+(zh?b[2]:b[3])+'</div></div>';});
html+='</div>';
$('badgesPanel').insertAdjacentHTML('beforeend',html);
})();

window.addEventListener('resize',()=>{document.querySelectorAll('.ch,.cht').forEach(el=>{const c=echarts.getInstanceByDom(el);if(c)c.resize();});});
</script></body></html>"""
    return template.replace("__DATA__", payload)

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
    today = local["today"]
    machine_count = len(machines)

    daily = dict(local["daily"])  # convert from defaultdict
    # Sort by date
    daily_sorted = sorted(daily.items(), key=lambda x: x[0])
    # Last 7 days for quick stats (today + 6 preceding days)
    last_7d = [(d, v) for d, v in daily_sorted if d >= (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")]

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
            LINE_COLORS = ["#5CC6A7", "#C9B87A", "#6BA4C9", "#D4CDC0"]   # teal, gold, blue, warm white
        else:
            LINE_COLORS = ["#1A5C4C", "#6B5C28", "#1B5A85", "#2C3040"]   # rich teal, bronze, deep blue, navy
        _color_idx = [0]

        def _gauge_color(pct):
            """Base color by position, overridden by danger at high utilization."""
            idx = _color_idx[0]
            _color_idx[0] += 1
            if pct >= 80: return "#E85838" if DARK else "#C03020"   # red
            if pct >= 60: return "#E8A838" if DARK else "#B86E1A"   # amber
            return LINE_COLORS[idx % len(LINE_COLORS)]

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
        if eu and (eu.get("is_enabled") or (eu.get("used_credits") or 0) > 0):
            # API returns utilization as percentage (0.56 = 0.56%)
            eu_util = eu.get("utilization") or 0
            eu_obj = {"utilization": eu_util, "resets_at": eu.get("resets_at", "")}
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
                        print(f"--Spent: ${spent / 100:.2f} | {ROW2}")
                    if limit is not None:
                        print(f"--Limit: ${limit / 100:.0f}/mo | {DIM}")
                    print(f"--Status: {status} | {DIM}")
                elif rt_local:
                    print(f"--{t('reset')}: {rt_local} | {DIM}")

    # ═══ 1b. USAGE STATUS HINTS (only when NO data at all) ═══
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
        trend_avg = 0
        if recent_days:
            avg_cost = sum(v["cost"] for _, v in recent_days) / len(recent_days)
            avg_msgs = sum(v["msgs"] for _, v in recent_days) / len(recent_days)
            # Suppress trend when today's activity < 30% of daily average
            if avg_cost > 0 and (avg_msgs <= 0 or today["msgs"] / avg_msgs >= 0.3):
                pct_change = (today["cost"] - avg_cost) / avg_cost * 100
                if pct_change >= 1:
                    trend = f" ↑{pct_change:.0f}%"
                    trend_avg = avg_cost
        print(f"── {today_label} ── | {ST}")
        print(f"⚡ {fc(today['cost'])} · {today['msgs']} {t('msgs')}{trend} | {SEC}")
        if trend and trend_avg > 0:
            print(f"--{t('trend_vs')} {fc(trend_avg)} | {DIM}")
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
        if dmin_all:
            total_days = max((datetime.now() - datetime.strptime(dmin_all, "%Y-%m-%d")).days + 1, 1)
            daily_avg = tc / total_days
            monthly_proj = daily_avg * 30
            print(f"--Daily: {fc(daily_avg)} · Monthly: {fc(monthly_proj)} | {DIM}")
        roi_note = t("roi_note").format(m=months_active, s=sub, p=total_paid, tc=fc(tc), x=multiplier)
        print(f"--{roi_note} | {DIM}")

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

    # Helper script path (defined early — used by Details and Settings)
    helper = str(Path.home() / ".config" / "cc-token-stats" / ".toggle.sh")

    # ── Details ──
    SH = "color=#5CC6A7 size=12" if DARK else "color=#1A5C4C size=12"
    details_label = t("details")
    print(f"── {details_label} ── | {ST}")

    # Daily Details (newest first, max 15 visible, older folded)
    all_total_cost = sum(v["cost"] for v in daily.values())
    all_total_msgs = sum(v["msgs"] for v in daily.values())
    active_days = [(d, v) for d, v in reversed(daily_sorted) if v["msgs"] > 0]
    print(f"{t('daily')} | {SH}")
    all_total_tokens = sum(v["tokens"] for v in daily.values())
    for date, data in active_days[:15]:
        dd = date[5:]
        print(f"--{dd}   {fc(data['cost']):>8}   {tk(data['tokens']):>8}   {data['msgs']:>5} msgs | {ROW2}")
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

    # Models
    print(f"{t('models')} | {SH}")
    for model, data in sorted(all_models.items(), key=lambda x: -x[1]["cost"]):
        short = MODEL_SHORT.get(model, model)
        pct = data["msgs"] / total_model_msgs * 100
        print(f"--{short:<12} {pct:>3.0f}%   {fc(data['cost']):>8}   {data['msgs']:>6,} msgs | {ROW2}")

    # Hourly Activity
    hourly_local = local["hourly"]
    if hourly_local:
        print(f"{t('hours')} | {SH}")
        total_hourly = max(sum(hourly_local.values()), 1)
        max_h = max(hourly_local.values()) if hourly_local else 1
        sparks = " ▁▂▃▄▅▆▇█"
        def spark(h):
            v = hourly_local.get(h, 0)
            if v == 0: return "▁"
            level = min(int(v / max_h * 8) + 1, 8)
            return sparks[level]
        block_defs = [
            (t("am"),   "06–12", range(6, 12)),
            (t("pm"),   "12–18", range(12, 18)),
            (t("eve"),  "18–24", range(18, 24)),
            (t("late"), "00–06", range(0, 6)),
        ]
        for label, time_str, hours_range in block_defs:
            count = sum(hourly_local.get(h, 0) for h in hours_range)
            if count == 0: continue
            pct = count / total_hourly * 100
            sparkline = "".join(spark(h) for h in hours_range)
            msgs_u = t("msgs")
            print(f"--{label} {time_str}  {sparkline}  {count:>5,} {msgs_u} {pct:>2.0f}% | {ROW2}")

    # Top Projects
    projects_local = dict(local["projects"])
    if projects_local:
        print(f"{t('projects')} | {SH}")
        top = sorted(projects_local.items(), key=lambda x: -x[1]["cost"])[:8]
        for name, data in top:
            short_name = f"{name[:14]:<14}" if len(name) <= 14 else f"{name[:13]}…"
            print(f"--{short_name}  {fc(data['cost']):>8}   {tk(data['tokens']):>8}   {data['msgs']:>5} msgs | {ROW2}")

    # Dashboard link
    print(f"{t('report')} | bash={helper} param1=dashboard terminal=false {SH}")

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
  dashboard)
    python3 {_escaped_plugin} --dashboard
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
    if len(sys.argv) > 1 and sys.argv[1] == "--dashboard":
        try:
            path = generate_dashboard()
            subprocess.run(["open", path])
        except Exception as e:
            print(f"Dashboard error: {e}", file=sys.stderr)
        sys.exit(0)
    try:
        main()
    except Exception:
        # Never crash — show basic menu bar item on any error
        print("CC")
        print("---")
        print("Error occurred | color=red")
        print("Click Refresh to retry | refresh=true")

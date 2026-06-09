#!/usr/bin/env python3
"""Smoke-test the dashboard's inline JavaScript.

The dashboard is one big <script> of IIFE panels. A ReferenceError in any
panel (e.g. calling a helper that's only defined inside another IIFE's scope)
throws and halts EVERY panel after it — the cards just render blank with no
error visible in the UI. This has bitten twice (esc() scope, v1.6.2).

This test generates the dashboard against a synthetic ~/.claude and executes
all inline scripts under a minimal DOM/echarts stub in Node, asserting nothing
throws. Skips cleanly if Node isn't installed.

Run directly:  python3 tests/test_dashboard_js.py
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "cc-token.5m.py"

HARNESS = r"""
const fs=require('fs');
const html=fs.readFileSync(process.argv[2],'utf8');
const scripts=[...html.matchAll(/<script\b(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);
const handler={get(t,p){if(p==='length')return 0;if(p===Symbol.toPrimitive)return ()=>'';
if(p==='forEach'||p==='map'||p==='filter'||p==='querySelectorAll')return ()=>fake;
if(p==='style'||p==='cells'||p==='classList'||p==='dataset')return fake;return fake;},
apply(){return fake;},set(){return true;}};
const fake=new Proxy(function(){},handler);
global.document={getElementById:()=>fake,createElement:()=>fake,querySelector:()=>fake,querySelectorAll:()=>fake,body:fake,addEventListener:()=>{}};
global.window={addEventListener:()=>{},matchMedia:()=>({matches:false,addEventListener:()=>{}}),devicePixelRatio:2};
global.navigator={language:'zh-CN'};
global.echarts={init:()=>({setOption(){},on(){},resize(){},dispose(){}}),graphic:{LinearGradient:function(){return {};}}};
global.setInterval=()=>0;global.setTimeout=()=>0;global.requestAnimationFrame=()=>0;global.location={href:'',hash:''};
let errs=[];
scripts.forEach((src,i)=>{try{new Function(src)();}catch(e){errs.push(`script[${i}] ${e.constructor.name}: ${e.message}`);}});
if(errs.length){console.error(errs.join('\n'));process.exit(1);}
process.exit(0);
"""


def _load_module():
    spec = importlib.util.spec_from_file_location("cct", str(PLUGIN))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class DashboardJsTest(unittest.TestCase):
    def setUp(self):
        if not shutil.which("node"):
            self.skipTest("node not installed")

    def test_dashboard_js_runs_without_throwing(self):
        # Synthetic ~/.claude with one project + a couple assistant rows so the
        # payload has daily/projects/models/sessions (exercises the topProj /
        # esc() path that previously threw).
        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / ".claude" / "projects" / "-Users-x-myproj"
            proj.mkdir(parents=True)
            # Spread across >=3 distinct dates: several panels (e.g. Usage
            # Wrapped) only render with 3+ days of data, and the esc()/topProj
            # path that regressed lives in one of them — so the synthetic data
            # must clear that bar for the test to actually exercise it.
            rows = []
            for n in range(4):
                rows.append(json.dumps({
                    "type": "assistant",
                    "message": {"id": f"m{n}", "model": "claude-opus-4-8",
                                "usage": {"input_tokens": 100, "output_tokens": 200,
                                          "cache_read_input_tokens": 50}},
                    "timestamp": "2026-06-0%dT01:00:00Z" % (5 + n),  # 06-05..06-08
                }))
            (proj / "a.jsonl").write_text("\n".join(rows) + "\n")

            env = dict(os.environ, HOME=tmp, CC_STATS_CLAUDE_DIR=str(proj.parent.parent),
                       CC_STATS_LANG="zh")
            # Generate the dashboard HTML via the plugin's own --dashboard path.
            subprocess.run(["python3", str(PLUGIN), "--dashboard"],
                           env=env, check=True, capture_output=True, timeout=60)
            dash = Path(tmp) / ".config" / "cc-token" / "dashboard.html"
            self.assertTrue(dash.is_file(), "dashboard.html was not generated")

            harness = Path(tmp) / "h.js"
            harness.write_text(HARNESS)
            r = subprocess.run(["node", str(harness), str(dash)],
                               capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0,
                             f"dashboard JS threw at runtime:\n{r.stderr}")


if __name__ == "__main__":
    unittest.main()

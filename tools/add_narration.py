# -*- coding: utf-8 -*-
"""Copy a standalone feature page from the taiwan-400 project and hook it up to tg.js
(Taigi narration, read-along subtitles, pictures).

  python tools/add_narration.py <path to taiwan-400 folder> dutch koxinga ...

Works for the pages that share the same playback code (dutch, koxinga, yiwei, wushe, airraids,
tapani). Every replacement must match exactly once, so a page whose code differs fails loudly
instead of being half-patched. The clip ids are p<phase index> and e<event index>.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sub1(s, pattern, repl, what):
    out, n = re.subn(pattern, repl, s, flags=re.S)
    if n != 1:
        raise SystemExit(f"  {what}: expected 1 match, found {n}")
    return out


def patch(src, name):
    s = src.read_text(encoding="utf-8")
    # scripts: clip list, pictures, shared module, before the page's own script
    s = sub1(s, r"<script>\n\(\(\) ?=> ?\{", f'<script src="narration-{name}.js"></script>\n<script src="pictures.js"></script>\n<script src="tg.js"></script>\n<script>\n(() => {{', "inline script")
    s = sub1(s, r"(function setPlaying\(p\)\{ playing=p; setK\(playBtn,[^\n]*?\); )\}", r"\1TG.sync(); }", "setPlaying")
    s = sub1(s, r"(function seek\(x\)\{[^\n]*?) ?\}\n", r"\1 TG.seek(); }\n", "seek")
    s = sub1(s, r"(playBtn\.addEventListener\('click', \(\)=>\{ if \(!playing && \w+>=\w+\) seek\(\w+\); )(setPlaying\(!playing\); \}\);)",
             r"\1if (!playing) TG.unlock(); \2", "play button")
    m = re.search(r"if \(playing\) \{ (\w)\+=dt\*rate\(\1\)\*\(\+speed\.value\); if \(\1>=(\w+)\) \{ \1=\2; setPlaying\(false\); \}", s)
    if not m:
        raise SystemExit("  frame: playback line not found")
    v, end = m.group(1), m.group(2)
    s = s.replace(m.group(0), f"if (playing) {{ {v}+=TG.step(dt*rate({v})*(+speed.value), now); if ({v}>={end}) {{ {v}={end}; if (!TG.busy()) setPlaying(false); }}")
    s = sub1(s, r"function frame\(now\)\{\n", "function frame(now){\n  TG.tick();\n", "frame")
    s = sub1(s, r"function applyLang\(\)\{\n", "function applyLang(){\n  TG.lang();\n", "applyLang")
    boot = re.search(r"\n(layout\(\); applyLang\(\); seek\((\w+)\); setPlaying\(playing\);)", s)
    if not boot:
        raise SystemExit("  boot line not found")
    start = boot.group(2)
    tg = (f"\n// Taigi narration, read-along subtitles and pictures (tg.js). Clip ids: p<phase index>, e<event index>.\n"
          f"const TG = TGNarration({{ name:'{name}', lang:()=>lang, getT:()=>{v}, isPlaying:()=>playing, setPlaying, stage:document.querySelector('.stage'), playBtn,\n"
          f"  cues:[...PHASES.map((p,i)=>({{y:Math.max(p[0],{start}), id:'p'+i}})), ...EVENTS.map((e,i)=>({{y:e.d, id:'e'+i}}))] }});\n"
          f"if (TG.on()) playing=false;   // sound needs a tap, so the narrated film waits for Play\n")
    s = s.replace(boot.group(0), tg + boot.group(1), 1)
    (ROOT / f"{name}.html").write_text(s, encoding="utf-8", newline="\n")
    print(f"  wrote {name}.html (clock '{v}', end {end}, start {start})")


def patch_engine(src, name):
    """Pages generated from tools/rebellions (guo, linshuangwen, daichaochun, feuds, indigenous): one Film(S) object."""
    s = src.read_text(encoding="utf-8")
    s = sub1(s, r"<script>\n", f'<script src="narration-{name}.js"></script>\n<script src="pictures.js"></script>\n<script src="tg.js"></script>\n<script>\n', "inline script")
    s = sub1(s, r"(f\.setPlaying = p => \{ f\.playing=p; setK\(play,[^\n]*?\); )\};", r"\1f.TG && f.TG.sync(); };", "setPlaying")
    s = sub1(s, r"(f\.seek = t => \{[^\n]*?) ?\};\n", r"\1 f.TG && f.TG.seek(); };\n", "seek")
    s = sub1(s, r"(play\.addEventListener\('click', \(\)=>\{ f\.started=true; if \(!f\.playing && f\.t>=T_END\) f\.seek\(0\); )(f\.setPlaying\(!f\.playing\); \}\);)",
             r"\1if (!f.playing) f.TG.unlock(); \2\n"
             f"  // Taigi narration, read-along subtitles and pictures (tg.js). Clip ids: p<phase index>, e<event index>.\n"
             f"  f.TG = TGNarration({{ name:'{name}', lang:()=>lang, getT:()=>f.t, isPlaying:()=>f.playing, setPlaying:p=>f.setPlaying(p), stage, playBtn:play,\n"
             f"    cues:[...S.PHASES.map((p,i)=>({{y:Math.max(p[0],0), id:'p'+i}})), ...S.EVENTS.map((e,i)=>({{y:e.d, id:'e'+i}}))] }});", "play button")
    s = sub1(s, r"if \(f\.playing\) \{ f\.t\+=dt\*rate\(f\.t\)\*\(\+speed\.value\); if \(f\.t>=T_END\) \{ f\.t=T_END; f\.setPlaying\(false\); \}",
             "f.TG.tick();\n    if (f.playing) { f.t+=f.TG.step(dt*rate(f.t)*(+speed.value), performance.now()); if (f.t>=T_END) { f.t=T_END; if (!f.TG.busy()) f.setPlaying(false); }", "tick")
    s = sub1(s, r"if \(e\.isIntersecting && !f\.started && !reduce\) \{", "if (e.isIntersecting && !f.started && !reduce && !f.TG.on()) {", "autoplay")
    s = sub1(s, r"(for \(const f of films\) f\.setPlaying\(f\.playing\);)", r"\1 for (const f of films) f.TG.lang();", "applyLang")
    (ROOT / f"{name}.html").write_text(s, encoding="utf-8", newline="\n")
    print(f"  wrote {name}.html (rebellion engine)")


def main():
    src_dir = Path(sys.argv[1])
    for name in sys.argv[2:]:
        print(name)
        src = src_dir / f"{name}.html"
        (patch_engine if "function Film(S){" in src.read_text(encoding="utf-8") else patch)(src, name)
    main_page = ROOT / "taiwan-400.html"
    s = main_page.read_text(encoding="utf-8")
    for name in sys.argv[2:]:   # the main page's card now opens the narrated copy
        s = s.replace(f'href="https://sinliongtoo.github.io/taiwan-400/{name}.html"', f'href="{name}.html"')
    main_page.write_text(s, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

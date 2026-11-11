# -*- coding: utf-8 -*-
"""Build the Taigi narration for the 400-year page.

Reads tools/narration_script.json, synthesizes every clip with Meta MMS-TTS
(facebook/mms-tts-nan) through the engine in the Taigi TTS Studio project, and writes
  audio/<id>.mp3     one clip per era text / event
  narration.js       window.NARRATION = { id: {han, poj, dur} }

  python tools/make_narration.py --dry-run      # only print the romanization, no audio
  python tools/make_narration.py                # synthesize clips that are missing or changed
  python tools/make_narration.py --force        # synthesize everything again
  python tools/make_narration.py --only ev-1603 era-1600

The engine folder defaults to the sibling project; override with --engine-dir or TAIGI_TTS_DIR.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = HERE / "narration_script.json"
AUDIO = ROOT / "audio"
MANIFEST = ROOT / "narration.js"
STATE = HERE / "narration_state.json"
DEFAULT_ENGINE = ROOT.parent / "Projects_antigravity" / "TIGI_TTS_MOREＭＯＤＬ"

SENTENCE_PAUSE_MS = 380   # after 。！？
CLAUSE_PAUSE_MS = 160     # after ，、；：
PEAK = 0.89
CLAUSE_RE = re.compile(r"([，、；：。！？]+)")


def split_clauses(han):
    """[(clause text, punctuation after it)], split where the voice pauses."""
    parts = CLAUSE_RE.split(han)
    out = []
    for i in range(0, len(parts), 2):
        text, punct = parts[i].strip(), parts[i + 1] if i + 1 < len(parts) else ""
        if text:
            out.append((text, punct))
        elif out and punct:
            out[-1] = (out[-1][0], out[-1][1] + punct)
    return out


def speech_span(wav, sr):
    """Where the voice actually starts and ends inside one synthesized clause (seconds)."""
    import numpy as np
    env = np.abs(wav)
    loud = np.nonzero(env > 0.06 * float(env.max() or 1.0))[0]
    if not len(loud):
        return 0.0, len(wav) / sr
    return loud[0] / sr, (loud[-1] + 1) / sr


def apply_lexicon(text, lexicon):
    """Swap hard-to-read words for romanization before G2P. Longest keys first."""
    for key in sorted(lexicon, key=len, reverse=True):
        text = text.replace(key, f" {lexicon[key]} ")
    return re.sub(r"[ \t]+", " ", text).strip()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--script", default=str(SCRIPT), help="narration script; tools/narration_<name>.json writes narration-<name>.js, audio/<name>/ and window.NARRATION_<name>")
    ap.add_argument("--engine-dir", default=os.environ.get("TAIGI_TTS_DIR", str(DEFAULT_ENGINE)))
    args = ap.parse_args()

    engine_dir = Path(args.engine_dir)
    if not (engine_dir / "mms_engine.py").exists():
        sys.exit(f"Taigi TTS engine not found in {engine_dir} (pass --engine-dir)")
    sys.path.insert(0, str(engine_dir))

    global AUDIO, MANIFEST, STATE
    script = Path(args.script)
    name = script.stem.replace("narration_script", "").replace("narration_", "")
    var = "NARRATION"
    if name:
        AUDIO, MANIFEST, STATE, var = ROOT / "audio" / name, ROOT / f"narration-{name}.js", HERE / f"narration_state_{name}.json", f"NARRATION_{name}"
    spec = json.loads(script.read_text(encoding="utf-8"))
    lexicon = spec.get("lexicon", {})
    clips = spec["clips"]
    ids = [c["id"] for c in clips]
    if len(set(ids)) != len(ids):
        sys.exit("duplicate clip ids in narration_script.json")

    from taigi_sandhi import TaigiTextPipeline, split_article_into_sentences
    g2p = TaigiTextPipeline(dialect="south")

    # Each clip is spoken clause by clause, so the page knows when every clause starts and ends
    # and can highlight the characters as they are read.
    for c in clips:
        c["segs"] = []
        for text, punct in split_clauses(c["han"]):
            poj = re.sub(r"\s+", " ", g2p.convert_to_poj_raw(apply_lexicon(text, lexicon))).strip()
            c["segs"].append({"h": text, "p": punct, "poj": poj})
        c["poj"] = " ".join(s["poj"] + {"。": ".", "！": "!", "？": "?", "": ""}.get(s["p"][:1], ",") for s in c["segs"])
        c["hash"] = hashlib.sha1(("v2|" + c["han"] + "|" + c["poj"]).encode("utf-8")).hexdigest()[:12]

    if args.dry_run:
        for c in clips:
            if args.only and c["id"] not in args.only:
                continue
            print(f"[{c['id']}]\n  {c['han']}\n  {c['poj']}\n")
        return

    import numpy as np
    import scipy.io.wavfile as wavfile
    from mms_engine import MmsTtsEngine

    AUDIO.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    engine = None
    for c in clips:
        out = AUDIO / f"{c['id']}.mp3"
        wanted = args.only is None or c["id"] in args.only
        fresh = out.exists() and state.get(c["id"], {}).get("hash") == c["hash"]
        if not wanted or (fresh and not args.force):
            continue
        if engine is None:
            engine = MmsTtsEngine()
            engine._ensure_loaded()
        sr = engine.sample_rate
        parts, pos, times = [], 0, []
        for i, s in enumerate(c["segs"]):
            clause = engine.clean_poj_for_mms(s["poj"])
            w = engine._infer(clause) if clause else np.zeros(int(sr * 0.1), dtype=np.float32)
            a, b = speech_span(w, sr)
            times.append([round((pos + a * sr) / sr, 2), round((pos + b * sr) / sr, 2)])
            parts.append(w); pos += len(w)
            if i < len(c["segs"]) - 1:
                ms = SENTENCE_PAUSE_MS if re.search(r"[。！？]", s["p"]) else CLAUSE_PAUSE_MS
                gap = np.zeros(int(sr * ms / 1000), dtype=np.float32)
                parts.append(gap); pos += len(gap)
        wav = np.concatenate(parts)
        peak = float(np.max(np.abs(wav))) or 1.0
        wav = wav * (PEAK / peak)
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "clip.wav"
            wavfile.write(str(tmp), sr, np.int16(np.clip(wav, -1, 1) * 32767))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                            "-ac", "1", "-ar", "24000", "-b:a", "48k", str(out)], check=True)
        state[c["id"]] = {"hash": c["hash"], "dur": round(len(wav) / sr, 2), "times": times}
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{c['id']}: {state[c['id']]['dur']} s")

    missing = [c["id"] for c in clips if state.get(c["id"], {}).get("hash") != c["hash"] or not (AUDIO / f"{c['id']}.mp3").exists()]
    if missing:
        sys.exit(f"clips not synthesized yet: {missing}")
    # segs: [han clause, punctuation after it, POJ, start s, end s]
    manifest = {c["id"]: {"han": c["han"], "poj": c["poj"], "dur": state[c["id"]]["dur"],
                          "segs": [[s["h"], s["p"], s["poj"], *t] for s, t in zip(c["segs"], state[c["id"]]["times"])]}
                for c in clips}
    MANIFEST.write_text(f"// Generated by tools/make_narration.py from tools/{script.name}. Do not edit by hand.\n"
                        f"window.{var} = " + json.dumps(manifest, ensure_ascii=False, indent=1) + ";\n",
                        encoding="utf-8")
    total = sum(m["dur"] for m in manifest.values())
    print(f"wrote {MANIFEST.name}: {len(manifest)} clips, {total:.0f} s of speech")


if __name__ == "__main__":
    main()

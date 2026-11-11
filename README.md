# 台灣四百年・台語旁白 (Taiwan: Four Centuries, narrated in Taiwanese)

The 400-year animated history page from the `taiwan-400` project
(<https://sinliongtoo.github.io/taiwan-400/>), with a spoken Taiwanese (Taigi) narration added.
The map, charts, rulers and 中文 / EN / 中英 text are unchanged; this copy adds the voice.

## What the narration does

- Press 播放. Each era text and each event is read aloud in Taigi as the film reaches it.
- The years keep moving while a passage is spoken, but wait just before the next one until the
  voice has finished. A full run takes about as long as the narration (see the minutes shown
  next to the record button) instead of one minute.
- The line being spoken is shown under the film in 台語漢字 with 白話字 (POJ) below it.
- Read-along highlight: the character being spoken turns gold, characters already spoken are bright,
  and the rest stay dim. The POJ of the phrase being spoken is brightened too.
  Each phrase (the text between punctuation marks) starts and ends exactly with the voice; inside a
  phrase the characters share the time evenly, so a single character can be a fraction of a second early or late.
- 🔊 台語旁白 turns the voice off; the film then plays at its original speed. The choice is remembered.
- Jumping to an era, dragging the slider or pressing ← → stops the voice and picks it up from the new year.
- 錄製影片 records the narration into the video when the page is opened over http(s).
  Opened as a local file (`file://`), browsers only allow the picture to be recorded.

## Files

| File | Purpose |
|---|---|
| `taiwan-400.html` | Page source (edit this one) |
| `index.html` | Generated from `taiwan-400.html` by `python build_pages.py` |
| `portraits.js` | Ruler portraits, copied unchanged from `taiwan-400` |
| `narration.js` | Generated: text, romanization and length of every clip |
| `audio/*.mp3` | Generated: one clip per era text (`era-<year>`) and per event (`ev-<year>`) |
| `tools/narration_script.json` | The Taigi script and the pronunciation lexicon (edit this one) |
| `tools/make_narration.py` | Synthesizes the clips and writes `narration.js` |
| `tools/smoke.js` | Smoke test from `taiwan-400`: `node tools/smoke.js index.html 400` |

To view locally with sound and recording: `python -m http.server 8400`, then open
<http://localhost:8400/>.

## Changing the narration

1. Edit `tools/narration_script.json`.
   - `han` is the Taigi text, written in 教育部推薦用字. It is what the subtitle shows.
   - `lexicon` replaces words the romanizer misreads with Tâi-lô before the text is spoken
     (names, years read digit by digit, words like 雞籠 → `Ke-lâng`). Add an entry when a word sounds wrong.
   - A clip id must match a year in the page: `era-<start year>` for an era text, `ev-<event year>` for an event.
     An event without a clip is simply not read (1875, 1937.6, 1949.38 and 1987.54 are covered by their era text).
2. `python tools/make_narration.py --dry-run` prints the romanization so it can be checked before any audio is made.
3. `python tools/make_narration.py` synthesizes only the clips whose text changed, then rewrites `narration.js`.

The voice is Meta MMS-TTS (`facebook/mms-tts-nan`), run through the engine in the Taigi TTS Studio
project (`../Projects_antigravity/TIGI_TTS_MOREＭＯＤＬ`; pass `--engine-dir` if it moves). It needs
`torch`, `transformers`, `taibun`, `scipy` and `ffmpeg`.

## Limits

- The voice is a synthetic one. It is real Taiwanese, not Mandarin, but its tones are not always natural,
  and proper names follow the readings in the lexicon.
- The Taigi script is a translation of the page's Chinese text and has not been reviewed by a second speaker.
- History content, sources and portrait credits are those of the `taiwan-400` project; see the References on the page.

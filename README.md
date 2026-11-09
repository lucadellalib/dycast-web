# DyCAST listening page

`index.html` is a standalone static page with the original five resynthesis
examples (A–E). Only their 120 audio files are retained: one reference and 23
codec outputs per example. Unused recordings and disabled example/retrieval
sections have been removed.
The page uses one comparison grid: codecs in the first column and Samples A–E
in the next five columns. Headers and codec names stay visible while scrolling.
The 23 codecs in `codecs.json` determine the row order; `samples.json` fixes the
five recording IDs and their column order. FlexiCodec is excluded.
FocalCodec50 uses the supplied `sr/focalcodec50/` recordings (filenames retain
the `_focalcodec.wav` suffix). FocalCodec25 and FocalCodec12.5 use the supplied
`sr/focalcodec25/` and `sr/focalcodec12_5/` recordings.

CodecSlime rates are 36/40/60/75 Hz; VARSTok thresholds are 0.6/0.7/0.8 with
maximum span 4. Their audio is resynthesized from every existing recording in
`sr/reference/`, using this repository's codec adapters and the locally cached
released checkpoints. The references and existing baseline/DyCAST audio are
unchanged. Each new codec folder includes `generation.json` with checkpoint and
input/output hashes, token counts, measured per-sample frame rates/bitrates, and
length-alignment details. Outputs are mono 16 kHz PCM16, cropped or replicate-padded
to match the reference sample count, as in the downstream resynthesis harness.
No gain normalization is applied.

Generate these samples from the repository root using the downstream environment:

```bash
HF_HUB_OFFLINE=1 downstream/.venv/bin/python dycast-web/resynthesize.py \
  --codec codecslime --settings 36 40 60 75
HF_HUB_OFFLINE=1 downstream/.venv/bin/python dycast-web/resynthesize.py \
  --codec varstok --settings 0.6 0.7 0.8
python3 dycast-web/build.py
```

Generation uses CPU with two threads by default; `--device cuda` and `--threads`
can change execution. VARSTok's source defaults to
`~/PycharmProjects/FunResearch/VARSTok`; override with `--varstok-source`.
These scripts regenerate only the selected baseline's samples.

The supplied FocalCodec25 and FocalCodec12.5 filenames follow:

```text
sr/focalcodec25/<utterance>_focalcodec25.wav
sr/focalcodec12_5/<utterance>_focalcodec12_5.wav
```

Then run `python3 dycast-web/build.py`. Existing audio gets an audio player;
missing audio gets an explicit "Audio coming soon" label, with no invalid source
URL. `python3 dycast-web/build.py --check` verifies HTML is up to date. Audio has
`preload="none"` to avoid downloading all samples when opening the page.

Displayed frame rates and two-decimal bitrates match the supplied paper table.
Displayed variable rates are LibriSpeech corpus averages, not per-recording
measurements. CodecSlime and VARSTok bitrates include 2 and 2 duration bits per
token respectively (15 and 14 total bits/token). FocalCodec25/12.5 nominal
bitrates use their 8192-entry codebooks (13 bits/token).

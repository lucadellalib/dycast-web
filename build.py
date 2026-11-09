"""Refresh static resynthesis tables from codecs.json and the local audio files."""

import argparse
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def audio_cell(path, label):
    escaped = html.escape(path.as_posix(), quote=True)
    if not (ROOT/path).is_file():
        return f'<span class="audio-pending" data-audio-path="{escaped}">Audio coming soon</span>'
    return (f'<audio controls preload="none" aria-label="{html.escape(label, quote=True)}">'
            f'<source src="{escaped}" type="audio/wav">Your browser does not support audio playback.</audio>')


def make_grid(codecs, samples):
    rows = ['<div class="comparison-scroll" role="region" aria-label="Speech resynthesis audio comparison" tabindex="0">',
            '<table class="comparison-grid">',
            '<caption class="visually-hidden">Compare the same five recordings across codecs. Frame rates and bitrates appear below codec names.</caption>',
            '<thead><tr><th scope="col" class="codec-column">Codec</th>']
    for i, sample in enumerate(samples):
        rows.append(f'<th scope="col" id="sample-{i}">{html.escape(sample["label"])}'
                    f'<span class="sample-id">{html.escape(sample["id"])}</span></th>')
    rows.extend(['</tr></thead>', '<tbody>', '<tr class="reference-row"><th scope="row" class="label" id="codec-reference">Reference</th>'])
    for i, sample in enumerate(samples):
        path = Path('sr/reference')/f'{sample["id"]}_reference.wav'
        rows.append(f'<td class="audio-cell" headers="codec-reference sample-{i}">'
                    f'{audio_cell(path, "Reference "+sample["label"])}</td>')
    rows.append('</tr>')
    for codec in codecs:
        name, key = codec['name'], codec['key']
        approximate = '≈ ' if codec.get('variable') else ''
        details = html.escape(f'{approximate}{codec["hz"]} Hz · {codec["kbps"]} kbps')
        ours_class = ' class="ours-row"' if codec.get('ours') else ''
        ours_label = ' <span class="ours-label">(Ours)</span>' if codec.get('ours') else ''
        rows.append(f'<tr data-codec="{html.escape(key)}"{ours_class}>'
                    f'<th scope="row" class="label" id="codec-{key}">'
                    f'<span class="codec-name">{html.escape(name)}{ours_label}</span>'
                    f'<span class="codec-meta">{details}</span></th>')
        for i, sample in enumerate(samples):
            path = Path('sr')/codec.get('directory', key)/f'{sample["id"]}_{key}.wav'
            rows.append(f'<td class="audio-cell" headers="codec-{key} sample-{i}">'
                        f'{audio_cell(path, name+" "+sample["label"])}</td>')
        rows.append('</tr>')
    rows.extend(['</tbody>', '</table>', '</div>'])
    return '\n'.join(rows)


def render(source):
    codecs = json.loads((ROOT/'codecs.json').read_text())
    samples = json.loads((ROOT/'samples.json').read_text())
    pattern = r'<!-- BEGIN SAMPLES GRID -->.*?<!-- END SAMPLES GRID -->'
    block = '<!-- BEGIN SAMPLES GRID -->\n'+make_grid(codecs, samples)+'\n<!-- END SAMPLES GRID -->'
    result, count = re.subn(pattern, lambda _: block, source, flags=re.S)
    if count != 1:
        raise ValueError('Expected one marked sample grid in index.html')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if the static HTML needs regeneration')
    args = parser.parse_args()
    path = ROOT/'index.html'
    source = path.read_text()
    updated = render(source)
    if args.check:
        if updated != source:
            raise SystemExit('Run python3 dycast-web/build.py to refresh the audio tables')
    else:
        path.write_text(updated)


if __name__ == '__main__':
    main()

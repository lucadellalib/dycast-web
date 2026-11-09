"""Generate website CodecSlime/VARSTok samples from the unchanged references."""

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for part in iter(lambda: f.read(1024*1024), b''):
            digest.update(part)
    return digest.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--codec', choices=['codecslime', 'varstok'], required=True)
    p.add_argument('--settings', type=float, nargs='+', required=True)
    p.add_argument('--device', default='cpu')
    p.add_argument('--threads', type=int, default=2)
    p.add_argument('--varstok-source', type=Path, default=Path.home()/'PycharmProjects/FunResearch/VARSTok')
    args = p.parse_args()
    import soundfile as sf
    import torch
    import torch.nn.functional as F
    import torchaudio
    torch.set_num_threads(args.threads)
    references = sorted((ROOT/'sr/reference').glob('*_reference.wav'))
    if not references:
        raise FileNotFoundError('No reference recordings')
    checkpoint_root = ROOT.parent/'audiocodecs/dynacast_/checkpoints'
    for setting in args.settings:
        if args.codec == 'codecslime':
            from audiocodecs.codecslime import CodecSlime
            key = f'codecslime_{setting:g}'
            checkpoint = checkpoint_root/'codecslime-vq8k.safetensors'
            codec = CodecSlime(16000, frame_rate=setting, checkpoint=str(checkpoint))
            bits_per_token = 15
        else:
            from audiocodecs.varstok import VARSTok
            key = f'varstok_{round(setting*10):02d}'
            checkpoint = checkpoint_root/f'varstok_thres{round(setting*10):02d}_maxspan4.ckpt'
            codec = VARSTok(16000, threshold=setting, source_dir=str(args.varstok_source), checkpoint=str(checkpoint))
            bits_per_token = 14
        codec.eval().requires_grad_(False).to(args.device)
        output = ROOT/'sr'/key
        output.mkdir(parents=True, exist_ok=True)
        records = []
        for reference in references:
            waveform, sr = sf.read(reference, dtype='float32', always_2d=True)
            signal = torchaudio.functional.resample(torch.from_numpy(waveform).mean(1), sr, 16000)[None].to(args.device)
            with torch.inference_mode():
                tokens = codec.sig_to_toks(signal)
                reconstructed = codec.toks_to_sig(tokens)
            decoded_samples = reconstructed.shape[-1]
            if not decoded_samples or not torch.isfinite(reconstructed).all():
                raise ValueError(f'Invalid reconstruction: {key}/{reference.name}')
            # Same length alignment as downstream/test_sr.py; no gain normalization.
            samples = signal.shape[-1]
            if decoded_samples < samples:
                reconstructed = F.pad(reconstructed, (0, samples-decoded_samples), mode='replicate')
            reconstructed = reconstructed[0, :samples].float().cpu().numpy()
            identifier = reference.stem.removesuffix('_reference')
            target = output/f'{identifier}_{key}.wav'
            sf.write(target, reconstructed, 16000, subtype='PCM_16')
            rate = tokens.shape[1]/(samples/16000)
            records.append(dict(id=identifier, reference=str(reference.relative_to(ROOT)),
                                reference_sha256=sha256(reference), output=str(target.relative_to(ROOT)),
                                output_sha256=sha256(target), samples=samples, decoded_samples=decoded_samples,
                                tokens=tokens.shape[1], frame_rate_hz=rate, bitrate_bps=rate*bits_per_token,
                                peak_before_pcm16=float(abs(reconstructed).max())))
            print(f'{key}: {identifier} ({tokens.shape[1]} tokens, {rate:.2f} Hz)', flush=True)
        metadata = dict(codec=args.codec, setting=setting, checkpoint=str(checkpoint.resolve()),
                        checkpoint_sha256=sha256(checkpoint), bits_per_token=bits_per_token,
                        sample_rate=16000, format='PCM_16', seed=None,
                        preprocessing='mono/resample16k; no gain normalization',
                        output_alignment='crop or replicate-pad to reference sample count', records=records)
        temp = output/'generation.json.tmp'
        temp.write_text(json.dumps(metadata, indent=2)+'\n')
        os.replace(temp, output/'generation.json')
        del codec
        gc.collect()


if __name__ == '__main__':
    main()

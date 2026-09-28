#!/usr/bin/env python3
"""Minimal Whisper ASR server for ModelArts custom NPU. Listens on :8000."""
from __future__ import annotations

import io
import os
from typing import Optional

import numpy as np
import soundfile as sf
import torch
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from language_tokens import ALIASES, LANGUAGE_TOKENS

WEIGHT = os.environ.get("WEIGHT_DIR", "/weight")
SAMPLE_RATE = 16000

if torch.npu.is_available():
    DEVICE = torch.device("npu:0")
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")

processor = WhisperProcessor.from_pretrained(WEIGHT)
model = WhisperForConditionalGeneration.from_pretrained(WEIGHT)
model.to(DEVICE)
model.eval()

app = FastAPI()


def resolve_lang(code: str) -> str:
    key = (code or "").strip().lower()
    key = ALIASES.get(key, key)
    if key not in LANGUAGE_TOKENS:
        raise HTTPException(400, f"unsupported language: {code}")
    return key


def load_audio(raw: bytes) -> np.ndarray:
    audio, sr = sf.read(io.BytesIO(raw), always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=-1)
    if sr != SAMPLE_RATE:
        import librosa

        audio = librosa.resample(audio.astype(np.float32), orig_sr=sr, target_sr=SAMPLE_RATE)
    return np.asarray(audio, dtype=np.float32)


@app.get("/health")
def health():
    return {"status": "ok", "device": str(DEVICE)}


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("swa"),
    prompt: Optional[str] = Form(None),
):
    lang = resolve_lang(language)
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "empty audio")
    wav = load_audio(raw)
    feats = processor(
        wav, sampling_rate=SAMPLE_RATE, do_normalize=True, return_tensors="pt"
    ).input_features.to(DEVICE)

    tok = processor.tokenizer
    forced = [
        (1, LANGUAGE_TOKENS[lang]),
        (2, tok.convert_tokens_to_ids("<|transcribe|>")),
        (3, tok.convert_tokens_to_ids("<|notimestamps|>")),
    ]
    gen_kw = dict(forced_decoder_ids=forced, num_beams=1, do_sample=False)
    if prompt and prompt.strip():
        gen_kw["prompt_ids"] = tok.get_prompt_ids(prompt.strip(), return_tensors="pt").to(DEVICE)

    with torch.inference_mode():
        ids = model.generate(feats, **gen_kw)
    text = processor.decode(ids[0], skip_special_tokens=True, clean_up_tokenization_spaces=False)
    return {"text": text, "language": lang}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

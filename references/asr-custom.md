# Custom ASR runtime (not vLLM)

Use this when §0 runtime gate says **custom**. Canonical model: `Sunbird/asr-whisper-51-african-languages` (Transformers Whisper large-v3, ~1.5B, ~6 GB F32 / ~3 GB on disk after download). Official conversion `Sunbird/faster-whisper-51-african-languages` is **CPU/CUDA CTranslate2 only** — do not deploy it to Ascend.

## Why not vLLM

[vLLM-Ascend support matrix](https://docs.vllm.ai/projects/ascend/en/latest/user_guide/support_matrix/supported_models.html) lists Whisper as ❌. Starting `vllm serve` on this checkpoint will fail or hang. Keep the v0.23 NPU image for CANN/`torch_npu`, change the process to FastAPI.

## Weights

Gated (`gated: auto`): user must accept the HF terms, then on ARM ECS:

```bash
export HF_TOKEN=...   # do not echo
hf download Sunbird/asr-whisper-51-african-languages --local-dir /data/weight
# inner folder must contain config.json
obsutil cp -r -f /data/weight obs://<bucket>/<prefix>/weight/ \
  -e=https://obs.<ma_region>.myhuaweicloud.com
```

Mount that prefix at `/weight/`.

## Image

On the same ARM ECS, FROM `quay.io/ascend/vllm-ascend:v0.23.0`, install:

`transformers accelerate librosa soundfile fastapi uvicorn python-multipart`

Push `linux/arm64` to **ModelArts-region** SWR. Container listens on **8000**.

## Code mount

Upload [templates/whisper/](../templates/whisper/) to OBS → `/code/`. Cmd: `bash /code/serve.sh`.

`serve.sh` must `python /code/server.py` (or uvicorn). Never call `vllm`.

## Language codes

This fine-tune **reuses Whisper language-token slots**. Never auto-detect.

Transformers path: use Sunbird ISO-639-3 codes and the token ids in `templates/whisper/language_tokens.py` (`swa`, `eng`, `afr`, `zul`, …).

If someone later runs the faster-whisper conversion on CPU, that runtime wants the **remapped** codes (`sw`, `en`, `af`, `br` for Zulu). Do not mix the two tables.

## Hotwords / prompt

Not a ModelArts feature. Whisper has no WFST hotword head.

- `prompt` / `initial_prompt`: decoder previous-text bias (spelling).
- faster-whisper `hotwords=` is the same bias; **unavailable on this NPU server**.

Pass `prompt` on the transcription request. Domain terms (M-Pesa, Safaricom, Vodacom, …) still need a glossary or fine-tune if acoustics miss them.

## Probe

```
GET  /v2/infer/<id>/health
POST /v2/infer/<id>/v1/audio/transcriptions
  file=@clip.wav
  language=swa
```

Do not send `/v1/chat/completions`. Body limit already ≥50MB on the service.

## NPU / flavor

1× Snt9b2 (`modelarts.bm.arm.24u.192g.npu.1d910b` on Johannesburg public) is enough. Do not request TP>1.

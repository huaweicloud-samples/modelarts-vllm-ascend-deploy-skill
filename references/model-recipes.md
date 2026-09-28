# Per-model recipes (reference deployment, `af-south-1`)

Values below are copied from a working Johannesburg public-pool deployment (the "reference deployment", which ran Qwen3.8 on 2 NPUs and Whisper on 1). Replace `<ns>` / `<bucket>` with **this account's** SWR namespace and OBS bucket. Do not reuse another account's SWR, OBS, or DEW.

Johannesburg NPU: Snt9b2 = Ascend 910B3 = **A2**. "8× 910B3" in a guide is the public inference pool node flavor `modelarts.bm.npu.arm.8snt9b2.d`, not the prep ECS size (prep ECS stays a small Kunpeng VM, §2). The public pool can schedule up to 8 NPUs per service. Dedicated pool + SFS Turbo is optional; neither deploy below needed it.

| Service flavor | NPU |
|---|---|
| `modelarts.bm.arm.24u.192g.npu.1d910b` | 1 |
| `modelarts.bm.arm.48u.384g.npu.2d910b` | 2 |

## Qwen3.8-27B (vLLM)

| Field | Value |
|---|---|
| Weights | `Eco-Tech/Qwen3.8-27B-w8a8` (W8A8 of `Qwen/Qwen3.8-27B`) → flat `obs://<bucket>/weight/` → `/weight/`. `--quantization ascend` needs this W8A8 checkpoint |
| Upstream image | `quay.io/ascend/vllm-ascend:qwen3.8-a2` (**not** `v0.23.0`) |
| SWR | `swr.af-south-1.myhuaweicloud.com/<ns>/vllm-ascend:qwen3.8-a2` (plain `docker pull` → `tag` → `push`, no rebuild) |
| NPU | **2**, TP 2. `unit_configs[0].count` = **1** instance; the flavor carries the 2 cards |
| Flavor | `modelarts.bm.arm.48u.384g.npu.2d910b` |
| Health | startup HTTP `/health`, initial delay 600s, period 30s, timeout 30s, failure threshold 40 |

```bash
vllm serve /weight --tensor-parallel-size 2 --quantization ascend \
  --served-model-name qwen3.8 --max-model-len 131072 --max-num-seqs 32 \
  --max-num-batched-tokens 16384 --gpu-memory-utilization 0.85 \
  --port 8000 --host 0.0.0.0
```

Not 1 card, not TP 1, not the v0.23.0 image. A later 1-NPU `v0.23.0` attempt did not match this recipe.

## Whisper `Sunbird/asr-whisper-51-african-languages` (custom)

| Field | Value |
|---|---|
| Image | custom `swr.af-south-1.myhuaweicloud.com/<ns>/whisper-custom:v0.23` (FROM `quay.io/ascend/vllm-ascend:v0.23.0` for CANN/`torch_npu`, see [asr-custom.md](asr-custom.md)) |
| Runtime | `transformers` + `torch_npu` FastAPI ([templates/whisper/](../templates/whisper/)) |
| NPU | **1** |
| Flavor | `modelarts.bm.arm.24u.192g.npu.1d910b` |
| Cmd | `bash /code/serve.sh` — never `vllm serve`, never `faster-whisper` |
| Mounts | `obs://<bucket>/weight/` → `/weight/`, `obs://<bucket>/code/` → `/code/` |
| Health | startup HTTP `/health`, initial delay 480s, period 10s, timeout 10s, failure threshold 18 |
| Languages | Sunbird ISO-639-3 (`swa`, `eng`, `afr`, `zul`, …) from `language_tokens.py`; always force `language`, no auto-detect |

Required OBS files (a failed deploy was missing `model.safetensors` and `language_tokens.py`):

| Mount | Must contain |
|---|---|
| `/weight/` | `config.json`, **`model.safetensors`**, tokenizer + `preprocessor_config.json` / `processor_config.json` |
| `/code/` | `serve.sh`, `server.py`, **`language_tokens.py`** ([templates/whisper/](../templates/whisper/)) |

Before CreateInferService, `obsutil ls` both prefixes and confirm every file above sits at the prefix root (not nested).

## v2 CreateService body (returned HTTP 200)

`POST https://modelarts.{ma_region}.myhuaweicloud.com/v2/{project_id}/services`. Shape only; fill values from the recipe.

```json
{
  "name": "<service>", "type": "REAL_TIME",
  "version": {
    "version": "1.0.0", "deploy_timeout_minutes": 60,
    "upgrade_config": {"type": "ROLLING", "rolling_update": {"max_surge": "0%", "max_unavailable": "100%"}},
    "runtime_config": {
      "service_invoke": {"auth_type": "API_KEY", "protocol": "HTTP", "port": 8000},
      "service_limit": {"rate_limit": {"num": 200, "unit": "SECONDS"}, "request_timeout": 180, "request_size_limit": 50}
    },
    "instance_groups": [{
      "name": "<group>", "count": 1, "secret_type": "DEW", "secret_name": "<this-account DEW secret>",
      "unit_configs": [{
        "name": "role-0", "count": 1, "port": 8000,
        "flavor": "<service flavor>",
        "image": {"source": "SWR", "swr_path": "swr.<region>.myhuaweicloud.com/<ns>/<name>:<tag>"},
        "cmd": "<recipe cmd>",
        "files": [{"source": "OBS", "type": "FILE", "address": "obs://<bucket>/weight/", "mount_path": "/weight/", "read_only": true}],
        "startup_health": {"check_method": "HTTP", "protocol": "HTTP", "url": "/health", "initial_delay_seconds": 600, "period_seconds": 30, "timeout_seconds": 30, "failure_threshold": 40}
      }]
    }]
  }
}
```

- `image` is an **object** `{source: SWR, swr_path}`. A plain string is rejected.
- `secret_type` `DEW`; the secret holds `accessKeyId` / `secretAccessKey` for the OBS mounts (§DEW).
- `rate_limit` lives under `runtime_config.service_limit` (missing → `ModelArts.8037`).
- Field name is `flavor`. Port **8000** in both `service_invoke` and the unit.

## Generic pitfalls (proven)

- **obsutil directory cp nests twice** (`prefix/dir/dir/`). Upload per-file (§Weights + code).
- **`obsutil ls obs://<missing-bucket>`** still prints the bucket name. Do not read that as "bucket exists"; check for objects / an error line.
- **SWR docker login host** is `swr.<region>.myhuaweicloud.com` (the token comes from `swr-api.<region>`). `docker login` without that host logs into docker.io.
- **Euler docker bridge cannot reach PyPI.** Build extras with `docker run --network host ... pip install ...`, then `docker commit` the container to the new tag, then push.
- **New account = fresh OBS bucket, SWR namespace, DEW secret, prep ECS.** Nothing carries over.

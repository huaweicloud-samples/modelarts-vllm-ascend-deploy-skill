# Huawei CodeArts Snap — AI coding instructions

# This file provides the Huawei ModelArts vLLM deploy skill for CodeArts Snap.
# Place this repo in your workspace and CodeArts Snap will read these instructions.

# Huawei ModelArts vLLM / custom NPU deploy

Ponytail. No orchestrator package. Sign REST with `scripts/huawei_signed.py`. Never commit, echo, or paste SK / ECS passwords / docker login tokens / HF tokens.

Uncertain → ask in Chinese, short, with a recommended option. Do not create or reuse a resource the user did not confirm.

**New Huawei account = fresh intake.** Do not reuse AK/SK, project id, ECS IP, OBS bucket, SWR namespace, or DEW secret from a previous chat or another `.env.local`.

## Signed calls

```bash
pip -q install huaweicloudsdkkernel
export HUAWEI_AK=... HUAWEI_SK=... HUAWEI_PROJECT_ID=<modelarts project>
python scripts/huawei_signed.py GET 'https://modelarts.af-south-1.myhuaweicloud.com/v2/$HUAWEI_PROJECT_ID/services'
python scripts/huawei_signed.py POST 'https://...' body.json
```

IAM projects (ModelArts region and ECS region are often **different**):

```
GET https://iam.ap-southeast-1.myhuaweicloud.com/v3/projects
```

Endpoints: `modelarts.{ma_region}`, `obs.{ma_region}`, `swr.{ma_region}`, `kms.{ma_region}` (DEW/CSMS), `ecs.{ecs_region}` — all `*.myhuaweicloud.com`.

## 0. Runtime gate (before recap)

Fetch [vLLM-Ascend supported models](https://docs.vllm.ai/projects/ascend/en/latest/user_guide/support_matrix/supported_models.html). Tell the user the source.

| Matrix | Runtime | Probe |
|---|---|---|
| ✅ / 🔵 LLM or VL | **vLLM** — §7 image + `vllm serve` | `/health` then `/v1/chat/completions` |
| ❌ Whisper, or encoder-decoder ASR not listed | **custom** — [references/asr-custom.md](references/asr-custom.md) | `/health` then `/v1/audio/transcriptions` |
| Unknown | Stop. Ask: vLLM vs custom. Recommend from architecture (`WhisperForConditionalGeneration` → custom). |

Do **not** start `vllm serve` for Whisper. Matrix marks Whisper ❌ ([issue 2262](https://github.com/vllm-project/vllm-ascend/issues/2262)). Do **not** use `faster-whisper` / CTranslate2 on Ascend NPU (CPU/CUDA only). NPU path is `transformers` + `torch_npu`.

Gated HF (`gated: auto` / agree-to-share): need `HF_TOKEN` on the ARM ECS **download** step only. Accept the model terms in the browser first. After OBS upload, do not put the token in the inference service env.

## 1. Intake (once)

Ask in Chinese. Defaults in **bold**. Block until AK/SK and model name exist.

| Input | Default | Notes |
|---|---|---|
| **AK / SK** | env `HUAWEI_AK` `HUAWEI_SK` (or `huawei-ak` / `huawei-sk` in a user-named `.env.local` **for this account**) | Required. Session export only. Wrong-account file → ignore, ask again. |
| **Model name** | — | HF / ModelScope id, e.g. `Qwen/Qwen3-VL-8B-Instruct` or `Sunbird/asr-whisper-51-african-languages` |
| **Runtime** | from §0 | `vllm` or `custom`. Do not let the user skip the gate. |
| **NPU count** | lookup | Known models first: [references/model-recipes.md](references/model-recipes.md) (Qwen3.8-27B → **2**, Whisper Sunbird → **1**). Else matrix / fallback Qwen3-VL-8B → **1**. |
| **ModelArts region** | **`af-south-1` 南非** | Option: `ap-southeast-1` 香港. Third region: list flavors first, then ask. |
| **ECS region** | **`ap-southeast-3` 新加坡** | Option: `ap-southeast-1` 香港 **only if** ListFlavors has Kunpeng/`kc1`/`aarch64`. |
| **Pool** | **`public`** | `dedicated`: list pools, user picks id. Never `POST /pools`. |
| **ARM ECS** | user provides | See §2. Always ask first. |
| **HF_TOKEN** | — | Required if gated. Session / ECS env only. |

Then **one recap** (model, runtime + matrix source, NPU, regions, pool, ECS plan). Wait for 点头 before any mutate.

Export AK/SK for this session only. Do not write them into files unless the user already has a named env file and asks.

## 2. ARM ECS ladder (never silent pick/create)

开局必问：「请提供一台 **Kunpeng ARM** 准备机（IP、用户、SSH 密码或密钥）。没有的话告诉我，我再查现成的。」

1. **User gave IP/auth** → SSH, `uname -m` must be `aarch64`. Use only for download / docker / obsutil. Do not install extras they did not need. Wrong arch → stop, do not fall through to another host.
2. **User cannot provide** → `ListServers` in the chosen ECS region, keep Kunpeng/`kc1`/`aarch64`. Send name / flavor / EIP. **Wait for them to pick.** Never auto-use a host from a previous chat or another Huawei account.
3. **List empty** → propose a **small prep VM** (does not run the model): ~2–4 vCPU, 8GB RAM, data disk `max(100, weights_GB * 3 + 40)` GB, EulerOS ARM, pay-per-use. EIP **yes**, bandwidth **100 Mbps**, `chargemode: traffic` (not 5 Mbps). Send flavor / AZ / password. **Wait, then** `POST /v1/{project_id}/cloudservers` on `ecs.{ecs_region}.myhuaweicloud.com`. After ACTIVE: docker + obsutil, data disk mounted.
4. **Prereqs missing** (no VPC/subnet/SG, no Kunpeng flavor, no ARM image, quota) → stop. List what to open in console. Do **not** create VPC unless the user explicitly says 「可以建」 at this gate.

## 3. Mutation gates

After intake recap, **only stop again** for these. Download, `docker push`, health poll: do not interrupt.

Ask in Chinese, short, with a recommended option. No confirm → no create API.

- Create or choose an OBS bucket; overwrite an existing weights/code prefix
- Create a DEW secret (if one exists, list it and let them pick reuse vs new)
- Create inference service / PUT new version / **stop an existing public-pool service** (quota clash)
- Create ECS (flavor, EIP 100 Mbps traffic, login) — §2 step 3
- Dedicated: send pool list; user picks `pool_id`. Empty → offer public, or tell them to buy a pool. Never `POST /pools`
- Stop/delete a prep VM we created (after deploy is healthy — §8)

## 4. Automate vs user-prep

| Item | Decision | Why | User prepares / sees on failure |
|---|---|---|---|
| Deploy CLI package | **Skip** | This skill + `huawei_signed.py` is the runner | Nothing |
| ModelArts agency | **Automate** | `POST /v2/{project_id}/agency` then `POST /v2/{project_id}/authorizations` | GET authorizations first; if missing, create immediately. 403 / no IAM → console checklist below |
| Buy dedicated pool | **Skip** | Prepaid nodes; not a deploy side effect | Console: Running pool, Infer enabled, idle NPU ≥ count; reply name or id. Else public or buy first |
| Enable ModelArts/OBS/SWR/DEW/ECS in a region | **Skip** | Account-level console; no reliable one-shot REST | Enable those services in **both** regions. On “not enabled”, name the region + service |
| Small ECS | **Automate after confirm** | CreateServers works | §2. Missing VPC etc. → prep list, no silent create |
| DEW / SWR login / OBS / service CRUD | **Automate** | AK/SK is enough | Overwrite/create still hits §3 gates |

### Agency (automate)

1. `GET /v2/{project_id}/authorizations`
2. Empty → `POST /v2/{project_id}/agency` (body can be `{}` → `ma_agency`) then `POST /v2/{project_id}/authorizations` binding that agency to the current user
3. 403 or IAM denied — tell the user to prepare:

- 该 ModelArts 区域控制台 → 权限管理 → 一键授权 OBS、SWR、DEW/CSMS
- IAM 里能看到委托且信任 ModelArts
- 该区域已开通 OBS / SWR / DEW

Do not continue deploy without a working agency.

### Dedicated pool (still skip buy)

If user chose dedicated:

1. `GET /v2/{project_id}/pools`
2. Show Running + Infer/X-Infer + enough NPU. Wait for pick. `group_configs[0].pool_id = <id>`
3. Empty — tell them:

- 同区域已有专属池，状态 Running，范围含 Infer
- 空闲 NPU ≥ 本次卡数
- 回复池名称或 id；没有就改公共池或先自己买

Never `POST /v2/{project_id}/pools` during deploy.

### Region not enabled

Stop and say: 「请在控制台开通 {region} 的 {service}，开通后再叫我继续。」

## 5. Regions

**ModelArts + OBS + SWR + DEW = same region.** ECS may differ (cross-region obsutil / docker push).

| Role | Code | Use |
|---|---|---|
| ModelArts default | `af-south-1` | Johannesburg public Snt9b2 / Atlas A2 |
| ModelArts option | `ap-southeast-1` | Hong Kong — do not reuse SA SWR/OBS paths |
| ECS default | `ap-southeast-3` | Singapore Kunpeng |
| ECS option | `ap-southeast-1` | Hong Kong Kunpeng **if listed** |

Public Johannesburg flavors that worked: `modelarts.bm.arm.24u.192g.npu.1d910b` (1× Snt9b2), `modelarts.bm.arm.48u.384g.npu.2d910b` (2×). Dedicated: flavor from that pool's `status.resources.available`, not the public SKU blindly.

Johannesburg Snt9b2 = Ascend 910B3 = **A2**. A guide's "8× 910B3" is the public inference pool node (`modelarts.bm.npu.arm.8snt9b2.d`), **not** the prep ECS size. Public pool can schedule up to 8 NPUs; dedicated pool + SFS Turbo is optional, not required for the reference Qwen3.8 / Whisper deploys.

## 6. Pool behavior

**Public:** omit `pool_id`. Compact scheduling. Multiple public-pool services **can** run simultaneously (e.g. 1-card + 2-card + 1-card = 4 NPU across 3 services) — total NPU is the quota, not service count. Multi-NPU public pods have hit missing HCCL rank-table — prefer **1 NPU** unless the model needs TP>1. Qwen3.8-27B does: it ran on the public pool at TP 2 (2-card flavor) — [references/model-recipes.md](references/model-recipes.md). Upgrade: `max_surge=0%`, `max_unavailable=100%` (stop → PUT version → start). Rolling 25/25 on 4 cards often `FailedScheduling`.

**Dedicated:** same OBS/SWR/DEW/image/code as public. TP = visible NPUs. Do not apply public-pool rank-table folklore.

## 7. Deploy checklist

```
- [ ] intake recap accepted (includes runtime)
- [ ] ARM ECS (provided / user-picked / confirmed create)
- [ ] agency GET, create if missing
- [ ] image linux/arm64 in regional SWR
- [ ] weights OBS folder has config.json at mount root
- [ ] code script OBS → /code/  (overwrite gated)
- [ ] DEW secret keys accessKeyId / secretAccessKey
- [ ] service create (public | confirmed pool_id)
- [ ] API key create + bind
- [ ] /health then one task probe (chat or transcription)
- [ ] stop or delete this session's prep ECS (pay-per-use — do not leave it running)
```

### Image

SWR **in ModelArts region**, `linux/arm64` only.

**vLLM:** known good base `quay.io/ascend/vllm-ascend:v0.23.0` → `swr.{ma_region}.myhuaweicloud.com/<ns>/<name>:<tag>`.

**Per-model tags / NPU / cmd:** [references/model-recipes.md](references/model-recipes.md). Qwen3.8-27B = `vllm-ascend:qwen3.8-a2` on **2** NPU (TP 2), not v0.23.0. Whisper Sunbird = custom `whisper-custom:v0.23` on **1** NPU.

CreateService v2 `image` = `{"source": "SWR", "swr_path": "..."}`, not a string. Euler docker bridge has no PyPI: `docker run --network host` → `pip install` → `docker commit`.

v0.23: **do not** wrap with v0.9 `serve.sh --enforce-eager` (BackOffStart). MM limits: dotted `--limit-mm-per-prompt.image N` — JSON `'{"image":N}'` can fail argparse.

**custom ASR:** same base for CANN/`torch_npu`. On ARM ECS, `docker build` FROM it, `pip install` transformers accelerate librosa soundfile fastapi uvicorn python-multipart. **CMD must not be `vllm serve`.** Use `bash /code/serve.sh` from [templates/whisper/](templates/whisper/).

SWR login: signed create-authorization (or console long-term login), then `docker push` from the ARM ECS.

### Weights + code

- Custom model: OBS prefix whose **inner** folder has `config.json` → `/weight/`
- File mount: **code only** → `/code/`
- Cmd: `bash /code/<script>.sh`
- Container HTTP **8000**; gateway HTTPS
- Health HTTP `/health`, initial delay **300–600s**
- `TENSOR_PARALLEL_SIZE` = NPU count (vLLM only)
- Request timeout **180s**, body **≥50MB** (audio/VL), deploy timeout **60 min**

`obsutil` `-e=https://obs.{ma_region}.myhuaweicloud.com` + same AK/SK.

**obsutil cp nesting trap:** `obsutil cp ./subdir obs://bucket/prefix/subdir -r` creates **double-nested** `prefix/subdir/subdir/`. To upload a local dir **flat** into an OBS prefix, loop per-file:

```bash
cd /data/model-dir && dest=obs://bucket/prefix/weight/
for f in *; do obsutil cp "$f" "$dest$f" -f; done
```

`obsutil ls obs://<bucket>` on a **missing** bucket still echoes the name — confirm objects or an error line, not the name.

OBS-to-OBS flatten of an already-nested prefix: `obsutil cp obs://a/b/ obs://a/ -r` is rejected ("source and destination are nested"). Copy per-object instead: list keys under `a/b/b/`, `obsutil cp` each to `a/b/<file>`, then `obsutil rm a/b/b/ -r -f`.

**LoRA merge → save_pretrained config drift (critical):** Merging a PEFT LoRA into a VL base with transformers ≥4.50 and `model.save_pretrained()` writes a **decomposed** `config.json` (nested `text_config` / `vision_config`, drops top-level `vision_start_token_id` / `vision_end_token_id` / `image_token_id` / `video_token_id`). vLLM-Ascend loads it but emits **garbage multilingual tokens**. Fix: after merge, copy the **base model's original `config.json`** over the merged one (`cp base/config.json merged/config.json`) before OBS upload. Weights are fine — only the config format is wrong. Also copy `generation_config.json` from base.

**LoRA merge OOM on 8GB prep VM:** load + `PeftModel.from_pretrained` + `merge_and_unload` + `save_pretrained` of a 3B model peaks ~12GB. 8GB RAM → OOM-kill during save. Fix: add swap first — `fallocate -l 16G /data/swapfile && chmod 600 /data/swapfile && mkswap /data/swapfile && swapon /data/swapfile`. Also run the merge from a stable cwd (not a dir that gets `rm -rf`'d mid-pipeline — `os.getcwd()` on a deleted dir throws `FileNotFoundError`).

**nohup for long OBS uploads:** SSH channel timeout (30s) kills remote `obsutil cp` loops. Wrap uploads >30s in `nohup bash -c '...' > /dev/null 2>&1 &` and poll the log file.

Prep ECS EIP (CreateServers `publicip.eip.bandwidth`):

```json
{"size": 100, "sharetype": "PER", "chargemode": "traffic"}
```

Never default to 5 Mbps. If an existing prep EIP is still 5, PUT the bandwidth to 100 / traffic before large HF/OBS/SWR transfers.

### DEW

Public OBS mount: CSMS keys **exactly** `accessKeyId` / `secretAccessKey`. Dedicated: same DEW first (`secret_type=dew`).

### CreateInferService

`POST https://modelarts.{ma_region}.myhuaweicloud.com/v2/{project_id}/services`

- `type`: `REAL_TIME`
- Public: no `pool_id`. Dedicated: confirmed `pool_id`
- v2 body that returned 200: [references/model-recipes.md](references/model-recipes.md#v2-createservice-body-returned-http-200). `image` = `{"source": "SWR", "swr_path": ...}` object, `secret_type` `DEW`, field `flavor`, port 8000
- NPU count comes from `flavor` (`...npu.1d910b` / `...npu.2d910b`). `unit_configs[0].count` = **1** instance, not the NPU count
- **`runtime_config.service_limit.rate_limit` required** or `ModelArts.8037 RateLimit must not be null`: add `"rate_limit": {"num": 200, "unit": "SECONDS"}`
- PUT existing version number → `ModelArts.8031` → bump
- STOP can take minutes; START after PUT may 400 while already DEPLOYING — poll GET
- `FailedScheduling` WARNING on public pool is often **transient** — pod retries and schedules within 5-10 min. Do not delete; poll GET until `running_count ≥ 1`.

### API key

Create + **bind** (`ModelArts.8902` if unbound). Probe:

```
GET https://<infer-ip>/v2/infer/<service-id>/health
Authorization: Bearer <key>
```

Then:

- vLLM: one `/v1/chat/completions`. VL: **base64** (remote URLs from Johannesburg often 500).
- custom ASR: one `POST /v1/audio/transcriptions` with a short wav + forced `language`. Do not probe chat.
- vLLM-Omni image edit: `POST /v1/images/edits` multipart (`image` file + `prompt` text), timeout **300s**. Response is **JSON** `{"data":[{"b64_json":"..."}], ...}` — decode `b64_json` to get the PNG, not raw bytes.
- `predict_url` in `GET /services/{id}` is a **list** `[{"type":"PUBLIC","urls":["<ip>"]}, ...]`, not a string. Extract gateway IP from `predict_url[0]["urls"][0]`. Gateway is **HTTP port 80** (not HTTPS).

## 8. Cleanup (do not leave pay-per-use running)

Prep ECS is **not** the inference host. After a successful probe (or if the user says 用完了 / 关掉):

1. **This session's Kunpeng prep VM** (the name we created): recommend **STOP**, then **DELETE** if they will not rebuild images. Ask in Chinese, one line; default STOP. Do not leave it ACTIVE overnight.
2. Inference service: leave RUNNING unless they ask to stop it (demo may still need it).
3. OBS weights / SWR image: keep. Do not delete buckets as a side effect.
4. Extra empty buckets created by accident: tell the user and delete only if they say yes.

Stopping the prep VM: `POST /v1/{project_id}/cloudservers/action` `{ "os-stop": { "servers": [{ "id": "<id>" }] } }`. Delete only after explicit 可以删.

## Stop conditions

- x86 image on ARM NPU
- `vllm serve` for a matrix-❌ model (Whisper)
- `faster-whisper` on NPU
- OBS prefix without `config.json` at `/weight/`
- Overwriting a shared OBS code path the user did not name
- Hong Kong SWR/OBS on a Johannesburg service (or the reverse)
- `POST /pools` as a side effect of deploy
- Silent use/create of ECS, VPC, bucket, secret, or service
- Reusing another account's AK/SK, ECS, OBS, SWR, or DEW
- Printing SK, docker login password, ECS password, or HF token

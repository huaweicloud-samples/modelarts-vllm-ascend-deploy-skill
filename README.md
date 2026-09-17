# modelarts-vllm-ascend-deploy-skill

[![Status](https://img.shields.io/badge/Status-Incubating-blue)]()
[![Huawei Cloud](https://img.shields.io/badge/Huawei%20Cloud-Samples-red)]()
[![Scenario](https://img.shields.io/badge/Scenario-deterministic%20operations-success)]()

An AI coding agent skill (Cursor / Claude Code / Codex CLI / Huawei CodeArts Snap) for deploying LLM/VL/ASR models to **Huawei Cloud ModelArts** real-time inference on Ascend NPU (Snt9b2 / Atlas A2), using AK/SK signed REST calls — no CLI package required.

## Quick start

### Cursor

```bash
cp -r . ~/.cursor/skills/huawei-modelarts-vllm-deploy
```

Attach the skill in Cursor chat. The `SKILL.md` frontmatter registers it.

### Claude Code

```bash
git clone https://github.com/huaweicloud-samples/modelarts-vllm-ascend-deploy-skill.git
cd modelarts-vllm-ascend-deploy-skill
claude  # CLAUDE.md is auto-loaded
```

### Codex CLI

```bash
git clone https://github.com/huaweicloud-samples/modelarts-vllm-ascend-deploy-skill.git
cd modelarts-vllm-ascend-deploy-skill
codex  # AGENTS.md is auto-loaded
```

### Huawei CodeArts Snap

Clone this repo into your CodeArts workspace. `CODEARTS.md` provides instructions for the Snap AI assistant.

## What it does

- **Runtime gate**: checks the [vLLM-Ascend support matrix](https://docs.vllm.ai/projects/ascend/en/latest/user_guide/support_matrix/supported_models.html) to pick `vllm serve` vs custom FastAPI (Whisper ASR).
- **Signed REST**: signs all ModelArts / OBS / SWR / ECS / DEW calls with `scripts/huawei_signed.py` (Huawei Cloud SDK signer).
- **Full deploy pipeline**: intake -> ARM ECS prep -> agency -> SWR image -> OBS weights -> DEW secret -> CreateInferService -> API key -> health + task probe -> cleanup.
- **LoRA merge**: on-prep-VM merge with swap + config-drift fix.
- **Custom ASR**: Whisper on `torch_npu` via FastAPI (vLLM does not support Whisper on Ascend).

## Files

| File | Platform | Purpose |
|------|----------|---------|
| `SKILL.md` | Cursor | Main skill (with frontmatter) |
| `CLAUDE.md` | Claude Code | Auto-loaded instructions |
| `AGENTS.md` | Codex CLI | Auto-loaded instructions |
| `CODEARTS.md` | CodeArts Snap | Instructions for Snap |
| `scripts/huawei_signed.py` | All | AK/SK REST signer |
| `templates/whisper/` | All | Custom ASR runtime (serve.sh, server.py, language_tokens.py) |
| `references/asr-custom.md` | All | Custom ASR reference |

All instruction files share the same content — only the header and entry point differ per platform.

## Prerequisites

```bash
pip install huaweicloudsdkkernel
```

Set env vars (never commit these):
```bash
export HUAWEI_AK=<your-ak>
export HUAWEI_SK=<your-sk>
export HUAWEI_PROJECT_ID=<modelarts-project-id>
```

## Security

- Never stores AK/SK, passwords, or tokens in files — all via env vars / session only.
- No account-specific info (IPs, project IDs, bucket names) in the skill itself.

## Contributing

Please use pull requests and follow the repository review rules.

## License

MIT

## Maintainers

CODEOWNERS: @SoraShen

## Feedback

Please use GitHub Issues: https://github.com/huaweicloud-samples/modelarts-vllm-ascend-deploy-skill/issues

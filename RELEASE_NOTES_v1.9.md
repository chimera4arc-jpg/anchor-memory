# Anchor Memory v1.9

## 为什么修

v1.8 之前 Anchor 的所有 LLM 调用都写死了 `anthropic.Anthropic()` + 写死的 Claude model id。问题：

1. **不是所有人都用 Claude**。Anchor 的目标用户是"养 AI 的人"——这些人里大多数养的不是 Claude。强制要求 Anthropic API key 把 ChatGPT、Gemini、DeepSeek、GLM、本地 Ollama 用户都拒之门外。
2. **默认 Sonnet 4.6 太贵**。dream pass 跑 50 对采样 ≈ $0.075/次。每天跑 = $2.25/月。auto-discovery 在大库上按比例放大，1000 条记忆 backfill 一次 = $1.17。新用户克隆 Anchor、灌入既往聊天记录、一夜烧光额度的风险真实存在。
3. **没有成本透明度**。用户不知道 dream pass 花了多少。
4. **没有 daily cap 防护**。

## 怎么修的

### 1. LLM 抽象层 (`anchor_llm.py`)

所有 LLM 调用现在走统一接口：

```python
class LLM:
    def call(self, system, user, max_tokens, temperature) -> LLMResponse: ...
```

实现：
- `AnthropicLLM` — Claude
- `OpenAILLM` — ChatGPT / GPT-5
- `GoogleLLM` — Gemini
- `OpenAICompatLLM` — DeepSeek / GLM / Ollama / LM Studio / 任何 OpenAI-兼容端点
- `CallableLLM` — 用户传函数（用于 MCP sampling 或任意自定义 backend）

### 2. 配置文件 `~/.anchor/config.yaml`

```yaml
llm:
  provider: anthropic
  model: claude-haiku-4-5-20251001
safety:
  max_cost_per_day_usd: 5.0
  warn_above_per_pass_usd: 0.10
```

### 3. 引导 CLI (`anchor_init.py`)

```
$ python -m anchor_init
What LLM provider do you use?
  1) Claude (Anthropic)
  2) ChatGPT / GPT-5 (OpenAI)
  3) Gemini (Google)
  4) DeepSeek
  5) GLM / Zhipu
  6) Local Ollama
  7) Skip
```

引导用户选 provider、推荐每家最便宜的小模型、可选设置 daily cap。

### 4. Spend tracking

每次 LLM 调用记到 `~/.anchor/spend.jsonl`：

```json
{"ts": 1716...., "date": "2026-05-23", "provider": "anthropic", "model": "claude-haiku-4-5-20251001", "input_tokens": 250, "output_tokens": 50, "cost_usd": 0.0005}
```

`today_spend_usd()` 查今天总花费。`session_spend_summary()` 按日期、provider 聚合。

### 5. Daily cap 强制执行

如果 `safety.max_cost_per_day_usd` 设置了，每次 LLM 调用前检查今日已花费。超过 cap → 抛 `SpendCapExceeded`，**调用根本不会发出**。明天才会重置。

### 6. 默认模型从 Sonnet 改成 Haiku

`ANCHOR_DREAM_MODEL` 老 env var 仍然被尊重（向后兼容），但**没有显式设置时默认就是 Haiku 4.5**。dream pass 成本降到原来的 1/3。

### 7. 御三家模型映射写进 README

README 现在有 "Recommended Models" 表，覆盖 Anthropic / OpenAI / Google / DeepSeek / GLM / Ollama，每家给推荐的最便宜小模型 + 典型 dream pass 成本估算。

## Resolution order

需要 LLM 时，按以下顺序解析：

1. 显式 `llm=` 参数
2. `ANCHOR_LLM` env (form: `provider/model`)
3. `~/.anchor/config.yaml`
4. Fallback: `ANTHROPIC_API_KEY` 在 env → Anthropic Haiku
5. `ConfigError` with 引导说明

## Breaking changes

**无**。所有现有函数签名保持兼容：

- `mem.split_bundled(model="claude-sonnet-4-6")` 仍然工作（当 `ANTHROPIC_API_KEY` 在 env 时使用此 model）
- `concept_link.extract_concepts(memories, cache, model=...)` 仍然工作
- `dream_extras.run_global_dedup(mem, model=...)` 仍然工作
- 任何代码不传 `llm=` 参数都会自动 fall back 到 `get_default_llm()`

`model=` 参数标记为 deprecated 但不会移除。新代码应该传 `llm=` 参数或依赖 `~/.anchor/config.yaml`。

## 迁移指南

**不需要任何迁移**。现有部署继续按原样工作（默认 Haiku 代替 Sonnet，成本下降）。

**推荐**（不强制）：

1. 运行 `python -m anchor_init` 一次，写入 `~/.anchor/config.yaml`
2. 设置 daily cap（推荐 $5 给个人用户）
3. 老的 `ANCHOR_DREAM_MODEL` env var 可以删掉

## 下一步（v2.0 思路）

- MCP `sampling` 协议支持 —— host AI 透明替 Anchor 跑 LLM 调用，零额外 API key 配置
- 第一次调用 MCP search 时通过 elicitation 让 host AI 帮用户配置
- `anchor cost --since=2026-05-01` CLI 命令查历史
- 让 dream pass 在启动前打印估算+确认（当前只在超过 warn cap 时警告）

# Anchor Memory v1.9.1

## 为什么修

v1.9 加了 LLM 抽象层，但 `AnthropicLLM._call_raw` 把 system prompt 当普通字符串传给 SDK——**根本没启用 prompt cache**。每次 dream pass / concept_link / dedup 都全量重发系统提示，没复用之前几秒前刚发过同样的字符串。

加上 anthropic 默认 cache TTL 只有 5 分钟。dream pass 跑大库时单次 walk 可以跑半小时——5min TTL 内每次 chunk 间隔超过 5min 就 miss，最坏情况下每个 chunk 都付 full price。

## 怎么修的

### 1. `AnthropicLLM` 自动启用 prompt cache

`call()` 现在把 system 包装成 `cache_control: ephemeral` block。对 prompt 大小 ≥1024 tokens 的调用 anthropic 会缓存；<1024 tokens 自动无效化但不报错——所以可以无条件包装。

### 2. 新增 `cache_ttl="5m"|"1h"` 参数

```python
llm.call(system=SYSTEM_PROMPT, user=content, cache_ttl="1h")
```

- `"5m"` (默认): 与 v1.9 行为一致，零成本上界
- `"1h"`: anthropic extended-cache-ttl beta，1h write 是 5m write 的 2x，但 read 一样 0.1x。只要单个 cache write 之后能撑过 2 次 read 就划算

Anchor 自带的长跑 pass 全部切到 `"1h"`：
- `dream_extras.run_global_dedup` / `run_fact_check`
- `concept_link.extract_concepts` / `confirm_pairs`
- `auto_consolidate._llm_confirm`
- `anchor_memory.split_bundled`

其他 provider (OpenAI / Google / OpenAI-compat / Callable) 接受相同参数但忽略它——它们各自有自动 cache 或不计费。

### 3. 真实的 cache 成本会计

`AnthropicLLM` 现在读响应里的 `cache_read_input_tokens` 和 `cache_creation_input_tokens`，按 anthropic 真实定价计算：

- input_no_cache: base × 1.0
- cache_read: base × 0.1
- cache_write_5m: base × 1.25
- cache_write_1h: base × 2.0

`~/.anchor/spend.jsonl` 写入的 cost_usd 现在准确反映 cache 优惠。

## 实测效果

诊断时一个典型 backfill 日 (5/23) Limen Sonnet 花了 $154，其中 input_no_cache $122 (79%)，cache_read $0.02 (~0%)——cache 完全没生效。

打开 1h TTL 后，预计同等工作量降到 $30-50（cache write 一次抵 10+ chunk 复用）。

## Breaking changes

无。

- 现有调用方不传 `cache_ttl` → 默认 `"5m"` → 行为和 v1.9 一致（除了现在 system 也会被包装、cache 会真正生效，省钱不破坏功能）
- `_price()` 增加可选参数 cache_read_tok/cache_write_tok/cache_ttl，老调用方不传时默认 0/0/"5m"，结果与 v1.9 一致

## 用法

什么都不用改。`dream_pass()`, `concept_link.run()`, etc. 都已经在内部用 1h TTL 了。

如果你有自己的 LLM 调用想用 1h TTL：

```python
from anchor_llm import get_default_llm

llm = get_default_llm()
resp = llm.call(system=MY_PROMPT, user=content, cache_ttl="1h")
print(f"cost: ${resp.cost_usd:.4f}")
```

## 下一步

v2.0 还在思路里 — MCP sampling、第一次 search 时通过 elicitation 配置、`anchor cost` CLI。

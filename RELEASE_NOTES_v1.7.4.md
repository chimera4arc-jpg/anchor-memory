# Anchor Memory v1.7.4

## 为什么修

存记忆的时候如果传进来的不是普通字符串（比如 `None`、`bytes`、从数据库取出来的特殊字符串类型），整个 `store()` 调用会直接崩在编码那一步。常见场景是从 CSV、API 返回、SQL 查询批量灌记忆——里面偶尔有一行的 text 字段是 `None`，整个流程就停了。

## 怎么修的

`store(memory_id, text, ...)` 一进来先把 `text` 强转成字符串、去空白：

- 是 `None` 或者空白 → 立刻抛清楚的 `ValueError("Memory text cannot be empty")`，不让脏数据进库
- 是 `bytes` / numpy 字符串 / 其他"近似 str" → 自动转成干净 `str`，正常往下走

明确报错比悄悄塞条空记忆然后让搜索时崩好。

## 修完之后

- 批量灌记忆遇到坏数据 → 看到清晰的错误信息，知道哪条挂了
- 之前隐式 work 的调用 → 行为完全一样
- 不会再因为 sentence-transformers 升级把所有老脚本崩掉

# Anchor Memory v1.7.5

## 为什么修

Windows 用户接 Anchor 的 MCP server 时（LobeHub / SillyTavern / Claude Code 等）会随机崩——查中文、写中文、几次下来 session 就 disconnect，看不出规律。

根因：Windows 命令行默认编码不是 UTF-8（中文 Windows 是 GBK）。Anchor 跟 MCP 的客户端走 UTF-8 协议，两边对不上的时候，中文进出都会乱：
- AI 回的中文写到 stdout 时被当 GBK 解码 → 报 `UnicodeDecodeError`
- 用户的中文 query 进 stdin 时变成乱码 → 存记忆崩

macOS 和 Linux 默认 UTF-8 所以从来没这问题，所以也没人提早发现。

## 怎么修的

MCP server 启动时，强制 stdin / stdout 走 UTF-8，不管系统默认是什么编码：

- 是 Windows，或者检测到 stdout 编码不是 UTF-8 → 自动重新包装成 UTF-8
- 万一上游真的传了乱字节进来 → 用 � 代替而不是让整个 session 崩

## 修完之后

- Windows 上接任何 MCP 客户端 → 中文进出正常，不再随机断
- 跨平台 → macOS / Linux 不受影响（已经是 UTF-8 不触发）
- 极端情况下哪怕字节真的坏了 → 单条消息显示替换符号，session 不挂

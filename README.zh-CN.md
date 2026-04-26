# Agent Harness CLI Example

[English](README.md) | [简体中文](README.zh-CN.md)

一个使用 `agent-harness-cli` 参考模式的最小 Codex 写作任务。

本仓库是 [Biaoo/agent-harness-cli](https://github.com/Biaoo/agent-harness-cli) 的可运行示例。它用“写一篇议论文”作为 artifact，演示这个实用参考框架如何作用于 agentic 写作任务：Codex 生成文章，项目级 hook 运行检查，报告再指导下一轮修改。

## Harness Engineering Flow

示例里的 artifact 是一篇短文，但重点是围绕 artifact 建立验收循环：

1. Codex 写入 `essay.md`。
2. 项目级 Stop hook 运行 `agent-harness`。
3. harness 执行确定性检查和 LLM 辅助检查。
4. blocking failure 会作为 continuation prompt 返回给 Codex。
5. Codex 修改 artifact，并重新进入检查循环，直到 blocking check 通过。

这展示了 harness engineering 在 agentic 工作中面向 artifact 的作用：让目标可约束、可观测、可验证；把验收标准外部化；并让 Agent 根据证据迭代。

同样的模式可以复用于项目文档、规格说明、研究笔记、代码修改、数据报告，以及其他需要 Agent 友好验收的 artifact。

这个示例也保持和 CLI 相同的边界：框架提供循环，项目自己负责 artifact 契约、checklist、check 脚本和 LLM judge 行为。

## 这个示例应该学到什么

- artifact 契约是明确的：Codex 必须写入 `essay.md`。
- 客观要求变成确定性检查，例如精确长度。
- 语义要求放在人类可读的 checklist 中。
- LLM judge 填写 checklist，而不是直接生成最终 harness JSON。
- check 脚本把 checklist 解析成确定性的 harness 输出。
- blocking check 失败时，Stop hook 会把失败报告变成 Codex 的下一轮提示。

## 相关项目

- CLI 和 skill 源码：[Biaoo/agent-harness-cli](https://github.com/Biaoo/agent-harness-cli)
- 本仓库演示已发布的 `agent-harness-cli` 包，以及 Codex Stop hook 工作流。

## 验收面

任务要求 Codex 写一篇关于“在效率时代保持深度思考”的议论文。

harness 会运行两个检查：

| 要求 | Check | 类型 | 严重性 | 要求来源 |
| --- | --- | --- | --- | --- |
| 文章长度为 1000 字符，允许正负 10 字符误差。 | `essay_length` | 确定性脚本 | `error` | `task.json` 中的长度配置 |
| 文章满足论证质量 rubric，包括使用一个今年的时事例子。 | `essay_quality` | 本地 Codex checklist judge | `error` | `checklists/essay_quality.md` |

内容要求放在 Markdown checklist 中。LLM judge 填写 checklist，check 脚本再把 `- [x]` 和 `- [ ]` 解析成 harness JSON。这样最终机器协议仍然是确定性的，同时避免强迫模型直接输出严格 JSON。

## 前置条件

| 工具 | 要求版本 | 用途 | 验证方式 |
| --- | --- | --- | --- |
| `uv` | `0.9.3` | 通过 `uvx` 运行已发布的 `agent-harness-cli` 包。 | `uv --version` |
| `agent-harness-cli` | `0.1.1` | 提供 `agent-harness run-checks` 和 `agent-harness view`。 | hook 固定使用 `uvx --from agent-harness-cli==0.1.1 ...`，不需要全局安装。 |
| Codex CLI | `codex-cli 0.125.0` | 通过 `codex exec` 运行本地 LLM checklist judge。 | `codex --version` |

如果 Codex CLI 是通过 npm 安装的：

```bash
npm install -g @openai/codex@0.125.0
```

质量 checklist check 会调用 `codex exec`，所以 Codex CLI 还需要在本目录中可以非交互运行并已登录。本示例验证环境为 Node.js `v22.22.2` 和 npm `10.9.7`。

## 试运行

在本目录启动 Codex session，并输入：

```text
Write an argumentative essay about "preserving deep thinking in the age of efficiency".
Save it to essay.md. The essay must be 1000 characters, with an allowed deviation of no more than 10 characters.
Use the project checklist as the content acceptance criteria.
```

当 Codex 准备停止时，`.codex/hooks.json` 中的项目级 Stop hook 会运行：

```bash
uvx --from agent-harness-cli==0.1.1 agent-harness run-checks --task task.json --report-id latest
```

如果 blocking check 失败，hook 会返回 Codex continuation decision，而不是允许本轮结束。Codex 应读取生成的报告、修改 artifact、重新运行 harness，并且只在 blocking check 通过后结束。

## 查看报告

报告会写入 `reports/`。

查看最新报告：

```bash
uvx --from agent-harness-cli==0.1.1 agent-harness view latest --page-size 2
```

只查看失败检查：

```bash
uvx --from agent-harness-cli==0.1.1 agent-harness view latest --failed-only --page-size 5
```

手动只运行确定性检查：

```bash
AGENT_HARNESS_ENABLE_LLM=0 uvx --from agent-harness-cli==0.1.1 agent-harness run-checks --task task.json --report-id deterministic
```

## 项目结构

```text
.codex/
  hooks.json                         项目级 Stop hook 配置。
  hooks/run-agent-harness-check.sh   运行 harness 的 hook 脚本。
checklists/
  essay_quality.md                   人类可读的内容 checklist。
checks/
  check_length.py                    确定性长度检查。
  check_llm_content.py               基于 checklist 的内容检查。
  local_codex_judge.py               本示例自有的 local codex exec helper。
task.json                            Harness task 定义。
essay.md                             生成 artifact，由 Codex 在任务中创建。
```

## 设计说明

- 示例通过 `uvx` 直接使用已发布的 PyPI 包。
- 不依赖相邻 checkout，也不使用 editable 本地依赖。
- Stop hook 对 blocking failure 使用 `decision: "block"`，让 Codex 继续工作。
- LLM 相关逻辑放在示例自己的 check 脚本中，而不是 CLI 中。
- `reports/` 是生成产物，不应提交。

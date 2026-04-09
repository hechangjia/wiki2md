# wiki2md

[![CI](https://github.com/hechangjia/wiki2md/actions/workflows/ci.yml/badge.svg)](https://github.com/hechangjia/wiki2md/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/wiki2md)](https://pypi.org/project/wiki2md/)
[![Python versions](https://img.shields.io/pypi/pyversions/wiki2md)](https://pypi.org/project/wiki2md/)
[![License](https://img.shields.io/github/license/hechangjia/wiki2md)](https://github.com/hechangjia/wiki2md/blob/main/LICENSE)

把 Wikipedia 人物词条转换成适合 AI / RAG 使用的本地 Markdown 语料包。

`wiki2md` 会把噪声较多的百科页面整理成稳定的本地语料目录：干净的 `article.md`、结构化 sidecar，以及本地 `assets/`，更适合切块、embedding、检索和审计。

## 为什么适合 AI / RAG

- `article.md` 优先保留干净 prose，方便阅读、切块和 embeddings
- `meta.json`、`references.json`、`infobox.json` 保留结构化上下文和来源线索
- 本地 `assets/` 避免远程图片漂移
- `batch` 支持可恢复的大批量语料构建

## 范围与限制

- 当前聚焦 Wikipedia 人物词条，person pages 是 v1 的一等目标
- 目前是 English-first Wikipedia 支持，优先保证英文人物页面的稳定输出
- 已提供中文兼容能力，但还不是对所有中文页面形态都完全通用
- 非目标或非一等目标包括 list、timeline、以及特殊命名空间等页面类型

## 快速开始

用户安装路径：

```bash
pip install wiki2md
wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
wiki2md inspect "https://en.wikipedia.org/wiki/Andrej_Karpathy"
wiki2md batch examples/batch/person-manifest.jsonl --output-dir output
```

贡献者仓库路径：

```bash
git clone https://github.com/hechangjia/wiki2md.git
cd wiki2md
uv sync --extra dev
uv run wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
uv run wiki2md inspect "https://en.wikipedia.org/wiki/Andrej_Karpathy"
uv run wiki2md batch examples/batch/person-manifest.jsonl --output-dir output
```

## 核心命令

```bash
wiki2md convert <url>
wiki2md inspect <url>
wiki2md batch <file>
```

`inspect` 只输出 JSON 元数据，不写入本地文件；`convert` 会落地单篇目录；`batch` 适合持续构建语料库。

```bash
uv run wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
uv run wiki2md inspect "https://en.wikipedia.org/wiki/Andrej_Karpathy"
uv run wiki2md batch examples/batch/person-manifest.jsonl --output-dir output
```

## 单篇人物示例

仓库内置示例目录：
- `examples/andrej-karpathy/`

运行后的代表性输出结构：

```text
output/
  people/
    andrej-karpathy/
      article.md
      meta.json
      references.json
      infobox.json
      assets/
```

仓库示例主要提交文本 sidecar：`article.md`、`meta.json`、`references.json`、`infobox.json`。真实运行时仍会下载并引用本地 `assets/`，只是二进制资源不纳入示例目录版本控制。

`examples/andrej-karpathy/article.md` 片段：

```markdown
# Andrej Karpathy

## Profile

Andrej Karpathy is a computer scientist.
```

如果你想先看完整输出，再对接自己的管线，可以直接从 `examples/andrej-karpathy/` 开始验证 `article.md`、`meta.json`、`references.json` 和 `infobox.json` 的消费方式。

## 批量语料工作流

`batch` 同时支持纯 `txt` URL 列表和结构化 `jsonl` manifest。推荐把单篇验证通过后的 URL 清单沉淀成 `examples/batch/person-manifest.jsonl` 这类输入，再统一输出到 `output/`。

`txt` 模式每行一个 URL，忽略空行和 `#` 注释：

```bash
uv run wiki2md batch urls.txt --output-dir output
```

`jsonl` 模式支持每行附带 `page_type`、`slug`、`tags`、`output_group` 等字段：

```bash
uv run wiki2md batch examples/batch/person-manifest.jsonl --output-dir output
```

示例 `jsonl` 行：

```json
{"url":"https://en.wikipedia.org/wiki/Andrej_Karpathy","page_type":"person","slug":"andrej-karpathy","tags":["ai","person"],"output_group":"people-ai"}
```

常用参数：
- `--output-dir`：指定输出根目录，默认 `output`
- `--overwrite`：目标目录已存在时强制重跑
- `--concurrency`：设置并发数，默认 `4`
- `--skip-invalid`：跳过非法 manifest 行，而不是严格失败
- `--resume`：从已有状态文件恢复长任务

恢复执行示例：

```bash
uv run wiki2md batch examples/batch/person-manifest.jsonl \
  --output-dir output \
  --resume output/.wiki2md/batches/<batch-id>/state.json
```

批处理状态文件位于 `output/.wiki2md/batches/`：
- `state.json`：可恢复执行状态
- `batch-report.json`：完整运行摘要和逐条结果
- `failed.txt`：失败 URL 快速清单
- `failed.jsonl`：失败 manifest 行，适合作为重试输入
- `invalid.jsonl`：非法 manifest 行，仅在出现非法行时生成

直接重试失败条目：

```bash
uv run wiki2md batch output/.wiki2md/batches/<batch-id>/failed.jsonl --output-dir output
```

## 输出契约

- `article.md`：优先面向阅读和 AI 消费的干净正文
- `meta.json`：抓取时间、源页面、统计信息等文章级元数据
- `references.json`：结构化来源与引用链路
- `infobox.json`：机器可读的人物结构化信息
- `assets/`：正文或 infobox 依赖的本地图片资源

契约重点：
- `article.md` 是 clean-first prose，不内嵌 Wikipedia 风格的 `[8]` 引用标记，方便切块与审计
- `article.md` 在可用时会渲染可读的 `## Profile` 段落，承接人物 infobox 的核心字段
- `infobox.json` 保存机器可读 infobox 数据，包括所选图片元信息和字段列表
- `references.json` 是 provenance sidecar；每条 reference 都会尽力写入 `primary_url`，每个 link 都会标注分类 `kind`，取值包括 `external`、`wiki`、`archive`、`identifier`、`other`

示例入口：
- `examples/andrej-karpathy/`
- `examples/batch/person-manifest.jsonl`

## 发布流程

正式发布由 GitHub Release 触发，并通过 PyPI Trusted Publishing 完成。

1. 更新 `pyproject.toml` 中的版本号，例如 `0.1.0` -> `0.1.1`
2. 更新 `CHANGELOG.md`
3. 将包含版本号和 changelog 更新的发布提交推送到 `main`
4. 等待该 `main` 提交对应的 CI 全部通过，再继续创建 release
5. 以这个已经通过 CI 的 `main` 提交为基准，在 GitHub 上创建并发布 `v0.1.1` tag / Release
6. `publish.yml` 会校验 release tag 与 `pyproject.toml` 版本一致后，再自动发布到 PyPI

前置条件：
- 需要先在 PyPI 项目侧配置 GitHub OIDC Trusted Publisher
- 仓库内不保存长期 PyPI token

## English Summary

`wiki2md` converts Wikipedia person pages into clean local corpus artifacts for AI workflows. It focuses on `article.md`, structured JSON sidecars, local assets, and resumable batch processing. Current scope: English-first Wikipedia, Chinese-compatible, person pages as the current focus.

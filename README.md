# wiki2md

[![CI](https://github.com/hechangjia/wiki2md/actions/workflows/ci.yml/badge.svg)](https://github.com/hechangjia/wiki2md/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/wiki2md)](https://pypi.org/project/wiki2md/)
[![Python versions](https://img.shields.io/pypi/pyversions/wiki2md)](https://pypi.org/project/wiki2md/)
[![License](https://img.shields.io/github/license/hechangjia/wiki2md)](https://github.com/hechangjia/wiki2md/blob/main/LICENSE)

一个通用 Wikipedia -> Markdown 转换工具，把 Wikipedia 条目整理成标准化、本地化、AI 可读的 Markdown 语料包。

`wiki2md` 的核心目标不是替你预做 RAG 处理，而是把 Wikipedia 原始页面清洗成稳定的本地 Markdown 与结构化 sidecar。它并不只限于人物页；人物 discovery 只是辅助工作流，核心仍然是通用转换。

## 为什么适合

- `article.md` 保持条目主体，尽量忠实投影 Wikipedia 内容结构
- `meta.json`、`references.json`、`infobox.json`、`section_evidence.json` 保留结构化上下文
- 本地 `assets/` 避免远程图片漂移
- `batch` 支持可恢复的大批量处理
- 后续要做 AI / RAG、知识库、审计或归档，都可以基于 `md + meta` 自己处理

## 快速开始

用户安装路径：

```bash
pip install wiki2md
wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
wiki2md inspect "https://en.wikipedia.org/wiki/Linux"
wiki2md batch ./urls.txt --output-dir output
```

贡献者仓库路径：

```bash
git clone https://github.com/hechangjia/wiki2md.git
cd wiki2md
uv sync --extra dev
uv run wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy"
uv run wiki2md inspect "https://en.wikipedia.org/wiki/Linux"
uv run wiki2md batch examples/manifests/turing-award-core.jsonl --output-dir output
```

## 核心命令

```bash
wiki2md convert <url>
wiki2md inspect <url>
wiki2md batch <file>
wiki2md batch discover <url-or-preset>
```

- `inspect` 只输出 JSON 元数据，不写本地文件
- `convert` 负责单篇条目转换
- `batch` 负责规模化抓取
- `batch discover` 负责从奖项页、机构页、列表页生成候选人物 manifest

## 单篇转换示例

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

单篇转换既可以是人物页：

```bash
uv run wiki2md convert "https://en.wikipedia.org/wiki/Andrej_Karpathy" --output-dir output
```

也可以是常见非人物页：

```bash
uv run wiki2md convert "https://en.wikipedia.org/wiki/Linux" --output-dir output
```

`examples/andrej-karpathy/article.md` 片段：

```markdown
# Andrej Karpathy

Andrej Karpathy is a computer scientist.

## Career

Karpathy worked at OpenAI and Tesla.
```

## 人物发现工作流

如果你要从奖项、机构、学校、列表页中发现值得抓取的人物，而不是只靠自己记忆，可以先生成一份候选 manifest：

```bash
uv run wiki2md batch discover turing-award --output-dir output
```

发现产物会落到：

```text
output/
  discovery/
    turing-award/
      manifest.jsonl
      index.md
      discovery.json
```

其中：
- `manifest.jsonl` 直接给 `wiki2md batch` 使用
- `index.md` 方便人工审查和筛选
- `discovery.json` 保留来源页、候选人和筛选理由

继续批量抓取：

```bash
uv run wiki2md batch output/discovery/turing-award/manifest.jsonl --output-dir output
```

## 批量语料工作流

`batch` 同时支持纯 `txt` URL 列表和结构化 `jsonl` manifest。

单篇和批量目前都会统一落到 `output/people/<slug>/`。这个目录名保持稳定，语义上的 `page_type` 则写进 `meta.json` 与 frontmatter，而不是再把不同页面类型拆成不同目录树。

`txt` 模式每行一个 URL，忽略空行和 `#` 注释：

```bash
uv run wiki2md batch urls.txt --output-dir output
```

`jsonl` 模式支持每行附带 `page_type`、`slug`、`tags`、`output_group` 等字段：

```bash
uv run wiki2md batch examples/manifests/turing-award-core.jsonl --output-dir output
```

示例 `jsonl` 行：

```json
{"url":"https://en.wikipedia.org/wiki/Geoffrey_Hinton","page_type":"person","slug":"geoffrey-hinton","tags":["computer-science","ai","turing-award"],"output_group":"turing-award"}
```

内置 starter manifests：
- `examples/manifests/turing-award-core.jsonl`
- `examples/manifests/fields-medal-core.jsonl`
- `examples/manifests/nobel-physics-core.jsonl`

常用参数：
- `--output-dir`：指定输出根目录，默认 `output`
- `--overwrite`：目标目录已存在时强制重跑
- `--concurrency`：设置并发数，默认 `4`
- `--skip-invalid`：跳过非法 manifest 行，而不是严格失败
- `--resume`：从已有状态文件恢复长任务

恢复执行示例：

```bash
uv run wiki2md batch examples/manifests/turing-award-core.jsonl \
  --output-dir output \
  --resume output/.wiki2md/batches/<batch-id>/state.json
```

批处理状态文件位于 `output/.wiki2md/batches/`：
- `state.json`
- `batch-report.json`
- `failed.txt`
- `failed.jsonl`
- `invalid.jsonl`

直接重试失败条目：

```bash
uv run wiki2md batch output/.wiki2md/batches/<batch-id>/failed.jsonl --output-dir output
```

## 输出契约

- `article.md`：条目主体，优先保留干净正文和信息结构
- `meta.json`：源页面、抓取时间、`page_type`、warnings、cleanup 统计
- `references.json`：结构化引用与来源链路
- `infobox.json`：机器可读 infobox 信息
- `section_evidence.json`：章节级 citation 聚合
- `sources.md`：按 section 组织的来源摘要
- `assets/`：本地图片资源

契约重点：
- `article.md` 不再额外注入人物知识卡，保持更纯粹的 article 形态
- `page_type` 写在 frontmatter 和 `meta.json`，用于后续程序判断
- `references.json` 中每条 reference 会尽量给出 `primary_url`
- 每个 reference link 都带 `kind`，可能值包括 `external`、`wiki`、`archive`、`identifier`、`other`
- `infobox.json` 继续保留结构化 infobox 数据，不强制在 `article.md` 里重渲染

示例入口：
- `examples/andrej-karpathy/`
- `examples/manifests/turing-award-core.jsonl`
- `examples/manifests/fields-medal-core.jsonl`
- `examples/manifests/nobel-physics-core.jsonl`

## 发布流程

正式发布由 GitHub Release 触发，并通过 PyPI Trusted Publishing 完成。

1. 更新 `pyproject.toml` 中的版本号，例如 `0.1.0` -> `0.1.1`
2. 更新 `CHANGELOG.md`
3. 将发布提交推送到 `main`
4. 等待该提交对应的 CI 全部通过
5. 以已经通过 CI 的 `main` 提交为基准，在 GitHub 上创建并发布 `v0.1.1` tag / Release
6. `publish.yml` 会校验 release tag 与 `pyproject.toml` 版本一致后，再自动发布到 PyPI

前置条件：
- 需要先在 PyPI 项目侧配置 GitHub OIDC Trusted Publisher
- 仓库内不保存长期 PyPI token

## English Summary

`wiki2md` is a general Wikipedia-to-Markdown converter. It produces a clean `article.md`, structured sidecars such as `meta.json` and `references.json`, local `assets/`, resumable batch output, and optional people discovery manifests from strong Wikipedia index pages such as awards and institutions.

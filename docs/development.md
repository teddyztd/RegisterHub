# 开发门禁：CI 与本地 pre-commit 钩子

本仓库用同一份 pytest 套件作为唯一事实来源（single source of truth）：CI 在每次 push / pull_request 上运行它，本地可选的 pre-commit 钩子在提交前运行同一条快速命令。

## 持续集成 (GitHub Actions)

工作流：`.github/workflows/tests.yml`

- **触发**：`push` 与 `pull_request`（目标分支 `main`）。
- **矩阵**：Python `3.10`、`3.11`、`3.12`、`3.13`。
- **步骤**：检出代码 → 安装 `requirements.txt` → 运行 `python -m pytest`。
- **失败语义**：任一测试失败即 `python -m pytest` 以非零码退出，对应 job 失败，从而阻断合并。

## 本地 pre-commit 钩子（可选 / opt-in）

仓库自带钩子：`.githooks/pre-commit`。它在每次 `git commit` 前运行 `python -m pytest`，测试失败则拒绝提交。

**一次性启用（仅写入本仓库的 `.git/config`，绝不改动全局 Git 配置）：**

```bash
git config core.hooksPath .githooks
```

启用后，正常提交即自动触发测试门禁：

```bash
git commit -m "your change"
# pre-commit: running pytest gate
```

**需要时显式绕过（例如裁剪中的 WIP 提交）：**

```bash
git commit --no-verify -m "wip"
```

**停用 / 还原：**

```bash
git config --unset core.hooksPath
```

### 说明

- 钩子与 CI 使用**同一条** `python -m pytest` 命令，避免本地与线上口径漂移。
- 该配置是**仓库级**的（`core.hooksPath` 写入本地 `.git/config`），不影响你机器上的其他仓库，也不修改全局配置。
- 凭据、`results/` 产物与临时沙盒始终被 `.gitignore` 排除，钩子不会把它们纳入提交。

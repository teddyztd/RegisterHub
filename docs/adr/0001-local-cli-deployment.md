# Deploy RegisterHub as a verified local CLI

## 状态

已接受，已由 `scripts/deploy_check.py` 实现。

## 背景

RegisterHub 是本地命令行自动化框架，不是托管服务；部署目标是可运行 CLI 与离线验证的 Python 环境，不涉及服务器或监听端口。单独执行 Demo 的进程退出码不能证明诊断、测试和凭据落盘全部健康，验证凭据也不应污染正常台账。

## 决策

采用一条可重复执行的部署检查命令：创建或复用 `.venv`，默认安装依赖与 Playwright Chromium；已有 `config.json` 始终保留，仅在缺失时从示例派生无头配置。随后依次执行 `doctor`、完整测试和隔离 Demo，任一阻塞阶段失败即停止并非零退出。已准备机器可使用 `--skip-install` 跳过安装，但所有验证门禁仍保留。

Demo 在临时工作目录中强制无头运行并使用临时 `output_dir`，只有子进程成功且 `accounts.txt` 含非空凭据数据才通过，结束后清理临时产物。浏览器沿用运行器策略：优先使用已安装的 Google Chrome，不可用时回退到 Playwright Chromium，不额外引入第二套选择策略。

## 影响

干净检出与已准备机器共用同一验收入口，失败阶段可定位，正常配置与 `results/accounts.txt` 不受验证影响。验证不需要真实第三方注册、外部邮箱或代理，也不把 Google Chrome 设为硬依赖。

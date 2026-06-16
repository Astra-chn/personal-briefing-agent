# Personal Briefing Agent

个人 AI 简报助手：通过 GitHub Actions 云端定时采集 GitHub 热门项目、AI 新闻和国际形势新闻，使用 DeepSeek API 生成中文简报，输出 Markdown/HTML 并通过邮件推送。

## 功能

- 每日/每周自动生成个人简报。
- GitHub 热门项目采集，关注 AI、LLM、Agent、RAG、Python、Java、自动化、MCP 等方向。
- RSS 新闻采集，支持 AI 行业动态和国际形势/科技政策。
- 内容清洗、去重、评分和筛选。
- DeepSeek API 中文总结；API 不可用时自动生成基础版简报。
- Markdown/HTML 归档到 `output/daily` 和 `output/weekly`。
- SMTP 邮件推送，失败时不影响文件保存。
- SQLite 辅助缓存，不作为唯一历史存储。
- Streamlit 本地历史简报查看。

## 本地运行

```powershell
cd D:\Portfolio\personal-briefing-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，至少配置：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
GITHUB_TOKEN=可选但推荐
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=邮箱授权码
BRIEFING_EMAIL_TO=receiver@email.com
```

生成每日简报：

```powershell
python main.py --mode daily
```

生成每周简报：

```powershell
python main.py --mode weekly
```

离线/不调用外部服务的演示运行：

```powershell
python main.py --mode daily --dry-run
```

## GitHub Actions

将仓库推到 GitHub 后，在仓库 Settings -> Secrets and variables -> Actions 中配置：

- `DEEPSEEK_API_KEY`
- `GITHUB_TOKEN`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `BRIEFING_EMAIL_TO`

可选配置：

- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`

工作流支持：

- 手动触发：Actions -> Personal Briefing -> Run workflow，选择 `daily` 或 `weekly`。
- 定时触发：北京时间每天 08:37 生成每日简报；北京时间每周日 20:37 生成每周简报。
- 自动提交：运行结束后提交 `output` 和 `data` 目录变化。

## Streamlit 查看

```powershell
streamlit run app.py
```

该页面只用于本地辅助查看历史简报，不影响 GitHub Actions 自动运行。

## 常见问题

### DeepSeek API 失败

程序会记录日志，并使用基础模板生成简报。请检查 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`。

### GitHub 或 RSS 访问失败

单个信息源失败不会中断任务。GitHub 采集建议配置 `GITHUB_TOKEN`，可减少限流。

### 邮件发送失败

简报仍会保存到 `output`。请检查 SMTP 地址、端口、账号、授权码和收件人。

### Actions 没有自动提交

确认仓库 workflow 权限允许写入：Settings -> Actions -> General -> Workflow permissions -> Read and write permissions。

## 测试

```powershell
pytest
```

测试默认不真实调用 DeepSeek、GitHub 或 SMTP。

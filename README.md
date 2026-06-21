# Personal Briefing Agent

个人 AI 简报助手：通过 GitHub Actions 云端定时采集 GitHub 项目、AI 新闻、国际新闻和中国国家政策信息，使用 DeepSeek API 生成中文简报，输出 Markdown/HTML 并通过邮件推送。

## 功能

- 每日/每周自动生成个人简报。
- GitHub 项目采集，关注 AI、LLM、Agent、RAG、Python、Java、自动化、MCP 等方向。
- RSS + GDELT 国际新闻采集，覆盖国际形势、科技政策、半导体、AI 监管、全球经济等方向。
- 中国国家政策采集，覆盖中国政府网、国家发改委、工信部、科技部、网信办等官网列表页。
- 内容清洗、去重、评分、历史重复降权和分类均衡筛选。
- DeepSeek API 中文总结；API 不可用时自动生成基础版简报。
- Markdown/HTML 归档到 `output/daily` 和 `output/weekly`。
- SMTP 邮件推送，失败时不影响文件保存。
- SQLite 辅助缓存，用于历史记录和重复惩罚。
- Streamlit 本地历史简报查看。

## 栏目均衡

为了避免 GitHub 高星项目连续多天霸榜，系统默认会：

- 对最近出现过的 URL 做历史降权。
- 每日简报限制 GitHub、AI 新闻、国际新闻、中国政策各自最多 4 条。
- GitHub 采集优先关注近期新建/更新项目，只少量保留高星项目。
- 国际新闻不足时通过 GDELT 免费新闻检索补充。
- 中国政策作为每日简报独立板块，不再用 GitHub 或 AI 新闻硬凑政策结论。

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

### 为什么之前每天重复度很高？

旧版 GitHub 采集按 stars 排序，持续更新的高星仓库会每天被重新选中。新版加入了历史重复降权、分类上限和新项目优先策略。

### 国际新闻为什么少？

旧版主要依赖少量 RSS 源，且关键词匹配偏窄。新版增加了 The Guardian RSS、GDELT 查询和 fallback 机制。

### 中国政策内容从哪里来？

新版会从中国政府网、国家发改委、工信部、科技部、网信办等官网列表页抓取政策条目。单个官网失败只记录日志，不影响整份简报。

### DeepSeek API 失败

程序会记录日志，并使用基础模板生成简报。请检查 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`。

### GitHub 或新闻源访问失败

单个信息源失败不会中断任务。GitHub 采集建议配置 `GITHUB_TOKEN`，可减少限流。

### 邮件发送失败

简报仍会保存到 `output`。请检查 SMTP 地址、端口、账号、授权码和收件人。

### Actions 没有自动提交

确认仓库 workflow 权限允许写入：Settings -> Actions -> General -> Workflow permissions -> Read and write permissions。

## 测试

```powershell
pytest --basetemp C:\Users\lenovo\AppData\Local\Temp\briefing-pytest-temp -o cache_dir=C:\Users\lenovo\AppData\Local\Temp\briefing-pytest-cache
```

测试默认不真实调用 DeepSeek、GitHub 或 SMTP。

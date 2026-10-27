"""Reviewable public publisher/project candidates; observed health is separate."""

PUBLISHERS = """
晚晴幽草轩|https://www.jeffjade.com/atom.xml|zh|dev
张鑫旭|https://www.zhangxinxu.com/wordpress/feed/|zh|dev
张乃欣|https://nexmoe.com/atom.xml|zh|dev
技术小黑屋|https://droidyue.com/atom.xml|zh|dev
掘金翻译计划|https://gold.xitu.io/rss|zh|dev
DIYgod|https://diygod.me/atom.xml|zh|dev
Anthony Fu|https://antfu.me/feed.xml|en|dev
大前端|https://www.daqianduan.com/feed|zh|dev
程序员的喵|https://catcoding.me/index.xml|zh|dev
HelloGitHub|https://hellogithub.com/rss|zh|dev
小胡同学|https://www.xiaohuz.com/atom.xml|zh|dev
宝玉的分享|https://baoyu.io/feed.xml|zh|ai
李继刚|https://lijigang.com/index.xml|zh|ai
数字尾巴|https://www.dgtle.com/rss/dgtle.xml|zh|tech
极客公园|https://www.geekpark.net/rss|zh|tech
阮一峰每周科技爱好者周刊|https://github.com/ruanyf/weekly/releases.atom|zh|tech
V2EX 技术节点|https://www.v2ex.com/feed/tech.xml|zh|dev
V2EX 创意节点|https://www.v2ex.com/feed/create.xml|zh|design
经济学人中国|https://www.economist.com/china/rss.xml|en|business
IMF Blog|https://www.imf.org/en/Blogs/rss|en|business
Federal Reserve Press Releases|https://www.federalreserve.gov/feeds/press_all.xml|en|business
Federal Reserve Research|https://www.federalreserve.gov/feeds/feds.xml|en|business
ECB Press Releases|https://www.ecb.europa.eu/rss/press.html|en|business
ECB Blog|https://www.ecb.europa.eu/rss/blog.html|en|business
Bank of England News|https://www.bankofengland.co.uk/rss/news|en|business
BIS Press Releases|https://www.bis.org/doclist/all_pressrels.rss|en|business
Our World in Data|https://ourworldindata.org/atom.xml|en|science
Science News|https://www.sciencenews.org/feed|en|science
Scientific American|https://www.scientificamerican.com/platform/syndication/rss/|en|science
Astronomy Magazine|https://www.astronomy.com/feed/|en|science
NOAA Research|https://research.noaa.gov/feed/|en|science
The Conversation Science|https://theconversation.com/global/topics/science-3/articles.atom|en|science
Frontiers Neuroscience|https://www.frontiersin.org/journals/neuroscience/rss|en|science
PLOS Biology|https://journals.plos.org/plosbiology/feed/atom|en|science
PLOS Computational Biology|https://journals.plos.org/ploscompbiol/feed/atom|en|science
LWN.net|https://lwn.net/headlines/rss|en|dev
Linux Kernel News|https://www.kernel.org/feeds/kdist.xml|en|dev
Debian News|https://www.debian.org/News/news|en|dev
Ubuntu Blog|https://ubuntu.com/blog/feed|en|dev
Fedora Magazine|https://fedoramagazine.org/feed/|en|dev
Arch Linux News|https://archlinux.org/feeds/news/|en|dev
FreeBSD News|https://www.freebsd.org/news/feed.xml|en|dev
DuckDB Blog|https://duckdb.org/feed.xml|en|dev
Grafana Blog|https://grafana.com/blog/index.xml|en|dev
Prometheus Blog|https://prometheus.io/blog/feed.xml|en|dev
OpenTelemetry Blog|https://opentelemetry.io/blog/index.xml|en|dev
HashiCorp Blog|https://www.hashicorp.com/blog/feed.xml|en|dev
Tailscale Blog|https://tailscale.com/blog/index.xml|en|dev
Fly.io Blog|https://fly.io/blog/feed.xml|en|dev
Vercel Blog|https://vercel.com/atom|en|dev
Svelte Blog|https://svelte.dev/blog/rss.xml|en|dev
Astro Blog|https://astro.build/rss.xml|en|dev
Pragmatic Engineer|https://newsletter.pragmaticengineer.com/feed|en|dev
Julia Language Blog|https://julialang.org/feed.xml|en|dev
LLVM Blog|https://blog.llvm.org/index.xml|en|dev
R-bloggers|https://www.r-bloggers.com/feed/|en|dev
Data Elixir|https://dataelixir.com/feed|en|ai
Allen AI Blog|https://allenai.org/blog/rss.xml|en|ai
Microsoft Research|https://www.microsoft.com/en-us/research/feed/|en|ai
Apple Machine Learning Research|https://machinelearning.apple.com/rss.xml|en|ai
AWS Machine Learning|https://aws.amazon.com/blogs/machine-learning/feed/|en|ai
GitHub Security Lab|https://github.blog/security/vulnerability-research/feed/|en|security
SecurityWeek|https://www.securityweek.com/feed/|en|security
Dark Reading|https://www.darkreading.com/rss.xml|en|security
EFF Deeplinks|https://www.eff.org/rss/updates.xml|en|security
Mozilla Security|https://blog.mozilla.org/security/feed/|en|security
Troy Hunt|https://www.troyhunt.com/rss/|en|security
Socket Security|https://socket.dev/blog/rss.xml|en|security
404 Media Podcast|https://feeds.megaphone.fm/404media|en|life
Syntax Podcast|https://feed.syntax.fm/rss|en|dev
Design Details Podcast|https://feeds.simplecast.com/4MvgQ73R|en|design
99% Invisible|https://feeds.simplecast.com/BqbsxVfO|en|design
NPR Planet Money|https://feeds.npr.org/510289/podcast.xml|en|business
NPR Science Friday|https://feeds.simplecast.com/y1LF_sn2|en|science
Web Designer Depot|https://www.webdesignerdepot.com/feed/|en|design
Creative Bloq|https://www.creativebloq.com/feed|en|design
Colossal|https://www.thisiscolossal.com/feed/|en|design
Open Culture|https://www.openculture.com/feed|en|life
Public Domain Review|https://publicdomainreview.org/rss.xml|en|life
Literary Hub|https://lithub.com/feed/|en|life
Smithsonian Magazine|https://www.smithsonianmag.com/rss/latest_articles/|en|life
The Guardian Books|https://www.theguardian.com/books/rss|en|life
The Guardian Environment|https://www.theguardian.com/environment/rss|en|science
The Conversation Business|https://theconversation.com/global/business/articles.atom|en|business
UN News Climate|https://news.un.org/feed/subscribe/en/news/topic/climate-change/feed/rss.xml|en|news
联合国新闻气候|https://news.un.org/feed/subscribe/zh/news/topic/climate-change/feed/rss.xml|zh|news
德国之声中文科技|https://rss.dw.com/rdf/rss-chi-sci|zh|science
BBC 中文国际|https://feeds.bbci.co.uk/zhongwen/simp/world/rss.xml|zh|news
"""

REPOSITORIES = """
ollama/ollama|Ollama 本地模型|ai
ggml-org/llama.cpp|llama.cpp 本地推理|ai
vllm-project/vllm|vLLM 推理服务|ai
sgl-project/sglang|SGLang 推理|ai
huggingface/transformers|Transformers 模型库|ai
huggingface/peft|PEFT 参数高效微调|ai
huggingface/diffusers|Diffusers 图像生成|ai
langchain-ai/langchain|LangChain 智能体|ai
langchain-ai/langgraph|LangGraph 智能体编排|ai
run-llama/llama_index|LlamaIndex RAG|ai
open-webui/open-webui|Open WebUI 本地助手|ai
langgenius/dify|Dify 应用开发|ai
infiniflow/ragflow|RAGFlow 检索增强|ai
unslothai/unsloth|Unsloth 微调|ai
ml-explore/mlx|MLX Apple 芯片机器学习|ai
ggerganov/whisper.cpp|Whisper.cpp 语音识别|ai
comfyanonymous/ComfyUI|ComfyUI 图像工作流|ai
astral-sh/uv|uv Python 包管理|dev
astral-sh/ruff|Ruff Python 检查|dev
fastapi/fastapi|FastAPI Web 框架|dev
pydantic/pydantic|Pydantic 数据校验|dev
django/django|Django Web 框架|dev
nodejs/node|Node.js 运行时|dev
vitejs/vite|Vite 构建工具|dev
vuejs/core|Vue 前端框架|dev
facebook/react|React 前端框架|dev
sveltejs/svelte|Svelte 前端框架|dev
spring-projects/spring-boot|Spring Boot Java|dev
kubernetes/kubernetes|Kubernetes 容器编排|dev
prometheus/prometheus|Prometheus 监控|dev
grafana/grafana|Grafana 可视化|dev
duckdb/duckdb|DuckDB 数据分析|dev
redis/redis|Redis 数据库|dev
milvus-io/milvus|Milvus 向量数据库|dev
qdrant/qdrant|Qdrant 向量检索|dev
aquasecurity/trivy|Trivy 漏洞扫描|security
gitleaks/gitleaks|Gitleaks 密钥检测|security
semgrep/semgrep|Semgrep 静态安全分析|security
owasp-amass/amass|OWASP Amass|security
projectdiscovery/nuclei|Nuclei 安全检测|security
"""


def records(categories):
    result = []
    for line in PUBLISHERS.strip().splitlines():
        name, url, language, category = line.split("|")
        podcast = (
            "Podcast" in name
            or "NPR Planet" in name
            or "NPR Science" in name
            or "99%" in name
        )
        result.append(
            dict(
                name=name,
                url=url,
                language=language,
                category=category,
                platform="rss",
                kind="podcast" if podcast else "publisher",
                tags=[
                    categories[category],
                    *(["播客", "podcast", "音频节目简介"] if podcast else []),
                ],
                description=(
                    "公开播客节目简介与原文链接；不下载音频、不做转录。"
                    if podcast
                    else f"{categories[category]}领域的公开 RSS/Atom 候选；可用性见实时检测。"
                ),
            )
        )
    for line in REPOSITORIES.strip().splitlines():
        repo, title, category = line.split("|")
        result.append(
            dict(
                name=f"GitHub Releases · {title}",
                url=f"https://api.github.com/repos/{repo}/releases?per_page=10",
                language="en",
                category=category,
                platform="api",
                kind="github",
                tags=[categories[category], repo, title, "开源", "项目发布", "release"],
                description=f"{repo} 官方发布说明；使用公开 GitHub API，不含未关联 Release 的普通标签；受匿名请求配额限制。",
                attribution=f"https://github.com/{repo}/releases",
            )
        )
    for name, url, category in [
        ("Daring Fireball JSON Feed", "https://daringfireball.net/feeds/json", "tech"),
        ("Flying Meat JSON Feed", "https://flyingmeat.com/blog/feed.json", "dev"),
        ("Manton Reece JSON Feed", "https://www.manton.org/feed.json", "tech"),
    ]:
        result.append(
            dict(
                name=name,
                url=url,
                category=category,
                language="en",
                platform="api",
                kind="jsonfeed",
                tags=[categories[category], "JSON Feed"],
                description="作者公开 JSON Feed；按标准提取摘要、正文和原文地址。",
                attribution=url,
            )
        )
    return result

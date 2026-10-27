"""Maintain the bundled, reviewable source directory; network checks are separate.

Records are candidates until checked by check_sources.py. No source is auto-subscribed.
"""

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from source_extensions import records as extension_records

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {
    "ai": "人工智能",
    "tech": "科技数码",
    "dev": "编程与开源",
    "security": "网络安全",
    "science": "科学与学术",
    "news": "新闻资讯",
    "business": "商业财经",
    "design": "设计与产品",
    "life": "生活与文化",
}

# name | URL | language | category. Prefer publisher feeds over public proxies.
FEEDS = """
少数派|https://sspai.com/feed|zh|tech
IT之家|https://www.ithome.com/rss/|zh|tech
Solidot|https://www.solidot.org/index.rss|zh|tech
月光博客|https://www.williamlong.info/rss.xml|zh|tech
小众软件|https://www.appinn.com/feed/|zh|tech
异次元软件世界|https://www.iplaysoft.com/feed|zh|tech
爱范儿|https://www.ifanr.com/feed|zh|tech
雷峰网|https://www.leiphone.com/feed|zh|ai
机器之心|https://www.jiqizhixin.com/rss|zh|ai
量子位|https://www.qbitai.com/feed|zh|ai
InfoQ 中文|https://www.infoq.cn/feed|zh|dev
阮一峰的网络日志|https://www.ruanyifeng.com/blog/atom.xml|zh|dev
酷壳|https://coolshell.cn/feed|zh|dev
廖雪峰|https://www.liaoxuefeng.com/feed|zh|dev
美团技术团队|https://tech.meituan.com/feed/|zh|dev
阿里云开发者|https://developer.aliyun.com/feed|zh|dev
腾讯技术工程|https://cloud.tencent.com/developer/column/100002/rss|zh|dev
V2EX 最新主题|https://www.v2ex.com/index.xml|zh|dev
博客园首页|https://www.cnblogs.com/rss|zh|dev
开源中国资讯|https://www.oschina.net/news/rss|zh|dev
Linux 中国|https://linux.cn/rss.xml|zh|dev
鸟窝|https://colobu.com/atom.xml|zh|dev
面向信仰编程|https://draveness.me/feed.xml|zh|dev
煎鱼的清汤锅|https://eddycjy.com/index.xml|zh|dev
冰霜之地|https://halfrost.com/rss/|zh|dev
云风的 BLOG|https://blog.codingnow.com/atom.xml|zh|dev
王垠|https://www.yinwang.org/atom.xml|zh|dev
科学空间|https://spaces.ac.cn/feed|zh|ai
FreeBuf|https://www.freebuf.com/feed|zh|security
安全客|https://api.anquanke.com/data/v1/rss|zh|security
Seebug Paper|https://paper.seebug.org/rss/|zh|security
知道创宇 404|https://blog.knownsec.com/feed/|zh|security
嘶吼|https://www.4hou.com/feed|zh|security
奇客安全|https://www.solidot.org/index.rss?tid=15|zh|security
36氪|https://36kr.com/feed|zh|business
虎嗅|https://www.huxiu.com/rss/0.xml|zh|business
钛媒体|https://www.tmtpost.com/rss.xml|zh|business
FT中文网|https://www.ftchinese.com/rss/feed|zh|business
端传媒|https://theinitium.com/feed/|zh|news
联合早报|https://www.zaobao.com.sg/rss/realtime/china|zh|news
BBC 中文|https://feeds.bbci.co.uk/zhongwen/simp/rss.xml|zh|news
纽约时报中文网|https://cn.nytimes.com/rss/|zh|news
德国之声中文|https://rss.dw.com/rdf/rss-chi-all|zh|news
联合国新闻中文|https://news.un.org/feed/subscribe/zh/news/all/rss.xml|zh|news
维基新闻中文|https://zh.wikinews.org/w/index.php?title=Special:NewsFeed&feed=atom&categories=Published&notcategories=No_publish|zh|news
机核|https://www.gcores.com/rss|zh|life
触乐|https://www.chuapp.com/feed|zh|life
游研社|https://www.yystv.cn/rss/feed|zh|life
 indienova|https://indienova.com/feed|zh|life
博海拾贝|https://www.bohaishibei.com/feed/|zh|life
ONE 一个|https://wufazhuce.com/feed|zh|life
人文与社会|https://wen.org.cn/rss.xml|zh|life
优设|https://www.uisdc.com/feed|zh|design
人人都是产品经理|https://www.woshipm.com/feed|zh|design
Hacker News 热门|https://hnrss.org/frontpage|en|tech
Hacker News 最新|https://hnrss.org/newest|en|tech
TechCrunch|https://techcrunch.com/feed/|en|tech
The Verge|https://www.theverge.com/rss/index.xml|en|tech
Ars Technica|https://feeds.arstechnica.com/arstechnica/index|en|tech
Wired|https://www.wired.com/feed/rss|en|tech
Engadget|https://www.engadget.com/rss.xml|en|tech
MIT Technology Review|https://www.technologyreview.com/feed/|en|tech
IEEE Spectrum|https://spectrum.ieee.org/feeds/feed.rss|en|tech
404 Media|https://www.404media.co/rss/|en|tech
OpenAI News|https://openai.com/news/rss.xml|en|ai
Google AI Blog|https://blog.google/technology/ai/rss/|en|ai
Google Research|https://research.google/blog/rss/|en|ai
Google DeepMind|https://deepmind.google/blog/rss.xml|en|ai
Hugging Face Blog|https://huggingface.co/blog/feed.xml|en|ai
BAIR Berkeley AI|https://bair.berkeley.edu/blog/feed.xml|en|ai
The Gradient|https://thegradient.pub/rss/|en|ai
Simon Willison|https://simonwillison.net/atom/everything/|en|ai
Lilian Weng|https://lilianweng.github.io/index.xml|en|ai
Sebastian Raschka|https://magazine.sebastianraschka.com/feed|en|ai
Chip Huyen|https://huyenchip.com/feed.xml|en|ai
Interconnects|https://www.interconnects.ai/feed|en|ai
Latent Space|https://www.latent.space/feed|en|ai
NVIDIA Technical Blog|https://developer.nvidia.com/blog/feed/|en|ai
GitHub Blog|https://github.blog/feed/|en|dev
GitLab Blog|https://about.gitlab.com/atom.xml|en|dev
Stack Overflow Blog|https://stackoverflow.blog/feed/|en|dev
Martin Fowler|https://martinfowler.com/feed.atom|en|dev
Julia Evans|https://jvns.ca/atom.xml|en|dev
Brendan Gregg|https://www.brendangregg.com/blog/rss.xml|en|dev
Cloudflare Blog|https://blog.cloudflare.com/rss/|en|dev
Netflix Tech Blog|https://netflixtechblog.com/feed|en|dev
Uber Engineering|https://www.uber.com/blog/engineering/rss/|en|dev
AWS Architecture|https://aws.amazon.com/blogs/architecture/feed/|en|dev
AWS News|https://aws.amazon.com/blogs/aws/feed/|en|dev
Google Cloud Blog|https://cloudblog.withgoogle.com/rss/|en|dev
Microsoft Developer Blogs|https://devblogs.microsoft.com/feed/|en|dev
Meta Engineering|https://engineering.fb.com/feed/|en|dev
Stripe Engineering|https://stripe.com/blog/engineering/feed.rss|en|dev
Discord Engineering|https://discord.com/blog/rss.xml|en|dev
Kubernetes Blog|https://kubernetes.io/feed.xml|en|dev
Docker Blog|https://www.docker.com/blog/feed/|en|dev
Rust Blog|https://blog.rust-lang.org/feed.xml|en|dev
Go Blog|https://go.dev/blog/feed.atom|en|dev
Python Insider|https://blog.python.org/feeds/posts/default|en|dev
Real Python|https://realpython.com/atom.xml|en|dev
PyPI Updates|https://pypi.org/rss/updates.xml|en|dev
Django Weblog|https://www.djangoproject.com/rss/weblog/|en|dev
Node.js Blog|https://nodejs.org/en/feed/blog.xml|en|dev
React Blog|https://react.dev/rss.xml|en|dev
Vue Blog|https://blog.vuejs.org/feed.rss|en|dev
Vite Blog|https://vite.dev/blog.rss|en|dev
TypeScript Blog|https://devblogs.microsoft.com/typescript/feed/|en|dev
.NET Blog|https://devblogs.microsoft.com/dotnet/feed/|en|dev
Spring Blog|https://spring.io/blog.atom|en|dev
JetBrains Blog|https://blog.jetbrains.com/feed/|en|dev
PostgreSQL News|https://www.postgresql.org/news.rss|en|dev
Redis Blog|https://redis.io/blog/feed/|en|dev
Elastic Blog|https://www.elastic.co/blog/feed|en|dev
MongoDB Blog|https://www.mongodb.com/blog/rss|en|dev
Mozilla Hacks|https://hacks.mozilla.org/feed/|en|dev
WebKit Blog|https://webkit.org/feed/|en|dev
Chromium Blog|https://blog.chromium.org/feeds/posts/default|en|dev
web.dev|https://web.dev/feed.xml|en|dev
MDN Blog|https://developer.mozilla.org/en-US/blog/rss.xml|en|dev
Krebs on Security|https://krebsonsecurity.com/feed/|en|security
Schneier on Security|https://www.schneier.com/feed/atom/|en|security
The Hacker News|https://feeds.feedburner.com/TheHackersNews|en|security
BleepingComputer|https://www.bleepingcomputer.com/feed/|en|security
SANS Internet Storm Center|https://isc.sans.edu/rssfeed.xml|en|security
Google Project Zero|https://googleprojectzero.blogspot.com/feeds/posts/default|en|security
Google Security Blog|https://security.googleblog.com/feeds/posts/default|en|security
Microsoft Security Blog|https://www.microsoft.com/en-us/security/blog/feed/|en|security
Cisco Talos|https://blog.talosintelligence.com/rss/|en|security
Trail of Bits|https://blog.trailofbits.com/feed/|en|security
PortSwigger Research|https://portswigger.net/research/rss|en|security
CISA Alerts|https://www.cisa.gov/cybersecurity-advisories/all.xml|en|security
US-CERT / CISA News|https://www.cisa.gov/news.xml|en|security
Nature|https://www.nature.com/nature.rss|en|science
Science|https://www.science.org/rss/news_current.xml|en|science
ScienceDaily|https://www.sciencedaily.com/rss/all.xml|en|science
Phys.org|https://phys.org/rss-feed/|en|science
Quanta Magazine|https://www.quantamagazine.org/feed/|en|science
NASA News|https://www.nasa.gov/news-release/feed/|en|science
ESA News|https://www.esa.int/rssfeed/Our_Activities/Space_Science|en|science
PLOS ONE|https://journals.plos.org/plosone/feed/atom|en|science
eLife|https://elifesciences.org/rss/recent.xml|en|science
MIT News|https://news.mit.edu/rss/feed|en|science
BBC World|https://feeds.bbci.co.uk/news/world/rss.xml|en|news
BBC Technology|https://feeds.bbci.co.uk/news/technology/rss.xml|en|tech
The Guardian World|https://www.theguardian.com/world/rss|en|news
The Guardian Technology|https://www.theguardian.com/technology/rss|en|tech
NPR News|https://feeds.npr.org/1001/rss.xml|en|news
Al Jazeera|https://www.aljazeera.com/xml/rss/all.xml|en|news
UN News|https://news.un.org/feed/subscribe/en/news/all/rss.xml|en|news
Deutsche Welle|https://rss.dw.com/rdf/rss-en-all|en|news
AP Top News|https://apnews.com/index.rss|en|news
CNBC Top News|https://www.cnbc.com/id/100003114/device/rss/rss.html|en|business
CNBC Finance|https://www.cnbc.com/id/10000664/device/rss/rss.html|en|business
Financial Times|https://www.ft.com/rss/home|en|business
The Economist Finance|https://www.economist.com/finance-and-economics/rss.xml|en|business
Y Combinator Blog|https://www.ycombinator.com/blog/rss/|en|business
Paul Graham Essays|https://www.aaronsw.com/2002/feeds/pgessays.rss|en|business
Product Hunt|https://www.producthunt.com/feed|en|design
Smashing Magazine|https://www.smashingmagazine.com/feed/|en|design
A List Apart|https://alistapart.com/main/feed/|en|design
Nielsen Norman Group|https://www.nngroup.com/feed/rss/|en|design
UX Collective|https://uxdesign.cc/feed|en|design
Figma Blog|https://www.figma.com/blog/feed/atom.xml|en|design
CSS-Tricks|https://css-tricks.com/feed/|en|design
Aeon|https://aeon.co/feed.rss|en|life
The Marginalian|https://www.themarginalian.org/feed/|en|life
Longreads|https://longreads.com/feed/|en|life
Atlas Obscura|https://www.atlasobscura.com/feeds/latest|en|life
Rock Paper Shotgun|https://www.rockpapershotgun.com/feed|en|life
PC Gamer|https://www.pcgamer.com/rss/|en|life
Eurogamer|https://www.eurogamer.net/feed|en|life
Polygon|https://www.polygon.com/rss/index.xml|en|life
"""

ARXIV = {
    "cs.AI": "人工智能",
    "cs.CL": "计算语言与自然语言处理",
    "cs.LG": "机器学习",
    "cs.CV": "计算机视觉",
    "cs.RO": "机器人",
    "cs.IR": "信息检索",
    "cs.CR": "密码与安全",
    "cs.SE": "软件工程",
    "cs.PL": "编程语言",
    "cs.DC": "分布式计算",
    "cs.DB": "数据库",
    "cs.DS": "数据结构与算法",
    "cs.HC": "人机交互",
    "cs.NE": "神经与进化计算",
    "cs.SI": "社会与信息网络",
    "cs.SY": "系统与控制",
    "cs.CY": "计算机与社会",
    "cs.CE": "计算工程",
    "cs.AR": "计算机体系结构",
    "cs.NI": "网络与互联网架构",
    "stat.ML": "统计机器学习",
    "stat.AP": "应用统计",
    "stat.CO": "统计计算",
    "stat.ME": "统计方法",
    "stat.TH": "统计理论",
    "math.OC": "优化与控制",
    "math.PR": "概率论",
    "math.ST": "数理统计",
    "math.NA": "数值分析",
    "math.CO": "组合数学",
    "math.IT": "信息论",
    "quant-ph": "量子物理",
    "astro-ph.EP": "地球与行星天体物理",
    "astro-ph.GA": "星系天体物理",
    "physics.soc-ph": "社会物理",
    "physics.bio-ph": "生物物理",
    "cond-mat.mtrl-sci": "材料科学",
    "q-bio.NC": "神经与认知",
    "q-bio.GN": "基因组学",
    "q-fin.CP": "计算金融",
    "q-fin.EC": "经济学",
    "q-fin.PM": "投资组合管理",
    "q-fin.RM": "风险管理",
    "econ.EM": "计量经济",
    "econ.GN": "一般经济",
}


def main():
    records = []
    for line in FEEDS.strip().splitlines():
        name, url, language, category = [s.strip() for s in line.split("|")]
        records.append(
            dict(
                name=name,
                url=url,
                language=language,
                category=category,
                kind="publisher",
                description=f"{CATEGORIES[category]}领域的 RSS / Atom 候选来源；请查看检测状态。",
            )
        )
    for code, title in ARXIV.items():
        records.append(
            dict(
                name=f"arXiv · {title}",
                url=f"https://rss.arxiv.org/rss/{code}",
                language="en",
                category=(
                    "ai"
                    if code
                    in {"cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.RO", "cs.NE", "stat.ML"}
                    else "science"
                ),
                kind="academic",
                description=f"arXiv {code} 学科论文摘要；正文通常为 PDF，不作为网页全文解析。",
            )
        )
    seen = set()
    records.extend(extension_records(CATEGORIES))
    for row in records:
        assert row["url"] not in seen, row["url"]
        seen.add(row["url"])
        row.update(
            id=hashlib.sha256(row["url"].encode()).hexdigest()[:16],
            platform=row.get("platform", "rss"),
            homepage=f'https://{urlparse(row["url"]).hostname}',
            tags=row.get("tags", [CATEGORIES[row["category"]]]),
            attribution=row.get(
                "attribution",
                (
                    "https://info.arxiv.org/help/rss.html"
                    if row["kind"] == "academic"
                    else row["url"]
                ),
            ),
        )
    path = ROOT / "nexus-python/app/data/sources.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"version": 2, "categories": CATEGORIES, "sources": records},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(records)} unique feed channels from {len({urlparse(r['url']).hostname for r in records})} hosts."
    )


if __name__ == "__main__":
    main()

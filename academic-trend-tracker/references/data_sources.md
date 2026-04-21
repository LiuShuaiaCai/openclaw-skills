# 学术热点数据源参考

## 1. CrossRef API

### 基础信息
- **官网**: https://www.crossref.org
- **文档**: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- **限制**: 免费，无需 API Key，但有速率限制

### 常用端点

```
GET https://api.crossref.org/works
```

### 查询参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `query` | 搜索关键词 | `query=AI+medicine` |
| `from-pub-date` | 发布日期起始 | `from-pub-date=2026-01-01` |
| `until-pub-date` | 发布日期结束 | `until-pub-date=2026-04-19` |
| `subject` | 学科分类 | `subject=AI` |
| `rows` | 返回数量 | `rows=100` |
| `offset` | 分页偏移 | `offset=0` |
| `select` | 选择字段 | `select=DOI,title,author,subject,published` |

### 示例查询

```bash
# 搜索 AI+医学 论文
curl "https://api.crossref.org/works?query=AI+medicine&rows=50&sort=published&order=desc"

# 搜索近7天论文
curl "https://api.crossref.org/works?from-pub-date=2026-04-12&until-pub-date=2026-04-19&rows=100"

# 搜索特定学科
curl "https://api.crossref.org/works?subject=computer science&rows=50"
```

### 学科分类（Subject）

常见学科分类：
- `AI` - Artificial Intelligence
- `medicine` - 医学
- `biology` - 生物学
- `chemistry` - 化学
- `physics` - 物理学
- `psychology` - 心理学
- `environmental science` - 环境科学
- `materials science` - 材料科学

---

## 2. Semantic Scholar API

### 基础信息
- **官网**: https://www.semanticscholar.org
- **文档**: https://api.semanticscholar.org/
- **限制**: 免费 API Key 可用，部分高级功能需要付费

### 获取 API Key
访问 https://www.semanticscholar.org/product/api 申请

### 常用端点

```
GET https://api.semanticscholar.org/graph/v1/paper/{paperId}
GET https://api.semanticscholar.org/graph/v1/paper/search
GET https://api.semanticscholar.org/graph/v1/author/search
```

### 查询参数

```bash
# 搜索论文
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=AI+medicine&limit=10&fields=title,authors,year,citationCount,externalIds"

# 获取论文详情
curl "https://api.semanticscholar.org/graph/v1/paper/ArXiv:2103.14030?fields=title,abstract,authors,year,citationCount,influentialCitationCount"
```

---

## 3. arXiv API

### 基础信息
- **官网**: https://arxiv.org
- **文档**: https://arxiv.org/help/api/basics
- **限制**: 无需 API Key，有速率限制

### 查询参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `search_query` | 搜索查询 | `ti:AI+AND+abs:medicine` |
| `id_list` | 论文ID列表 | `2301.00001,2301.00002` |
| `start` | 起始索引 | `start=0` |
| `max_results` | 最大结果 | `max_results=50` |
| `sortBy` | 排序字段 | `sortBy=submittedDate` |
| `sortOrder` | 排序顺序 | `sortOrder=descending` |

### 搜索语法

```
ti: - 标题
au: - 作者
abs: - 摘要
cat: - 分类 (cs.AI, cs.LG, etc.)
```

### 示例

```bash
# 搜索 AI 论文
curl "https://export.arxiv.org/api/query?search_query=cat:cs.AI&max_results=50&sortBy=submittedDate&sortOrder=descending"

# 搜索跨学科论文
curl "https://export.arxiv.org/api/query?search_query=abs:AI+AND+abs:biology&max_results=50"
```

---

## 4. PubMed API

### 基础信息
- **官网**: https://pubmed.ncbi.nlm.nih.gov
- **文档**: https://eutils.ncbi.nlm.nih.gov/home/tutorial/
- **限制**: 免费，需要 API Key（可选但推荐）

### 端点

```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
```

### 示例

```bash
# 搜索论文
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=AI+medicine&retmax=50&sort=date"

# 获取详情
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=12345678"
```

---

## 5. 学术热点追踪关键词

### AI+学术 热点关键词

| 领域 | 关键词 |
|------|--------|
| AI基础 | `large language model`, `transformer`, `neural network`, `deep learning` |
| AI+医学 | `AI+medicine`, `AI+diagnosis`, `medical AI`, `clinical AI` |
| AI+生物 | `AlphaFold`, `protein structure`, `computational biology` |
| AI+材料 | `materials discovery`, `computational chemistry`, `molecular simulation` |

### 热点事件关键词

| 事件类型 | 关键词 |
|----------|--------|
| 诺贝尔奖 | `Nobel Prize`, 奖项名称 |
| 撤稿事件 | `retraction`, `scientific misconduct` |
| 重大突破 | `breakthrough`, `discovery`, `revolution` |
| AI进展 | `GPT`, `Claude`, `Gemini`, `Sora` |

---

## 6. 数据采集脚本模板

### Python 脚本示例

```python
import requests
from datetime import datetime, timedelta

def search_crossref(query, days=7, rows=100):
    """从 CrossRef 获取近期论文"""
    base_url = "https://api.crossref.org/works"
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")
    
    params = {
        "query": query,
        "from-pub-date": from_date,
        "until-pub-date": to_date,
        "rows": rows,
        "sort": "published",
        "order": "desc"
    }
    
    response = requests.get(base_url, params=params)
    return response.json()

def search_arxiv(query, max_results=50):
    """从 arXiv 获取论文"""
    base_url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": query,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    
    response = requests.get(base_url, params=params)
    return response.text  # 返回 XML
```

---

## 7. 注意事项

1. **速率限制**: 各 API 都有速率限制，批量请求时添加延迟
2. **数据缓存**: 热点内容可以缓存24小时，避免重复请求
3. **错误处理**: API 可能返回错误，需要适当的错误处理
4. **数据验证**: 获取数据后验证 DOI、标题等关键信息
5. **API Key**: 优先获取免费 API Key 提高限制

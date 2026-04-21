# CrossRef REST API 参考文档

## 基本信息

- **Base URL**：`https://api.crossref.org`
- **认证**：在 URL 中添加 `mailto` 参数（格式：`mailto=your@email.com`）
- **返回格式**：JSON
- **限流**：50 requests/second，建议添加 mailto

## 主要端点

### 获取文章列表（Works）

```
GET /works
```

**查询参数**：

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `filter` | string | 过滤器，多个用逗号分隔 | `from-pub-date:2026-04-18` |
| `rows` | integer | 返回数量（最大100） | `100` |
| `offset` | integer | 偏移量（用于分页） | `0` |
| `select` | string | 指定返回字段（逗号分隔） | `DOI,title,author` |
| `sort` | string | 排序字段 | `published` |
| `order` | string | 排序方向 | `desc` 或 `asc` |
| `query` | string | 全文搜索关键词 | `machine learning` |
| `mailto` | string | 必填，用于 API 限流识别 | `your@email.com` |

### 过滤器（filter）常用选项

```
from-pub-date:{YYYY-MM-DD}       # 起始发布日期
until-pub-date:{YYYY-MM-DD}      # 截止发布日期
from-created-date:{YYYY-MM-DD}   # 起始创建日期
until-created-date:{YYYY-MM-DD}  # 截止创建日期
type:journal-article             # 文章类型
subject:CHEMISTRY                # 学科分类
publisher:ELSEVIER               # 出版商
```

### 文章类型（type）参考

- `journal-article` - 期刊文章
- `proceedings-article` - 会议论文
- `book-chapter` - 书籍章节
- `review-article` - 综述文章
- `book` - 书籍
- `dissertation` - 学位论文

### 学科分类（subject）参考

CrossRef 使用 BAS (British Academic Subjects) 分类：
- `CHEMISTRY` - 化学
- `PHYSICS` - 物理
- `BIOLOGY` - 生物
- `MATHEMATICS` - 数学
- `COMPUTER` - 计算机
- `ENGINEERING` - 工程
- `MEDICINE` - 医学
- `PSYCHOLOGY` - 心理学
- `ECONOMICS` - 经济
- `LINGUISTICS` - 语言学
- `LAW` - 法律
- `PHILOSOPHY` - 哲学
- `HISTORY` - 历史
- `ART` - 艺术

## 请求示例

### 获取当天发布的所有文章

```http
GET https://api.crossref.org/works?filter=from-pub-date:2026-04-18,until-pub-date:2026-04-18&rows=100&select=DOI,title,author,published,subject,container-title,publisher,type&mailto=your@email.com
```

### 获取计算机领域当天文章

```http
GET https://api.crossref.org/works?filter=from-pub-date:2026-04-18,until-pub-date:2026-04-18,subject:COMPUTER&rows=50&select=DOI,title,author,published,subject,container-title,publisher&mailto=your@email.com
```

## 响应字段说明

### 完整响应结构

```json
{
  "status": "ok",
  "message-type": "work-list",
  "message": {
    "total-results": 12345,
    "items": [
      {
        "DOI": "10.1234/example.doi",
        "title": ["Article Title"],
        "author": [
          {
            "given": "John",
            "family": "Doe",
            "affiliation": [
              {
                "name": "University of Example"
              }
            ]
          }
        ],
        "published": {
          "date-parts": [[2026, 4, 18]]
        },
        "subject": ["COMPUTER", "MATHEMATICS"],
        "container-title": ["Journal Name"],
        "publisher": "Publisher Name",
        "type": "journal-article"
      }
    ]
  }
}
```

### 字段说明

| 字段路径 | 说明 |
|---------|------|
| `message.items[].DOI` | 数字对象标识符 |
| `message.items[].title` | 文章标题（数组） |
| `message.items[].author` | 作者列表 |
| `message.items[].author[].given` | 作者名 |
| `message.items[].author[].family` | 作者姓 |
| `message.items[].author[].affiliation` | 所属机构 |
| `message.items[].published.date-parts` | 发布日期 [年, 月, 日] |
| `message.items[].subject` | 学科分类数组 |
| `message.items[].container-title` | 期刊/会议名称 |
| `message.items[].publisher` | 出版商 |
| `message.items[].type` | 文章类型 |

## 分页处理

CrossRef API 每次最多返回 100 条记录。如需获取更多数据，使用 offset 参数分页：

```python
all_items = []
offset = 0
while True:
    url = f"https://api.crossref.org/works?filter=from-pub-date:{date},until-pub-date:{date}&rows=100&offset={offset}&mailto=your@email.com"
    # 请求并解析...
    if len(items) < 100:
        break
    offset += 100
```

## 错误处理

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 403 | 权限不足或 IP 被封禁 |
| 429 | 请求过于频繁（限流） |
| 500 | 服务器内部错误 |

## 最佳实践

1. **必填 mailto**：添加到每个请求中
2. **控制请求频率**：即使有限流保护，也建议添加适当延迟
3. **处理空值**：部分字段（如 subject、affiliation）可能为空
4. **日期解析**：`date-parts` 是嵌套数组，需解析为标准日期格式
5. **批量处理**：使用 Python 脚本批量抓取，避免重复劳动

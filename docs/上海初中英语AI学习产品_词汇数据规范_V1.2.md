# 上海初中英语 AI 学习产品——词汇数据规范 V1.2

## 1. 文档定位

本规范定义产品中的 `Vocabulary`（词汇知识）数据模型，同时作为产品/业务数据定义、AI Agent 抽取规则、工程数据契约、数据质检与人工审核依据。

机器可执行的数据格式约束另见：
`上海初中英语AI学习产品_词汇JSONSchema_V1.2.json`

> JSON Schema 负责“格式是否正确”；本规范负责“字段是什么意思、从哪里来、怎么取值、何时为空、字段如何区分”。

## 2. Vocabulary 的职责边界

`Vocabulary` 描述“这个英语词本身是什么，以及资料中明确提供了哪些与它相关的知识”。

| 数据对象 | 回答的问题 |
|---|---|
| Vocabulary | 这个词是什么？ |
| UserVocabularyState | 这个孩子会不会？ |
| Question | 这个知识点怎么考？ |
| LearningRecord | 孩子学过什么？ |
| ErrorRecord | 孩子哪里容易错？ |
| LearningPlan | 下一步学什么？ |
| AIInteraction | AI 给孩子提供过什么教学服务？ |

Vocabulary 不保存学生掌握度、错误次数、学习计划、个性化口诀/解释/例句等用户状态或 AI 服务结果。

## 3. 数据来源原则

主要知识来源为《2027年上海市初中英语考纲词汇用法手册》PDF。

来源优先级：
1. PDF 明确出现的信息；
2. PDF 的结构化标记，如 `词形拓展`、`词组拓展`、`名师点拨`、`谚语`；
3. 仅 `word_forms` 允许在明确规则下由 AI 受控补全。

除 `word_forms` 外，AI 不得根据自身知识创造 PDF 未提供的 Vocabulary 知识；无法确认时留空。

## 4. 字段总览

| 字段 | 含义 | 来源 | AI补全 |
|---|---|---|---|
| id | 稳定内部编号 | 工程 | 否 |
| word | 标准英文词形/lemma | PDF | 否 |
| phonetic | PDF 音标 | PDF | 否 |
| meanings | 词性+中文释义 | PDF | 否 |
| word_forms | 当前词自身词形变化 | PDF/受控AI | 是 |
| related_words | 派生/词形拓展/相关词 | PDF | 否 |
| phrases | 常用词组、固定短语等 | PDF | 否 |
| collocations | 明确标记的典型搭配 | PDF | 否 |
| proverbs | 明确的谚语/格言/俗语 | PDF | 否 |
| examples | PDF 例句 | PDF | 否 |
| usage_notes | 用法/语法等说明 | PDF | 否 |
| teaching_notes | 名师点拨等教学内容 | PDF | 否 |
| tags | 来源/属性标签 | PDF | 否 |
| exam_level | PDF 星级标记 | PDF | 否 |
| textbook | 教材年级/学期/单元 | PDF | 否 |

## 5. 字段详细定义

### 5.1 id
稳定内部编号，格式 `V00001`、`V00002`……由工程生成，从 `V00001` 递增，不因内容修改而改变。

### 5.2 word
当前词条的标准英文词形/lemma。默认小写；不包含词性、音标、中文释义。

### 5.3 phonetic
PDF 中提供的音标。可做明显排版/OCR 清理；PDF 未提供则 `""`；不得 AI 猜测。

### 5.4 meanings
PDF 明确给出的中文词义及对应词性。一个词性对应一个对象；不得根据模型常识增加 PDF 未出现的词义。

结构：
```json
[{"pos":"n.","meaning":"事故；意外"}]
```

### 5.5 word_forms
**当前词自身的词形变化，不是派生词。**

`type` 枚举：
- `plural`：名词复数
- `third_person`：动词第三人称单数
- `past`：过去式
- `past_participle`：过去分词
- `present_participle`：现在分词
- `comparative`：比较级
- `superlative`：最高级

`source`：
- `document`：PDF 明确出现
- `ai`：AI 按受控规则补全

例：
```text
act → acts / acted / acting = word_forms
action / active / actor / activity = related_words
```

### 5.6 related_words
PDF 明确出现的派生词、词形拓展、相关词。

`relation`：
- `派生词`
- `词形拓展`
- `相关词`

不得仅因词根相同而自行扩展。

### 5.7 phrases
PDF 明确列出的常用词组、固定短语、短语动词、固定表达，尤其是 `词组拓展`。

例如：`by accident`、`look forward to`。

如果 PDF 没有中文释义，`meaning` 可以为空。

### 5.8 collocations
仅记录 PDF 明确作为典型搭配呈现的组合。

`phrases` 与 `collocations` 不要仅凭语言模型知识互相转换。不确定时为空。

### 5.9 proverbs
仅记录 PDF 明确标记为谚语、俗语、格言、proverb、saying 等内容。普通例句不能因“看起来像格言”而进入此字段。

### 5.10 examples
PDF 中提供的英文例句及中文释义。

`type`：
- `general`：普通例句
- `exam`：明确来自考试/真题等
- `textbook`：明确来自教材

只有明确知道来源时才使用 `exam` 或 `textbook`。

### 5.11 usage_notes
PDF 中直接说明的用法、语法规则、固定用法、介词搭配、特殊使用限制等。

### 5.12 teaching_notes
PDF 中 `名师点拨` 等教学指导。

`type`：
- `comparison`：词义/词语辨析
- `usage`：用法说明
- `grammar`：语法说明
- `common_error`：常见错误
- `exam_tip`：考试提示

`title` 优先保留原小标题；没有标题时可做忠实的短标题。`content` 只允许轻度排版/OCR清理，不得自行扩写知识。

### 5.13 tags
仅根据 PDF 明确来源添加：
- `考纲`
- `三级词汇`
- `学科教学基本要求`
- `教材`

允许多个。

### 5.14 exam_level
PDF 星级标记：
- `0`：无星
- `1`：★
- `2`：★★
- `3`：★★★

**不是学习难度、优先级或 AI 推荐等级。**

### 5.15 textbook
PDF 明确提供的上海新教材年级、学期、单元信息。

结构：
```json
[{"grade":"六","semester":"上","unit":"4"}]
```
没有教材来源标记时为空数组。

## 6. 字段边界

| 字段 | 判断标准 |
|---|---|
| word_forms | 当前词自己的语法/词形变化 |
| related_words | 其他派生词/相关词 |
| phrases | 固定词组、短语、短语动词、词组拓展 |
| collocations | 明确作为典型搭配呈现 |
| examples | 例句 |
| proverbs | 明确标记的谚语/格言/俗语 |
| usage_notes | 一般用法/规则说明 |
| teaching_notes | 名师点拨/教学指导 |

核心原则：**不要因为 AI“知道”某个关系，就把它写入知识库；首先必须有 PDF 证据。**

## 7. 空值规则

所有字段均保留：
- string → `""`
- array → `[]`
- number → `0`

不得因无内容删除字段。

## 8. 数据生产 Pipeline

```text
PDF
 ↓
PyMuPDF
 ↓
Raw Page / Block
 ↓
Python 规则预处理
 ↓
Raw Entry
 ↓
Markdown 中间层
 ↓
Structuring Agent
 ↓
Vocabulary JSON
 ↓
JSON Schema Validator
 ↓
Evidence Validator
 ↓
Repair Agent（仅处理失败项）
 ↓
Vocabulary DB
```

工程负责 PDF 读取、block/页码、词条编号识别与切分、页眉页脚过滤、章节识别、完整性/连续性/重复检查及 Schema 校验。

AI 负责语义字段分类、词组/词形拓展/相关词分类、名师点拨结构化、受控 `word_forms` 补全和异常内容的语义修复。

## 9. Evidence Validator

仅 Schema 校验不够，还应验证 AI 输出是否能在 Raw Entry/Markdown 中找到依据。

重点验证：
`related_words`、`phrases`、`collocations`、`proverbs`、`examples`、`usage_notes`、`teaching_notes`、`tags`、`exam_level`、`textbook`。

找不到依据 → FAIL → Repair Agent → 再校验；仍无法确认则保持为空。

## 10. 完整示例

```json
{
  "id": "V00001",
  "word": "accident",
  "phonetic": "/ˈæksɪdənt/",
  "meanings": [{"pos": "n.", "meaning": "事故；意外"}],
  "word_forms": [],
  "related_words": [],
  "phrases": [{"text": "by accident", "meaning": "偶然地"}],
  "collocations": [],
  "proverbs": [],
  "examples": [{"en": "It happened by accident.", "zh": "这件事是偶然发生的。", "type": "general"}],
  "usage_notes": [],
  "teaching_notes": [],
  "tags": ["考纲"],
  "exam_level": 1,
  "textbook": []
}
```

## 11. 版本管理

当前版本：**V1.2**

- 增加字段/兼容性枚举 → minor version
- 修改字段含义、删除字段、改变已有字段语义 → major version

Data Specification、JSON Schema、Agent Prompt 必须保持同版本。

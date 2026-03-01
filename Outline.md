很好，这一步我们就把它当成一个**真正要交付的mini项目来设计**，目标是：

> **结构清晰 + 可快速实现 + 能写进CV + 能讲给老师听**

我给你一个**更工程化 + 更紧凑的设计版本（接近真实项目设计文档）**。

---

# **PolyU Course RAG Demo | 设计大纲**

---

# 一、系统目标（System Goal）

> 构建一个 **课程知识问答系统**，能够基于 lecture materials 回答问题，并提供来源。

---

# 二、系统边界（Scope）

## 输入（Input）

* 课程资料（PDF）
* 用户问题（text）

## 输出（Output）

* 答案（answer）
* 来源（source chunks + page）

---

# 三、系统架构（Architecture）

分为两个阶段：

---

## **1. Offline Pipeline（离线构建）**

```text
PDF → Text → Chunk → Embedding → Vector Store
```

---

## **2. Online Pipeline（在线查询）**

```text
Query → Retrieval → Prompt → LLM → Answer
```

---

# 四、模块拆解（核心部分）

---

# **模块1：Document Loader**

## 功能

读取课程资料

## Input

```text
PDF 文件路径
```

## Output

```text
List[Document]
```

---

# **模块2：Chunking**

## 功能

将文档切成可检索单位

## Input

```text
Document
```

## Process

* 分段
* 控制长度 + overlap

## Output

```text
List[Chunk]
Chunk = {
  text,
  source,
  page
}
```

---

# **模块3：Embedding & Index**

## 功能

构建向量索引

## Input

```text
List[Chunk]
```

## Process

文本 → 向量：

[
v_i = f(c_i)
]

v_i = f(c_i)

---

## Output

```text
VectorStore
```

---

# **模块4：Retriever（核心）**

## 功能

根据问题找相关内容

## Input

```text
query
VectorStore
```

## Process

[
\text{Top-k} = \arg\max_i ; sim(v_q, v_i)
]

\text{Top-k} = \arg\max_i ; sim(v_q, v_i)

---

## Output

```text
Top-k Chunks
```

---

# **模块5：Prompt Builder**

## 功能

构建 RAG prompt

## Input

```text
query + chunks
```

## Output

```text
prompt (string)
```

---

# **模块6：LLM Generator**

## 功能

生成回答

## Input

```text
prompt
```

## Output

```text
answer
```

---

# **模块7：Response Formatter**

## 功能

增强输出

## Input

```text
answer + chunks
```

## Output

```text
{
  answer,
  sources
}
```

---

# 五、数据流（你必须能讲出来）

```text
[Offline]
PDF
 ↓
Loader
 ↓
Chunking
 ↓
Embedding
 ↓
Vector DB

====================

[Online]
User Query
 ↓
Retriever
 ↓
Top-k Chunks
 ↓
Prompt Builder
 ↓
LLM
 ↓
Answer + Sources
```

---

# 六、核心设计点（面试/老师最看重）

---

## 1. Grounded Generation（防幻觉）

* 强制：

  * “ONLY use context”
* 不在 context → 输出 I don’t know

---

## 2. Chunk + Retrieval 质量

* chunk size
* overlap
* top-k

---

## 3. Source Attribution（关键加分点）

输出：

```text
Answer: xxx

Sources:
- Lecture 3, Page 12
- Lecture 5, Page 4
```

---

## 4. 模块解耦（工程能力）

每一层独立：

* retrieval 可替换
* embedding 可替换
* LLM 可替换

---

# 七、最小实现路径（你现在该做的）

## Day 1

* Loader + Chunking

## Day 2

* Embedding + FAISS

## Day 3

* Retrieval + LLM

## Day 4（加分）

* UI + Source显示

---

# 八、代码结构参考（直接照这个建）

```text
rag-demo/
│
├── data/
├── loader.py
├── chunking.py
├── embedding.py
├── retriever.py
├── prompt.py
├── generator.py
├── app.py
```



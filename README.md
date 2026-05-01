# Agentic RAG 医学问答系统：基于 MCP 协议的动态知识增强
## medical_agentic_rag


### Agentic RAG / MCP / LangChain / BM25 / Qwen3 / ReAct / Memory


### 项目描述
&emsp;针对通用 LLM 在医学知识上的时效性不足与单轮检索局限，设计并实现了一个具备自主规划、工具调用的 Agentic RAG 系统。
  
&emsp;通过 MCP（Model Context Protocol）动态接入权威医学 API（诊疗指南、药品说明书、ICD-10/SNOMED CT 编码映射），同时构建本地糖尿病文档库。
  
&emsp;Agent 根据用户意图智能路由检索策略，实现高可靠、可溯源的医学问答。

    
### 功能介绍

&emsp;&emsp;1.**Agent 自主决策与工具调用**：基于 ReAct 模式设计，Agent 自动判断“何时查本地、何时调 API、何时混合检索”，支持多步推理与纠错重试。

&emsp;&emsp;2.**Memory 记忆机制**

&emsp;&emsp;&emsp;&emsp;**短期记忆**：维护多轮对话上下文（滑动窗口 + Redis 缓存），支持指代消解与连贯追问（如“那个药对肾有影响吗？”）。

&emsp;&emsp;&emsp;&emsp;**长期记忆**：基于向量数据库存储糖尿病 PDF 知识库（经 PyMuPDF4LLM/Docling 清洗为 Markdown），Agent 可跨会话检索历史知识与文档溯源，实现持续性个性化问答。

&emsp;&emsp;3.**MCP 医学知识增强**：封装权威指南（NCCN/ESC/中国2型糖尿病指南）、药品说明书及 ICD-10/SNOMED CT 编码查询为 MCP Server，Agent 实时获取最新信息，克服模型训练滞后。下一步 待做：药品信息准确率提升指标。

&emsp;&emsp;4.**端到端评估**：(待做)


### 安装相关依赖
```python
pip install ollama
npm install puppeteer## 1. 安装 puppeteer（完整版，包含谷歌浏览器下载功能），浏览器部分会下载不下来

# 于是在系统(ubuntun 22.02)上单独下载chrome浏览器
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb #清理安装包
google-chrome --version

pip install -r requirements.txt
```
### 在project目录下
```
ollama serve # 终端1：项目运行时始终保持此终端运行
python app.py #终端2：运行项目
```
## 本地文档分块与检索
**分块策略：**
1. 按 Markdown 标题（#、##、###）进行拆分
2. 合并小于 2000 字符的分块
3. 拆分大于 4000 字符的分块
4. 从每个父块中创建子块（500 字符）
5. 将父块存储为 JSON 文件
6. 将子块索引到向量数据库中

**两阶段检索：**
1. 代理搜索子块（快速，语义搜索）
2. 代理根据需要检索父块以获取完整上下文

## 基于对话上下文与查询改写
当前问题：用户可能连续追问（如“那II型糖尿病呢？”），若没有上下文，Agent无法理解指代。

维护对话历史（最近3-5轮），每次请求时自动将历史拼接后送给Agent。

增加查询改写模块：当本地检索结果不佳时，让LLM基于上下文改写用户问题（例如“它”替换为具体疾病名），再重新检索。
技术实现：前端传递session_id，后端存储对话历史；改写可用prompt：“基于对话历史，将用户当前问题改写为独立的、清晰的查询语句。”


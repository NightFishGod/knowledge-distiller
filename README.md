# 知识蒸馏工具 v2.0

> 通用个人知识蒸馏——从你电脑上的工作文件夹，自动提取技能画像、工作流和知识库。**任何人、任何行业、开箱即用。**

## 一句话解释

把你的工作文件夹（PPT、Excel、Word、图片、代码等）拖进去，它自动分析你在做什么、用什么工具、擅长什么、工作节奏什么样，生成一份**个人知识报告**。

---

## 核心能力

| 阶段 | 功能 | 说明 |
|------|------|------|
| **发现** | 自动扫描文件夹 | 纯结构评分，无需手动指定哪个文件夹是"工作" |
| **提取** | 深挖内容 | PPT 备注+SmartArt、Excel 全表+批注、Word 页眉页脚 |
| **分析** | 时间聚类 | 按文件修改时间自动划分工作阶段 |
| **分析** | 目录语义 | 从文件夹名推断工作领域（设计/开发/运营/财务等） |
| **分析** | 工具链检测 | 根据文件扩展名反推使用的软件 |
| **分析** | 写作风格 | 提取全量文本的风格特征 |
| **报告** | 一键生成 | 输出结构化的 Markdown 知识库文件 |

---

## 快速开始

### 方式一：下载 EXE（推荐）

从 [Releases](https://github.com/NightFishGod/knowledge-distiller/releases) 下载 `知识蒸馏工具-v2.0.exe`，双击运行，浏览器自动打开 http://127.0.0.1:8932。

> 无需安装 Python，Windows 10/11 直接可用。

### 方式二：源码运行

```bash
# 1. 克隆
git clone https://github.com/NightFishGod/knowledge-distiller.git
cd knowledge-distiller

# 2. 安装依赖
pip install flask pyyaml python-docx openpyxl python-pptx

# 3. 启动
python app.py
```

浏览器打开 http://127.0.0.1:8932。

---

## 使用步骤

1. 打开 Web 页面
2. 点击"开始蒸馏"
3. 工具自动扫描你的 `桌面`、`文档`、`D盘` 等位置（可在 `config.yaml` 中修改范围）
4. 等待 1-3 分钟（取决于文件量）
5. 查看生成的个人知识报告

报告内容包括：
- 工作领域推断
- 技能关键词图谱
- 工具链全景
- 工作节奏时间线
- 文件命名风格分析

---

## 配置

编辑 `config.yaml` 可自定义：

```yaml
discovery:
  search_roots:           # 扫描哪些目录
    - "~\\Desktop"
    - "~\\Documents"
    - "D:\\"

extraction:
  image_ocr: false        # 是否启用图片 OCR（慢但有用）
  ocr_lang: "chi_sim+eng"

analysis:
  workflow_time_gap_days: 30   # 工作阶段划分间隔
```

详细配置项见 `config.yaml` 内注释。

---

## 项目结构

```
knowledge-distiller/
├── app.py              # Flask Web 入口
├── discover.py         # 文件夹自动发现（纯结构评分）
├── scanner.py          # 文件扫描与索引
├── extractor.py        # 内容提取引擎
├── analyzer.py         # 知识分析引擎
├── report_generator.py # 报告生成
├── build_exe.py        # 打包脚本
├── config.yaml         # 全局配置
├── templates/
│   └── index.html      # Web 前端
├── static/
│   └── style.css       # 暗色主题样式
└── .gitignore
```

## 隐私

**全部本地运行，不上传任何文件。** 127.0.0.1 是本机回环地址，断网也能用。代码开源，可自行审计。

---

## 许可证

MIT License
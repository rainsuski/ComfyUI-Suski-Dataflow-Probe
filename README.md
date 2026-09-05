# ComfyUI-DataflowProbe

**通用数据流血统探针与动态元数据注入系统**
*Universal Dataflow Lineage Probe & Dynamic Metadata Injection System for ComfyUI*

---

## 📖 简介

在 ComfyUI 运行复杂多阶段管线（如 Base+Refiner 分步精修、动态 Switch 旁路分支、视频/音频多模态合成、动态 Wildcard 抽卡）时，原生的静态工作流保存机制往往无法获取运行时实际计算出的动态参数，且多阶段参数容易互相混淆。

`ComfyUI-DataflowProbe` 旨在解决生产级资产追踪（Asset Lineage）问题。它通过**无侵入数据流串联探针**，结合 **DAG 静态拓扑反向遍历**、**执行器运行时缓存穿透（Execution Cache Penetration）** 与 **模型血统边界阻断**，提供一套完整的工业级多阶段时序元数据账单生成与注入方案。

---

## 🧩 核心节点体系

| 节点名称                                                             | 核心职责                                                                                           |
| :------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------- |
| **🔍 Dataflow Lineage Probe** (`DataflowProbe`)              | 核心探针节点。串联在主干流动路径上，以输入连线为锚点向上回溯提取当前阶段参数快照。                 |
| **🔗 Meta Cascade Combine** (`MetaCombine`)                  | 元数据级联合并器。接收两个阶段的元数据（支持字典、列表或 JSON 字符串），按序合并为一个有序列表。   |
| **🛠️ Meta Transformer** (`MetaTransformer`)                | 元数据中继清洗器。挂载在探针与聚合器之间，支持字段重命名、黑名单丢弃与手动标签覆写追加。           |
| **📦 Meta Aggregator & Injector** (`MetaAggregatorInjector`) | 最终聚合注入器。接收多阶段元数据，构建标准多阶段时序账单，写入`extra_pnginfo` 并输出 JSON 文本。 |
| **⚪ Empty Stage Meta** (`EmptyStageMeta`)                   | 空元数据发生器。专为 Switch 旁路、条件分支占位设计，输出合法的空阶段数据，杜绝报错。               |

---

## 📋 常见键名规格说明 (`sniff_keys`)

探针节点通过 `sniff_keys` 配置监听目标字段，系统内置了对主流参数名及规范别名的自动归一化：

| 键名                  | 规范化映射 / 别名                             | 说明                                                                                  |
| :-------------------- | :-------------------------------------------- | :------------------------------------------------------------------------------------ |
| `seed`              | `seed`, `noise_seed`                      | 随机种子（原生 KSampler、rgthree Seed、Primitive 节点均兼容）                         |
| `steps`             | `steps`, `start_at_step`                  | 采样步数                                                                              |
| `cfg`               | `cfg`                                       | 无分类器引导比率 (Classifier Free Guidance)                                           |
| `sampler_name`      | `sampler_name`, `sampler`                 | 采样算法名称（如`euler`, `dpmpp_2m`, `res_multistep`）                          |
| `scheduler`         | `scheduler`                                 | 调度器类型（如`normal`, `karras`, `simple`）                                    |
| `denoise`           | `denoise`                                   | 去噪强度                                                                              |
| `ckpt_name`         | `ckpt_name`                                 | 整体底模权重名称（当加载器包含`checkpoint`/`ckpt` 时智能归一化）                  |
| `unet_name`         | `unet_name`, `model_name`                 | Diffusion / UNET 专属底模（当加载器包含`unet`/`booster`/`anima` 时智能归一化）  |
| `clip_name`         | `clip_name`, `clip_name1`, `clip_name2` | CLIP 文本编码器权重文件名                                                             |
| `loras`             | `loras`, `lora_name`, `lora_stack`      | LoRA 模型载荷。自动将第三方列表解析为`[{"lora_name": "...", "strength": 1.0}]` 结构 |
| `text` / `prompt` | `positive_prompt`, `negative_prompt`      | 正向与负向提示词。依据条件分支槽位自动打标，并对拼接片段进行去重合并                  |

---

## 📦 输出 Payload 格式规范与解析示例

聚合节点（`MetaAggregatorInjector`）最终输出的 `metadata_json` 遵循标准化时序 Schema：

```json
{
  "schema_version": "3.0",
  "stage_count": 2,
  "stages": [
    {
      "stage_name": "Stage_1_Base",
      "params": {
        "seed": 1045715967499289,
        "steps": 8,
        "cfg": 1.0,
        "sampler_name": "res_multistep",
        "scheduler": "simple",
        "unet_name": "anima-turbo-v1.1.safetensors",
        "clip_name": "qwen_3_06b_base.safetensors",
        "loras": [
          {
            "lora_name": "gpt-image-2_anima-base1_v1-1",
            "strength": 1.0
          }
        ],
        "positive_prompt": "good quality, newest, standing, upper body, cute cat girl, @gpt-image-2, masterpiece, 8k",
        "negative_prompt": "worst quality, low quality, score_1, score_2, score_3, old, blurry"
      },
      "node_id": "1595:1844",
      "timestamp": 1788583307.2131455
    },
    {
      "stage_name": "Stage_2_Detailer",
      "params": {
        "seed": 48291039481923,
        "steps": 15,
        "cfg": 2.5,
        "sampler_name": "euler",
        "scheduler": "normal",
        "denoise": 0.35,
        "positive_prompt": "detailed face, realistic skin texture, sharp focus"
      },
      "node_id": "1610:204",
      "timestamp": 1788583320.1042312
    }
  ],
  "custom": {
    "project": "Anime_Production_2026",
    "artist": "Studio_Core"
  }
}
```

---

## ⚠️ 关键提醒：动态分支（Switch）与旁路意外唤醒

在包含条件分支（如 `ComfySwitchNode`, `rgthree` 的 Any Switch, 或第三方 Flow Switch）的工作流中，请特别注意 ComfyUI 调度器的执行唤醒机制：

1. **唤醒风险原理**：
   ComfyUI 的底层执行器是基于依赖反向驱动的。如果你在主干数据流上通过 Switch 旁路阻断了某个分支（例如关闭了二采 Refiner），但**元数据流（`STAGE_META`）却没有同步经过对应的 Switch 进行阻断**，而是直接连入了下游的 `MetaCombine`，聚合节点的依赖拉取会导致**本已被跳过的分支被调度器强行拉起并意外执行**！
2. **最佳工程走线规范**：
   * **同步选通**：当主数据流（`flow`）经过 Switch 节点时，元数据流（`stage_meta`）必须配合 Switch 节点同步选通。
   * **占位安全切断**：在 Switch 节点的未选通分支（如 `on_false` 槽位）上，直接连接一个 **`EmptyStageMeta`** 节点，或者传入空字符串 `""`。
   * 下游的 `MetaCombine` 与 `MetaAggregatorInjector` 会自动将空输入当作“无效分支”静默剔除，保证只有实际生效的计算分支被记录，杜绝废弃参数残留与分支误唤醒。

```text
[主分支 FLOW] ----------> [主 Switch (选通)] --------> [下一步 FLOW]
                                │
[探针 STAGE_META] -------> [元数据 Switch (同步)] ----> [MetaCombine / Aggregator]
                                ▲
[EmptyStageMeta 节点] ──────────┘ (未选通分支安全占位)
```

---

## ⚠️ 免责声明与第三方节点兼容性说明

1. **兼容适配范围**：
   本插件的核心回溯与清洗逻辑针对 **ComfyUI 官方原生节点（Native Nodes）** 以及主流社区扩展（包括但不限于：`rgthree` 系列种子/控制节点、`Lora-Manager`、`TeaCache` 加速节点、`RescaleCFG`、常见 Primitive 基础节点以及标准 `ComfySwitch` 选通节点）进行了靶向验证与深度适配。
2. **非标第三方节点的局限性**：
   ComfyUI 社区存在大量由个人开发者维护的自定义节点，其内部实现可能存在非标准的槽位命名、非公开的内部包装类（如在执行函数内部二次包裹局部 DAG 或在 Python 端即时动态编译），或者未将真实产物写入标准的执行器槽位。
   **对于预料外的非标第三方节点，本插件不保证回溯与提取效果**。遇到未捕获的特殊字段时，推荐使用 `MetaTransformer` 中继节点进行手动重命名、打标或标签补齐。

---

## 🛠️ 安装说明

进入 ComfyUI 的插件目录，使用 Git 克隆本仓库并重启 ComfyUI：

```bash
cd custom_nodes
git clone https://github.com/your-username/ComfyUI-DataflowProbe.git
```

本插件采用纯标准库与轻量架构实现，零第三方重量级依赖。

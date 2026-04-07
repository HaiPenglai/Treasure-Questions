# 宝藏资源链接大全

> 大模型学习与研究重要资源与参考实现汇总

---

## 学习资源

| 链接 | 说明 |
|------|------|
| [MIT 6.5940 TinyML](https://github.com/PKUFlyingPig/MIT6.5940_TinyML) | MIT TinyML 课程 |
| [Stanford CS336](https://stanford-cs336.github.io/) | Stanford 大语言模型课程主页 |
| [CS336 Assignment 1](https://github.com/stanford-cs336/assignment1-basics) | Transformer 基础实现 |
| [CS336 Assignment 2](https://github.com/stanford-cs336/assignment2-systems) | 系统优化与并行 |
| [CS336 Assignment 3](https://github.com/stanford-cs336/assignment3-scaling) | 模型 Scaling Law |
| [CS336 Assignment 4](https://github.com/stanford-cs336/assignment4-data) | 数据处理与清洗 |
| [CS336 Assignment 5](https://github.com/stanford-cs336/assignment5-alignment) | RLHF 对齐训练 |

## 核心库

| 链接 | 说明 |
|------|------|
| [Transformers](https://github.com/huggingface/transformers) | HuggingFace 预训练模型库 |
| [Diffusers](https://github.com/huggingface/diffusers) | HuggingFace 扩散模型库 |
| [Datasets](https://github.com/huggingface/datasets) | HuggingFace 数据集处理库 |
| [Tokenizers](https://github.com/huggingface/tokenizers) | 高性能 tokenizer |

## 微调与训练

| 链接 | 说明 |
|------|------|
| [PEFT](https://github.com/huggingface/peft) | 参数高效微调 (LoRA/Adapter) |
| [TRL](https://github.com/huggingface/trl) | 强化学习训练 (PPO/DPO) |
| [Accelerate](https://github.com/huggingface/accelerate) | 分布式训练加速 |

## 推理引擎

### 服务端推理引擎（高吞吐/多并发）

| 链接 | 说明 |
|------|------|
| [vLLM](https://github.com/vllm-project/vllm) | 高吞吐 LLM 推理 |
| [SGLang](https://github.com/sgl-project/sglang) | 结构化生成推理框架 |
| [nano-vllm](https://github.com/GeeeekExplorer/nano-vllm) | vLLM 极简实现 |
| [mini-sglang](https://github.com/sgl-project/mini-sglang) | SGLang 迷你版 |
| [xFasterTransformer](https://github.com/intel/xFasterTransformer) | Intel 加速方案 |

### 个人端推理引擎（本地单用户/量化友好）

| 链接 | 说明 |
|------|------|
| [llama.cpp](https://github.com/ggerganov/llama.cpp) | 纯C++实现，支持多种量化格式，CPU/GPU混合推理 |
| [Ollama](https://github.com/ollama/ollama) | 基于llama.cpp的易用封装，一键运行本地大模型 |

## 量化加速

| 链接 | 说明 |
|------|------|
| [BitNet](https://github.com/microsoft/BitNet) | 微软 1-bit 量化 |
| [llm-awq](https://github.com/mit-han-lab/llm-awq) | AWQ 官方实现 |
| [AutoAWQ](https://github.com/casper-hansen/AutoAWQ) | AWQ 易用封装 |
| [AutoGPTQ](https://github.com/AutoGPTQ/AutoGPTQ) | GPTQ 量化工具 |
| [smoothquant](https://github.com/mit-han-lab/smoothquant) | SmoothQuant 量化 |
| [bitsandbytes](https://github.com/TimDettmers/bitsandbytes) | 8-bit/4-bit 量化 |

## 注意力优化

| 链接 | 说明 |
|------|------|
| [FlashAttention](https://github.com/Dao-AILab/flash-attention) | 高效注意力计算 |

## CUDA/GPU 优化

| 链接 | 说明 |
|------|------|
| [CUDA Samples](https://github.com/NVIDIA/cuda-samples) | NVIDIA CUDA 官方示例 |
| [DALI](https://github.com/NVIDIA/DALI) | NVIDIA 数据加载加速 |
| [tiny-cuda-nn](https://github.com/NVlabs/tiny-cuda-nn) | 轻量 CUDA 神经网络 |
| [NCCL](https://github.com/NVIDIA/nccl) | GPU 多卡通信库 |
| [cuDNN](https://developer.nvidia.com/cudnn) | NVIDIA 深度学习基元库 |
| [TensorRT](https://github.com/NVIDIA/TensorRT) | NVIDIA 推理优化框架 |

## 训练/推理框架

| 链接 | 说明 |
|------|------|
| [PyTorch](https://github.com/pytorch/pytorch) | 主流深度学习框架 |
| [MindSpore](https://gitee.com/mindspore/mindspore) | 华为昇思框架 |
| [TensorFlow](https://github.com/tensorflow/tensorflow) | Google 深度学习框架 |
| [JAX](https://github.com/google/jax) | Google 高性能计算框架 |
| [DeepSpeed](https://github.com/microsoft/DeepSpeed) | 微软分布式训练框架 |
| [Megatron-LM](https://github.com/NVIDIA/Megatron-LM) | NVIDIA 大模型训练框架 |
| [ColossalAI](https://github.com/hpcaitech/ColossalAI) | 集成式大模型训练系统 |

## 多模态/语音

| 链接 | 说明 |
|------|------|
| [Whisper](https://github.com/openai/whisper) | OpenAI 语音识别 |
| [tiktoken](https://github.com/openai/tiktoken) | OpenAI 快速 tokenizer |

## 算法方法

| 链接 | 说明 |
|------|------|
| [Tree of Thought](https://github.com/princeton-nlp/tree-of-thought-llm) | ToT 思维树推理 |

---

*持续更新中...*

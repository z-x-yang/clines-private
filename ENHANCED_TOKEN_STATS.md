# Enhanced Token Statistics

## 概述

项目现在包含了增强的token统计功能，提供更详细的token使用情况分析。新功能包括原始chunk token统计、平均token使用情况等。

## 新增的统计指标

### Chunk级别统计

每个处理的chunk现在包含以下新的统计信息：

- **原始chunk token数**: 输入chunk在分块时的实际token数量
- **平均prompt tokens per call**: 该chunk中每次LLM调用的平均prompt token数
- **平均completion tokens per call**: 该chunk中每次LLM调用的平均completion token数
- **平均total tokens per call**: 该chunk中每次LLM调用的平均总token数

### Note级别统计

每个处理完成的note包含以下增强统计：

- **总原始chunk tokens**: 所有chunk的原始token数总和
- **平均原始chunk tokens**: 每个chunk的平均原始token数
- **平均prompt tokens per chunk**: 每个chunk的平均prompt token数
- **平均completion tokens per chunk**: 每个chunk的平均completion token数
- **平均LLM calls per chunk**: 每个chunk的平均LLM调用次数

### 运行级别统计

程序运行过程中显示的总体平均值：

- **Average original chunk tokens per note**: 每个note的平均原始chunk token数
- **Average prompt tokens per chunk (overall)**: 所有chunk的平均prompt token数
- **Average completion tokens per chunk (overall)**: 所有chunk的平均completion token数

## 实现细节

### 核心修改

1. **LLMManager类** (`llm_interface/llm_manager.py`)
   - 添加了 `current_chunk_original_tokens` 属性来跟踪当前chunk的原始token数
   - 添加了 `chunk_original_token_stats` 列表来存储每个chunk的原始token数
   - 新增了 `set_chunk_original_tokens()` 方法来设置chunk的原始token数
   - 增强了 `finish_chunk()` 方法来计算更详细的统计信息

2. **PipelineCoordinator类** (`ehr_processing_pipeline/pipeline_coordinator.py`)
   - 在处理每个chunk前调用 `set_chunk_original_tokens()` 方法
   - 支持单chunk和多chunk场景

3. **主程序** (`main.py`)
   - 更新了日志输出来显示新的统计信息
   - 添加了运行级别的统计汇总

### 新增方法

```python
def set_chunk_original_tokens(self, chunk_text):
    """
    设置当前正在处理的chunk的原始token数量
    
    Args:
        chunk_text (str): 原始chunk文本
    """
```

## 使用示例

运行测试脚本查看新功能：

```bash
python test_token_stats.py
```

## 示例输出

```
Token Usage Statistics for the note:
  Total prompt tokens: 1250
  Total completion tokens: 380
  Total tokens: 1630
  Number of chunks: 3
  Average tokens per chunk: 543.33
  Total original chunk tokens: 892
  Average original chunk tokens: 297.33
  Average prompt tokens per chunk: 416.67
  Average completion tokens per chunk: 126.67
  Average LLM calls per chunk: 4.33

Overall Token Usage Averages (this run):
  Average prompt tokens per note: 1250.00
  Average completion tokens per note: 380.00
  Average total tokens per note: 1630.00
  Average original chunk tokens per note: 297.33
  Average prompt tokens per chunk (overall): 416.67
  Average completion tokens per chunk (overall): 126.67
```

## 注意事项

1. **Tokenizer依赖**: 原始chunk token统计依赖于模型的tokenizer。对于不支持tokenizer的模型，会使用单词数作为估算。

2. **兼容性**: 新功能向后兼容，不会影响现有的token统计功能。

3. **性能**: 添加的统计计算对性能影响很小，主要是在chunk处理结束时进行计算。

## 应用场景

这些增强的统计信息可以帮助：

- **成本估算**: 更准确地预估API调用成本
- **性能优化**: 了解不同chunk大小对token使用的影响
- **效率分析**: 分析prompt设计对token使用效率的影响
- **资源规划**: 基于历史数据预测资源需求 
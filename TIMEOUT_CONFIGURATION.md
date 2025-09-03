# Mem0 MCP 超时配置说明

## 写入超时配置的重要性

### 问题背景
根据实际使用经验，Mem0 API的写入操作通常需要较长时间：
- **小数据（< 100KB）**: 通常需要 10-30 秒
- **中等数据（100KB - 1MB）**: 通常需要 30-60 秒  
- **大数据（> 1MB）**: 通常需要 1-3 分钟
- **超大数据（> 5MB）**: 可能需要 3-5 分钟

### 原始问题
原始的mem0客户端和httpx默认配置：
- **httpx默认写入超时**: 5秒
- **mem0客户端超时**: 300秒（5分钟）
- **实际写入时间**: 2分钟左右

这导致60秒的写入超时设置不够用，经常出现写入超时错误。

### 解决方案

#### 1. 调整写入超时配置
```python
"timeout": {
    "write": 300.0,  # 写入超时5分钟，适应2分钟写入时间
}
```

#### 2. 环境变量配置
```bash
# 根据您的数据大小调整写入超时
export MEM0_WRITE_TIMEOUT=300   # 5分钟（推荐）
export MEM0_WRITE_TIMEOUT=600   # 10分钟（大数据）
export MEM0_WRITE_TIMEOUT=900   # 15分钟（超大数据）
```

#### 3. 动态超时配置
根据数据大小动态调整超时时间：

```python
def get_dynamic_timeout(data_size_mb):
    """根据数据大小动态计算超时时间"""
    if data_size_mb < 0.1:
        return 60    # 小数据：1分钟
    elif data_size_mb < 1:
        return 180   # 中等数据：3分钟
    elif data_size_mb < 5:
        return 300   # 大数据：5分钟
    else:
        return 600   # 超大数据：10分钟
```

## 超时配置最佳实践

### 1. 根据使用场景配置
```bash
# 开发环境 - 快速失败
export MEM0_WRITE_TIMEOUT=120

# 生产环境 - 稳定优先
export MEM0_WRITE_TIMEOUT=300

# 大数据处理 - 长时间等待
export MEM0_WRITE_TIMEOUT=600
```

### 2. 监控和调整
- 监控实际写入时间
- 根据网络状况调整
- 考虑服务器负载情况

### 3. 错误处理
```python
try:
    result = client.add(large_data)
except httpx.WriteTimeout:
    # 写入超时，可以重试或分块处理
    logger.warning("写入超时，尝试分块处理")
    result = client._add_large_data(large_data)
```

## 配置建议

### 推荐配置
```bash
# 标准配置（适合大多数场景）
export MEM0_WRITE_TIMEOUT=300    # 5分钟写入超时
export MEM0_TIMEOUT=600          # 10分钟读取超时
export MEM0_CONNECT_TIMEOUT=30   # 30秒连接超时
```

### 大数据场景配置
```bash
# 大数据处理配置
export MEM0_WRITE_TIMEOUT=600    # 10分钟写入超时
export MEM0_TIMEOUT=1200         # 20分钟读取超时
export MEM0_CHUNK_SIZE=524288    # 512KB块大小
export MEM0_MAX_RETRIES=5        # 增加重试次数
export MEM0_RETRY_DELAY=2.0      # 重试延迟2秒
```

### 网络不稳定环境配置
```bash
# 网络不稳定环境
export MEM0_WRITE_TIMEOUT=900    # 15分钟写入超时
export MEM0_MAX_RETRIES=5        # 增加重试次数
export MEM0_RETRY_DELAY=2.0      # 重试延迟2秒
```

## 故障排除

### 常见超时错误
1. **WriteTimeout**: 写入超时，增加 `MEM0_WRITE_TIMEOUT`
2. **ReadTimeout**: 读取超时，增加 `MEM0_TIMEOUT`
3. **ConnectTimeout**: 连接超时，检查网络连接

### 调试方法
```bash
# 启用详细日志
export MEM0_LOG_LEVEL=DEBUG

# 监控超时情况
grep "timeout" mem0.log
```

## 总结

写入超时配置是Mem0 MCP客户端稳定性的关键因素。根据实际使用经验，建议：

1. **默认写入超时**: 300秒（5分钟）
2. **大数据场景**: 600秒（10分钟）
3. **网络不稳定**: 900秒（15分钟）
4. **监控和调整**: 根据实际使用情况动态调整

这样可以确保在各种使用场景下都能稳定工作，避免因超时导致的写入失败。

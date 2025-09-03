# 增强版Mem0 MCP客户端使用指南

## 概述

本增强版Mem0 MCP客户端解决了原始版本中的超时和数据传输问题，提供了更稳定和可靠的服务。

## 主要改进

### 1. 超时问题解决
- **连接超时**: 30秒（可配置）
- **读取超时**: 10分钟（可配置）
- **写入超时**: 5分钟（可配置）- 适应2分钟写入时间
- **连接池超时**: 30秒（可配置）

### 2. 数据传输优化
- **数据分块**: 自动将大数据分割成1MB块（可配置）
- **重试机制**: 失败时自动重试，支持指数退避
- **连接池优化**: 增加最大连接数和保持连接数

### 3. 配置管理
- **统一配置**: 通过`mem0_config.py`管理所有配置
- **环境变量支持**: 可通过环境变量覆盖配置
- **日志记录**: 详细的日志记录，便于调试

## 文件结构

```
├── main.py                    # 主程序
├── enhanced_mem0_client.py    # 增强版客户端
├── mem0_config.py            # 配置文件
├── start_mem0_mcp.bash       # 启动脚本
└── ENHANCED_MEM0_GUIDE.md    # 使用指南
```

## 配置说明

### 默认配置

```python
DEFAULT_CONFIG = {
         # 超时设置
     "timeout": {
         "connect": 30.0,      # 连接超时（秒）
         "read": 600.0,        # 读取超时（秒）- 10分钟
         "write": 300.0,       # 写入超时（秒）- 5分钟，适应2分钟写入时间
         "pool": 30.0,         # 连接池超时（秒）
     },
    
         # 重试设置
     "retry": {
         "max_retries": 5,     # 最大重试次数
         "retry_delay": 2.0,   # 重试延迟（秒）
         "backoff_factor": 2.0, # 指数退避因子
     },
    
    # 连接池设置
    "limits": {
        "max_connections": 200,           # 最大连接数
        "max_keepalive_connections": 50,  # 最大保持连接数
        "keepalive_expiry": 30.0,        # 保持连接过期时间（秒）
    },
    
    # 数据处理设置
    "data": {
        "chunk_size": 1024 * 1024,       # 数据块大小（字节）- 1MB
        "max_chunk_size": 2 * 1024 * 1024, # 最大块大小（字节）- 2MB
        "chunk_delay": 0.1,              # 块间延迟（秒）
    }
}
```

### 环境变量配置

可以通过以下环境变量覆盖默认配置：

```bash
 # 超时设置
 export MEM0_TIMEOUT=600              # 读取超时（秒）
 export MEM0_CONNECT_TIMEOUT=30       # 连接超时（秒）
 export MEM0_WRITE_TIMEOUT=300        # 写入超时（秒）- 5分钟
 export MEM0_POOL_TIMEOUT=30          # 连接池超时（秒）

# 重试设置
export MEM0_MAX_RETRIES=5            # 最大重试次数
export MEM0_RETRY_DELAY=2.0          # 重试延迟（秒）

# 数据处理设置
export MEM0_CHUNK_SIZE=1048576       # 数据块大小（字节）
export MEM0_MAX_CHUNK_SIZE=2097152   # 最大块大小（字节）

# 服务器设置
export MEM0_HOST=0.0.0.0            # 服务器主机
export MEM0_PORT=8080               # 服务器端口
export MEM0_DEBUG=true              # 调试模式

# 日志设置
export MEM0_LOG_LEVEL=INFO          # 日志级别
export MEM0_LOG_FILE=mem0.log       # 日志文件（可选）
```

## 使用方法

### 1. 启动服务

```bash
# 使用启动脚本（推荐）
./start_mem0_mcp.bash

# 或直接运行
uv run python main.py
```

### 2. 在Cursor中连接

连接到SSE端点：
```
http://0.0.0.0:8080/sse
```

### 3. 使用工具

增强版客户端提供三个主要工具：

#### add_coding_preference
添加编码偏好，支持大数据自动分块：
```python
# 大数据会自动分块处理
await add_coding_preference(large_code_content)
```

#### get_all_coding_preferences
获取所有编码偏好：
```python
preferences = await get_all_coding_preferences()
```

#### search_coding_preferences
搜索编码偏好：
```python
results = await search_coding_preferences("Python async programming")
```

## 故障排除

### 1. 超时问题
如果仍然遇到超时，可以增加超时时间：
```bash
export MEM0_TIMEOUT=1200  # 读取超时20分钟
export MEM0_WRITE_TIMEOUT=600  # 写入超时10分钟（适应更长的写入时间）
```

### 2. 数据大小问题
如果数据仍然太大，可以减小块大小：
```bash
export MEM0_CHUNK_SIZE=524288  # 512KB
```

### 3. 连接问题
如果连接不稳定，可以增加重试次数和延迟：
```bash
export MEM0_MAX_RETRIES=5        # 最大重试次数
export MEM0_RETRY_DELAY=2.0      # 重试延迟（秒）
```

### 4. 日志调试
启用详细日志：
```bash
export MEM0_LOG_LEVEL=DEBUG
export MEM0_LOG_FILE=mem0_debug.log
```

## 性能优化建议

1. **合理设置块大小**: 根据网络状况调整`MEM0_CHUNK_SIZE`
2. **调整重试策略**: 根据服务器稳定性调整重试次数和延迟
3. **监控日志**: 定期检查日志文件，了解性能瓶颈
4. **网络优化**: 确保网络连接稳定，避免频繁重试

## 技术细节

### 数据分块策略
- 按行分割，保持数据完整性
- 单行过长时强制分割
- 块间添加延迟，避免服务器压力

### 重试机制
- 指数退避算法
- 只对网络错误重试，HTTP状态错误不重试
- 详细的重试日志记录

### 连接池优化
- 增加最大连接数到200
- 保持连接数增加到50
- 连接过期时间30秒

## 更新日志

### v1.0.0
- 解决超时问题
- 实现数据分块传输
- 添加重试机制
- 统一配置管理
- 增强日志记录

## 支持

如果遇到问题，请检查：
1. 日志文件中的错误信息
2. 网络连接状态
3. Mem0 API密钥是否正确
4. 配置参数是否合理

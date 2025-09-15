# Mem0 MCP 连接管理配置说明

## 问题背景

在长时间运行的服务中，经常出现 `ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host` 错误。这个错误通常发生在：

1. **网络不稳定**：网络连接中断或波动
2. **服务器端超时**：远程服务器主动关闭空闲连接
3. **连接池管理问题**：连接池中的连接状态不一致
4. **异步连接处理**：asyncio层面的连接管理问题

## 解决方案：连接池健康检查和自动重建机制

### 核心特性

1. **连接健康检查**：定期检查连接状态
2. **自动连接重建**：检测到连接问题时自动重建
3. **心跳保活机制**：维持连接活跃状态
4. **智能重试策略**：集成连接管理的重试机制

## 配置说明

### 连接管理配置

```python
"connection": {
    "health_check_interval": 30,      # 健康检查间隔（秒）
    "heartbeat_interval": 60,         # 心跳间隔（秒）
    "auto_rebuild": True,             # 自动重建连接
    "connection_timeout": 10,         # 连接超时（秒）
}
```

### 环境变量配置

```bash
# 连接管理设置
export MEM0_HEALTH_CHECK_INTERVAL=30    # 健康检查间隔
export MEM0_HEARTBEAT_INTERVAL=60       # 心跳间隔
export MEM0_AUTO_REBUILD=true           # 自动重建连接
export MEM0_CONNECTION_TIMEOUT=10       # 连接超时
```

## 工作机制

### 1. 连接健康检查

```python
def _check_connection_health(self) -> bool:
    """检查连接健康状态"""
    try:
        # 发送ping请求检查连接
        response = self.client.get("/v1/ping/", timeout=self._connection_timeout)
        if response.status_code == 200:
            self._connection_healthy = True
            self._last_health_check = datetime.now()
            return True
        else:
            self._connection_healthy = False
            return False
    except Exception as e:
        self._connection_healthy = False
        return False
```

**特点**：
- 使用轻量级的ping请求检查连接
- 可配置的连接超时时间
- 自动更新连接状态和时间戳

### 2. 自动连接重建

```python
def _rebuild_connection(self):
    """重建连接"""
    try:
        # 关闭旧连接
        if hasattr(self, 'client') and self.client:
            self.client.close()
        
        # 重新创建客户端
        self._create_client(timeout_config, limits_config)
        
        # 重新验证API密钥
        self.user_email = self._validate_api_key()
        
        self._connection_healthy = True
        logger.info("连接重建成功")
    except Exception as e:
        logger.error(f"连接重建失败: {e}")
        self._connection_healthy = False
```

**特点**：
- 完全重建HTTP客户端
- 重新验证API密钥
- 错误处理和状态更新

### 3. 心跳保活机制

```python
def _start_heartbeat(self):
    """启动心跳保活机制"""
    def heartbeat_worker():
        while not self._heartbeat_stop_event.is_set():
            try:
                # 检查是否需要健康检查
                if (datetime.now() - self._last_health_check).seconds >= self._health_check_interval:
                    if not self._check_connection_health():
                        logger.warning("连接不健康，尝试重建...")
                        self._rebuild_connection()
                
                # 等待心跳间隔
                self._heartbeat_stop_event.wait(self._heartbeat_interval)
            except Exception as e:
                logger.error(f"心跳保活机制异常: {e}")
                time.sleep(5)
    
    self._heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
    self._heartbeat_thread.start()
```

**特点**：
- 后台线程运行，不阻塞主线程
- 定期健康检查和连接重建
- 异常处理和自动恢复

### 4. 智能重试策略

```python
def _retry_on_failure(self, func, *args, **kwargs):
    """重试机制装饰器，集成连接健康检查"""
    # 确保连接健康
    self._ensure_healthy_connection()
    
    for attempt in range(self.max_retries):
        try:
            return func(*args, **kwargs)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError, ConnectionResetError) as e:
            # 检测到连接错误时，尝试重建连接
            if isinstance(e, (httpx.ConnectError, ConnectionResetError)) and self._auto_rebuild:
                logger.warning(f"检测到连接错误，尝试重建连接: {e}")
                try:
                    self._rebuild_connection()
                except Exception as rebuild_error:
                    logger.error(f"连接重建失败: {rebuild_error}")
            
            # 指数退避重试
            wait_time = self.retry_delay * (self.backoff_factor ** attempt)
            time.sleep(wait_time)
```

**特点**：
- 请求前确保连接健康
- 检测到连接错误时自动重建
- 支持ConnectionResetError重试
- 指数退避策略

## 使用示例

### 基本使用

```python
from enhanced_mem0_client import EnhancedMemoryClient

# 使用默认配置
client = EnhancedMemoryClient()

# 使用自定义配置
config = {
    "connection": {
        "health_check_interval": 20,     # 20秒健康检查
        "heartbeat_interval": 30,        # 30秒心跳
        "auto_rebuild": True,            # 自动重建
        "connection_timeout": 5,         # 5秒连接超时
    }
}
client = EnhancedMemoryClient(config=config)

# 正常使用
result = client.add("测试数据")
```

### 环境变量配置

```bash
# 设置连接管理参数
export MEM0_HEALTH_CHECK_INTERVAL=20
export MEM0_HEARTBEAT_INTERVAL=30
export MEM0_AUTO_REBUILD=true
export MEM0_CONNECTION_TIMEOUT=5

# 启动服务
./start_mem0_mcp.bash
```

## 监控和调试

### 1. 启用详细日志

```bash
export MEM0_LOG_LEVEL=DEBUG
```

### 2. 监控连接状态

```python
# 检查连接健康状态
if client._connection_healthy:
    print("连接健康")
else:
    print("连接不健康")

# 检查最后健康检查时间
print(f"最后健康检查: {client._last_health_check}")
```

### 3. 日志分析

```bash
# 查看连接相关日志
grep "连接" mem0.log
grep "健康检查" mem0.log
grep "重建" mem0.log
```

## 性能优化建议

### 1. 根据网络环境调整

```bash
# 稳定网络环境
export MEM0_HEALTH_CHECK_INTERVAL=60
export MEM0_HEARTBEAT_INTERVAL=120

# 不稳定网络环境
export MEM0_HEALTH_CHECK_INTERVAL=20
export MEM0_HEARTBEAT_INTERVAL=30
```

### 2. 根据使用模式调整

```bash
# 高频使用
export MEM0_HEALTH_CHECK_INTERVAL=15
export MEM0_HEARTBEAT_INTERVAL=30

# 低频使用
export MEM0_HEALTH_CHECK_INTERVAL=60
export MEM0_HEARTBEAT_INTERVAL=120
```

## 故障排除

### 常见问题

1. **连接重建频繁**：增加健康检查间隔
2. **心跳机制异常**：检查线程状态和异常处理
3. **连接超时**：调整连接超时时间
4. **内存泄漏**：确保正确关闭客户端

### 调试方法

```python
# 手动触发健康检查
client._check_connection_health()

# 手动重建连接
client._rebuild_connection()

# 停止心跳机制
client._stop_heartbeat()
```

## 总结

连接池健康检查和自动重建机制解决了以下问题：

1. **ConnectionResetError**：通过自动重建连接解决
2. **连接状态不一致**：通过定期健康检查解决
3. **长时间运行稳定性**：通过心跳保活机制解决
4. **网络波动影响**：通过智能重试策略解决

这个机制确保了Mem0 MCP客户端在各种网络环境下都能稳定运行，大大减少了连接相关的错误。

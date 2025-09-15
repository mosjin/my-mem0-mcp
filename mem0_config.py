"""
Mem0 MCP 配置文件
"""
import os
from typing import Dict, Any

# 默认配置
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
    },
    
    # 连接管理设置
    "connection": {
        "health_check_interval": 30,      # 健康检查间隔（秒）
        "heartbeat_interval": 60,         # 心跳间隔（秒）
        "auto_rebuild": True,             # 自动重建连接
        "connection_timeout": 10,         # 连接超时（秒）
    },
    
    # 服务器设置
    "server": {
        "host": "0.0.0.0",
        "port": 8080,
        "debug": True,
        "timeout_keep_alive": 1800,      # 保持连接超时（秒）
        "ws_ping_interval": 120,         # WebSocket ping间隔（秒）
        "ws_ping_timeout": 120,          # WebSocket ping超时（秒）
    },
    
    # 日志设置
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": None,  # 日志文件路径，None表示只输出到控制台
    }
}

def get_config() -> Dict[str, Any]:
    """获取配置，支持环境变量覆盖"""
    config = DEFAULT_CONFIG.copy()
    
    # 从环境变量读取配置
    env_mappings = {
        "MEM0_TIMEOUT": ("timeout", "read"),
        "MEM0_CONNECT_TIMEOUT": ("timeout", "connect"),
        "MEM0_WRITE_TIMEOUT": ("timeout", "write"),
        "MEM0_POOL_TIMEOUT": ("timeout", "pool"),
        "MEM0_MAX_RETRIES": ("retry", "max_retries"),
        "MEM0_RETRY_DELAY": ("retry", "retry_delay"),
        "MEM0_CHUNK_SIZE": ("data", "chunk_size"),
        "MEM0_MAX_CHUNK_SIZE": ("data", "max_chunk_size"),
        "MEM0_HOST": ("server", "host"),
        "MEM0_PORT": ("server", "port"),
        "MEM0_DEBUG": ("server", "debug"),
        "MEM0_LOG_LEVEL": ("logging", "level"),
        "MEM0_LOG_FILE": ("logging", "file"),
    }
    
    for env_var, (section, key) in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            # 类型转换
            if key in ["max_retries", "port"]:
                config[section][key] = int(value)
            elif key in ["debug"]:
                config[section][key] = value.lower() in ("true", "1", "yes", "on")
            elif key in ["chunk_size", "max_chunk_size"]:
                config[section][key] = int(value)
            else:
                try:
                    config[section][key] = float(value)
                except ValueError:
                    config[section][key] = value
    
    return config

def get_httpx_timeout_config(config: Dict[str, Any]) -> Dict[str, float]:
    """获取httpx超时配置"""
    timeout_config = config["timeout"]
    return {
        "connect": timeout_config["connect"],
        "read": timeout_config["read"],
        "write": timeout_config["write"],
        "pool": timeout_config["pool"],
    }

def get_httpx_limits_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取httpx连接限制配置"""
    limits_config = config["limits"]
    return {
        "max_connections": limits_config["max_connections"],
        "max_keepalive_connections": limits_config["max_keepalive_connections"],
        "keepalive_expiry": limits_config["keepalive_expiry"],
    }

def get_retry_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取重试配置"""
    return config["retry"]

def get_data_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取数据处理配置"""
    return config["data"]

def get_connection_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取连接管理配置"""
    return config["connection"]

def get_server_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取服务器配置"""
    return config["server"]

def get_logging_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """获取日志配置"""
    return config["logging"]

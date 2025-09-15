"""
增强版Mem0客户端，解决超时和数据传输问题
"""
import os
import json
import logging
import time
import asyncio
import threading
from typing import Any, Dict, List, Optional, Union
from functools import wraps
from datetime import datetime, timedelta

import httpx
from mem0.client.main import MemoryClient, APIError
from mem0_config import get_config, get_httpx_timeout_config, get_httpx_limits_config, get_retry_config, get_data_config, get_connection_config

logger = logging.getLogger(__name__)

class EnhancedMemoryClient(MemoryClient):
    """增强版Mem0客户端，解决超时和数据传输问题"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        host: Optional[str] = None,
        org_id: Optional[str] = None,
        project_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """初始化增强版客户端
        
        Args:
            api_key: Mem0 API密钥
            host: API主机地址
            org_id: 组织ID
            project_id: 项目ID
            config: 自定义配置字典，如果为None则使用默认配置
        """
        # 获取配置
        self.config = config or get_config()
        
        # 从配置中获取参数
        timeout_config = get_httpx_timeout_config(self.config)
        limits_config = get_httpx_limits_config(self.config)
        retry_config = get_retry_config(self.config)
        data_config = get_data_config(self.config)
        connection_config = get_connection_config(self.config)
        
        # 设置实例变量
        self.api_key = api_key or os.getenv("MEM0_API_KEY")
        self.host = host or "https://api.mem0.ai"
        self.org_id = org_id
        self.project_id = project_id
        self.max_retries = retry_config["max_retries"]
        self.retry_delay = retry_config["retry_delay"]
        self.backoff_factor = retry_config["backoff_factor"]
        self.chunk_size = data_config["chunk_size"]
        self.max_chunk_size = data_config["max_chunk_size"]
        self.chunk_delay = data_config["chunk_delay"]
        
        # 连接管理相关属性
        self._connection_healthy = True
        self._last_health_check = datetime.now()
        self._health_check_interval = connection_config["health_check_interval"]
        self._heartbeat_interval = connection_config["heartbeat_interval"]
        self._auto_rebuild = connection_config["auto_rebuild"]
        self._connection_timeout = connection_config["connection_timeout"]
        self._heartbeat_thread = None
        self._heartbeat_stop_event = threading.Event()
        
        if not self.api_key:
            raise ValueError("Mem0 API Key not provided. Please provide an API Key.")
        
        # 创建增强的httpx客户端配置
        self._create_client(timeout_config, limits_config)
        
        # 验证API密钥
        self.user_email = self._validate_api_key()
        
        # 启动心跳保活机制
        self._start_heartbeat()
    
    def _create_client(self, timeout_config, limits_config):
        """创建httpx客户端"""
        self.client = httpx.Client(
            base_url=self.host,
            headers={
                "Authorization": f"Token {self.api_key}",
                "User-Agent": "Enhanced-Mem0-Client/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(**timeout_config),
            limits=httpx.Limits(**limits_config),
            follow_redirects=True,
            max_redirects=10,
        )
        logger.info("HTTP客户端已创建")
    
    def _check_connection_health(self) -> bool:
        """检查连接健康状态"""
        try:
            # 发送一个简单的ping请求检查连接
            response = self.client.get("/v1/ping/", timeout=self._connection_timeout)
            if response.status_code == 200:
                self._connection_healthy = True
                self._last_health_check = datetime.now()
                logger.debug("连接健康检查通过")
                return True
            else:
                logger.warning(f"连接健康检查失败，状态码: {response.status_code}")
                self._connection_healthy = False
                return False
        except Exception as e:
            logger.warning(f"连接健康检查异常: {e}")
            self._connection_healthy = False
            return False
    
    def _rebuild_connection(self):
        """重建连接"""
        try:
            logger.info("开始重建连接...")
            # 关闭旧连接
            if hasattr(self, 'client') and self.client:
                self.client.close()
            
            # 重新创建客户端
            timeout_config = get_httpx_timeout_config(self.config)
            limits_config = get_httpx_limits_config(self.config)
            self._create_client(timeout_config, limits_config)
            
            # 重新验证API密钥
            self.user_email = self._validate_api_key()
            
            self._connection_healthy = True
            self._last_health_check = datetime.now()
            logger.info("连接重建成功")
            
        except Exception as e:
            logger.error(f"连接重建失败: {e}")
            self._connection_healthy = False
    
    def _start_heartbeat(self):
        """启动心跳保活机制"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        
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
                    time.sleep(5)  # 异常时等待5秒再继续
        
        self._heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
        self._heartbeat_thread.start()
        logger.info("心跳保活机制已启动")
    
    def _stop_heartbeat(self):
        """停止心跳保活机制"""
        if self._heartbeat_thread:
            self._heartbeat_stop_event.set()
            self._heartbeat_thread.join(timeout=5)
            logger.info("心跳保活机制已停止")
    
    def _ensure_healthy_connection(self):
        """确保连接健康"""
        # 如果连接不健康或长时间未检查，进行健康检查
        if (not self._connection_healthy or 
            (datetime.now() - self._last_health_check).seconds >= self._health_check_interval):
            
            if not self._check_connection_health():
                logger.warning("连接不健康，尝试重建...")
                self._rebuild_connection()
    
    def _retry_on_failure(self, func, *args, **kwargs):
        """重试机制装饰器，集成连接健康检查"""
        # 确保连接健康
        self._ensure_healthy_connection()
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError, ConnectionResetError) as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"所有重试失败: {e}")
                    raise APIError(f"请求失败，已重试{self.max_retries}次: {str(e)}")
                
                # 检测到连接错误时，尝试重建连接
                if isinstance(e, (httpx.ConnectError, ConnectionResetError)) and self._auto_rebuild:
                    logger.warning(f"检测到连接错误，尝试重建连接: {e}")
                    try:
                        self._rebuild_connection()
                    except Exception as rebuild_error:
                        logger.error(f"连接重建失败: {rebuild_error}")
                
                wait_time = self.retry_delay * (self.backoff_factor ** attempt)  # 指数退避
                logger.warning(f"请求失败，{wait_time}秒后重试 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                time.sleep(wait_time)
            except httpx.HTTPStatusError as e:
                # HTTP状态错误不重试
                logger.error(f"HTTP错误: {e}")
                raise APIError(f"API请求失败: {e.response.text}")
            except Exception as e:
                logger.error(f"未知错误: {e}")
                raise APIError(f"请求失败: {str(e)}")
    
    def _chunk_data(self, data: str, max_chunk_size: Optional[int] = None) -> List[str]:
        """将大数据分块处理"""
        if max_chunk_size is None:
            max_chunk_size = self.max_chunk_size
        
        # 确保max_chunk_size不为None
        if max_chunk_size is None:
            max_chunk_size = self.max_chunk_size
        
        # 再次确保不为None
        if max_chunk_size is None:
            max_chunk_size = 2 * 1024 * 1024  # 默认2MB
        
        # 如果数据小于块大小，直接返回
        if len(data.encode('utf-8')) <= max_chunk_size:
            return [data]
        
        chunks = []
        current_chunk = ""
        
        # 按行分割，保持完整性
        lines = data.split('\n')
        for line in lines:
            # 如果单行就超过块大小，强制分割
            if len(line.encode('utf-8')) > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # 强制分割长行
                while len(line.encode('utf-8')) > max_chunk_size:
                    chunk = line[:max_chunk_size//4]  # 保守估计，考虑UTF-8编码
                    chunks.append(chunk)
                    line = line[max_chunk_size//4:]
                
                if line:
                    current_chunk = line
            else:
                # 检查添加这行是否会超过块大小
                test_chunk = current_chunk + ('\n' if current_chunk else '') + line
                if len(test_chunk.encode('utf-8')) > max_chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk = test_chunk
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def add(self, messages: Union[str, List[Dict[str, str]]], **kwargs) -> Dict[str, Any]:
        """增强的添加记忆方法，支持大数据和重试"""
        def _add_implementation():
            kwargs_prepared = self._prepare_params(kwargs)
            payload = self._prepare_payload(messages, kwargs_prepared)
            
            # 检查数据大小
            payload_str = json.dumps(payload, ensure_ascii=False)
            payload_size = len(payload_str.encode('utf-8'))
            
            logger.info(f"准备发送数据，大小: {payload_size / 1024 / 1024:.2f} MB")
            
            # 如果数据太大，分块处理
            if payload_size > self.chunk_size:
                logger.info(f"数据过大，将分块处理")
                return self._add_large_data(messages, kwargs_prepared)
            
            # 正常大小的数据直接发送
            response = self.client.post("/v1/memories/", json=payload)
            response.raise_for_status()
            
            if "metadata" in kwargs_prepared:
                del kwargs_prepared["metadata"]
            
            result = response.json()
            return result if result is not None else {}
        
        result = self._retry_on_failure(_add_implementation)
        return result if result is not None else {}
    
    def _add_large_data(self, messages: Union[str, List[Dict[str, str]]], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """处理大数据的分块添加"""
        if isinstance(messages, str):
            chunks = self._chunk_data(messages)
        else:
            # 对于消息列表，将每个消息的内容分块
            chunks = []
            for msg in messages:
                if isinstance(msg, dict) and 'content' in msg:
                    msg_chunks = self._chunk_data(msg['content'])
                    for i, chunk in enumerate(msg_chunks):
                        chunk_msg = msg.copy()
                        chunk_msg['content'] = chunk
                        if len(msg_chunks) > 1:
                            chunk_msg['chunk_info'] = f"part_{i+1}_of_{len(msg_chunks)}"
                        chunks.append(chunk_msg)
                else:
                    chunks.append(msg)
        
        results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"发送数据块 {i+1}/{len(chunks)}")
            
            if isinstance(chunk, str):
                chunk_payload = self._prepare_payload(chunk, kwargs)
            else:
                chunk_payload = self._prepare_payload([chunk], kwargs)
            
            response = self.client.post("/v1/memories/", json=chunk_payload)
            response.raise_for_status()
            results.append(response.json())
            
            # 块之间稍作延迟，避免服务器压力
            if i < len(chunks) - 1:
                time.sleep(self.chunk_delay)
        
        # 返回最后一个结果，或者合并结果
        if len(results) == 1:
            return results[0]
        else:
            return {
                "message": f"成功添加{len(results)}个数据块",
                "chunks": len(results),
                "results": results
            }
    
    def search(self, query: str, version: str = "v1", **kwargs) -> List[Dict[str, Any]]:
        """增强的搜索方法，支持重试"""
        def _search_implementation():
            payload = {"query": query}
            params = self._prepare_params(kwargs)
            payload.update(params)
            
            response = self.client.post(f"/{version}/memories/search/", json=payload)
            response.raise_for_status()
            
            if "metadata" in kwargs:
                del kwargs["metadata"]
            
            result = response.json()
            return result if result is not None else []
        
        result = self._retry_on_failure(_search_implementation)
        return result if result is not None else []
    
    def get_all(self, version: str = "v1", **kwargs) -> List[Dict[str, Any]]:
        """增强的获取所有记忆方法，支持重试"""
        def _get_all_implementation():
            params = self._prepare_params(kwargs)
            if version == "v1":
                response = self.client.get(f"/{version}/memories/", params=params)
            elif version == "v2":
                if "page" in params and "page_size" in params:
                    query_params = {"page": params.pop("page"), "page_size": params.pop("page_size")}
                    response = self.client.post(f"/{version}/memories/", json=params, params=query_params)
                else:
                    response = self.client.post(f"/{version}/memories/", json=params)
            
            response.raise_for_status()
            
            if "metadata" in kwargs:
                del kwargs["metadata"]
            
            result = response.json()
            return result if result is not None else []
        
        result = self._retry_on_failure(_get_all_implementation)
        return result if result is not None else []
    
    def close(self):
        """关闭客户端连接"""
        try:
            # 停止心跳保活机制
            self._stop_heartbeat()
            
            # 关闭HTTP客户端
            if hasattr(self, 'client') and self.client:
                self.client.close()
                logger.info("HTTP客户端已关闭")
            
            # 重置连接状态
            self._connection_healthy = False
            logger.info("客户端连接已完全关闭")
            
        except Exception as e:
            logger.error(f"关闭客户端时出现异常: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

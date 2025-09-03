"""
增强版Mem0客户端，解决超时和数据传输问题
"""
import os
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from functools import wraps

import httpx
from mem0.client.main import MemoryClient, APIError
from mem0_config import get_config, get_httpx_timeout_config, get_httpx_limits_config, get_retry_config, get_data_config

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
        
        if not self.api_key:
            raise ValueError("Mem0 API Key not provided. Please provide an API Key.")
        
        # 创建增强的httpx客户端配置
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
        
        # 验证API密钥
        self.user_email = self._validate_api_key()
    
    def _retry_on_failure(self, func, *args, **kwargs):
        """重试机制装饰器"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"所有重试失败: {e}")
                    raise APIError(f"请求失败，已重试{self.max_retries}次: {str(e)}")
                
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
        if hasattr(self, 'client'):
            self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

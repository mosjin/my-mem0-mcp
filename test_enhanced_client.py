#!/usr/bin/env python3
"""
测试增强版Mem0客户端的脚本
"""
import os
import sys
import logging
from dotenv import load_dotenv

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_mem0_client import EnhancedMemoryClient
from mem0_config import get_config

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_client_initialization():
    """测试客户端初始化"""
    try:
        config = get_config()
        client = EnhancedMemoryClient(config=config)
        logger.info("✅ 客户端初始化成功")
        return client
    except Exception as e:
        logger.error(f"❌ 客户端初始化失败: {e}")
        return None

def test_small_data(client):
    """测试小数据添加"""
    try:
        small_data = "这是一个小的测试数据，用于验证基本功能。"
        result = client.add(small_data, user_id="test_user", output_format="v1.1")
        logger.info("✅ 小数据添加成功")
        return True
    except Exception as e:
        logger.error(f"❌ 小数据添加失败: {e}")
        return False

def test_large_data(client):
    """测试大数据添加"""
    try:
        # 创建一个较大的测试数据（约1.5MB）
        large_data = "这是一个大的测试数据。\n" * 100000  # 约1.5MB
        
        logger.info(f"准备添加大数据，大小: {len(large_data.encode('utf-8')) / 1024 / 1024:.2f} MB")
        result = client.add(large_data, user_id="test_user", output_format="v1.1")
        logger.info("✅ 大数据添加成功")
        return True
    except Exception as e:
        logger.error(f"❌ 大数据添加失败: {e}")
        return False

def test_search(client):
    """测试搜索功能"""
    try:
        results = client.search("测试数据", user_id="test_user", output_format="v1.1")
        logger.info(f"✅ 搜索成功，找到 {len(results.get('results', []))} 个结果")
        return True
    except Exception as e:
        logger.error(f"❌ 搜索失败: {e}")
        return False

def test_get_all(client):
    """测试获取所有数据"""
    try:
        results = client.get_all(user_id="test_user", page=1, page_size=10)
        logger.info(f"✅ 获取所有数据成功，找到 {len(results.get('results', []))} 个结果")
        return True
    except Exception as e:
        logger.error(f"❌ 获取所有数据失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("开始测试增强版Mem0客户端...")
    logger.info("配置信息: 重试次数=5, 重试延迟=2秒, 写入超时=5分钟")
    
    # 检查API密钥
    if not os.getenv("MEM0_API_KEY"):
        logger.error("❌ 未找到MEM0_API_KEY环境变量，请设置API密钥")
        return False
    
    # 测试客户端初始化
    client = test_client_initialization()
    if not client:
        return False
    
    # 运行测试
    tests = [
        ("小数据添加", lambda: test_small_data(client)),
        ("大数据添加", lambda: test_large_data(client)),
        ("搜索功能", lambda: test_search(client)),
        ("获取所有数据", lambda: test_get_all(client)),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"运行测试: {test_name}")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            logger.error(f"测试 {test_name} 出现异常: {e}")
    
    # 关闭客户端
    try:
        client.close()
        logger.info("✅ 客户端已关闭")
    except Exception as e:
        logger.warning(f"关闭客户端时出现警告: {e}")
    
    # 输出测试结果
    logger.info(f"测试完成: {passed}/{total} 个测试通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！增强版客户端工作正常。")
        return True
    else:
        logger.warning(f"⚠️  有 {total - passed} 个测试失败，请检查配置和网络连接。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

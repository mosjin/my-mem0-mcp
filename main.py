from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn
from mem0 import MemoryClient
from enhanced_mem0_client import EnhancedMemoryClient
from typing import Union
from mem0_config import get_config, get_logging_config, get_server_config
from dotenv import load_dotenv
import json
import logging

load_dotenv()

# 获取配置
config = get_config()
logging_config = get_logging_config(config)
server_config = get_server_config(config)

# 配置日志
log_config = {
    'level': getattr(logging, logging_config['level'].upper()),
    'format': logging_config['format']
}

if logging_config['file']:
    log_config['filename'] = logging_config['file']

logging.basicConfig(**log_config)
logger = logging.getLogger(__name__)

# Initialize FastMCP server for mem0 tools
mcp = FastMCP("mem0-mcp")

# Initialize enhanced mem0 client and set default user
mem0_client: Union[EnhancedMemoryClient, MemoryClient]
try:
    mem0_client = EnhancedMemoryClient(config=config)
    logger.info("使用增强版Mem0客户端")
    logger.info(f"配置信息: 超时={config['timeout']['read']}s, 重试={config['retry']['max_retries']}次, 块大小={config['data']['chunk_size']//1024}KB")
except Exception as e:
    logger.warning(f"增强版客户端初始化失败，使用标准客户端: {e}")
    mem0_client = MemoryClient()

DEFAULT_USER_ID = "cursor_mcp"
CUSTOM_INSTRUCTIONS = """
Extract the Following Information:  

- Code Snippets: Save the actual code for future reference.  
- Explanation: Document a clear description of what the code does and how it works.
- Related Technical Details: Include information about the programming language, dependencies, and system specifications.  
- Key Features: Highlight the main functionalities and important aspects of the snippet.
"""
mem0_client.update_project(custom_instructions=CUSTOM_INSTRUCTIONS)

@mcp.tool(
    description="""Add a new coding preference to mem0. This tool stores code snippets, implementation details,
    and coding patterns for future reference. Store every code snippet. When storing code, you should include:
    - Complete code with all necessary imports and dependencies
    - Language/framework version information (e.g., "Python 3.9", "React 18")
    - Full implementation context and any required setup/configuration
    - Detailed comments explaining the logic, especially for complex sections
    - Example usage or test cases demonstrating the code
    - Any known limitations, edge cases, or performance considerations
    - Related patterns or alternative approaches
    - Links to relevant documentation or resources
    - Environment setup requirements (if applicable)
    - Error handling and debugging tips
    The preference will be indexed for semantic search and can be retrieved later using natural language queries."""
)
async def add_coding_preference(text: str) -> str:
    """Add a new coding preference to mem0.

    This tool is designed to store code snippets, implementation patterns, and programming knowledge.
    When storing code, it's recommended to include:
    - Complete code with imports and dependencies
    - Language/framework information
    - Setup instructions if needed
    - Documentation and comments
    - Example usage

    Args:
        text: The content to store in memory, including code, documentation, and context
    """
    try:
        logger.info(f"开始添加编码偏好，数据大小: {len(text.encode('utf-8')) / 1024:.2f} KB")
        
        messages = [{"role": "user", "content": text}]
        result = mem0_client.add(messages, user_id=DEFAULT_USER_ID, output_format="v1.1")
        
        logger.info("编码偏好添加成功")
        return f"Successfully added preference: {text[:200]}{'...' if len(text) > 200 else ''}"
    except Exception as e:
        logger.error(f"添加编码偏好失败: {str(e)}")
        return f"Error adding preference: {str(e)}"

@mcp.tool(
    description="""Retrieve all stored coding preferences for the default user. Call this tool when you need 
    complete context of all previously stored preferences. This is useful when:
    - You need to analyze all available code patterns
    - You want to check all stored implementation examples
    - You need to review the full history of stored solutions
    - You want to ensure no relevant information is missed
    Returns a comprehensive list of:
    - Code snippets and implementation patterns
    - Programming knowledge and best practices
    - Technical documentation and examples
    - Setup and configuration guides
    Results are returned in JSON format with metadata."""
)
async def get_all_coding_preferences() -> str:
    """Get all coding preferences for the default user.

    Returns a JSON formatted list of all stored preferences, including:
    - Code implementations and patterns
    - Technical documentation
    - Programming best practices
    - Setup guides and examples
    Each preference includes metadata about when it was created and its content type.
    """
    try:
        logger.info("开始获取所有编码偏好")
        memories = mem0_client.get_all(user_id=DEFAULT_USER_ID, page=1, page_size=50)
        if isinstance(memories, dict) and "results" in memories:
            results = memories.get("results", [])
            flattened_memories = [memory.get("memory", "") for memory in results if isinstance(memory, dict)]
        else:
            flattened_memories = []
        
        logger.info(f"成功获取 {len(flattened_memories)} 个编码偏好")
        return json.dumps(flattened_memories, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取编码偏好失败: {str(e)}")
        return f"Error getting preferences: {str(e)}"

@mcp.tool(
    description="""Search through stored coding preferences using semantic search. This tool should be called 
    for EVERY user query to find relevant code and implementation details. It helps find:
    - Specific code implementations or patterns
    - Solutions to programming problems
    - Best practices and coding standards
    - Setup and configuration guides
    - Technical documentation and examples
    The search uses natural language understanding to find relevant matches, so you can
    describe what you're looking for in plain English. Always search the preferences before 
    providing answers to ensure you leverage existing knowledge."""
)
async def search_coding_preferences(query: str) -> str:
    """Search coding preferences using semantic search.

    The search is powered by natural language understanding, allowing you to find:
    - Code implementations and patterns
    - Programming solutions and techniques
    - Technical documentation and guides
    - Best practices and standards
    Results are ranked by relevance to your query.

    Args:
        query: Search query string describing what you're looking for. Can be natural language
              or specific technical terms.
    """
    try:
        logger.info(f"开始搜索编码偏好，查询: {query}")
        memories = mem0_client.search(query, user_id=DEFAULT_USER_ID, output_format="v1.1")
        if isinstance(memories, dict) and "results" in memories:
            results = memories.get("results", [])
            flattened_memories = [memory.get("memory", "") for memory in results if isinstance(memory, dict)]
        else:
            flattened_memories = []
        
        logger.info(f"搜索完成，找到 {len(flattened_memories)} 个相关结果")
        return json.dumps(flattened_memories, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"搜索编码偏好失败: {str(e)}")
        return f"Error searching preferences: {str(e)}"

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    mcp_server = mcp._mcp_server

    import argparse

    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    try:
        uvicorn.run(
            starlette_app, 
            host=args.host, 
            port=args.port,
            timeout_keep_alive=server_config['timeout_keep_alive'],
            ws_ping_interval=server_config['ws_ping_interval'],
            ws_ping_timeout=server_config['ws_ping_timeout'],
            log_level=logging_config['level'].lower()
        )
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务...")
    finally:
        # 确保客户端正确关闭
        if isinstance(mem0_client, EnhancedMemoryClient):
            mem0_client.close()
        logger.info("服务已关闭")

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import asyncio
import os
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from typing import Any


@dataclass
class ToolParameter:
    """Represents a parameter for a tool.
    
    Attributes:
        name: Parameter name
        parameter_type: Parameter type (e.g., "string", "number")
        description: Parameter description
        required: Whether the parameter is required
        default: Default value for the parameter
    """
    name: str
    parameter_type: str
    description: str
    required: bool = False
    default: Any = None


@dataclass
class ToolDef:
    """Represents a tool definition.
    
    Attributes:
        name: Tool name
        description: Tool description
        parameters: List of ToolParameter objects
        metadata: Optional dictionary of additional metadata
        identifier: Tool identifier (defaults to name)
    """
    name: str
    description: str
    parameters: List[ToolParameter]
    metadata: Optional[Dict[str, Any]] = None
    identifier: str = ""


@dataclass
class ToolInvocationResult:
    """Represents the result of a tool invocation.
    
    Attributes:
        content: Result content as a string
        error_code: Error code (0 for success, 1 for error)
    """
    content: str
    error_code: int

class MCPClient:
    def __init__(self):
        self.server_url = os.getenv("MCP_SERVER_URL")
        self.tools = []
        self.resources = []
        self.prompts = []
    
    async def initialize(self):
        try:
            print(f"Attempting to connect to MCP server at {self.server_url}")
            async with sse_client(self.server_url) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    self.tools = await session.list_tools()
                    print("Connected to MCP server at", self.server_url)

        except Exception as e:
            print(f"Error connecting to MCP server at {self.server_url}")
            print(f"Error details: {str(e)}")
            import traceback
            traceback.print_exc()
    
    async def get_tools(self) -> List[ToolDef]:
        """List available tools from the MCP endpoint
        
        Returns:
            List of ToolDef objects describing available tools
        """
        tools = []
        async with sse_client(self.server_url) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                
                for tool in tools_result.tools:
                    parameters = []
                    required_params = tool.inputSchema.get("required", [])
                    for param_name, param_schema in tool.inputSchema.get("properties", {}).items():
                        parameters.append(
                            ToolParameter(
                                name=param_name,
                                parameter_type=param_schema.get("type", "string"),
                                description=param_schema.get("description", ""),
                                required=param_name in required_params,
                                default=param_schema.get("default"),
                            )
                        )
                    tools.append(
                        ToolDef(
                            name=tool.name,
                            description=tool.description,
                            parameters=parameters,
                            metadata={"endpoint": self.server_url},
                            identifier=tool.name  # Using name as identifier
                        )
                    )
        return tools

    async def invoke_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolInvocationResult:
        """Invoke a specific tool with parameters
        
        Args:
            tool_name: Name of the tool to invoke
            kwargs: Dictionary of parameters to pass to the tool
            
        Returns:
            ToolInvocationResult containing the tool's response
        """
        async with sse_client(self.server_url) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, kwargs)

        return ToolInvocationResult(
            content="\n".join([result.model_dump_json() for result in result.content]),
            error_code=1 if result.isError else 0,
        )
    
    @staticmethod
    def print_tools(tools: List[ToolDef]):
        for tool in tools:
            print(f"- Tool > {tool.name}: {tool.description}")
            print("  Parameters:")
            for param in tool.parameters:
                print(f"    - {param.name} ({param.parameter_type}): {param.description}")

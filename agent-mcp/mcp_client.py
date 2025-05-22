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
        self.session = None
        self.streams = None
    
    async def initialize(self):
        try:
            print(f"Attempting to connect to MCP server at {self.server_url}")
            # Keep the sse_client and session open
            self.streams = sse_client(self.server_url)
            self.session = ClientSession(*(await self.streams.__aenter__())) # Manually enter the sse_client context
            await self.session.initialize()
            # self.tools = await self.session.list_tools() # This line should be removed
            print("Connected to MCP server at", self.server_url)

        except Exception as e:
            print(f"Error connecting to MCP server at {self.server_url}")
            print(f"Error details: {str(e)}")
            if self.session:
                await self.session.__aexit__(None, None, None) # Ensure session is closed on error
                self.session = None
            if self.streams:
                await self.streams.__aexit__(None, None, None) # Ensure streams are closed on error
                self.streams = None
            import traceback
            traceback.print_exc()
    
    async def get_tools(self) -> List[ToolDef]:
        if not self.session:
            # This case should ideally be handled by explicit initialization by the caller
            print("MCPClient session not initialized. Initializing now...")
            await self.initialize() 
            if not self.session: # If initialization failed
                print("Failed to initialize session in get_tools.")
                return []

        tools_result = await self.session.list_tools()
        
        processed_tools = []
        for tool_def_proto in tools_result.tools: # Assuming tools_result.tools is the list of tool definitions
            parameters = []
            required_params = tool_def_proto.inputSchema.get("required", [])
            for param_name, param_schema in tool_def_proto.inputSchema.get("properties", {}).items():
                parameters.append(
                    ToolParameter(
                        name=param_name,
                        parameter_type=param_schema.get("type", "string"),
                        description=param_schema.get("description", ""),
                        required=param_name in required_params,
                        default=param_schema.get("default"),
                    )
                )
            processed_tools.append(
                ToolDef(
                    name=tool_def_proto.name,
                    description=tool_def_proto.description,
                    parameters=parameters,
                    metadata={"endpoint": self.server_url}, # Assuming self.server_url is still relevant
                    identifier=tool_def_proto.name 
                )
            )
        self.tools = processed_tools # Store in self.tools
        return processed_tools

    async def invoke_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolInvocationResult:
        if not self.session:
            # This case should ideally be handled by explicit initialization by the caller
            print("MCPClient session not initialized. Initializing now...")
            await self.initialize()
            if not self.session: # If initialization failed
                print("Failed to initialize session in invoke_tool.")
                # Return an error ToolInvocationResult
                return ToolInvocationResult(content="Failed to initialize MCP session", error_code=1)

        result = await self.session.call_tool(tool_name, kwargs)

        return ToolInvocationResult(
            content="\n".join([res.model_dump_json() for res in result.content]), # Assuming result.content is a list of models
            error_code=1 if result.isError else 0,
        )

    async def close(self):
        print("Closing MCPClient session...")
        if self.session:
            try:
                await self.session.__aexit__(None, None, None) # Assuming ClientSession is an async context manager
                print("MCP session closed.")
            except Exception as e:
                print(f"Error closing MCP session: {str(e)}")
            finally:
                self.session = None
        
        if self.streams:
            try:
                await self.streams.__aexit__(None, None, None) # Assuming sse_client returns an async context manager
                print("MCP streams closed.")
            except Exception as e:
                print(f"Error closing MCP streams: {str(e)}")
            finally:
                self.streams = None
    
    @staticmethod
    def print_tools(tools: List[ToolDef]):
        for tool in tools:
            print(f"- Tool > {tool.name}: {tool.description}")
            print("  Parameters:")
            for param in tool.parameters:
                print(f"    - {param.name} ({param.parameter_type}): {param.description}")

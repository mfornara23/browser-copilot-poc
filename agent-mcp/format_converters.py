"""
Format converters for transforming MCP tool definitions to various LLM formats.
"""
from typing import List, Dict, Any
from mcp_client import ToolDef, ToolParameter

# Type mapping from Python/MCP types to JSON Schema types
TYPE_MAPPING = {
    "int": "integer",
    "bool": "boolean",
    "str": "string",
    "float": "number",
    "list": "array",
    "dict": "object",
    "boolean": "boolean",  # Already correct but included for completeness
    "string": "string",    # Already correct but included for completeness
    "integer": "integer",  # Already correct but included for completeness
    "number": "number",    # Already correct but included for completeness
    "array": "array",      # Already correct but included for completeness
    "object": "object"     # Already correct but included for completeness
}


def _infer_array_item_type(param: ToolParameter) -> str:
    """Infer the item type for an array parameter based on its name and description.
    
    Args:
        param: The ToolParameter object
        
    Returns:
        The inferred JSON Schema type for array items
    """
    # Default to string items
    item_type = "string"
    
    # Check if parameter name contains hints about item type
    param_name_lower = param.name.lower()
    if any(hint in param_name_lower for hint in ["language", "code", "tag", "name", "id"]):
        item_type = "string"
    elif any(hint in param_name_lower for hint in ["number", "count", "amount", "index"]):
        item_type = "integer"
    
    # Also check the description for hints
    if param.description:
        desc_lower = param.description.lower()
        if "string" in desc_lower or "text" in desc_lower or "language" in desc_lower:
            item_type = "string"
        elif "number" in desc_lower or "integer" in desc_lower or "int" in desc_lower:
            item_type = "integer"
    
    return item_type


def to_openai_format(tools: List[ToolDef]) -> List[Dict[str, Any]]:
    """Convert ToolDef objects to OpenAI function format.
    
    Args:
        tools: List of ToolDef objects to convert
        
    Returns:
        List of dictionaries in OpenAI function format
    """
    
    openai_tools = []
    for tool in tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        # Add properties
        for param in tool.parameters:
            # Map the type or use the original if no mapping exists
            schema_type = TYPE_MAPPING.get(param.parameter_type, param.parameter_type)
            
            param_schema = {
                "type": schema_type,  # Use mapped type
                "description": param.description
            }
            
            # For arrays, we need to specify the items type
            if schema_type == "array":
                item_type = _infer_array_item_type(param)
                param_schema["items"] = {"type": item_type}
            
            openai_tool["function"]["parameters"]["properties"][param.name] = param_schema
            
            # Add default value if provided
            if param.default is not None:
                openai_tool["function"]["parameters"]["properties"][param.name]["default"] = param.default
                
            # Add to required list if required
            if param.required:
                openai_tool["function"]["parameters"]["required"].append(param.name)
                
        openai_tools.append(openai_tool)
    return openai_tools


def to_anthropic_format(tools: List[ToolDef]) -> List[Dict[str, Any]]:
    """Convert ToolDef objects to Anthropic tool format.
    
    Args:
        tools: List of ToolDef objects to convert
        
    Returns:
        List of dictionaries in Anthropic tool format
    """
    
    anthropic_tools = []
    for tool in tools:
        anthropic_tool = {
            "name": tool.name,
            "description": tool.description,
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        
        # Add properties
        for param in tool.parameters:
            # Map the type or use the original if no mapping exists
            schema_type = TYPE_MAPPING.get(param.parameter_type, param.parameter_type)
            
            param_schema = {
                "type": schema_type,  # Use mapped type
                "description": param.description
            }
            
            # For arrays, we need to specify the items type
            if schema_type == "array":
                item_type = _infer_array_item_type(param)
                param_schema["items"] = {"type": item_type}
            
            anthropic_tool["input_schema"]["properties"][param.name] = param_schema
            
            # Add default value if provided
            if param.default is not None:
                anthropic_tool["input_schema"]["properties"][param.name]["default"] = param.default
                
            # Add to required list if required
            if param.required:
                anthropic_tool["input_schema"]["required"].append(param.name)
                
        anthropic_tools.append(anthropic_tool)
    return anthropic_tools


def to_langchain_format(tools: List[ToolDef]) -> List:
    """Convert ToolDef objects to LangChain tool format.
    
    Args:
        tools: List of ToolDef objects to convert
        
    Returns:
        List of LangChain Tool objects
    """
    from langchain.tools import StructuredTool
    from langchain.pydantic_v1 import create_model, Field
    
    langchain_tools = []
    for tool in tools:
        # Create a dynamic Pydantic model for the tool parameters
        field_definitions = {}
        for param in tool.parameters:
            # Get the Python type from the parameter type
            python_type = str  # Default to string
            if param.parameter_type in ["int", "integer"]:
                python_type = int
            elif param.parameter_type in ["float", "number"]:
                python_type = float
            elif param.parameter_type in ["bool", "boolean"]:
                python_type = bool
            
            # Add the field to the model definition
            field_definitions[param.name] = (
                python_type,
                Field(
                    description=param.description,
                    default=param.default if not param.required else ...,
                )
            )
        
        # Create the Pydantic model for the tool parameters
        param_model = create_model(f"{tool.name}Parameters", **field_definitions)
        
        # Create a function that will invoke the tool
        async def _tool_func(**kwargs):
            from mcp_client import MCPClient
            client = MCPClient()
            await client.initialize()
            result = await client.invoke_tool(tool.name, kwargs)
            return result.content
        
        # Create the LangChain tool
        langchain_tool = StructuredTool.from_function(
            func=_tool_func,
            name=tool.name,
            description=tool.description,
            args_schema=param_model,
            return_direct=False,
            coroutine=_tool_func,
        )
        
        langchain_tools.append(langchain_tool)
    
    return langchain_tools
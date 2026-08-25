"""
Talks to the tool server over JSON-RPC.

Starts the server as a separate process, sends a request down a pipe, and
reads the reply back. Spawning takes about six seconds, which is why the
timeout is generous.
"""

import asyncio
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

# How long to wait for the server. Generous because the server is started fresh
# for every call and imports the whole package on the way up — about six seconds
# idle, more when the machine is busy. Raise it rather than lower it: a timeout
# here loses a tool result, and the agent then answers without the data.
MCP_TIMEOUT_S = 120

MCP_SERVERS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server")
UNIFIED_SERVER_PATH = os.path.join(MCP_SERVERS_PATH, "mcp_server.py")


class MCPClient:
    """Client for communicating with MCP servers via stdio"""
    
    def __init__(self, server_path: str):
        self.server_path = server_path
        
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool on an MCP server"""
        try:
            # Start the MCP server process
            process = await asyncio.create_subprocess_exec(
                sys.executable, self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024*1024  # 1MB limit for large responses
            )
            
            # MCP initialization request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "trip-planner-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            # Send initialization
            init_message = json.dumps(init_request) + "\n"
            process.stdin.write(init_message.encode())  # type: ignore
            await process.stdin.drain()  # type: ignore
            
            # Read initialization response with larger buffer
            init_response = await asyncio.wait_for(
                process.stdout.readline(),  # type: ignore
                timeout=MCP_TIMEOUT_S
            )
            if init_response:
                init_data = json.loads(init_response.decode().strip())
                logger.info(f"MCP Server initialized: {init_data}")
            
            # Send tool call request
            tool_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            tool_message = json.dumps(tool_request) + "\n"
            process.stdin.write(tool_message.encode())  # type: ignore
            await process.stdin.drain()  # type: ignore
            
            # Read tool response - use read() with timeout for large responses
            try:
                # Read all available output
                tool_response = await asyncio.wait_for(
                    process.stdout.readline(),  # type: ignore
                    timeout=MCP_TIMEOUT_S
                )
            except asyncio.TimeoutError:
                logger.error("MCP server response timeout")
                return {"success": False, "error": "Response timeout"}
            
            # Close the process
            process.stdin.close()  # type: ignore
            await process.wait()
            
            if tool_response:
                response_data = json.loads(tool_response.decode().strip())
                if "result" in response_data and "content" in response_data["result"]:
                    # Extract the actual content from MCP response
                    content = response_data["result"]["content"]
                    if isinstance(content, list) and len(content) > 0:
                        return {"success": True, "data": content[0]["text"]}
                    else:
                        return {"success": True, "data": str(content)}
                else:
                    return {"success": False, "error": "Invalid MCP response format", "raw": response_data}
            else:
                return {"success": False, "error": "No response from MCP server"}
                
        except asyncio.TimeoutError:
            # Named separately because str(asyncio.TimeoutError()) is the EMPTY
            # STRING. This surfaced as "MCP client error: " with nothing after it,
            # twice, during a live London run — a failure with no message at all,
            # which is the hardest kind to chase.
            #
            # It times out because every call spawns a fresh server process, and
            # that process imports the whole package. Roughly six seconds on an
            # idle machine; under a live run with the model working it can exceed
            # the timeout entirely.
            logger.error(
                "MCP call to %r timed out after %ss. Each call starts a new "
                "server process, which is slow enough to miss this deadline when "
                "the machine is busy.", tool_name, MCP_TIMEOUT_S)
            return {"success": False,
                    "error": f"MCP call to {tool_name!r} timed out after "
                             f"{MCP_TIMEOUT_S}s (the server is started per call)"}
        except Exception as e:
            # The type matters as much as the message, because several exceptions
            # on this path stringify to nothing.
            logger.error("MCP client error calling %r: %s: %s",
                         tool_name, type(e).__name__, e)
            return {"success": False, "error": str(e)}


# Initialize unified MCP client
mcp_client = MCPClient(UNIFIED_SERVER_PATH)


def run_async_tool(coro):
    """Helper to run async MCP calls from sync tools"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an event loop, we need to run in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except Exception:
        # Fallback: create new event loop
        return asyncio.run(coro)

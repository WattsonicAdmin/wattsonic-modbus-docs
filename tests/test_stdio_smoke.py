"""MCP stdio smoke test: start the server as a subprocess, initialize, list tools, call one tool, read a resource,
get the prompt."""
import json
import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {"search_registers", "get_register", "list_sunspec_models", "get_sunspec_point", "list_recipes",
                  "get_recipe", "validate_write", "generate_client_code", "get_doc_section"}


async def _run():
    params = StdioServerParameters(command=sys.executable, args=["-m", "wattsonic_modbus_docs"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "wattsonic-modbus-docs"
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            assert EXPECTED_TOOLS <= names
            for t in tools.tools:
                assert t.description and len(t.description) > 40
            res = await session.call_tool("get_register", {"address": "11045"})
            assert not res.isError
            payload = json.loads(res.content[0].text)
            assert payload["name"] == "Active_Power_Set"
            vw = await session.call_tool("validate_write", {"address": "11300", "value": 1, "function_code": "0x10"})
            assert json.loads(vw.content[0].text)["verdict"] == "reject"
            resources = await session.list_resources()
            uris = {str(r.uri) for r in resources.resources}
            assert "wattsonic://docs/native.md" in uris
            body = await session.read_resource("wattsonic://docs/llms.txt")
            assert "Wattsonic MATIC" in body.contents[0].text
            prompts = await session.list_prompts()
            assert "integrate-matic-ems" in {p.name for p in prompts.prompts}
            pr = await session.get_prompt("integrate-matic-ems", {"goal": "zero export"})
            assert "zero export" in pr.messages[0].content.text


def test_stdio_smoke():
    anyio.run(_run)

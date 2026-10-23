# wattsonic-modbus-docs

Read-only [Model Context Protocol](https://modelcontextprotocol.io) server with the Modbus documentation of the
**Wattsonic MATIC** hybrid inverter (ARM firmware M013V1130B01D05 or later), the same content as
<https://modbus.wattsonic.com/>:

- the native EMS register map (10000-19800) with integration fields (write function, effective conditions,
  read-back registers, persistence),
- the SunSpec model chain (40000-40478: models 1, 123, 124, 103, 203, 120, 121, 122, 160) in the SunSpec JSON layout,
- closed-loop control recipes (EMS session with watchdog and heartbeat, active-power setpoint, power limit, reactive
  power, Eco schedule, SunSpec gate, SunSpec limit, forced charge/discharge, recovery, emergency stop),
- both reference pages as Markdown.

## Safety

**Documentation only.** The server has no Modbus client, opens no network connection and never connects to an
inverter. `validate_write` checks a planned write against the documentation and returns guidance; it does not write.
`generate_client_code` returns source code as text; that code writes to a real inverter when *you* run it, so review
it first.

## Tools

| Tool | Purpose |
|---|---|
| `search_registers(query, interface?)` | Find registers by address, name, SunSpec point or words |
| `get_register(address)` | Full record of a native register or SunSpec point |
| `list_sunspec_models()` | Model chain, addresses, lengths, writable points, conventions |
| `get_sunspec_point(model, point)` | One SunSpec point with device notes, writable range, scale factor |
| `list_recipes()` / `get_recipe(task)` | Closed-loop control recipes |
| `validate_write(address, value, function_code)` | Access, range, scale, 0x06-only rule, preconditions, read-back |
| `generate_client_code(recipe_id, language, transport="tcp")` | Python (pymodbus), Node.js (modbus-serial), C# (NModbus), Go (goburrow/modbus) |
| `get_doc_section(page, section)` | One section of the documentation as Markdown |

Resources: `wattsonic://docs/native.md`, `wattsonic://docs/sunspec.md`, `wattsonic://docs/llms.txt`,
`wattsonic://docs/registers.v1130.json`, `wattsonic://docs/sunspec-models.v1130.json`,
`wattsonic://docs/recipes.v1130.json`, `wattsonic://docs/VERSION.json`.
Prompt: `integrate-matic-ems` (goal, interface).

Data version: `VERSION.json` (`<firmware>+<build date>`, e.g. `M013V1130B01D05+2026-10-23`).

## Install and configure

Requires [uv](https://docs.astral.sh/uv/). Run directly:

```bash
uvx wattsonic-modbus-docs
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "wattsonic-modbus-docs": { "command": "uvx", "args": ["wattsonic-modbus-docs"] }
  }
}
```

**Claude Code**:

```bash
claude mcp add wattsonic-modbus-docs -- uvx wattsonic-modbus-docs
```

**Cursor** (`.cursor/mcp.json` or `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "wattsonic-modbus-docs": { "command": "uvx", "args": ["wattsonic-modbus-docs"] }
  }
}
```

## Development

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e ".[test]"
.venv/bin/python -m pytest -q
```

## License

Code: [Apache License 2.0](LICENSE). Documentation data: [CC BY 4.0](LICENSE-DATA). See [NOTICE](NOTICE) for trademarks.

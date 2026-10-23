"""MCP server (stdio) for the Wattsonic MATIC Modbus documentation.  Read-only; never connects to a device."""
from __future__ import annotations

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import __version__, codegen, docs

INSTRUCTIONS = (
    "Documentation server for the Modbus interface of Wattsonic MATIC hybrid inverters (ARM firmware "
    "M013V1130B01D05 or later). Modbus TCP port 502, unit 1; native EMS registers 10000-19800 and the SunSpec map "
    "40000-40478 share the connection and are selected by the start address of each request. Use it to find "
    "registers, scale factors, access rules and closed-loop control sequences, to check a planned write and to "
    "generate client code. " + docs.SAFETY + " Follow every control as a closed loop: preconditions, write sequence, "
    "read-back confirmation, failure and recovery (see list_recipes)."
)

mcp = FastMCP("wattsonic-modbus-docs", instructions=INSTRUCTIONS)
mcp._mcp_server.version = __version__  # report the package version, not the SDK version


@mcp.tool()
def search_registers(
    query: Annotated[str, Field(description="Register address (e.g. '11045'), name fragment (e.g. 'Active_Power'), "
                                            "SunSpec point (e.g. '123.WMaxLimPct') or words (e.g. 'battery power').")],
    interface: Annotated[Literal["native", "sunspec"] | None,
                         Field(description="Limit to the native EMS map or the SunSpec map; omit for both.")] = None,
    limit: Annotated[int, Field(ge=1, le=100, description="Maximum number of results.")] = 20,
) -> dict:
    """Search the documented registers of the Wattsonic MATIC inverter (native EMS map and SunSpec map).

    Returns compact entries: address, name or SunSpec point, type, unit/scale or sf, access. Use get_register for the
    full record (value list, range, write function, effective conditions, read-back registers, persistence).
    Documentation only; never touches a device."""
    return docs.search_registers(query, interface, limit)


@mcp.tool()
def get_register(
    address: Annotated[str, Field(description="Register address as a number ('11045', '40075'), a native register "
                                              "name ('Active_Power_Set') or a SunSpec point ('123.WMaxLimPct').")],
) -> dict:
    """Full documentation of one register: name, description, type, scale/unit, access, documented range and values,
    and where documented: applies_from_firmware, write_function (0x06 only or 0x06/0x10), effective_when,
    confirm_by (registers to read back) and persistence (retained, volatile, volatile_over_tcp, command).
    For SunSpec addresses: model, point, size, sf with its constant value, writable range, device notes.
    Documentation only; never touches a device."""
    return docs.get_register(address)


@mcp.tool()
def list_sunspec_models() -> dict:
    """The device's SunSpec model chain: base address 40000 ('SunS'), each model with ID address, length, point count
    and writable points, the END marker, transport and data conventions (word order, scale factors, not-implemented
    values). Documentation only; never touches a device."""
    return docs.list_sunspec_models()


@mcp.tool()
def get_sunspec_point(
    model: Annotated[int, Field(description="SunSpec model number of this device: 1, 123, 124, 103, 203, 120, 121, "
                                            "122 or 160.")],
    point: Annotated[str, Field(description="Point name, e.g. 'WMaxLimPct'. For model 160 modules use "
                                            "'module[2].DCW' or just 'DCW' for all modules.")],
) -> dict:
    """One SunSpec point in the SunSpec model layout (name, type, size, sf, units, access, mandatory, symbols) with
    the device object: address, offset, implemented (yes/conditional/no), writable and write_range (raw), write_kind
    (control, stored_setting, fixed_value), sf_address and sf_value, and the device notes on how to read or write it
    precisely. Documentation only; never touches a device."""
    return docs.get_sunspec_point(model, point)


@mcp.tool()
def list_recipes() -> dict:
    """List the closed-loop control recipes (id, title, interface, summary): EMS session with watchdog and
    heartbeat, active-power setpoint 11045, power limit 11320/11321, reactive power, Eco schedule, watchdog
    recovery, restart recovery, emergency stop, SunSpec gate, SunSpec active-power limit, SunSpec forced
    charge/discharge. Documentation only; never touches a device."""
    return docs.list_recipes()


@mcp.tool()
def get_recipe(
    task: Annotated[str, Field(description="Recipe id (e.g. 'native.ems_session_start') or a task description "
                                           "(e.g. 'forced charge sunspec').")],
) -> dict:
    """A closed-loop control recipe: preconditions (with read checks), ordered steps (op read/write, address,
    function code, raw value or value range, check), confirmation reads with expected values, failure and recovery,
    notes and the documentation sections it is based on. Values are raw register values; negative values are sent as
    16-bit two's complement. Documentation only; never touches a device."""
    return docs.get_recipe(task)


@mcp.tool()
def validate_write(
    address: Annotated[str, Field(description="Register address ('11321', '40075') or name / SunSpec point.")],
    value: Annotated[float, Field(description="Value to write: raw register value by default (e.g. 700 for 70.0 % on "
                                              "11321, -1000 for -10.00 kW on 11045).")],
    function_code: Annotated[str, Field(description="'0x06' (write single register) or '0x10' (write multiple).")] = "0x06",
    value_is_engineering: Annotated[bool, Field(description="True if value is in engineering units (kW, %, ...) and "
                                                            "must be converted with the register scale.")] = False,
) -> dict:
    """Check a planned write against the documentation WITHOUT writing anything: access (read-only points are
    rejected), documented range, scale, single-register requirement (0x06 only for 11300-11303, 11320-11324, 11330,
    11057, 11254, commands), SunSpec writable range, gate and veto preconditions, side effects (e.g. 0x5A5A on 12026)
    and the registers to read back afterwards. Returns verdict ok / ok_with_warnings / reject with reasons.
    Guidance only; this server never connects to a device and never writes registers."""
    return docs.validate_write(address, value, function_code, value_is_engineering)


@mcp.tool()
def generate_client_code(
    recipe_id: Annotated[str, Field(description="Recipe id from list_recipes, e.g. 'native.active_power_setpoint'.")],
    language: Annotated[Literal["python", "nodejs", "csharp", "go"], Field(description="Target language.")],
    transport: Annotated[Literal["tcp"], Field(description="Only Modbus TCP (port 502) is generated.")] = "tcp",
    host: Annotated[str, Field(description="Inverter IP address to put in the template.")] = "192.168.1.100",
    unit_id: Annotated[int, Field(ge=0, le=255, description="Modbus unit identifier (default 1).")] = 1,
) -> dict:
    """Generate a client program template for a recipe, using the libraries of the website examples: Python pymodbus
    (ModbusTcpClient), Node.js modbus-serial, C# NModbus, Go goburrow/modbus. The template checks the preconditions,
    performs the write sequence with the documented function codes, reads the confirmation registers and runs the
    keep-alive. Conditional steps are behind flags that default to off. The code writes to a live inverter when run:
    review it first. This server only returns text and never connects to a device."""
    return codegen.generate(recipe_id, language, transport, host, unit_id)


@mcp.tool()
def get_doc_section(
    page: Annotated[Literal["native", "sunspec"], Field(description="'native' = EMS protocol page, 'sunspec' = SunSpec "
                                                                     "interface page.")],
    section: Annotated[str, Field(description="Heading text or a fragment of it, e.g. 'Control gate', 'Scenarios', "
                                              "'Checking whether the active-power limit is applied'.")],
) -> dict:
    """Return one section of the published documentation as Markdown (from the heading to the next heading of the
    same level). If the heading is not found, returns the list of section headings. Documentation only; never
    touches a device."""
    return docs.get_doc_section(page, section)


# ------------------------------------------------------------------------------------------------ resources
def _resource(name: str, mime: str):
    uri = "wattsonic://docs/" + name

    @mcp.resource(uri, name=name, description="Wattsonic MATIC Modbus documentation: " + name, mime_type=mime)
    def _r() -> str:
        return docs.text(name)
    return _r


for _name, _mime in docs.DATA_FILES.items():
    _resource(_name, _mime)


# ------------------------------------------------------------------------------------------------ prompt
@mcp.prompt(name="integrate-matic-ems",
            description="Guide an EMS integration with a Wattsonic MATIC inverter step by step, precisely and "
                        "closed-loop.")
def integrate_matic_ems(goal: str = "monitor the inverter and dispatch battery power",
                        interface: str = "native") -> str:
    v = docs.version()
    return (
        "You are integrating an energy management system with a Wattsonic MATIC hybrid inverter over Modbus TCP "
        "(port 502, unit 1), ARM firmware %s or later (documentation edition %s). Goal: %s. Preferred interface: %s.\n\n"
        "Work only from the documentation tools of this server; do not assume registers or behaviour that the "
        "documentation does not state. This server never connects to a device.\n\n"
        "1. Identify: read 13021 (>= 1130), 13016 (10-14 = MATIC), 13034 (rated power) and 14030 (0x1018 on an "
        "EMS-native channel). Use get_register for each.\n"
        "2. Choose the interface: native EMS registers for full control (EMS session, 11045 setpoint, watchdog), or "
        "SunSpec (40000) for standard read-out and SunSpec controls behind the gate 11790. Use one writing "
        "connection.\n"
        "3. For every control, take the recipe (list_recipes / get_recipe) and keep its closed loop: preconditions, "
        "write sequence with the documented function codes (0x06 for single-register controls), confirmation reads, "
        "failure and recovery (watchdog, restart, release).\n"
        "4. Before writing any value, run validate_write and apply its preconditions and read-back registers; respect "
        "scale factors and signed values.\n"
        "5. Plan the keep-alive: native heartbeat 12026 within 11701 and well below 30 s; SunSpec enable re-writes at "
        "most RvrtTms/3.\n"
        "6. Plan for restarts: 11045 and 12002 read 0 after a restart; RAM-held values must be written again "
        "(see persistence in get_register); SunSpec controls are released.\n"
        "7. Generate code with generate_client_code and review it before it runs against a real inverter.\n"
        "Cite the documentation section (get_doc_section) for every rule you apply."
        % (v["firmware"], v["edition"], goal, interface)
    )


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()

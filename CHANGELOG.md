# Changelog

Versions follow the documentation data: each release states the inverter firmware it applies to.

## 0.1.2 — 2026-10-23
- Data: new register 19074 RS485_Port_Role (0 automatic / 1 reserved for an EMS / 2 heat pump / 3 boiler).
- Data: Modbus RTU on RS-485 explained for an EMS (unit ID, the search after a restart, how to reserve the port);
  on the SunSpec interface, RS-485 reads are listed without a condition.

## 0.1.1 — 2026-10-23
- `get_register` and `validate_write` accept the address as a number (e.g. 11045) as well as a string.

## 0.1.0 — 2026-10-23
- First public release. Data applies to Wattsonic MATIC ARM firmware M013V1130B01D05 and later.
- Tools: search_registers, get_register, list_sunspec_models, get_sunspec_point, list_recipes,
  get_recipe, validate_write, generate_client_code, get_doc_section; resources for the Markdown
  documentation and JSON data; prompt `integrate-matic-ems`.

# MATIC · EMS Modbus TCP/IP Interface Specification

> Machine-readable copy of https://modbus.wattsonic.com/Wattsonic_EMS_Modbus_Protocol.html (English). Applies to ARM firmware M013V1130B01D05 or later. Edition 2026-10-23. Generated from the published page; the HTML page is authoritative.

Register map and protocol reference for the Wattsonic MATIC residential hybrid inverter series (10–25 kW). Modbus TCP, port 502, unit ID 1.

## Overview

Modbus EMS protocol for the Wattsonic MATIC residential hybrid inverter series (10–25 kW). Connect over Modbus TCP (port 502, unit ID 1) for monitoring, settings, and EMS dispatch control.

- **Protocol**: `Modbus TCP/IP v2.0.20`
- **Transport**: `TCP · Port 502 · Unit ID 1`
- **Function Codes**: `FC03 / FC06 / FC16`
- **Product Series**: `Wattsonic MATIC · 10–25 kW`
- **Registers**: `178`
- **Firmware**: `ARM ≥ M013V1130B01D05`
- **Revision**: `2026-10-23`

> **Scope of this document**
>
> - This document describes the **EMS-channel register view**: Modbus TCP on port 502 (Ethernet or Wi-Fi) and Modbus RTU over RS-485. **Cloud channels see a different view for some addresses** (for example 10009 and 10685-10689). Read `14030`: it returns `0x1018` (4120) only on an EMS-native channel.
> - Applicable firmware: ARM **M013V1130B01D05** or later (`13021` ≥ 1130). Read it after connecting.
> - EMS commands take effect only while the EMS is in control: 11700 = 1, 11060 = 1, 12002 = 1, heartbeat on 12026 within the 11701 timeout. `12002` is not retained: write it again after every restart of the inverter.
> - Rated power depends on the model: read `13034` (Inverter_Rated_Power, 0.01 kW/LSB) after connecting and clamp setpoints to it. Do not hard-code 25 kW.

### Which interface should I use?

The inverter offers two Modbus register interfaces. Both are served on TCP port 502 (Ethernet and Wi-Fi) over the same connection; the register address selects the interface.

- **Native protocol (this document)**: Full control for an EMS: active-power setpoint (`11045`), battery dispatch and limits, grid-service settings and the communications watchdog session (`11700`-`11704`, heartbeat `12026`). Addresses 10000-19800.
- **SunSpec**: Standard read-out (measurements, nameplate, settings) and the SunSpec control models. Register bank at 40000, model chain 1 / 123 / 124 / 103 / 203 / 120 / 121 / 122 / 160. See the [SunSpec interface](sunspec.md) page.
- **Same connection**: Native and SunSpec requests can be mixed on one TCP connection. Keep each request within one range (10000-19800 or the SunSpec bank).
- **SunSpec writes**: To enable SunSpec control writes, set the installer write gate `11790` = `0x5355`, then write the SunSpec control points on port 502.
- **Arbitration**: Use one controller at a time. While the native EMS is in control (11700 = 1, 11060 = 1, 12002 = 1 with heartbeat) it has priority; SunSpec control commands take effect once the native EMS releases control.
- **Active-power limit via SunSpec**: A SunSpec active-power limit (model 123 WMaxLimPct) is applied only while the inverter runs EMS dispatch (mode 20), for example while a SunSpec forced charge/discharge command (model 124, negative OutWRte/InWRte) or native EMS external control (11045) is active. For a permanent export cap use Export_Limits (`11113`).

### Controlling the inverter: closed loop

1. **Preconditions.** Set the watchdog: `11701` timeout (s), `11702` timeout action, `11704` recovery mode, then `11700` = 1. Write `11060` = 1 and `12002` = 1. Confirm: `14044` = 1 (EMS control active) and `14031` = 1 (watchdog normal).
2. **Write sequence.** Write the heartbeat `12026` every 1–5 s (any value except 0x5A5A); this also keeps write control on port 502. Write setpoints with `0x06`: `11045` active power (+discharge / -charge, 0.01 kW, ±2500); optionally `11320` = 1 with `11321` as a discharge cap; reactive power: first `11300`, then `11302` (mode 1) or `11301` (mode 2).
3. **Confirm it is in force.** Read the Setpoint Shadow: `14250` requested and `14251` applied value of `11045`, `14253` rejection flag. Check the result at `10019` (inverter active power) and `10346` (battery power), and that `14031` stays 1.
4. **Failure and recovery.** Without a heartbeat for `11701` s the inverter enters SAFE_STATE (`14031` = 3, cause in `14042`) and applies the `11702` action; `14031` = 2 before that is the pre-warning. Recovery follows `11704` and needs `14044` = 1 (`11060` = 1 and `12002` = 1): AUTO returns with the next heartbeat; MANUAL_CONFIRM: with the heartbeat running, write `12001` = 1, the next heartbeat returns to normal; LATCH: set `11700` = 0, wait at least 2 s, write the heartbeat and within 5 s `12001` = 1, wait at least 2 s, then set `11700` = 1. After an inverter restart, write the heartbeat, `12002` = 1 and your setpoints again (`11045` reads 0 after a restart; if the EMS was in control before, the unit starts in SAFE_STATE with `14042` = 6 until this first write). Values written over TCP port 502 to `11068`, `11069`, `11300`–`11303`, `11320` and `11321` are held in RAM only: write them again after every restart.

### What changed in this edition

Edition 2026-10-23, applicable to ARM firmware M013V1130B01D05 or later (`13021` ≥ 1130). Customer-relevant changes compared with the previous edition, each with the action to take:

1. **Second-battery registers removed.** MATIC has one battery input. Removed: 10342, 10344, 10345, 10725, 10726, 10728, 10729, 10730, 10731, 10733, 10747, 11058, 11076, 11077, 14004, 14032 and alarm bits 14023:10/11. *Action:* stop reading or writing them; use the battery port 1 registers and `10346` for total battery power.
2. **Reactive power mode `11300` corrected.** Previously published: 1 = fixed power factor, 2 = fixed reactive power, 3 = Cosφ(P), 4 = Q(U). Correct: 1 = fixed reactive power (setpoint `11302`), 2 = fixed power factor (setpoint `11301`), 3 = Q(U), 4 = Cosφ(P). *Action:* remap the mode values your EMS writes; `11301` belongs to mode 2 and `11302` to mode 1.
3. **Battery BMS 32-bit values are high word first.** `10677`, `10679` and `10693` are U32_BE. Units running older firmware may deliver them low word first. *Action:* if your EMS also serves such units, read `13021` and swap the two words when it is below 1126.
4. **Active_Power_Set `11045`.** Values outside ±2500 (±25.00 kW, 0.01 kW) are clamped to ±2500 without an exception; the default is 0 and the value is not retained across a restart. *Action:* send the setpoint again after a restart; compare requested and applied values in `14250` / `14251`.
5. **Corrected defaults and ranges.** `11177` = 2500, `11300` = 1, `11301` = 0, `11303` = 10000 (range 0-10000), `11322` = 10, `11323` = 40, `11324` = 10, `11330` = 1; minimum of `11000` = 1990. *Action:* do not rely on the previously published defaults; write the values you need.
6. **Active_Power_Limit_Pct `11321`** applies only during EMS dispatch (mode 20): the EMS is in control and has written `11045`, or a SunSpec forced charge/discharge command is active. *Action:* for a feed-in cap that holds in every operating mode use Export_Limits `11113` (enable `11107`).
7. **Start-up after a restart.** If the EMS was in control before a restart, the inverter starts in SAFE_STATE (`14031` = 3, `14042` = 6) and applies the `11702` action until the EMS's first successful write. `12002` reads 0 after every restart. *Action:* after reconnecting, send the heartbeat (`12026`) and write `12002` = 1 again.
8. **Connections on port 502.** Port 502 accepts two simultaneous connections. One connection holds write control; writes from the other connection are answered with exception 0x06. Requests split across TCP segments are reassembled, back-to-back requests are answered in order, and a rejected `0x10` frame writes nothing. Port 5001 is a service port. *Action:* write from one connection only and treat exception 0x06 as "another client holds write control".
9. **Example code corrected.** Earlier examples wrote `12008` = 0x55AA as a "safety unlock" and `12007` = 1 as emergency stop. `12008` requests a reset of operating parameters and `12007` is not the emergency stop. *Action:* remove any write to `12007` or `12008` copied from the old examples; emergency stop is `12021` = 1, no unlock needed.
10. **Run_Mode_Set `11151`:** values 7-20 are reserved. *Action:* write only the documented values 0-6 and read the value back.
11. **Watchdog LATCH recovery order corrected.** With `14044` = 1: set `11700` = 0, wait at least 2 s, write the heartbeat `12026` and within 5 s `12001` = 1, wait at least 2 s, then set `11700` = 1 again. Writing `12001` while the watchdog is enabled does not clear the latch. *Action:* update your recovery sequence.
12. **New: SunSpec interface.** A SunSpec register bank is available on port 502 (from 40000); see the [SunSpec interface](sunspec.md) page. Native and SunSpec requests can share one connection.
13. **Eco schedule.** Eco mode is `11151` = 2 (value 4 selects a different time-of-use mode). Period type (`11192` and every third register after it): 0 = discharge, 1 = charge, 2 = self-consumption. The Eco SOC band `11262`-`11268` reads 0 after start-up and, when `11263` - `11262` > 4.00 %, takes precedence over the periods. *Action:* write 2 to `11151`, remap your period types, keep `11262`/`11263` at 0 for period control, and write band values again after every restart if you use the band.
14. **Sign of grid and meter power.** `10041` and `10765` are positive for export to the grid and negative for import. The sign-convention table and several examples previously stated the opposite. *Action:* check your sign handling; grid import = −`10765`.
15. **Heartbeat and watchdog.** Write the heartbeat `12026` every 1–5 s (any value except 0x5A5A); this also keeps write control on port 502. `14031` = 2 is the pre-warning, 3 the safe state. `11704` is accepted only while the watchdog is disabled. *Action:* shorten the heartbeat interval if it is longer, and write `11704` before `11700` = 1.
16. **Values held in RAM.** Written over TCP port 502, `11068`, `11069`, `11300`–`11303`, `11320` and `11321` change the working value only; after a restart they return to their last stored value. *Action:* write them again after every restart, together with `12002` = 1 and `11045`.
17. **Setpoint Shadow.** For `11060`, `14290` is the requested and `14291` the applied value. Reject codes are 0 (accepted), 1 (out of range), 3 (write refused) and 6 (other); for every setpoint except `11045` the shadow registers are updated by `0x06` writes only. *Action:* read the applied value from `14291` and write setpoints with `0x06`.
18. **Mode-specific SOC and power settings.** `11162`–`11165` and `11176`–`11179` are not used for control. *Action:* set the SOC limits with `11108`/`11109` and the grid limits with `11106`/`11112` and `11107`/`11113`.

- **Total Registers**: 178
- **Implemented**: 178

*Implemented*

> **Grid-service and EMS-control registers** (reactive power 11300–11303, active power % 11320–11324, frequency-watt 11330, communication watchdog and fail-safe 11700–11704 · 12021 · 12026 · 14031 · 14042 · 14044) are available on ARM firmware M013V1130B01D05 or later (`13021` ≥ 1130).

### Communication Parameters

- **Protocol**: Modbus TCP & RTU: same register map
- **TCP Interface**: Ethernet and Wi-Fi: port `502` (MBAP, no CRC)
- **Port 5001**: Reserved for the installer service tool (commissioning, local firmware update). EMS: use port 502.
- **mDNS / DNS-SD**: `_modbus._tcp` on port `502` (instance name = serial number)
- **RTU Interface**: RS-485: `115200` baud, 8N1 (unit ID + PDU + CRC-16, CRC low byte first)
- **Baud Rate**: `115200`, 8N1 (RTU only)
- **Unit ID**: `1`: configurable with register `11007`. On TCP the inverter also answers unit ID 0 and 255; requests to other unit IDs get no response.
- **Byte Order**: Big-Endian (MSB first)
- **Word Order**: High-word first (32-bit)
- **Poll Interval**: 1–5 s real-time data, 30–60 s energy counters
- **Applicable Models**: MATIC 10 / 12 / 15 / 20 / 25 kW (50 A)

### Supported Modbus Functions

- **0x03 Read Holding**: Read monitoring data and settings
- **0x06 Write Single**: Write control commands and settings
- **0x10 Write Multiple**: Write multi-register values (32-bit, strings)

### Register Address Map

| Address range | Content |
|---|---|
| 10000 - 10799 | **Real-Time Monitoring** RO: AC / PV / Battery / Grid / Meter / Energy |
| 11000 - 11249 | **System Settings** RW: Mode / SOC / TOU / Export Limit / Power |
| 11262 - 11268 | **Eco SOC Band** RW: minimum/maximum SOC, import/export power limits, grid charging, battery to grid, charge power |
| 12000 - 12006 | **Control Commands** W: On/Off / Fault Clear / Remote / Restart |
| 13000 - 13042 | **Device Information & Diagnostics** RO: SN / Model / Firmware / Protocol Version / Modbus diagnostics |
| 14000 - 14030 | **System Status** RO: Working Mode / State / On-Off Status |
| 14100 - 14199 | **Alarms & Faults** ALARM: Grid / Inverter / Battery / System |

### Sign Convention

| Parameter | Positive (+) | Negative (-) |
|---|---|---|
| Grid power (10041, 10765) | Export to grid | Import from grid |
| Battery Power | Discharge | Charge |
| Active Power Setpoint | Discharge | Charge from grid |
| Reactive Power | Leading (capacitive) | Lagging (inductive) |

### EMS Integration Notes

1. Enable EMS mode by writing `1` to register `11060` (EMS_Switch_Set) before sending control commands.
2. Set `Remote_Mode (12002) = 1` to enable remote control.
3. Apply the scale factor specified for each register. Example: register value `2500` with scale factor 0.01 kW = `25.00 kW`.
4. SOC values use scale factor 0.01 %. Example: register value `8000` = `80.00 %`.
5. TOU time values are given in minutes after midnight (0–1440). Example: `480` = 08:00, `1080` = 18:00.
6. **Meter Current Scale:** Meter current registers (10758-10760) use scale `0.1 A` while inverter/grid currents use `0.01 A`. Handle both scale factors in your parser.
7. Read the ARM firmware version `13021` after connecting; this document applies when it reads 1130 or higher.
8. Enable the communication watchdog `11700` and write the heartbeat `12026` every 1–5 s to keep the fail-safe function active.

### Reference Standards

- **SunSpec Alliance**: the inverter provides a SunSpec Modbus interface on port 502 (register bank at 40000, models 1 / 123 / 124 / 103 / 203 / 120 / 121 / 122 / 160), described on the [SunSpec interface](sunspec.md) page. Register names in this document follow SunSpec naming where practical.
- **IEC 61850**: some register descriptions use logical node names from IEC 61850-7-4 and IEC 61850-7-420 Ed.2 (MMXU, MMDC, ZBAT) for readability. The inverter does not provide an IEC 61850 interface (MMS, GOOSE, SV or SCL/ICD files).
- **EN 50549-1:2019**: European LV grid code for generating plants. The inverter implements LFSM-O / LFSM-U / FRT and the reconnection ramp according to the configured grid code. While the EMS is in control, the EMS-facing registers 11320-11324 (active power % and ramps) and 11330 (P(f)) apply; otherwise the grid-code settings apply.
- **VDE-AR-N 4105:2018-11**: German LV grid code. The inverter implements Cosφ(P), P(f) droop and ramp rates per §5.7 through the grid-code settings; registers 11300–11303 (reactive power), 11320–11324 and 11330 apply while the EMS is in control. Rules for controllable consumers are set out in §14a **EnWG** and the related BNetzA determinations.
- **SG Ready**: BWP e.V. "Technical Interface Specifications for SG Ready" v1.1 (2025-05-01) defines a three-state dry-contact heat-pump interface (blocked / normal / switch-on recommended). Register 11355 `Heatpump_Hint_Mode` drives the inverter's dry-contact relay outputs when `11380 DC_Mode = 1` (SG Ready mode); see registers `11380–11399` (configuration) and `14126–14139` (status).

## Data Types

Data formats used in the register map. All multi-byte values are transmitted in big-endian byte order.

> **Important: use function code 0x04 for read-only registers only**
>
> Function code `0x04` (Read Input Registers) is served **only** for the read-only register ranges (`10xxx`, `13xxx`, `14xxx`, `17xxx`).
>
> Issuing `0x04` against a **read/write** register (e.g. `11045`, `11113`, `12000`, `15000`) causes the device to return a **malformed response**: a 6-byte MBAP header with `Length = 0x0000` and no PDU, which standard Modbus client libraries report as a timeout or parse error. Use 0x03 for these registers.
>
> **Use `0x03` (Read Holding Registers) for all registers.** Do not rely on `0x04`.

> **32-bit registers are high word first, including the battery-BMS energies and alarm**
>
> Every 32-bit quantity occupies two consecutive registers with the **high word at the lower address** (`U32_BE`). This includes `10677` BMS_Bat1_Charge_Energy, `10679` BMS_Bat1_Discharge_Energy and `10693` BMS_Bat1_Alarm.
>
> Units running older firmware may deliver these three pairs low word first. If your EMS also serves such units, read `13021` after connecting, and swap the two words of these three registers if the version is below 1126.

> **Important: keep each read request within one address block**
>
> The register map is organized as **200-register blocks**. If one read request runs past the end of a block, the device **silently returns 0** for the out-of-range part instead of an exception, whereas reading the *same* address on its own correctly returns exception `0x02`.
>
> A client that polls in large chunks will therefore receive **zeros that look like real measurements** (e.g. "0 kW").
>
> **Block start addresses:** read-only `10000`, `10336`, `10597`, `10797`, `13000`, `14000`, `14200`, `17000`, `17200`; read/write `11000`, `11200`, `11400`, `11600`, `12000`, `15000`, `15200`, `16000`, `16200`, `18000`, `18200`, `18400`, `19000`, `19200`, `19400`, `19600`. Each block spans 200 registers (e.g. `17200-17399`).
>
> **Keep every request inside one block**, and read only the addresses listed in this document.

> **Connections on port 502: one writer at a time**
>
> Port `502` on Ethernet accepts **two** Modbus TCP connections at the same time. Every connection may read. **Only one connection holds write control:** the first connection that sends a write (`0x06` / `0x10`) becomes the writer. A write from any other connection is answered with exception `0x06` (Server Device Busy) and is not executed. Write control is released when the writer closes its connection or has not executed a write for 30 s; a new connection from the writer's own IP address takes over at once (for example after an EMS restart).
>
> A new connection never disconnects the connection that holds write control. When both connections are in use, an idle connection or the one without write control is replaced.
>
> A monitoring client can be given a reserved read-only connection: write its IPv4 address to `19024` (first two octets, first octet in the high byte) and `19025` (last two octets). That address is admitted to the second connection only and never takes write control.
>
> Each connection is handled as a byte stream: a request split across TCP segments is reassembled, and several requests may be sent back-to-back without waiting for each reply (pipelining). Replies are returned in request order.
>
> Port `502` on Wi-Fi follows the same rules with its own writer. RS485 (Modbus RTU) serves the same register map for an EMS.
>
> Connect the EMS to port `502`. Port `5001` is reserved for the installer service tool (commissioning, local firmware update).
>
> The inverter announces the Modbus service via mDNS / DNS-SD as `_modbus._tcp` on port 502 (instance name = serial number).

> **Important: write multiple registers only within documented, contiguous address ranges**
>
> Write only to the addresses documented here, and keep every `0x10` (Write Multiple Registers) request entirely inside a documented, contiguous run of addresses. Do not write a whole block back just because you read a whole block.
>
> Some undocumented addresses inside the same blocks are **command triggers**. They behave differently from ordinary registers in ways that make blind block writes dangerous:
>
> - They fire on **any** written value - including `0`. No value can be written to them without effect.
> - A **rejected** `0x10` frame has no effect: the device checks every register of the frame first and, if any register is refused, returns the exception code without writing any value or executing any command.
> - Their effects include resetting operating parameters and network configuration, which persist across power cycles.
>
> **Practical rule:** use `0x06` for every control register; reserve `0x10` for contiguous runs of documented data registers; never issue a write request derived from a block read.

> **A timeout does not mean the write failed: read the register back before retrying**
>
> A write request whose **response never reached the client** had nevertheless **been executed by the inverter**. The client only lost the acknowledgement, not the write.
>
> This happens whenever a connection drops while a response is in flight (network interruption, Wi-Fi roaming, or an idle connection that was replaced by a new client).
>
> **On timeout: reconnect, read the register back, and only then decide whether to resend.** Do not assume "no response" means "not written".
>
> **Whether a retry is safe depends on the register type:**
>
> - **Ordinary setpoints and limits** assign the value you send. Writing twice leaves the same state as writing once, so a retry is harmless.
> - **Command triggers act on the write itself, not on the value.** For those, a retry is a second command. Combined with the note above about undocumented addresses, this is another reason never to replay a block write blindly.
>
> If your Modbus client retries automatically, apply the retry policy per register type, not globally.

| Type | Length | Description | Example | Bytes |
|---|---|---|---|---|
| VALUE_U16 | 2 bytes | Unsigned 16-bit integer, Big-Endian | 65244 | FE DC |
| VALUE_S16 | 2 bytes | Signed 16-bit integer, Big-Endian | -292 | FE DC |
| VALUE_U32_BE | 4 bytes | Unsigned 32-bit, Big-Endian (2 registers, high word first) | 4275878552 | FE DC BA 98 |
| VALUE_S32_BE | 4 bytes | Signed 32-bit, Big-Endian (2 registers, high word first) | -19088744 | FE DC BA 98 |
| ASCII_STRING32 | 32 bytes | ASCII string, 32 bytes (16 registers) | ABC123... | 41 42 43 ... |
| BIT_BOOLEAN | 1 bit | Boolean flag within a 16-bit register (bit 0-15) | bit0=1 | 00 01 |

### Modbus Protocol Compliance (SPEC)

| Parameter | Value | Notes |
|---|---|---|
| Supported Functions | 0x03, 0x06, 0x10 | Read every register with 0x03 (Read Holding Registers). 0x04 (Read Input Registers) is supported for read-only registers only; do not use it for read/write registers. Write the control registers 11300–11303 and 11320–11321 with 0x06 (Write Single Register), one register per request. |
| Max Registers per Read | 125 | Maximum 125 registers (250 bytes of data) per request, as defined in the Modbus Application Protocol Specification. Larger requests return exception 02. |
| Inter-Frame Silence (RTU) | 3.5 chars (~4ms @115200) | Minimum gap between frames. Frames arriving faster may be discarded. |
| Min Poll Interval | 200 ms | Leave at least 200 ms between consecutive requests on one connection. |
| Write Validation | Firmware-enforced | A value outside the range documented for the register is answered with exception 03 (Illegal Data Value) and not written. Exception: `11045` accepts any value and clamps it to ±2500. |

### Modbus Exception Codes (ERROR)

| Code | Name | Trigger Conditions |
|---|---|---|
| 01 | Illegal Function | Write function code (0x06 or 0x10) sent to a read-only register (10xxx, 13xxx, 14xxx). |
| 02 | Illegal Data Address | Register address does not exist or falls in a reserved/gap range. Read request spans beyond valid address block. |
| 03 | Illegal Data Value | Written value outside the documented range; watchdog timeout below 10 s; pre-warning time not shorter than the timeout (Prewarn_Sec ≥ Timeout). |
| 04 | Server Device Failure | Internal error during register access. Retry after 1 s. |
| 06 | Server Device Busy | Write from a connection that does not hold write control on port 502: another connection has executed a write within the last 30 s, or this is the reserved read-only connection (19024/19025). The write is not executed; write from one connection only. |

### Recommended Polling Groups (OPTIMIZATION)

| Group | Address Range | Registers | Interval | Purpose |
|---|---|---|---|---|
| 1. AC & Grid | 10000 - 10064 | 65 | 1–2 s | Inverter output, grid, backup power (single read) |
| 2a. Battery DC Power | 10337 - 10346 | 10 | 2–5 s | Battery converter V/I/P (use 10346 for total) |
| 2b. PV / DC | 10348 - 10368 | 21 | 2–5 s | PV strings + total power (10367) + DC bus |
| 3. Battery Port 1 | 10671 - 10697 | 27 | 2–5 s | SOC, voltage, current, energy, alarms |
| 5. Meter | 10752 - 10783 | 32 | 1–2 s | External meter data |
| 6. Energy | 10785 - 10799 | 15 | 30–60 s | Energy counters (daily + lifetime) |
| 6a. Load & KPIs | 10800 - 10812 | 13 | 1–2 s | Load power + system KPIs |
| 7. Status | 14000 - 14149 | 150 | 2–5 s | Operating state, alarms, operating limits, grid code, DC output, energy-storage dispatch |
| 8. Settings Read-Back | 11000 - 11006 | 7 | 60 s | RTC; settings read-back after each change |
| 10. Diesel | 10077, 10096, 14011 | 3 | 2–5 s | Diesel generator frequency, power, working status |
| 11. MATIC On-Grid Load | 10074 - 10076 | 3 | 2–5 s | On-grid load power per phase |

## Monitoring Registers

Real-time measurements. All registers are read-only; read them with function code 0x03. Poll every 1–5 s.

*Implemented (98 registers)*

### Monitoring Registers (READ-ONLY)

| Status | Register | Name | Description | Type | Unit | Scale | Notes |
|---|---|---|---|---|---|---|---|
| **1. AC Inverter Output** |  |  |  |  |  |  |  |
| Implemented | 10000 | Inverter_Frequency | Inverter Output Frequency | S16 | Hz | 0.01 |  |
| Implemented | 10001 | Inverter_Voltage_A | Phase A Inverter Voltage (RMS) | S16 | V | 0.1 |  |
| Implemented | 10002 | Inverter_Voltage_B | Phase B Inverter Voltage (RMS) | S16 | V | 0.1 |  |
| Implemented | 10003 | Inverter_Voltage_C | Phase C Inverter Voltage (RMS) | S16 | V | 0.1 |  |
| Implemented | 10004 | Inverter_Current_A | Phase A Inverter Current (RMS) | S16 | A | 0.01 |  |
| Implemented | 10005 | Inverter_Current_B | Phase B Inverter Current (RMS) | S16 | A | 0.01 |  |
| Implemented | 10006 | Inverter_Current_C | Phase C Inverter Current (RMS) | S16 | A | 0.01 |  |
| Implemented | 10019 | Inverter_Active_Power_Total | Total Active Power | S16 | kW | 0.01 | + output (discharge/export) / − input (charge) |
| Implemented | 10020 | Inverter_Reactive_Power_Total | Total Reactive Power | S16 | kVar | 0.01 |  |
| Implemented | 10021 | Inverter_Apparent_Power_Total | Total Apparent Power | S16 | kVA | 0.01 |  |
| Implemented | 10009 | Inverter_Power_Factor | Inverter Displacement Power Factor | S16 |  | 0.001 | −1.000 to +1.000. Use this value to confirm that reactive power control is in effect. |
| **2. AC Grid Side** |  |  |  |  |  |  |  |
| Implemented | 10022 | Grid_Frequency | Grid Frequency at PCC | S16 | Hz | 0.01 |  |
| Implemented | 10023 | Grid_Voltage_A | Phase A Grid Voltage (RMS) | S16 | V | 0.1 |  |
| Implemented | 10024 | Grid_Voltage_B | Phase B Grid Voltage (RMS) | S16 | V | 0.1 |  |
| Implemented | 10025 | Grid_Voltage_C | Phase C Grid Voltage (RMS) | S16 | V | 0.1 |  |
| Implemented | 10026 | Grid_Current_A | Phase A Grid Current (RMS) | S16 | A | 0.01 |  |
| Implemented | 10027 | Grid_Current_B | Phase B Grid Current (RMS) | S16 | A | 0.01 |  |
| Implemented | 10028 | Grid_Current_C | Phase C Grid Current (RMS) | S16 | A | 0.01 |  |
| Implemented | 10041 | Grid_Active_Power_Total | Total Grid Active Power | S16 | kW | 0.01 | +export / -import |
| Implemented | 10042 | Grid_Reactive_Power_Total | Total Grid Reactive Power | S16 | kVar | 0.01 |  |
| Implemented | 10043 | Grid_Apparent_Power_Total | Total Grid Apparent Power | S16 | kVA | 0.01 |  |
| **3. Backup Load Output** |  |  |  |  |  |  |  |
| Implemented | 10062 | Backup_Active_Power_Total | Total Backup Active Power | S16 | kW | 0.01 |  |
| Implemented | 10063 | Backup_Reactive_Power_Total | Total Backup Reactive Power | S16 | kVar | 0.01 |  |
| Implemented | 10064 | Backup_Apparent_Power_Total | Total Backup Apparent Power | S16 | kVA | 0.01 |  |
| **3a. On-Grid Load Output** |  |  |  |  |  |  |  |
| Implemented | 10074 | Ongrid_Active_Power_Total | On-Grid Load Total Active Power | S16 | kW | 0.01 |  |
| Implemented | 10075 | Ongrid_Reactive_Power_Total | On-Grid Load Total Reactive Power | S16 | kVar | 0.01 |  |
| Implemented | 10076 | Ongrid_Apparent_Power_Total | On-Grid Load Total Apparent Power | S16 | kVA | 0.01 |  |
| **3c. Battery DC Power (Converter Level, 10337–10346)** |  |  |  |  |  |  |  |
| **Battery DC-DC Converter Measurements**: DC bus voltage, current and power at the battery converter stage. The BMS registers (10671 onwards) report pack-level data from the battery management system. Use **Bat_Power_Total (10346)** for real-time battery power instead of calculating V×I from BMS registers. |  |  |  |  |  |  |  |
| Implemented | 10337 | Bat1_Voltage | Battery Port 1 DC Bus Voltage | S16 | V | 0.1 |  |
| Implemented | 10339 | Bat1_Current | Battery Port 1 DC Bus Current | S16 | A | 0.01 | +discharge / −charge |
| Implemented | 10340 | Bat1_Power | Battery Port 1 DC Power | S16 | kW | 0.01 | +discharge / −charge |
| Implemented | 10346 | Bat_Power_Total | Total Battery DC Power | S16 | kW | 0.01 | +discharge / −charge. **Use this for EMS battery power monitoring.** |
| **4. PV / DC Input** |  |  |  |  |  |  |  |
| **PV block layout.** PV1 voltage / current / power at 10348-10350; PV2 to PV5 follow, each preceded by one register that is not used by an EMS. `PV_Total_Power` is at **10367** (end of the block). |  |  |  |  |  |  |  |
| Implemented | 10348 | PV1_Voltage | MPPT 1 DC Input Voltage | S16 | V | 0.1 |  |
| Implemented | 10349 | PV1_Current | MPPT 1 DC Input Current | S16 | A | 0.01 |  |
| Implemented | 10350 | PV1_Power | MPPT 1 DC Input Power | S16 | kW | 0.01 |  |
| Implemented | 10352 | PV2_Voltage | MPPT 2 DC Input Voltage | S16 | V | 0.1 |  |
| Implemented | 10353 | PV2_Current | MPPT 2 DC Input Current | S16 | A | 0.01 |  |
| Implemented | 10354 | PV2_Power | MPPT 2 DC Input Power | S16 | kW | 0.01 |  |
| Implemented | 10356 | PV3_Voltage | MPPT 3 DC Input Voltage | S16 | V | 0.1 |  |
| Implemented | 10357 | PV3_Current | MPPT 3 DC Input Current | S16 | A | 0.01 |  |
| Implemented | 10358 | PV3_Power | MPPT 3 DC Input Power | S16 | kW | 0.01 |  |
| Implemented | 10360 | PV4_Voltage | MPPT 4 DC Input Voltage | S16 | V | 0.1 |  |
| Implemented | 10361 | PV4_Current | MPPT 4 DC Input Current | S16 | A | 0.01 |  |
| Implemented | 10362 | PV4_Power | MPPT 4 DC Input Power | S16 | kW | 0.01 |  |
| Implemented | 10364 | PV5_Voltage | MPPT 5 DC Input Voltage | S16 | V | 0.1 | Not available on all models |
| Implemented | 10365 | PV5_Current | MPPT 5 DC Input Current | S16 | A | 0.01 | Not available on all models |
| Implemented | 10366 | PV5_Power | MPPT 5 DC Input Power | S16 | kW | 0.01 | Not available on all models |
| Implemented | 10367 | PV_Total_Power | Total PV DC Input Power | S16 | kW | 0.01 | **Primary EMS register for PV generation.** Sum of all active MPPT trackers. |
| Implemented | 10368 | DC_Bus_Voltage | DC Bus Average Voltage | S16 | V | 0.1 | Internal DC bus voltage. Useful for system health monitoring. |
| **5. Battery (Pack Level)** |  |  |  |  |  |  |  |
| Implemented | 10671 | BMS_Bat1_SOC | Battery Port 1 State of Charge | U16 | % | 0.01 | 0–10000 (0–100.00 %). Use the value only when it lies in this range. |
| Implemented | 10672 | BMS_Bat1_SOH | Battery Port 1 State of Health | U16 | % | 0.01 | 0-10000 (0-100.00%) |
| Implemented | 10674 | BMS_Bat1_Voltage | Battery Port 1 DC Voltage | U16 | V | 0.1 |  |
| Implemented | 10675 | BMS_Bat1_Current | Battery Port 1 DC Current | S16 | A | 0.1 | +discharge / -charge |
| Implemented | 10676 | BMS_Bat1_Temperature | Battery Port 1 Temperature | S16 | °C | 0.1 |  |
| Implemented | 10677 | BMS_Bat1_Charge_Energy | Battery Port 1 Total Charge Energy | U32_BE | kWh | 0.1 | 2 registers, high word first. |
| Implemented | 10679 | BMS_Bat1_Discharge_Energy | Battery Port 1 Total Discharge Energy | U32_BE | kWh | 0.1 | 2 registers, high word first. |
| Implemented | 10685 | BMS_Bat1_Power | Battery Port 1 Active Power | S16 | kW | 0.01 | +discharge / -charge. Direct readout avoids V×I calculation errors. |
| Implemented | 10686 | BMS_Bat1_Max_Charge_Power | BMS Allowed Max Charge Power | U16 | kW | 0.01 | RO. Maximum charge power permitted by the BMS; may differ from the EMS setting depending on temperature and SOC. |
| Implemented | 10687 | BMS_Bat1_Max_Discharge_Power | BMS Allowed Max Discharge Power | U16 | kW | 0.01 | RO. Maximum discharge power permitted by the BMS; may be lower at low temperature or SOC. |
| Implemented | 10688 | BMS_Bat1_Rated_Capacity | Battery Port 1 Rated Capacity | U16 | kWh | 0.01 | RO. Total rated capacity, for example for dispatch planning. |
| Implemented | 10689 | BMS_Bat1_Available_Energy | Battery Port 1 Available Energy | U16 | kWh | 0.01 | RO. Remaining usable energy (SOC × usable capacity). |
| Implemented | 10693 | BMS_Bat1_Alarm | Battery Port 1 Alarm Code | U32_BE |  | 1 | Bitmap, 2 registers, high word first. |
|  |  |  |  |  |  |  |  |
| **Scale factors differ by register**: meter current registers `10758-10760` use **0.1 A**, inverter / grid current registers `10026-10028` use **0.01 A** (raw 250 = 25.0 A on `Meter_Current_A`, 2.50 A on `Grid_Current_A`). Meter voltage is 0.1 V like inverter / grid voltage; meter power is 0.01 kW like inverter power. Select the scale factor by register address, not by register category. |  |  |  |  |  |  |  |
| Implemented | 10752 | Meter_Voltage_A | Meter Voltage Phase A (RMS) | S16 | V | 0.1 |  |
| Implemented | 10753 | Meter_Voltage_B | Meter Voltage Phase B (RMS) | S16 | V | 0.1 |  |
| Implemented | 10754 | Meter_Voltage_C | Meter Voltage Phase C (RMS) | S16 | V | 0.1 |  |
| Implemented | 10758 | Meter_Current_A | Meter Current Phase A (RMS) | S16 | A | 0.1 |  |
| Implemented | 10759 | Meter_Current_B | Meter Current Phase B (RMS) | S16 | A | 0.1 |  |
| Implemented | 10760 | Meter_Current_C | Meter Current Phase C (RMS) | S16 | A | 0.1 |  |
| Implemented | 10765 | Meter_Active_Power_Total | Meter Total Active Power | S16 | kW | 0.01 | +export / -import |
| Implemented | 10769 | Meter_Reactive_Power_Total | Meter Total Reactive Power | S16 | kVar | 0.01 |  |
| Implemented | 10777 | Meter_Power_Factor_Total | Meter Total Power Factor | S16 |  | 0.01 | -1.00 to 1.00 |
| Implemented | 10778 | Meter_Frequency | Grid Frequency at PCC | S16 | Hz | 0.01 |  |
| Implemented | 10781 | Meter_Energy_Import | Total Import Energy | U32_BE | kWh | 0.1 | 2 registers |
| Implemented | 10783 | Meter_Energy_Export | Total Export Energy | U32_BE | kWh | 0.1 | 2 registers |
| **7. Energy Counters** |  |  |  |  |  |  |  |
| Implemented | 10785 | PV_To_Grid_Energy_Today | Daily PV-to-Grid Energy | U16 | kWh | 0.1 |  |
| Implemented | 10786 | PV_To_Load_Energy_Today | Daily PV-to-Load Energy | S16 | kWh | 0.1 | Signed 16-bit value; maximum 3276.7 kWh per day. |
| Implemented | 10787 | Battery_To_Grid_Today | Daily Battery-to-Grid Energy | S16 | kWh | 0.1 | Signed 16-bit value; maximum 3276.7 kWh per day. |
| Implemented | 10788 | Battery_To_Load_Energy_Today | Daily Battery-to-Load Energy | U16 | kWh | 0.1 |  |
| Implemented | 10789 | PV_To_Grid_Energy_Total | Total PV to Grid Energy | U32_BE | kWh | 0.1 | 2 registers |
| Implemented | 10791 | PV_To_Load_Energy_Total | Total PV to Load Energy | U32_BE | kWh | 0.1 | 2 registers |
| Implemented | 10793 | Battery_To_Grid_Total | Total Battery to Grid Energy | U32_BE | kWh | 0.1 | 2 registers |
| Implemented | 10795 | Battery_To_Load_Energy_Total | Total Battery to Load Energy | U32_BE | kWh | 0.1 | 2 registers |
|  |  |  |  |  |  |  |  |

## Settings Registers

Configurable settings. Write with function code 0x06 (Write Single Register) or 0x10 (Write Multiple Registers); the control registers 11300–11303 and 11320–11321 accept 0x06 only. Changes take effect immediately unless otherwise noted.

*Implemented (60 registers)*

### Settings Registers (READ/WRITE)

| Status | Register | Name | Description | Type | Unit | Scale | Default | Min | Max | Values / Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **1. System Time** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11000 | RTC_Year_Set | RTC Year | S16 |  | 1 | 0 | 1990 | 2099 |  |
| Implemented | 11001 | RTC_Month_Set | RTC Month | S16 |  | 1 | 0 | 1 | 12 |  |
| Implemented | 11002 | RTC_Day_Set | RTC Day | S16 |  | 1 | 0 | 1 | 31 |  |
| Implemented | 11003 | RTC_Hour_Set | RTC Hour | S16 |  | 1 | 0 | 0 | 23 |  |
| Implemented | 11004 | RTC_Minute_Set | RTC Minute | S16 |  | 1 | 0 | 0 | 59 |  |
| Implemented | 11005 | RTC_Second_Set | RTC Second | S16 |  | 1 | 0 | 0 | 59 |  |
| Implemented | 11006 | Time_Zone_Set | Time Zone | S16 |  | 1 | 1 | 1 | 650 | Lookup table: 1=UTC-12..., 13=UTC+0 (GMT), 14=UTC+1 (CET), 15=UTC+2 (EET)..., 25=UTC+12. Half-hour zones: 530=UTC+5:30 (IST), 545=UTC+5:45 (NPT).<br>*Important: set the correct time zone for TOU schedules.* |
| **2. EMS Control Enable** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11060 | EMS_Switch_Set | External EMS Dispatch Enable | S16 |  | 1 | 0 | 0 | 1 | 0: Disabled 1: Enabled<br>*Must be set to 1 for EMS commands to take effect.* |
| **3. Active Power Control** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11045 | Active_Power_Set | Active Power Setpoint (Total) | S16 | kW | 0.01 | 0 | -2500 | 2500 | Positive = discharge, negative = charge from grid. Values outside -2500..+2500 are accepted and clamped to +/-2500 (25.00 kW); requested and applied values are reported in the Setpoint Shadow (14250 / 14251). The inverter also limits the setpoint to its rated power: read `13034` after connecting. The setpoint is executed only while the EMS is in control (11700 = 1, 11060 = 1, 12002 = 1, heartbeat on 12026). After a restart it reads 0: write the setpoint again once the EMS is back in control. |
| **4. Working Mode** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11151 | Run_Mode_Set | Operating Mode | S16 |  | 1 | 0 | 0 | 6 | 0: General (Self-Consumption)<br>1: Grid Balancing<br>2: Eco (time schedule 11190–11249)<br>3: UPS / Backup Priority<br>4: TOU (Time-of-Use)<br>5: Forecast<br>6: Off-Grid<br>*Write only the values 0-6 listed above; 7-20 are reserved.* |
| **5. SOC Limits** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11108 | Grid_tied_SOC_MIN | On-Grid Minimum SOC | S16 | % | 0.01 | 1000 | 0 | 10000 | Do not discharge below this SOC |
| Implemented | 11109 | Grid_tied_SOC_MAX | On-Grid Maximum SOC | S16 | % | 0.01 | 10000 | 0 | 10000 | Do not charge above this SOC |
| Implemented | 11110 | Off_grid_SOC_MIN | Off-Grid Minimum SOC | S16 | % | 0.01 | 1000 | 0 | 10000 | Backup reserve SOC |
| Implemented | 11111 | Off_grid_SOC_MAX | Off-Grid Maximum SOC | S16 | % | 0.01 | 10000 | 0 | 10000 |  |
| Implemented | 11162 | Gen_Mode_Min_SOC_Set | General Mode Min SOC | S16 | % | 0.01 | 1000 | 0 | 10000 | Not used for control. Set the SOC limits with `11108` / `11109`. |
| Implemented | 11163 | Gen_Mode_Max_SOC_Set | General Mode Max SOC | S16 | % | 0.01 | 8000 | 0 | 10000 | Not used for control. Set the SOC limits with `11108` / `11109`. |
| Implemented | 11176 | Grid_Bal_Min_SOC_Set | Grid Balancing Mode Min SOC | S16 | % | 0.01 | 1000 | 0 | 10000 | Not used for control. Set the SOC limits with `11108` / `11109`. |
| Implemented | 11177 | Grid_Bal_Max_SOC_Set | Grid Balancing Mode Max SOC | S16 | % | 0.01 | 2500 | 0 | 10000 | Not used for control. Set the SOC limits with `11108` / `11109`. |
| **6. Grid Export / Import Limits** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11106 | Import_Limits_Switch | Import Power Limit Enable | S16 |  | 1 | 0 | 0 | 1 | 0: Disabled 1: Enabled |
| Implemented | 11107 | Export_Limits_Switch | Export Power Limit Enable | S16 |  | 1 | 0 | 0 | 1 | 0: Disabled 1: Enabled |
| Implemented | 11112 | Import_Limits | Max Import Power | S16 | kW | 0.01 | 2500 | 0 | 5000 | ***Range:** Maximum 2500 (25 kW). Read `13034` (Inverter_Rated_Power) and limit the value accordingly.* |
| Implemented | 11113 | Export_Limits | Max Export Power | S16 | kW | 0.01 | 2500 | 0 | 2500 | Set to 0 for zero-export.<br>***Range:** Maximum 2500 (25 kW). Read `13034` (Inverter_Rated_Power) and limit the value accordingly.* |
| Implemented | 11164 | Gen_Mode_Max_Buy_Power | General Mode Maximum Import Power | S16 | kW | 0.01 | 2500 | 0 | 5000 | Not used for control. Set import and export limits with `11106` / `11112` and `11107` / `11113`. |
| Implemented | 11165 | Gen_Mode_Max_Sell_Power | General Mode Maximum Export Power | S16 | kW | 0.01 | 2500 | 0 | 5000 | Not used for control. Set import and export limits with `11106` / `11112` and `11107` / `11113`. |
| Implemented | 11178 | Grid_Bal_Max_Buy_Power_Set | Grid Balancing Mode Max Import | S16 | kW | 0.01 | 2500 | 0 | 5000 | Not used for control. Set import and export limits with `11106` / `11112` and `11107` / `11113`. |
| Implemented | 11179 | Grid_Bal_Max_Sell_Power_Set | Grid Balancing Mode Max Export | S16 | kW | 0.01 | 2500 | 0 | 5000 | Not used for control. Set import and export limits with `11106` / `11112` and `11107` / `11113`. |
| **7. Battery Power Limits** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11057 | Bat_1_Enable | Battery Port 1 Enable | S16 |  | 1 | 1 | 0 | 1 | 0: Disabled 1: Enabled |
| Implemented | 11068 | Bat1_Max_Chg_Power | Battery Port 1 Max Charge Power | S16 | kW | 0.01 | 2500 | 0 | 3200 | Over TCP port 502 (Ethernet or Wi-Fi) a write changes the working value only: after a restart the register returns to its last stored value. Write it again after every restart. |
| Implemented | 11069 | Bat1_Max_Dchg_Power | Battery Port 1 Max Discharge Power | S16 | kW | 0.01 | 2500 | 0 | 3200 | Over TCP port 502 (Ethernet or Wi-Fi) a write changes the working value only: after a restart the register returns to its last stored value. Write it again after every restart. |
| **8. Eco Schedule (Economic Mode, 11190–11249)** |  |  |  |  |  |  |  |  |  |  |
| Eco schedule (`11151` = 2): up to 20 periods, 3 registers each (11190–11249): start and end in minutes after midnight (0–1440, local inverter time; a period applies while start ≤ time < end) and the period type: 0 = discharge, 1 = charge, 2 = self-consumption. Outside all periods the inverter runs self-consumption. Weekdays: `11254` (bit0 = Monday to bit6 = Sunday). Write each register with function code 0x06 or a block of whole periods with 0x10, then read the block back. |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11190 | Eco_Start1_Set | Eco Period 1 Start Time | S16 | min | 1 | 0 | 0 | 1440 |  |
| Implemented | 11191 | Eco_End1_Set | Eco Period 1 End Time | S16 | min | 1 | 0 | 0 | 1440 |  |
| Implemented | 11192 | Eco_Peak_Sel1_Set | Eco Period 1 Type | S16 |  | 1 | 0 | 0 | 2 | 0: Discharge 1: Charge 2: Self-consumption |
| Implemented | 11193–11195 | Eco_Period2 | Eco Period 2 (Start/End/Type) | S16 | min | 1 | 0 | 0 | 1440 | Same structure as Period 1 |
| Implemented | 11196–11198 | Eco_Period3 | Eco Period 3 (Start/End/Type) | S16 | min | 1 | 0 | 0 | 1440 |  |
| Implemented | 11199–11201 | Eco_Period4 | Eco Period 4 (Start/End/Type) | S16 | min | 1 | 0 | 0 | 1440 |  |
| Implemented | 11202–11204 | Eco_Period5 | Eco Period 5 (Start/End/Type) | S16 | min | 1 | 0 | 0 | 1440 |  |
| Implemented | 11205–11207 | Eco_Period6 | Eco Period 6 (Start/End/Type) | S16 | min | 1 | 0 | 0 | 1440 |  |
| Implemented | 11208–11210 | Eco_Period7 | Eco Period 7 (Start/End/Type) | S16 | min | 1 | 0 | 0 | 1440 |  |
| Implemented | 11211–11213 | Eco_Period8 | Eco Period 8 (Start/End/Type) | S16 | min | 1 | 0 | 0 | 1440 |  |
| Implemented | 11214–11216 | Eco_Period9 | Eco Period 9 (Start/End/Type) | S16 | min | 1 | 0 | 0 | 1440 |  |
| Implemented | 11217–11219 | Eco_Period10 | Eco Period 10 (Start/End/Type) | S16 | min | 1 | 0 | 0 | 1440 |  |
| Periods 11–20 follow the same pattern (registers 11220–11249). |  |  |  |  |  |  |  |  |  |  |
| Program periods 1–20 only (11190–11249). On this interface `11254` is the weekday mask of the Eco schedule. The Eco SOC band follows at `11262`–`11268`. |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11262 | Eco_Min_SOC_Set | Eco Mode Minimum SOC | S16 | % | 0.01 | 0 | 0 | 10000 | Eco SOC band (with 11263). Active in Eco mode when 11263 - 11262 > 400 (4.00 %) with a BMS-connected battery; it then takes precedence over the Eco periods: self-consumption, charging below 11262 (from the grid when 11266 = 1, at up to 11268), with 11264 / 11265 capping grid import / export. Held in RAM: write again after every restart. |
| Implemented | 11263 | Eco_Max_SOC_Set | Eco Mode Maximum SOC | S16 | % | 0.01 | 0 | 0 | 10000 | Upper limit of the Eco SOC band (see 11262). Held in RAM: write again after every restart. |
| Implemented | 11264 | Eco_Max_Buy_Power_Set | Eco Mode Maximum Grid Import Power | S16 | kW | 0.01 | 0 | 0 | 6000 |  |
| Implemented | 11265 | Eco_Max_Sell_Power_Set | Eco Mode Maximum Grid Export Power | S16 | kW | 0.01 | 0 | 0 | 6000 |  |
| Implemented | 11266 | Eco_Grid_Charge_Set | Eco Mode Allow Grid Charging | S16 |  | 1 | 0 | 0 | 1 | 0: Disabled 1: Allow grid to charge battery during Eco mode. |
| Implemented | 11267 | Eco_Batto_Grid_Set | Eco Mode Allow Battery to Grid | S16 |  | 1 | 0 | 0 | 1 | 0: Disabled 1: Allow battery discharge to grid during Eco mode. |
| Implemented | 11268 | Eco_Max_Chg_Set | Eco Mode Max Grid Charge Power | S16 | kW | 0.01 | 0 | 0 | 6000 | Maximum battery charging power from the grid when Eco_Grid_Charge_Set = 1. |
| **9. Backup / Off-Grid** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11137 | Backup_Switch | Backup Output Enable | S16 |  | 1 | 1 | 0 | 1 | 0: Disabled 1: Enabled |
| Implemented | 11041 | On_Off_Grid_Switch_Enable | Planned Off-Grid Enable | S16 |  | 1 | 1 | 0 | 1 | 0: Disabled 1: Enabled |
| **10. Reactive Power Control** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11300 | Reactive_Power_Mode | Reactive Power Control Mode | S16 |  | 1 | 1 | 0 | 4 | 0: Off<br>1: Fixed reactive power Q (setpoint 11302)<br>2: Fixed power factor (setpoint 11301)<br>3: Q(U) curve<br>4: Cosφ(P) curve<br>Factory default 1 with 11302 = 0 (no reactive power). These values are used while the EMS is in control (11700 = 1, 11060 = 1, 12002 = 1, heartbeat on 12026); otherwise the grid-code settings apply. Set the mode first, then the setpoint, with FC06 single-register writes; an FC16 block write to 11300–11303 does not set these values. Reactive power flows only while the inverter is exchanging active power. Over TCP port 502 (Ethernet or Wi-Fi) a write changes the working value only: after a restart the register returns to its last stored value. Write it again after every restart. |
| Implemented | 11301 | Reactive_Power_PF_Set | Power Factor Setpoint | S16 |  | 0.001 | 0 | -1000 | 1000 | −1.000 to +1.000 (mode 2). The value is stored with a resolution of 0.01; the last digit reads back as 0 (for example, 994 reads back as 990). Over TCP port 502 (Ethernet or Wi-Fi) a write changes the working value only: after a restart the register returns to its last stored value. Write it again after every restart. |
| Implemented | 11302 | Reactive_Power_Q_Set | Reactive Power Setpoint | S16 | kVar | 0.01 | 0 | -2500 | 2500 | +leading/-lagging (mode 1) Over TCP port 502 (Ethernet or Wi-Fi) a write changes the working value only: after a restart the register returns to its last stored value. Write it again after every restart. |
| Implemented | 11303 | Reactive_Power_Q_Max | Max Reactive Power | S16 | kVar | 0.01 | 10000 | 0 | 10000 | Upper limit for the reactive-power command. Used while the EMS is in control. Over TCP port 502 (Ethernet or Wi-Fi) a write changes the working value only: after a restart the register returns to its last stored value. Write it again after every restart. |
| **11. Active Power Limit Percentage** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11320 | Active_Power_Limit_Pct_Enable | Active Power Limit (%) Enable | S16 |  | 1 | 0 | 0 | 1 | 0: No percentage limit (100 %) 1: Apply Active_Power_Limit_Pct (11321) to EMS dispatch Over TCP port 502 (Ethernet or Wi-Fi) a write changes the working value only: after a restart the register returns to its last stored value. Write it again after every restart. |
| Implemented | 11321 | Active_Power_Limit_Pct | Active Power Limit as % of Pn | U16 | % | 0.1 | 1000 | 0 | 1000 | 0-100.0 % of rated power (700 = 70.0 %). Applied while the inverter runs EMS dispatch: the EMS is in control (11700 = 1, 11060 = 1, 12002 = 1, heartbeat on 12026) and has written Active_Power_Set (11045). With 11320 = 1 the discharge (positive) setpoint is then capped at this percentage of rated power; 11320 = 0 means 100 %. For a feed-in cap that holds in every operating mode, use Export_Limits (11113, enable 11107). Over TCP port 502 (Ethernet or Wi-Fi) a write changes the working value only: after a restart the register returns to its last stored value. Write it again after every restart. |
| **12. Power Ramp Rate / Gradient** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11322 | Power_Ramp_Rate_Up | Power Increase Ramp Rate | U16 | %Pn/s | 0.1 | 10 | 1 | 1000 | Rate of active power increase. 100 = 10.0 %Pn/s. Used while the EMS is in control; otherwise the grid-code ramp settings apply. |
| Implemented | 11323 | Power_Ramp_Rate_Down | Power Decrease Ramp Rate | U16 | %Pn/s | 0.1 | 40 | 1 | 1000 | Rate of active power decrease. Used while the EMS is in control; otherwise the grid-code ramp settings apply. |
| Implemented | 11324 | Reconnect_Ramp_Rate | Post-Reconnection Ramp Rate | U16 | %Pn/min | 0.1 | 10 | 10 | 1000 | Ramp rate after grid reconnection. Used while the EMS is in control; otherwise the grid-code setting applies. |
| **13. Frequency-Watt P(f) Response** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11330 | Freq_Watt_Enable | Frequency-Watt Response Enable | S16 |  | 1 | 1 | 0 | 1 | 0: Disabled 1: Enabled (default). Used while the EMS is in control; otherwise the grid-code P(f) setting applies. |
| **22. Communications Watchdog Configuration** |  |  |  |  |  |  |  |  |  |  |
| Implemented | 11700 | Comms_Watchdog_Enable | Watchdog Enable | S16 |  | 1 | 0 | 0 | 1 | 0: Disabled 1: Enabled<br>*Enables the fail-safe action on loss of communication.* |
| Implemented | 11701 | Comms_Watchdog_Timeout | Watchdog Timeout | S16 |  | 1 | 60 | 10 | 600 | Time without a heartbeat before the fail-safe action is executed (s). |
| Implemented | 11702 | Comms_Timeout_Action | Timeout Action | S16 |  | 1 | 0 | 0 | 3 | 0: **Stop inverter**: holds PowerOn_Switch (12000) at 0. After the recovery set in 11704, write 12000 = 1 to restart. \| 1: **Self-consumption**: the inverter operates in General mode; the stored values of 11151, 11107 and 11113 are not changed. \| 2: **Hold last state**: no degradation, EMS setpoints retained. \| 3: **Zero-export**: export is limited to 0 kW (stored settings are not changed). The inverter stays connected to the grid and remains in operation; this is export curtailment, not a shutdown. |
| Implemented | 11703 | Comms_Watchdog_Prewarn_Sec | Pre-Warning Time | U16 |  | 1 | 20 | 5 | 300 | Pre-warning time in seconds. When `11701` − `14041` ≤ `11703` (the heartbeat is overdue), `14031 Comms_Watchdog_Status` changes to `2` (PREWARN) and bit 0 of `14106` is set; the next heartbeat returns it to 1. Must be smaller than `11701`, otherwise the write is answered with exception 0x03. |
| Implemented | 11704 | Comms_Watchdog_Resume_Mode | Recovery Behavior | U16 |  | 1 | 1 | 0 | 2 | `0` LATCH: after a timeout the `11702` action stays in force, also across a restart, even when heartbeats resume, until it is cleared as described below.<br>`1` AUTO-RESUME (default): the first heartbeat received in SAFE_STATE returns the watchdog to NORMAL.<br>`2` MANUAL_CONFIRM: with the heartbeat running every 1–5 s, write `12001` = 1; the next heartbeat returns the watchdog to NORMAL.<br>**Write 11704 only while the watchdog is disabled** (`11700` = 0, or `14044` = 0) and no LATCH is stored, that is before `11700` = 1; otherwise the write is answered with exception 0x03.<br>**Recovery** needs `14044` = 1 (`11060` = 1 and `12002` = 1). `0` LATCH: set `11700` = 0, wait ≥ 2 s, write the heartbeat `12026` and within 5 s `Malfunction_Clear (12001)` = 1, wait ≥ 2 s, then set `11700` = 1. The latch is stored in non-volatile memory and survives a power cycle; writing `12001` while `11700` = 1 does not clear it. If `11702` = 0 (stop), also write `12000` = 1 to restart the inverter. |

## Control Commands

Command registers. Write them with function code 0x06, one register per request. 12000, 12002 and 12021 can be read back to confirm the state; 12002 reads 0 after every restart.

> **Important: write the registers below with FC06 (Write Single Register), not FC16.**
>
> Write these registers with `0x06`, one register per request: `11300`-`11303`, `11320`-`11324`, `11330`, `11442`-`11444`.
>
> Read each value back after writing it. A `0x10` request covering two or more of these registers writes other settings at the same addresses instead (for example the TOU schedule), so always use one `0x06` request per register.

> **Integration notes**
>
> **Unit ID must be 1.** Requests carrying any other unit ID (except 0) are **silently discarded**: no exception is returned, so an incorrect unit ID results in a timeout. Requests with unit ID 0 are answered.
>
> **Two registers report battery voltage.** `10337` Bat1_Voltage is measured by the inverter; `10674` BMS_Bat1_Voltage is reported by the BMS. The two values can differ significantly. Use one source consistently in your integration.
>
> **Read only the addresses listed in this document.** Addresses that fall between documented entries may return real but undocumented values whose meaning and scaling are not guaranteed.

*Implemented (7 registers)*

### Control Commands (WRITE ONLY)

| Status | Register | Name | Description | Type | Default | Min | Max | Values / Notes |
|---|---|---|---|---|---|---|---|---|
| Implemented | 12000 | PowerOn_Switch | Power On / Off | S16 | 0 | 0 | 1 | 0: Power Off 1: Power On |
| Implemented | 12001 | Malfunction_Clear | Fault Clear | S16 | 0 | 0 | 1 | 0: No action 1: Clear faults |
| Implemented | 12002 | Remote_Mode | Remote Control Mode | S16 | 0 | 0 | 1 | 0: Local 1: Remote<br>*Set to 1 for EMS control* |
| **Emergency Stop** |  |  |  |  |  |  |  |  |
| Implemented | 12021 | Emergency_Stop | Emergency Stop | S16 | 0 | 0 | 1 | 1: Stop all power conversion immediately. Writing 12021 = 1 latches the inverter in the safe state.<br>*Safety-critical. Latches until cleared via `12001 Malfunction_Clear`=1; then write `12000` = 1 to restart. No unlock is required.* |
| **Communications Watchdog** |  |  |  |  |  |  |  |  |
| Implemented | 12026 | Comms_Heartbeat | Heartbeat | U16 | 0 | 0 | 65535 | Heartbeat: write any value except 0x5A5A every 1–5 s. Each write restarts the watchdog time (14041 = 0). 0x5A5A trips the watchdog on purpose (14042 = 2). |

## Device Information

Device identification and firmware information. Read these registers once after connecting, and check that `13016` reads 10–14 (MATIC).

*Implemented (9 registers)*

### Device Registers (READ-ONLY)

| Status | Register | Name | Description | Type | Unit | Scale | Notes |
|---|---|---|---|---|---|---|---|
| Implemented | 13000 | Device_SN | Device Serial Number | ASCII32 |  | 1 | 16 registers (32 bytes) |
| Implemented | 13016 | Device_Info | Device Model Code (MATIC variant) | U16 |  | 1 | MATIC units report 10-14: 10 = 10 kW, 11 = 12 kW, 12 = 15 kW, 13 = 20 kW, 14 = 25 kW (see Model Code Reference; the rated power is also in 13034). Any other value means the device is not a MATIC inverter covered by this document. |
| Implemented | 13017 | DSP_AC_App_Version | AC DSP Firmware Version | U16 |  | 1 |  |
| Implemented | 13019 | DC_App_V_Ver | DC DSP Firmware Version | U16 |  | 1 |  |
| Implemented | 13021 | ARM_App_V_Ver | ARM Firmware Version | U16 |  | 1 |  |
| Implemented | 13025 | WIFI_App_Ver | Wi-Fi Module Firmware Version | U16 |  | 1 | Use for communication diagnostics and firmware inventory. |
| Implemented | 13029 | Hardware_Ver | Hardware Version | U16 |  | 1 |  |
| Implemented | 13034 | Inverter_Rated_Power | Rated Power | U16 | kW | 0.01 |  |
| Implemented | 13035 | Inverter_Max_Power | Maximum Output Power | U16 | kW | 0.01 |  |
| Implemented | 13120 | Inverter_Total_Working_Time | Total Working Time | U32_BE | h | 0.1 | 2 registers |

### Model Code Reference (INFO)

| Code | Series | Model | Rated Power | Max Power |
|---|---|---|---|---|
| 10 | MATIC | MATIC-10KW-50A | 10.00 kW | 10.00 kW |
| 11 | MATIC | MATIC-12KW-50A | 12.00 kW | 12.00 kW |
| 12 | MATIC | MATIC-15KW-50A | 15.00 kW | 15.00 kW |
| 13 | MATIC | MATIC-20KW-50A | 20.00 kW | 20.00 kW |
| 14 | MATIC | MATIC-25KW-50A | 25.00 kW | 25.00 kW |

## System Status

Current operating state of inverter subsystems. Poll these registers to determine system readiness and operating conditions.

*Implemented (16 registers)*

### Status Registers (READ-ONLY)

| Status | Register | Name | Description | Type | Values / States |
|---|---|---|---|---|---|
| Implemented | 14000 | PCS_Working_Mode | PCS Working Mode | U16 | 0: General 1: Grid Balancing 2: Economic 3: UPS 4: TOU 5: Forecast 6: Off-Grid |
| Implemented | 14001 | TOU_Submode | TOU Sub-Mode | U16 | 0: Self-Use 1: Charge 2: Discharge 3: Peak Shaving 4: Battery Off |
| Implemented | 14002 | PCS_Working_Status | PCS Running Status | U16 | 0: Self-checking 1: Standby 2: Pre-charging 3: Grid-synchronizing 4: Waiting 5: Initializing 6: Starting 7: Connecting 8: Running<br>*EMS commands are accepted only in states 1 (Standby) and 8 (Running).* |
| Implemented | 14003 | Battery1_Working_Status | Battery Port 1 Status | U16 | 0: Stop 1: Charging 2: Discharging 3: Not Connected 4: Abnormal |
| Implemented | 14005 | PV1_Working_Status | PV1 Status | U16 | 0: Stop 1: Running 2: Not Connected 3: Abnormal 4: No Interface |
| Implemented | 14006 | PV2_Working_Status | PV2 Status | U16 | Same as PV1 |
| Implemented | 14007 | PV3_Working_Status | PV3 Status | U16 | Same as PV1 |
| Implemented | 14008 | PV4_Working_Status | PV4 Status | U16 | Same as PV1 |
| Implemented | 14009 | PV5_Working_Status | PV5 Status | U16 | Same as PV1 |
| Implemented | 14010 | Grid_Working_Status | Grid Connection Status | U16 | 0: On-Grid 1: Off-Grid (Islanded) |
| Implemented | 14027 | AC_Power_On_Off_Status | AC Side On/Off Status | U16 | 0: Off 1: On |
| Implemented | 14028 | DC_Power_On_Off_Status | DC Side On/Off Status | U16 | 0: Off 1: On |
| **Communications Watchdog Status** |  |  |  |  |  |
| Implemented | 14031 | Comms_Watchdog_Status | Watchdog State | U16 | 0: Disabled (`11700` = 0 or `14044` = 0) \| 1: Normal (heartbeat OK) \| 2: Pre-warning: the heartbeat is overdue (`11701` − `14041` ≤ `11703`); write `12026` at once \| **3: SAFE_STATE: the `11702` action is applied; recover as set in `11704` (cause in `14042`)** |
| Implemented | 14041 | Comms_Watchdog_Age_Sec | Seconds Since Last Heartbeat | U16 | Seconds since the last heartbeat write to `12026` (0 after each heartbeat, maximum 65535). Time left before the timeout = `11701` − `14041`; the pre-warning (`14031` = 2) starts when this is `11703` or less. |
| Implemented | 14042 | Comms_Watchdog_Trip_Reason | Reason for the last watchdog trip (held until the watchdog is enabled again) | U16 | 0: Never-tripped \| 1: Heartbeat timeout (age > 11701 Timeout) \| 2: Manual trigger (write 12026=0x5A5A) \| 3: reserved \| 4: EMS control closed while the watchdog is enabled (11060 != 1 or 12002 != 1) \| **5: SAFE_STATE held/restored from the EEPROM latch** (not 'reserved'). \| **6: restart while the EMS was in control**: the unit started in SAFE_STATE and waits for the EMS's first write. **Important: read this register promptly.** when 11704 Resume_Mode = LATCH, the true trip reason (1-4) is readable for **about 1 second** after the trip; the value then changes to 5. Poll 14031 and read 14042 as soon as 14031 changes to 3. While the latch is set, the inverter also **sets 11704 to LATCH**; a different Resume_Mode written while the latch is set is replaced by LATCH. To clear the latch (with `14044` = 1): 11700 = 0 → wait ≥ 2 s → heartbeat 12026 and within 5 s 12001 = 1 → wait ≥ 2 s → 11700 = 1. |
| Implemented | 14030 | EMS_Channel_Canary | Constant 0x1018 on EMS channels: use it to verify that you are reading the EMS register view | U16 | **Reads 0x1018 (4120) only on EMS-native channels** (Modbus TCP 502, Wi-Fi 502, RS-485 RTU). This document describes the EMS-channel view; cloud channels see a different view for some addresses (e.g. 10009, 10685–10689). If this register does not read 0x1018, you are not connected to an EMS channel and the register definitions in this document do not apply. |
| **EMS Control & Mode Readback** |  |  |  |  |  |
| Implemented | 14044 | EMS_Control_Active | EMS Control Active Status | U16 | 0: EMS disabled (local control) 1: EMS active (remote control)<br>Combined state of EMS_Switch_Set (11060) and Remote_Mode (12002). |

## EMS Setpoint Shadow

For the setpoints listed above, four shadow registers report the last requested value, the applied value, the seconds since the last accepted write (65535 = not written since the restart) and the reject code. Use them to confirm every setpoint write.

> ### Write-and-Verify Loop for EMS Setpoints
>
> Use this write-and-verify sequence for each setpoint that has shadow registers: `11045` (14250–14253), `11321` (14262–14265), `11068` (14266–14269), `11069` (14270–14273), `11701` (14282–14285), `11704` (14286–14289), `11060` (14290–14293). The four registers are, in this order: requested value, applied value, seconds since the write, reject code.
>
> 1. **(once, after connecting)** Enable EMS dispatch: `FC 0x06 @ 11060 = 1` (EMS_Switch_Set) and `FC 0x06 @ 12002 = 1` (Remote_Mode). Confirm with `14291 EMS_Switch_Set_Last_Applied == 1` and `14044 == 1`. Setpoint writes take effect only while 14044 = 1.
> 2. **(once, after connecting)** Enable the communication watchdog: with `11700` = 0 write `11701` (timeout, s), `11702` (action) and `11704` (recovery mode), then `FC 0x06 @ 11700 = 1`. Confirm with `14031 Comms_Watchdog_Status == 1 (Normal)`.
> 3. **(continuous, every 1–5 s)** Send heartbeat: `FC 0x06 @ 12026` = any value except 0x5A5A (Comms_Heartbeat). `14041 Comms_Watchdog_Age_Sec` returns to 0 with each heartbeat.
> 4. **(on dispatch change)** Write the setpoint with `FC 0x06`, one register per request (e.g. 11045 Active_Power_Set, 11321 Active_Power_Limit_Pct). For 11321, 11068, 11069, 11701, 11704 and 11060 only `0x06` writes update the shadow registers.
> 5. **(1–2 s later)** Read the four shadow registers for that setpoint (Last_Requested, Last_Applied, Last_Write_Age_Sec, Last_Reject_Code). If *Last_Applied != Last_Requested*, check *Last_Reject_Code*.
>
> **Reading the result:** applied = requested and reject code 0: the write is in force while the EMS is in control (14044 = 1, 14031 = 1). Reject code 1: value out of range (11045: clamped to ±2500, the applied value shows the clamp; other setpoints: exception 03, not written). Reject code 3: the write was refused (exception 04). Reject code 6: other exception. Watchdog trips are reported separately: monitor `14031` and `14042 Comms_Watchdog_Trip_Reason`.

> **Usage pattern (pseudocode):**
>
> ```text
> write(11045, requested_kW * 100)      # FC 0x06
> sleep(1 s)
> requested = read(14250)                # Active_Power_Set_Last_Requested
> applied   = read(14251)                # Active_Power_Set_Last_Applied (after the ±2500 clamp)
> reject    = read(14253)                # 0 = accepted, 1 = clamped
> if reject != 0 or applied != requested:
>     use applied as the setpoint in force; keep requests within ±rated power (13034)
> check the result at 10019 (inverter active power) and 10346 (battery power)
> ```
>
> **Reject codes:** 0 = accepted, 1 = out of range, 3 = write refused, 6 = other exception.

*Shadow block 14250–14293: four registers per setpoint; the setpoints are listed above.*

## Alarms & Faults

Alarm and fault registers, grouped by category. Each register is a bit field; a set bit indicates an active alarm or fault. Poll these registers periodically.

#### AC Side Derating Alarms (WARNING)

| Bit | Name | Description |
|---|---|---|
| 14022:0 | AC_External_Temp_Derating | AC External Ambient Temperature Derating |
| 14022:1 | AC_Internal_Temp_Derating | AC Internal Ambient Temperature Derating |
| 14022:2 | AC_Bus_Derating | AC Bus Derating |
| 14022:4 | Grid_Voltage_Derating | Grid Voltage Derating |
| 14022:5 | AC_Overload_Derating | AC Overload Derating |
| 14022:6 | AC_Radiator_Temp_Derating | AC Heatsink Temperature Derating |

#### DC Side Derating Alarms (WARNING)

| Bit | Name | Description |
|---|---|---|
| 14023:3 | DC_External_Temp_Derating | DC External Ambient Temperature Derating |
| 14023:4 | DC_Inside_Temp_Derating | DC Internal Ambient Temperature Derating |
| 14023:5 | Battery_Bus_Voltage_Derating | Battery Bus Voltage Derating |
| 14023:6 | PV_Bus_Voltage_Derating | PV Bus Voltage Derating |
| 14023:8 | BMS1_Charge_Prohibited | BMS1 Charge Prohibited |
| 14023:9 | BMS1_Discharge_Prohibited | BMS1 Discharge Prohibited |

#### Grid Voltage / Frequency Alarms (ALARM)

| Bit | Name | Description |
|---|---|---|
| 14100:0 | Grid_LV1_OV_A | Grid Level-1 Over-Voltage Phase A |
| 14100:3 | Grid_LV2_OV_A | Grid Level-2 Over-Voltage Phase A |
| 14100:6 | Grid_LV3_OV_A | Grid Level-3 Over-Voltage Phase A |
| 14100:9 | Grid_10min_OV_A | Grid 10-min Over-Voltage Phase A |
| 14100:12 | Grid_LV1_UV_A | Grid Level-1 Under-Voltage Phase A |
| 14101:6 | Grid_LV1_OF | Grid Level-1 Over-Frequency |
| 14101:7 | Grid_LV2_OF | Grid Level-2 Over-Frequency |
| 14101:8 | Grid_LV1_UF | Grid Level-1 Under-Frequency |
| 14101:9 | Grid_LV2_UF | Grid Level-2 Under-Frequency |
| 14101:10 | Grid_Phase_Sequence | Grid Phase Sequence Error |
| 14101:12 | Grid_Phase_Loss_A | Grid Phase A Loss |
| 14101:15 | ROCOF | Grid Rate of Change of Frequency (RoCoF) |

#### Critical Faults (FAULT)

| Register | Name | Description |
|---|---|---|
| 14109:0-14 | Grid_Voltage_Faults | Grid Over/Under Voltage Faults (3 levels, 3 phases) |
| 14110:0-5 | Grid_VF_Faults_LV2_3 | Grid Level-2/3 Under-Voltage + Frequency Faults |
| 14110:10-14 | Grid_Phase_Faults | Grid Phase Sequence / Loss / Lock Faults |
| 14112:0-2 | BackUp_Overcurrent | Backup Output Overcurrent (A/B/C) |
| 14112:3-5 | BackUp_Overload_Timeout | Backup Overload Timeout (A/B/C) |
| 14113:3-6 | Inv_HW_Overcurrent | Inverter Hardware Overcurrent |
| 14113:7-9 | Inv_SW_Overcurrent | Inverter Software Overcurrent (A/B/C) |
| 14115:0-2 | Inv_Short_Circuit | Inverter Short Circuit (A/B/C) |
| 14104:0 | Anti_Islanding | Anti-Islanding Protection Triggered |
| 14104:1 | Heatsink_Overtemp | Inverter Heatsink Over-Temperature |
| 14104:3 | CT_Reverse | CT Reverse Polarity Detected (Alarm) |
| 14104:7 | Anti_Backfeed_Failure | Anti-Backfeed Failure |

For the complete fault register list, contact Wattsonic technical support.

## Quick Start Guide

Step-by-step guide for integrating the Wattsonic MATIC inverter via Modbus.

### 1. Connect & Identify

- Connect over Modbus TCP, port `502`, unit ID `1`, or over Modbus RTU (RS-485, `115200` baud, 8N1, unit ID `1`)
- Read `Device_SN (13000)` and `Device_Info (13016)` to verify device identity
- **Confirm the model:** read `Device_Info (13016)`. MATIC units report 10-14 (10 = 10 kW, 11 = 12 kW, 12 = 15 kW, 13 = 20 kW, 14 = 25 kW); any other value means the device is not a MATIC inverter covered by this document.
- Read `Inverter_Rated_Power (13034)` to determine the rated power and limit power setpoints to it.

### 2. Enable EMS Control

- Write `Comms_Watchdog_Timeout (11701) = 60` (60 s), with `11700` = 0.
- Write `Comms_Timeout_Action (11702) = 1` (self-consumption on timeout).
- Write `Comms_Watchdog_Resume_Mode (11704) = 1` (AUTO). 11704 can be written only while the watchdog is disabled.
- Write `Comms_Watchdog_Enable (11700) = 1` to enable the communication watchdog.
- Write `EMS_Switch_Set (11060) = 1` to enable external EMS dispatch.
- Write `Remote_Mode (12002) = 1`, then the first heartbeat `12026`. Confirm: `14044` = 1 and `14031` = 1.

### 3. Monitor System State

Poll real-time data every 1–5 s:

- Grid power: `Meter_Active_Power_Total (10765)`, +export / −import
- PV power: `PV_Total_Power (10367)`
- Battery SOC: `BMS_Bat1_SOC (10671)`
- Battery power: `Bat_Power_Total (10346)`, +discharge / −charge
- Load power: `Load_Power_Total (10800)`
- Working mode: `PCS_Working_Mode (14000)`
- Grid status: `Grid_Working_Status (14010)`
- Watchdog: `Comms_Watchdog_Status (14031)`
- Alarms: registers `14022`–`14026` and `14100` onwards

### 4. Send Heartbeat (Loop)

Write the heartbeat register every 1–5 s:

Heartbeat Loop

Write Comms_Heartbeat (12026) = counter (any value except 0x5A5A)  
Interval: every 1–5 s (this also keeps write control on port 502, which is released after 30 s without a write)  
14031 = 2 (pre-warning): the heartbeat is overdue; write it at once and check the connection.  
14031 = 3 (SAFE_STATE): the 11702 action is applied; recover as set in 11704.

### 5. Control Operations

- **Set Working Mode:** Write `Run_Mode_Set (11151)` = 0 / 2 / 4
- **Set Active Power:** Write `Active_Power_Set (11045)`

Active Power Examples

Write 1500 = discharge 15.00 kW  
Write -1000 = charge 10.00 kW from grid

- **Export Limit (Zero Export):** Write `Export_Limits_Switch (11107) = 1`, then `Export_Limits (11113) = 0`.
- **SOC Limits:** Write `Grid_tied_SOC_MIN (11108) = 1000` (10.00%)
- **Reactive Power:** Write `Reactive_Power_Mode (11300)` first, then the setpoint: `11302` (Q, mode 1) or `11301` (PF, mode 2).

### 6. Safety & Error Handling

- Poll the alarm and fault registers periodically.
- Use `Malfunction_Clear (12001) = 1` to clear recoverable faults
- **Emergency Stop:** Write `Emergency_Stop (12021) = 1` to stop power conversion immediately. To clear it, write `Malfunction_Clear (12001) = 1`.
- **Verify EMS:** Poll `EMS_Control_Active (14044)` periodically. 0 means that `11060` or `12002` is no longer 1 (12002 reads 0 after every restart); write `11060` = 1 and `12002` = 1 again.
- Before shutting down the inverter, write `PowerOn_Switch (12000) = 0`.
- Before disconnecting the EMS, write `EMS_Switch_Set (11060) = 0`.

## Scenarios

Eight typical EMS integration scenarios with the communication path and example code in Python, Node.js, C# and Go. Each example shows the register sequence, scale factors and sign conventions of its scenario; the control examples open the EMS session first (Quick Start step 2) and write the heartbeat every 1–5 s. Add error handling and logging for your installation.

*RTU RS-485 serial (on-site controllers) · TCP Ethernet / Wi-Fi · RTU + TCP Both supported*

### 1. Real-Time Monitoring Dashboard (RTU + TCP)

Read inverter output, PV production, battery SOC, and grid/meter power to build a live monitoring dashboard. Poll every 1-2 seconds for near-real-time visibility into system state.

#### Key Registers

- `10000` Inverter_Frequency: Read, scale 0.01 Hz
- `10001-10003` Inverter_Voltage_A/B/C: Read, scale 0.1 V
- `10367` PV_Total_Power: Read, scale 0.01 kW
- `10348` / `10352` PV1/PV2_Voltage: Read, scale 0.1 V
- `10346` Bat_Power_Total: Read, scale 0.01 kW, signed (+discharge/−charge)
- `10671` BMS_Bat1_SOC: Read, scale 0.01 %
- `10675` BMS_Bat1_Current: Read, scale 0.1 A, signed (+discharge/−charge)
- `10765` Meter_Active_Power_Total: Read, scale 0.01 kW, signed (+export/−import)
- `14002` PCS_Working_Status: Read

1. **SETUP** · Connect · `RTU or TCP`
2. **READ** · AC & Grid · `10000–10064` · 65 regs
3. **READ** · PV / DC · `10348–10367` · 20 regs
4. **READ** · Battery · `10671–10697` · 27 regs
5. **READ** · Meter · `10765` · Total kW
6. **READ** · Status · `14002` · PCS State
7. LOOP 1–2 s

**Python**

```python
from pymodbus.client import ModbusTcpClient  # or ModbusSerialClient
import time, struct

# RTU: client = ModbusSerialClient(port="/dev/ttyUSB0", baudrate=115200)
client = ModbusTcpClient("192.168.1.100", port=502)
client.connect()

def signed16(val):
    return val - 65536 if val >= 32768 else val

while True:
    # Group 1: inverter basics (10000-10003)
    g1 = client.read_holding_registers(10000, 4, slave=1)
    freq = g1.registers[0] * 0.01          # Hz
    v_a  = g1.registers[1] * 0.1           # V
    v_b  = g1.registers[2] * 0.1           # V
    v_c  = g1.registers[3] * 0.1           # V

    # Group 2: PV production (10348-10367, 20 regs)
    g2 = client.read_holding_registers(10348, 20, slave=1)
    pv1_v    = g2.registers[0] * 0.1       # V  (10348)
    pv2_v    = g2.registers[4] * 0.1       # V  (10352, skip [3]=Given_V)
    pv_total = g2.registers[19] * 0.01     # kW (10367)

    # Group 3: battery (10671-10675)
    g3 = client.read_holding_registers(10671, 5, slave=1)
    soc     = g3.registers[0] * 0.01       # %
    bat_cur = signed16(g3.registers[4]) * 0.1  # A (+dis/-chg)

    # Meter power
    m = client.read_holding_registers(10765, 1, slave=1)
    meter_w = signed16(m.registers[0]) * 0.01  # kW (+export/-import)

    # PCS status
    s = client.read_holding_registers(14002, 1, slave=1)
    print(f"Grid:{freq:.1f}Hz V:{v_a:.0f}/{v_b:.0f}/{v_c:.0f}V "
          f"PV:{pv_total:.2f}kW SOC:{soc:.0f}% Meter:{meter_w:.2f}kW")
    time.sleep(1)
```

**Node.js**

```javascript
const ModbusRTU = require('modbus-serial');
const client = new ModbusRTU();

// RTU: await client.connectRTUBuffered("/dev/ttyUSB0", { baudRate: 115200 });
await client.connectTCP("192.168.1.100", { port: 502 });
client.setID(1);

function signed16(v) { return v >= 32768 ? v - 65536 : v; }

setInterval(async () => {
    // Group 1: inverter basics
    const g1 = await client.readHoldingRegisters(10000, 4);
    const freq = g1.data[0] * 0.01;        // Hz
    const vA = g1.data[1] * 0.1;           // V

    // Group 2: PV production (10348-10367, 20 regs)
    const g2 = await client.readHoldingRegisters(10348, 20);
    const pv1V = g2.data[0] * 0.1;         // V  (10348)
    const pv2V = g2.data[4] * 0.1;         // V  (10352)
    const pvTotal = g2.data[19] * 0.01;    // kW (10367)

    // Group 3: battery
    const g3 = await client.readHoldingRegisters(10671, 5);
    const soc = g3.data[0] * 0.01;         // %
    const batCur = signed16(g3.data[4]) * 0.1; // A

    // Meter power (+export / -import)
    const m = await client.readHoldingRegisters(10765, 1);
    const meterW = signed16(m.data[0]) * 0.01; // kW

    // PCS working status
    const s = await client.readHoldingRegisters(14002, 1);
    console.log(`PV:${pvTotal.toFixed(2)}kW SOC:${soc.toFixed(0)}% `
              + `Meter:${meterW.toFixed(2)}kW Freq:${freq.toFixed(1)}Hz`);
}, 1000);
```

**C#**

```csharp
using NModbus;
using System.Net.Sockets;

// RTU: var port = new SerialPort("/dev/ttyUSB0", 115200);
//      var master = factory.CreateRtuMaster(port);
var tcp = new TcpClient("192.168.1.100", 502);
var factory = new ModbusFactory();
var master = factory.CreateMaster(tcp);

short Signed16(ushort v) => v >= 32768 ? (short)(v - 65536) : (short)v;

while (true) {
    // Group 1: inverter basics (10000-10003)
    var g1 = master.ReadHoldingRegisters(1, 10000, 4);
    double freq = g1[0] * 0.01;            // Hz
    double vA   = g1[1] * 0.1;             // V

    // Group 2: PV production (10348-10367, 20 regs)
    var g2 = master.ReadHoldingRegisters(1, 10348, 20);
    double pv1V = g2[0] * 0.1;             // V  (10348)
    double pvTotal = g2[19] * 0.01;        // kW (10367)

    // Group 3: battery (10671-10675)
    var g3 = master.ReadHoldingRegisters(1, 10671, 5);
    double soc    = g3[0] * 0.01;          // %
    double batCur = Signed16(g3[4]) * 0.1; // A

    // Meter power
    var m = master.ReadHoldingRegisters(1, 10765, 1);
    double meterW = Signed16(m[0]) * 0.01; // kW (+export/-import)

    Console.WriteLine($"PV:{pvTotal:F2}kW SOC:{soc:F0}% Meter:{meterW:F2}kW");
    Thread.Sleep(1000);
}
```

**Go**

```go
package main
import (
    "fmt"; "time"
    "github.com/goburrow/modbus"
    "encoding/binary"
)

func signed16(v uint16) int16 { return int16(v) }

func main() {
    // RTU: handler := modbus.NewRTUClientHandler("/dev/ttyUSB0")
    handler := modbus.NewTCPClientHandler("192.168.1.100:502")
    handler.SlaveId = 1
    handler.Connect()
    defer handler.Close()
    client := modbus.NewClient(handler)

    for {
        // Group 1: inverter basics
        g1, _ := client.ReadHoldingRegisters(10000, 4)
        freq := float64(binary.BigEndian.Uint16(g1[0:2])) * 0.01

        // Group 2: PV production (10348-10367, 20 regs)
        g2, _ := client.ReadHoldingRegisters(10348, 20)
        pv1V := float64(binary.BigEndian.Uint16(g2[0:2])) * 0.1    // 10348
        pvTotal := float64(binary.BigEndian.Uint16(g2[38:40])) * 0.01 // 10367

        // Group 3: battery SOC and current
        g3, _ := client.ReadHoldingRegisters(10671, 5)
        soc := float64(binary.BigEndian.Uint16(g3[0:2])) * 0.01
        batCur := float64(signed16(binary.BigEndian.Uint16(g3[8:10]))) * 0.1

        // Meter power (+export / -import)
        m, _ := client.ReadHoldingRegisters(10765, 1)
        meterW := float64(signed16(binary.BigEndian.Uint16(m[0:2]))) * 0.01

        fmt.Printf("PV:%.2fkW SOC:%.0f%% Meter:%.2fkW Freq:%.1fHz\n",
            pvTotal, soc, meterW, freq)
        time.Sleep(1 * time.Second)
    }
}
```

### 2. Zero-Export Control (RTU + TCP)

Prevent export to the grid by adjusting the inverter output to the local load. Use this where the grid operator limits or prohibits feed-in.

#### Key Registers

- `10765` Meter_Active_Power_Total: Read, scale 0.01 kW, signed (+export/−import)
- `10367` PV_Total_Power: Read, scale 0.01 kW
- `10671` BMS_Bat1_SOC: Read, scale 0.01 %
- `11107` Export_Limits_Switch: Write, 1 = enable
- `11113` Export_Limits: Write, 0 = zero export
- `11700` / `11060` / `12002`: open the EMS session (Quick Start step 2); heartbeat `12026` every 1–5 s
- `11045` Active_Power_Set: Write, scale 0.01 kW, signed (+discharge/−charge)

1. **WRITE** · EMS Session · `11700 · 11060 · 12002` · = 1
2. **WRITE** · Export Limit · `11113` · = 0
3. **READ** · Meter Power · `10765` · kW ±
4. **DECIDE** · Calculate · if export→reduce
5. **WRITE** · Power Set · `11045` · kW ±
6. LOOP 1 s

**Python**

```python
from pymodbus.client import ModbusTcpClient
import time

# RTU: from pymodbus.client import ModbusSerialClient
#      client = ModbusSerialClient(port="/dev/ttyUSB0", baudrate=115200)
client = ModbusTcpClient("192.168.1.100", port=502)
client.connect()
UNIT = 1

def signed16(v): return v - 65536 if v >= 32768 else v
def to_unsigned(v): return v + 65536 if v < 0 else v
def w(addr, value): client.write_register(addr, value, slave=UNIT)   # FC 0x06, one register per request
def r(addr): return client.read_holding_registers(addr, 1, slave=UNIT).registers[0]

# Open the EMS session (Quick Start step 2)
w(11700, 0)      # watchdog off while it is configured (11704 is writable only then)
w(11701, 60)     # watchdog timeout 60 s
w(11702, 1)      # action on timeout: self-consumption
w(11704, 1)      # recovery after a timeout: AUTO
w(11700, 1)      # watchdog on
w(11060, 1)      # EMS dispatch on
w(12002, 1)      # remote mode on
w(12026, 1)      # heartbeat: repeat every 1-5 s
rated_kw = r(13034) * 0.01                                  # rated power, kW

# Zero-export limit (holds in every operating mode)
w(11107, 1)      # export limit on
w(11113, 0)      # export limit 0 kW

MARGIN = 0.05    # keep about 50 W of import to avoid oscillation
power_set = 0.0  # battery dispatch in kW (+discharge / -charge)

while True:
    w(12026, 1)                                    # heartbeat
    meter_kw = signed16(r(10765)) * 0.01           # +export / -import
    soc = r(10671) * 0.01

    # exporting (meter_kw > 0): lower the dispatch (charge more)
    # importing more than MARGIN: raise the dispatch (discharge more)
    power_set -= (meter_kw + MARGIN) * 0.5
    power_set = max(-rated_kw, min(rated_kw, power_set))
    if soc > 98.0 and power_set < 0: power_set = 0  # battery full: no charging
    if soc < 10.0 and power_set > 0: power_set = 0  # battery low: no discharging

    w(11045, to_unsigned(int(power_set * 100)))    # 0.01 kW
    print(f"Meter:{meter_kw:+.2f}kW SOC:{soc:.0f}% Dispatch:{power_set:+.2f}kW")
    time.sleep(1)
```

**Node.js**

```javascript
const ModbusRTU = require("modbus-serial");
const client = new ModbusRTU();

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const signed16 = (v) => (v >= 32768 ? v - 65536 : v);
const toUnsigned = (v) => (v < 0 ? v + 65536 : v);
const w = (addr, value) => client.writeRegister(addr, value);            // FC 0x06
const r = async (addr) => (await client.readHoldingRegisters(addr, 1)).data[0];

async function openSession() {                        // Quick Start step 2
    await w(11700, 0);                                // watchdog off while it is configured
    await w(11701, 60);                               // watchdog timeout 60 s
    await w(11702, 1);                                // action on timeout: self-consumption
    await w(11704, 1).catch(() => {});                // recovery AUTO (exception 03 while a LATCH is stored)
    await w(11700, 1);                                // watchdog on
    await w(11060, 1);                                // EMS dispatch on
    await w(12002, 1);                                // remote mode on
    await w(12026, 1);                                // heartbeat: repeat every 1-5 s
}

async function connect() {
    // RTU: await client.connectRTUBuffered("/dev/ttyUSB0", { baudRate: 115200 });
    await client.connectTCP("192.168.1.100", { port: 502 });
    client.setID(1);
    await openSession();
    return (await r(13034)) * 0.01;                   // rated power, kW
}

async function main() {
    const ratedKw = await connect();
    await w(11107, 1);                                // export limit on
    await w(11113, 0);                                // export limit 0 kW
    const MARGIN = 0.05;                              // keep about 50 W of import
    let powerSet = 0.0;                               // +discharge / -charge, kW
    for (;;) {
        await w(12026, 1);                            // heartbeat
        const meterKw = signed16(await r(10765)) * 0.01;   // +export / -import
        const soc = (await r(10671)) * 0.01;
        powerSet -= (meterKw + MARGIN) * 0.5;         // exporting: charge more; importing: discharge more
        powerSet = Math.max(-ratedKw, Math.min(ratedKw, powerSet));
        if (soc > 98 && powerSet < 0) powerSet = 0;
        if (soc < 10 && powerSet > 0) powerSet = 0;
        await w(11045, toUnsigned(Math.round(powerSet * 100)));
        console.log(`Meter:${meterKw.toFixed(2)}kW SOC:${soc.toFixed(0)}% Set:${powerSet.toFixed(2)}kW`);
        await sleep(1000);
    }
}

main().catch((e) => { console.error(e); process.exit(1); });
```

**C#**

```csharp
using NModbus;
using System;
using System.Net.Sockets;
using System.Threading;

// RTU: var port = new System.IO.Ports.SerialPort("/dev/ttyUSB0", 115200); port.Open();
//      var master = new ModbusFactory().CreateRtuMaster(port);
var tcp = new TcpClient("192.168.1.100", 502);
var master = new ModbusFactory().CreateMaster(tcp);
const byte UNIT = 1;

short Signed16(ushort v) => (short)v;
ushort ToUnsigned(int v) => (ushort)(v < 0 ? v + 65536 : v);
void W(ushort addr, ushort value) => master.WriteSingleRegister(UNIT, addr, value);   // FC 0x06
ushort R(ushort addr) => master.ReadHoldingRegisters(UNIT, addr, 1)[0];

// Open the EMS session (Quick Start step 2)
W(11700, 0);                                          // watchdog off while it is configured
W(11701, 60);                                         // watchdog timeout 60 s
W(11702, 1);                                          // action on timeout: self-consumption
try { W(11704, 1); } catch (SlaveException) { }       // recovery AUTO (exception 03 while a LATCH is stored)
W(11700, 1);                                          // watchdog on
W(11060, 1);                                          // EMS dispatch on
W(12002, 1);                                          // remote mode on
W(12026, 1);                                          // heartbeat: repeat every 1-5 s
double ratedKw = R(13034) * 0.01;                     // rated power, kW

W(11107, 1);                                          // export limit on
W(11113, 0);                                          // export limit 0 kW
const double MARGIN = 0.05;                           // keep about 50 W of import
double powerSet = 0.0;                                // +discharge / -charge, kW

while (true) {
    W(12026, 1);                                      // heartbeat
    double meterKw = Signed16(R(10765)) * 0.01;       // +export / -import
    double soc = R(10671) * 0.01;
    powerSet -= (meterKw + MARGIN) * 0.5;             // exporting: charge more; importing: discharge more
    powerSet = Math.Clamp(powerSet, -ratedKw, ratedKw);
    if (soc > 98 && powerSet < 0) powerSet = 0;
    if (soc < 10 && powerSet > 0) powerSet = 0;
    W(11045, ToUnsigned((int)(powerSet * 100)));
    Console.WriteLine($"Meter:{meterKw:+0.00}kW SOC:{soc:F0}% Set:{powerSet:+0.00}kW");
    Thread.Sleep(1000);
}
```

**Go**

```go
package main

import (
    "encoding/binary"
    "fmt"
    "math"
    "time"

    "github.com/goburrow/modbus"
)

var client modbus.Client

func w(addr, value uint16) error { _, err := client.WriteSingleRegister(addr, value); return err } // FC 0x06
func r(addr uint16) uint16 {
    b, err := client.ReadHoldingRegisters(addr, 1)
    if err != nil { return 0 }
    return binary.BigEndian.Uint16(b)
}
func kw(v uint16) float64 { return float64(int16(v)) * 0.01 }     // signed, 0.01 kW
func raw(k float64) uint16 { return uint16(int16(math.Round(k * 100))) }

// openSession: Quick Start step 2; returns the rated power in kW
func openSession() float64 {
    w(11700, 0)  // watchdog off while it is configured
    w(11701, 60) // watchdog timeout 60 s
    w(11702, 1)  // action on timeout: self-consumption
    w(11704, 1)  // recovery AUTO (exception 03 while a LATCH is stored)
    w(11700, 1)  // watchdog on
    w(11060, 1)  // EMS dispatch on
    w(12002, 1)  // remote mode on
    w(12026, 1)  // heartbeat: repeat every 1-5 s
    return float64(r(13034)) * 0.01
}

func connect() float64 {
    // RTU: handler := modbus.NewRTUClientHandler("/dev/ttyUSB0") (115200 baud, 8N1)
    handler := modbus.NewTCPClientHandler("192.168.1.100:502")
    handler.SlaveId = 1
    if err := handler.Connect(); err != nil { panic(err) }
    client = modbus.NewClient(handler)
    return openSession()
}

func main() {
    ratedKw := connect()
    w(11107, 1) // export limit on
    w(11113, 0) // export limit 0 kW
    margin := 0.05 // keep about 50 W of import
    powerSet := 0.0 // +discharge / -charge, kW
    for {
        w(12026, 1)                 // heartbeat
        meterKw := kw(r(10765))     // +export / -import
        soc := float64(r(10671)) * 0.01
        powerSet -= (meterKw + margin) * 0.5 // exporting: charge more; importing: discharge more
        powerSet = math.Max(-ratedKw, math.Min(ratedKw, powerSet))
        if soc > 98 && powerSet < 0 { powerSet = 0 }
        if soc < 10 && powerSet > 0 { powerSet = 0 }
        w(11045, raw(powerSet))
        fmt.Printf("Meter:%+.2fkW SOC:%.0f%% Set:%+.2fkW\n", meterKw, soc, powerSet)
        time.Sleep(time.Second)
    }
}
```

### 3. Eco Schedule Programming (TCP)

Run the battery on a daily time schedule. Select Eco mode with Run_Mode_Set `11151` = 2 and program up to 20 periods from `11190`, 3 registers each: start and end in minutes from midnight (local inverter time) and the period type 0 = discharge, 1 = charge, 2 = self-consumption. A period applies while start ≤ time < end; outside all periods the inverter runs self-consumption. `11254` selects the weekdays (bit0 = Monday to bit6 = Sunday, 0x7F = every day). Charge and discharge power per period, and grid charging in charge periods, follow the installer settings (factory: 100 % of rated power, charging from PV). Keep the Eco SOC band `11262` / `11263` at 0 while you use periods: a band wider than 4.00 % takes precedence over the periods (self-consumption, with charging below `11262`, from the grid when `11266` = 1). Confirm by reading `11190` onward back.

#### Key Registers

- `11151` Run_Mode_Set: Write 2 = Eco mode (uses the schedule from 11190)
- `11190` Eco_Start1_Set: Write, minutes after midnight (0–1440)
- `11191` Eco_End1_Set: Write, minutes after midnight
- `11192` Eco_Peak_Sel1_Set: Write, 0 = discharge, 1 = charge, 2 = self-consumption
- `11193-11195` Eco_Period2: Write, same 3-register pattern
- `11196-11219` Eco_Period3 through Period10: Write, 3 registers each
- `11254` TOU_Day_Of_Week_Mask: Write, bitmap (bit0=Mon, bit6=Sun)
- `11262` / `11263` Eco SOC band: leave at 0 to run the period schedule
- `11108` Grid_tied_SOC_MIN: Write, scale 0.01 %
- `11109` Grid_tied_SOC_MAX: Write, scale 0.01 %

1. **WRITE** · Mode = Eco · `11151` · = 2
2. **WRITE** · Period 1 · `11190–11192` · Start/End/Mode
3. **WRITE** · Period 2 · `11193–11195` · Start/End/Mode
4. **WRITE** · Period 3 · `11196–11198` · Start/End/Mode
5. **WRITE** · Weekday Mask · `11254` · = 0x7F
6. **WRITE** · SOC Limits · `11108–11109` · Min/Max
7. **READ** · Readback · `11190+` · Verify all
8. **VERIFY** · Confirmed · Values match

**Python**

```python
from pymodbus.client import ModbusTcpClient

# RTU: from pymodbus.client import ModbusSerialClient
#      client = ModbusSerialClient(port="/dev/ttyUSB0", baudrate=115200)
client = ModbusTcpClient("192.168.1.100", port=502)
client.connect()

# Eco mode (11151 = 2) and general SOC limits
client.write_register(11151, 2, slave=1)       # Eco mode

# General SOC limits
client.write_register(11108, int(10.0 * 100), slave=1)   # SOC_MIN = 10%
client.write_register(11109, int(100.0 * 100), slave=1)  # SOC_MAX = 100%
# Period 1: Charge 00:00-07:00 (charge)
client.write_registers(11190, [0, 420, 1], slave=1)      # start=0, end=420, charge=1

# Period 2: Self-use 07:00-17:00
client.write_registers(11193, [420, 1020, 2], slave=1)   # start=420, end=1020, self-use=2

# Period 3: Discharge 17:00-23:00 (discharge)
client.write_registers(11196, [1020, 1380, 0], slave=1)  # start=1020, end=1380, discharge=0

# Enable for all days (Mon-Sun = bits 0-6 = 0x7F)
client.write_register(11254, 0x7F, slave=1)

# Verify by readback
r = client.read_holding_registers(11190, 9, slave=1)
for i in range(3):
    start, end, mode = r.registers[i*3], r.registers[i*3+1], r.registers[i*3+2]
    label = ["Discharge", "Charge", "Self-use"][mode]
    print(f"Period {i+1}: {start//60:02d}:{start%60:02d}-{end//60:02d}:{end%60:02d} [{label}]")
client.close()
```

**Node.js**

```javascript
const ModbusRTU = require('modbus-serial');
const client = new ModbusRTU();

// RTU: await client.connectRTUBuffered("/dev/ttyUSB0", { baudRate: 115200 });
await client.connectTCP("192.168.1.100", { port: 502 });
client.setID(1);

// Eco mode (11151 = 2) and general SOC limits
await client.writeRegister(11151, 2);                    // Eco mode
await client.writeRegister(11108, Math.round(10 * 100)); // SOC_MIN = 10%
await client.writeRegister(11109, Math.round(100 * 100));// SOC_MAX = 100%
// Period 1: Charge 00:00-07:00 (charge during off-peak)
await client.writeRegisters(11190, [0, 420, 1]);

// Period 2: Self-use 07:00-17:00
await client.writeRegisters(11193, [420, 1020, 2]);

// Period 3: Discharge 17:00-23:00 (discharge during peak)
await client.writeRegisters(11196, [1020, 1380, 0]);

// All days of week (Mon-Sun)
await client.writeRegister(11254, 0x7F);

// Readback verification
const r = await client.readHoldingRegisters(11190, 9);
const labels = ['Discharge', 'Charge', 'Self-use'];
for (let i = 0; i < 3; i++) {
    const s = r.data[i*3], e = r.data[i*3+1], m = r.data[i*3+2];
    const fmt = (v) => `${String(Math.floor(v/60)).padStart(2,'0')}:${String(v%60).padStart(2,'0')}`;
    console.log(`Period ${i+1}: ${fmt(s)}-${fmt(e)} [${labels[m]}]`);
}
client.close();
```

**C#**

```csharp
using NModbus;
using System.Net.Sockets;

// RTU: var port = new SerialPort("/dev/ttyUSB0", 115200);
//      var master = factory.CreateRtuMaster(port);
var tcp = new TcpClient("192.168.1.100", 502);
var factory = new ModbusFactory();
var master = factory.CreateMaster(tcp);

// Eco mode (11151 = 2) and general SOC limits
master.WriteSingleRegister(1, 11151, 2);                     // Eco mode
master.WriteSingleRegister(1, 11108, (ushort)(10.0 * 100));  // SOC_MIN=10%
master.WriteSingleRegister(1, 11109, (ushort)(100.0 * 100)); // SOC_MAX=100%
// Period 1: Charge 00:00-07:00 (charge)
master.WriteMultipleRegisters(1, 11190, new ushort[] { 0, 420, 1 });
// Period 2: Self-use 07:00-17:00
master.WriteMultipleRegisters(1, 11193, new ushort[] { 420, 1020, 2 });
// Period 3: Discharge 17:00-23:00 (discharge)
master.WriteMultipleRegisters(1, 11196, new ushort[] { 1020, 1380, 0 });

// All days (Mon-Sun = 0x7F)
master.WriteSingleRegister(1, 11254, 0x7F);

// Readback verification
var r = master.ReadHoldingRegisters(1, 11190, 9);
string[] labels = { "Discharge", "Charge", "Self-use" };
for (int i = 0; i < 3; i++) {
    int s = r[i*3], e = r[i*3+1], m = r[i*3+2];
    Console.WriteLine($"Period {i+1}: {s/60:D2}:{s%60:D2}-{e/60:D2}:{e%60:D2} [{labels[m]}]");
}
tcp.Close();
```

**Go**

```go
package main
import (
    "fmt"
    "github.com/goburrow/modbus"
    "encoding/binary"
)

func main() {
    // RTU: handler := modbus.NewRTUClientHandler("/dev/ttyUSB0")
    handler := modbus.NewTCPClientHandler("192.168.1.100:502")
    handler.SlaveId = 1
    handler.Connect()
    defer handler.Close()
    client := modbus.NewClient(handler)

    // Eco mode (11151 = 2) and general SOC limits
    client.WriteSingleRegister(11151, 2)          // Eco mode
    client.WriteSingleRegister(11108, uint16(10*100))  // SOC_MIN=10%
    client.WriteSingleRegister(11109, uint16(100*100)) // SOC_MAX=100%
    // Period 1: Charge 00:00-07:00, Period 2: Self-use 07:00-17:00, Period 3: Discharge 17:00-23:00
    periods := []uint16{0, 420, 1, 420, 1020, 2, 1020, 1380, 0}
    buf := make([]byte, len(periods)*2)
    for i, v := range periods { binary.BigEndian.PutUint16(buf[i*2:], v) }
    client.WriteMultipleRegisters(11190, uint16(len(periods)), buf)

    client.WriteSingleRegister(11254, 0x7F) // all days

    // Readback
    r, _ := client.ReadHoldingRegisters(11190, 9)
    labels := []string{"Discharge", "Charge", "Self-use"}
    for i := 0; i < 3; i++ {
        s := binary.BigEndian.Uint16(r[i*6:])
        e := binary.BigEndian.Uint16(r[i*6+2:])
        m := binary.BigEndian.Uint16(r[i*6+4:])
        fmt.Printf("Period %d: %02d:%02d-%02d:%02d [%s]\n", i+1, s/60, s%60, e/60, e%60, labels[m])
    }
}
```

### 4. Peak Shaving / Demand Management (RTU + TCP)

Keep grid import below a set demand limit. The battery discharges to cover the load above the limit, which reduces demand charges.

#### Key Registers

- `10765` Meter_Active_Power_Total: Read, scale 0.01 kW, signed (+export/−import)
- `10671` BMS_Bat1_SOC: Read, scale 0.01 %
- `11700` / `11060` / `12002`: open the EMS session (Quick Start step 2); heartbeat `12026` every 1–5 s
- `11350` Demand_Power_Limit: Write, scale 0.01 kW
- `11045` Active_Power_Set: Write, scale 0.01 kW, signed (+discharge/−charge)
- `14251` Active_Power_Set_Last_Applied: Read, setpoint in force (Setpoint Shadow)

1. **WRITE** · EMS Session · `11700 · 11060 · 12002` · = 1
2. **WRITE** · Demand Limit · `11350` · kW
3. **READ** · Meter Power · `10765` · kW import
4. **DECIDE** · Exceeds Limit? · import > demand
5. **WRITE** · Discharge · `11045` · kW +
6. **READ** · Feedback · `14251` · Applied kW
7. LOOP 1 s

**Python**

```python
from pymodbus.client import ModbusTcpClient
import time

# RTU: from pymodbus.client import ModbusSerialClient
#      client = ModbusSerialClient(port="/dev/ttyUSB0", baudrate=115200)
client = ModbusTcpClient("192.168.1.100", port=502)
client.connect()
UNIT = 1

def signed16(v): return v - 65536 if v >= 32768 else v
def to_unsigned(v): return v + 65536 if v < 0 else v
def w(addr, value): client.write_register(addr, value, slave=UNIT)   # FC 0x06, one register per request
def r(addr): return client.read_holding_registers(addr, 1, slave=UNIT).registers[0]

# Open the EMS session (Quick Start step 2)
w(11700, 0)      # watchdog off while it is configured (11704 is writable only then)
w(11701, 60)     # watchdog timeout 60 s
w(11702, 1)      # action on timeout: self-consumption
w(11704, 1)      # recovery after a timeout: AUTO
w(11700, 1)      # watchdog on
w(11060, 1)      # EMS dispatch on
w(12002, 1)      # remote mode on
w(12026, 1)      # heartbeat: repeat every 1-5 s
rated_kw = r(13034) * 0.01                                  # rated power, kW

DEMAND_LIMIT = 8.0   # maximum grid import in kW
SOC_RESERVE = 15.0   # do not discharge below this SOC (%)

w(11350, int(DEMAND_LIMIT * 100))                # Demand_Power_Limit, 0.01 kW
power_set = 0.0                                  # battery discharge in kW

while True:
    w(12026, 1)                                  # heartbeat
    meter_kw = signed16(r(10765)) * 0.01         # +export / -import
    import_kw = -meter_kw                        # grid import in kW
    soc = r(10671) * 0.01

    if soc > SOC_RESERVE:
        # discharge just enough to bring the import down to the limit
        power_set = max(0.0, min(rated_kw, power_set + import_kw - DEMAND_LIMIT))
    else:
        power_set = 0.0
    w(11045, to_unsigned(int(power_set * 100)))  # +discharge, 0.01 kW
    applied_kw = signed16(r(14251)) * 0.01       # setpoint in force (Setpoint Shadow)
    print(f"Import:{import_kw:.1f}kW Limit:{DEMAND_LIMIT}kW SOC:{soc:.0f}% Bat:{applied_kw:+.1f}kW")
    time.sleep(1)
```

**Node.js**

```javascript
const ModbusRTU = require("modbus-serial");
const client = new ModbusRTU();

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const signed16 = (v) => (v >= 32768 ? v - 65536 : v);
const toUnsigned = (v) => (v < 0 ? v + 65536 : v);
const w = (addr, value) => client.writeRegister(addr, value);            // FC 0x06
const r = async (addr) => (await client.readHoldingRegisters(addr, 1)).data[0];

async function openSession() {                        // Quick Start step 2
    await w(11700, 0);                                // watchdog off while it is configured
    await w(11701, 60);                               // watchdog timeout 60 s
    await w(11702, 1);                                // action on timeout: self-consumption
    await w(11704, 1).catch(() => {});                // recovery AUTO (exception 03 while a LATCH is stored)
    await w(11700, 1);                                // watchdog on
    await w(11060, 1);                                // EMS dispatch on
    await w(12002, 1);                                // remote mode on
    await w(12026, 1);                                // heartbeat: repeat every 1-5 s
}

async function connect() {
    // RTU: await client.connectRTUBuffered("/dev/ttyUSB0", { baudRate: 115200 });
    await client.connectTCP("192.168.1.100", { port: 502 });
    client.setID(1);
    await openSession();
    return (await r(13034)) * 0.01;                   // rated power, kW
}

async function main() {
    const ratedKw = await connect();
    const DEMAND_LIMIT = 8.0;                         // maximum grid import, kW
    const SOC_RESERVE = 15.0;                         // %
    await w(11350, Math.round(DEMAND_LIMIT * 100));   // Demand_Power_Limit, 0.01 kW
    let powerSet = 0.0;
    for (;;) {
        await w(12026, 1);                            // heartbeat
        const importKw = -signed16(await r(10765)) * 0.01;   // 10765 is +export / -import
        const soc = (await r(10671)) * 0.01;
        powerSet = soc > SOC_RESERVE
            ? Math.max(0, Math.min(ratedKw, powerSet + importKw - DEMAND_LIMIT))
            : 0;
        await w(11045, toUnsigned(Math.round(powerSet * 100)));
        const appliedKw = signed16(await r(14251)) * 0.01;   // setpoint in force
        console.log(`Import:${importKw.toFixed(1)}kW SOC:${soc.toFixed(0)}% Bat:${appliedKw.toFixed(1)}kW`);
        await sleep(1000);
    }
}

main().catch((e) => { console.error(e); process.exit(1); });
```

**C#**

```csharp
using NModbus;
using System;
using System.Net.Sockets;
using System.Threading;

// RTU: var port = new System.IO.Ports.SerialPort("/dev/ttyUSB0", 115200); port.Open();
//      var master = new ModbusFactory().CreateRtuMaster(port);
var tcp = new TcpClient("192.168.1.100", 502);
var master = new ModbusFactory().CreateMaster(tcp);
const byte UNIT = 1;

short Signed16(ushort v) => (short)v;
ushort ToUnsigned(int v) => (ushort)(v < 0 ? v + 65536 : v);
void W(ushort addr, ushort value) => master.WriteSingleRegister(UNIT, addr, value);   // FC 0x06
ushort R(ushort addr) => master.ReadHoldingRegisters(UNIT, addr, 1)[0];

// Open the EMS session (Quick Start step 2)
W(11700, 0);                                          // watchdog off while it is configured
W(11701, 60);                                         // watchdog timeout 60 s
W(11702, 1);                                          // action on timeout: self-consumption
try { W(11704, 1); } catch (SlaveException) { }       // recovery AUTO (exception 03 while a LATCH is stored)
W(11700, 1);                                          // watchdog on
W(11060, 1);                                          // EMS dispatch on
W(12002, 1);                                          // remote mode on
W(12026, 1);                                          // heartbeat: repeat every 1-5 s
double ratedKw = R(13034) * 0.01;                     // rated power, kW

const double DemandLimit = 8.0;                       // maximum grid import, kW
const double SocReserve = 15.0;                       // %
W(11350, (ushort)(DemandLimit * 100));                // Demand_Power_Limit, 0.01 kW
double powerSet = 0.0;

while (true) {
    W(12026, 1);                                      // heartbeat
    double importKw = -Signed16(R(10765)) * 0.01;     // 10765 is +export / -import
    double soc = R(10671) * 0.01;
    powerSet = soc > SocReserve
        ? Math.Clamp(powerSet + importKw - DemandLimit, 0.0, ratedKw)
        : 0.0;
    W(11045, ToUnsigned((int)(powerSet * 100)));
    double appliedKw = Signed16(R(14251)) * 0.01;     // setpoint in force
    Console.WriteLine($"Import:{importKw:F1}kW SOC:{soc:F0}% Bat:{appliedKw:+0.0}kW");
    Thread.Sleep(1000);
}
```

**Go**

```go
package main

import (
    "encoding/binary"
    "fmt"
    "math"
    "time"

    "github.com/goburrow/modbus"
)

var client modbus.Client

func w(addr, value uint16) error { _, err := client.WriteSingleRegister(addr, value); return err } // FC 0x06
func r(addr uint16) uint16 {
    b, err := client.ReadHoldingRegisters(addr, 1)
    if err != nil { return 0 }
    return binary.BigEndian.Uint16(b)
}
func kw(v uint16) float64 { return float64(int16(v)) * 0.01 }     // signed, 0.01 kW
func raw(k float64) uint16 { return uint16(int16(math.Round(k * 100))) }

// openSession: Quick Start step 2; returns the rated power in kW
func openSession() float64 {
    w(11700, 0)  // watchdog off while it is configured
    w(11701, 60) // watchdog timeout 60 s
    w(11702, 1)  // action on timeout: self-consumption
    w(11704, 1)  // recovery AUTO (exception 03 while a LATCH is stored)
    w(11700, 1)  // watchdog on
    w(11060, 1)  // EMS dispatch on
    w(12002, 1)  // remote mode on
    w(12026, 1)  // heartbeat: repeat every 1-5 s
    return float64(r(13034)) * 0.01
}

func connect() float64 {
    // RTU: handler := modbus.NewRTUClientHandler("/dev/ttyUSB0") (115200 baud, 8N1)
    handler := modbus.NewTCPClientHandler("192.168.1.100:502")
    handler.SlaveId = 1
    if err := handler.Connect(); err != nil { panic(err) }
    client = modbus.NewClient(handler)
    return openSession()
}

func main() {
    ratedKw := connect()
    demandLimit := 8.0 // maximum grid import, kW
    socReserve := 15.0 // %
    w(11350, uint16(demandLimit*100)) // Demand_Power_Limit, 0.01 kW
    powerSet := 0.0
    for {
        w(12026, 1)                  // heartbeat
        importKw := -kw(r(10765))    // 10765 is +export / -import
        soc := float64(r(10671)) * 0.01
        if soc > socReserve {
            powerSet = math.Max(0, math.Min(ratedKw, powerSet+importKw-demandLimit))
        } else {
            powerSet = 0
        }
        w(11045, raw(powerSet))
        fmt.Printf("Import:%.1fkW SOC:%.0f%% Bat:%+.1fkW\n", importKw, soc, kw(r(14251)))
        time.Sleep(time.Second)
    }
}
```

### 5. Self-Consumption Optimization (RTU + TCP)

Maximize self-consumption of PV energy. Charge the battery with surplus PV energy and discharge it to cover the load when PV generation is insufficient.

#### Key Registers

- `10367` PV_Total_Power: Read, scale 0.01 kW
- `10765` Meter_Active_Power_Total: Read, scale 0.01 kW, signed (+export/−import)
- `10346` Bat_Power_Total: Read, scale 0.01 kW, signed (+discharge/−charge)
- `10671` BMS_Bat1_SOC: Read, scale 0.01 %
- `11700` / `11060` / `12002`: open the EMS session (Quick Start step 2); heartbeat `12026` every 1–5 s
- `11045` Active_Power_Set: Write, scale 0.01 kW, signed (+discharge/−charge)
- `11108` Grid_tied_SOC_MIN: Write, scale 0.01 %, reserve for evening use

1. **WRITE** · EMS Session · `11700 · 11060 · 12002` · = 1
2. **WRITE** · SOC Reserve · `11108` · = 10%
3. **READ** · PV Power · `10367` · kW
4. **READ** · Meter · `10765` · kW ±
5. **READ** · Battery SOC · `10671` · %
6. **DECIDE** · PV Surplus? · export → charge
7. **WRITE** · Power Set · `11045` · kW ±
8. LOOP 1 s

**Python**

```python
from pymodbus.client import ModbusTcpClient
import time

# RTU: from pymodbus.client import ModbusSerialClient
#      client = ModbusSerialClient(port="/dev/ttyUSB0", baudrate=115200)
client = ModbusTcpClient("192.168.1.100", port=502)
client.connect()
UNIT = 1

def signed16(v): return v - 65536 if v >= 32768 else v
def to_unsigned(v): return v + 65536 if v < 0 else v
def w(addr, value): client.write_register(addr, value, slave=UNIT)   # FC 0x06, one register per request
def r(addr): return client.read_holding_registers(addr, 1, slave=UNIT).registers[0]

# Open the EMS session (Quick Start step 2)
w(11700, 0)      # watchdog off while it is configured (11704 is writable only then)
w(11701, 60)     # watchdog timeout 60 s
w(11702, 1)      # action on timeout: self-consumption
w(11704, 1)      # recovery after a timeout: AUTO
w(11700, 1)      # watchdog on
w(11060, 1)      # EMS dispatch on
w(12002, 1)      # remote mode on
w(12026, 1)      # heartbeat: repeat every 1-5 s
rated_kw = r(13034) * 0.01                                  # rated power, kW

SOC_MIN = 20.0   # keep this SOC (%) for the evening
RAMP = 0.5       # maximum change per cycle (kW)
w(11108, int(SOC_MIN * 100))                     # On-Grid minimum SOC, 0.01 %
power_set = 0.0                                  # battery dispatch in kW (+discharge / -charge)

while True:
    w(12026, 1)                                  # heartbeat
    pv_kw = r(10367) * 0.01
    meter_kw = signed16(r(10765)) * 0.01         # +export / -import
    soc = r(10671) * 0.01

    # target: no grid exchange. Exporting -> charge more, importing -> discharge more
    target = power_set - meter_kw
    power_set += max(-RAMP, min(RAMP, target - power_set))
    power_set = max(-rated_kw, min(rated_kw, power_set))
    if soc <= SOC_MIN and power_set > 0: power_set = 0    # stop discharging
    if soc >= 99.5 and power_set < 0: power_set = 0       # stop charging

    w(11045, to_unsigned(int(power_set * 100)))  # 0.01 kW
    print(f"PV:{pv_kw:.2f}kW Meter:{meter_kw:+.2f}kW SOC:{soc:.0f}% Set:{power_set:+.2f}kW")
    time.sleep(1)
```

**Node.js**

```javascript
const ModbusRTU = require("modbus-serial");
const client = new ModbusRTU();

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const signed16 = (v) => (v >= 32768 ? v - 65536 : v);
const toUnsigned = (v) => (v < 0 ? v + 65536 : v);
const w = (addr, value) => client.writeRegister(addr, value);            // FC 0x06
const r = async (addr) => (await client.readHoldingRegisters(addr, 1)).data[0];

async function openSession() {                        // Quick Start step 2
    await w(11700, 0);                                // watchdog off while it is configured
    await w(11701, 60);                               // watchdog timeout 60 s
    await w(11702, 1);                                // action on timeout: self-consumption
    await w(11704, 1).catch(() => {});                // recovery AUTO (exception 03 while a LATCH is stored)
    await w(11700, 1);                                // watchdog on
    await w(11060, 1);                                // EMS dispatch on
    await w(12002, 1);                                // remote mode on
    await w(12026, 1);                                // heartbeat: repeat every 1-5 s
}

async function connect() {
    // RTU: await client.connectRTUBuffered("/dev/ttyUSB0", { baudRate: 115200 });
    await client.connectTCP("192.168.1.100", { port: 502 });
    client.setID(1);
    await openSession();
    return (await r(13034)) * 0.01;                   // rated power, kW
}

async function main() {
    const ratedKw = await connect();
    const SOC_MIN = 20.0;                             // %
    const RAMP = 0.5;                                 // kW per cycle
    await w(11108, Math.round(SOC_MIN * 100));        // On-Grid minimum SOC
    let powerSet = 0.0;
    for (;;) {
        await w(12026, 1);                            // heartbeat
        const meterKw = signed16(await r(10765)) * 0.01;   // +export / -import
        const soc = (await r(10671)) * 0.01;
        const target = powerSet - meterKw;            // no grid exchange
        powerSet += Math.max(-RAMP, Math.min(RAMP, target - powerSet));
        powerSet = Math.max(-ratedKw, Math.min(ratedKw, powerSet));
        if (soc <= SOC_MIN && powerSet > 0) powerSet = 0;
        if (soc >= 99.5 && powerSet < 0) powerSet = 0;
        await w(11045, toUnsigned(Math.round(powerSet * 100)));
        console.log(`Meter:${meterKw.toFixed(2)}kW SOC:${soc.toFixed(0)}% Set:${powerSet.toFixed(2)}kW`);
        await sleep(1000);
    }
}

main().catch((e) => { console.error(e); process.exit(1); });
```

**C#**

```csharp
using NModbus;
using System;
using System.Net.Sockets;
using System.Threading;

// RTU: var port = new System.IO.Ports.SerialPort("/dev/ttyUSB0", 115200); port.Open();
//      var master = new ModbusFactory().CreateRtuMaster(port);
var tcp = new TcpClient("192.168.1.100", 502);
var master = new ModbusFactory().CreateMaster(tcp);
const byte UNIT = 1;

short Signed16(ushort v) => (short)v;
ushort ToUnsigned(int v) => (ushort)(v < 0 ? v + 65536 : v);
void W(ushort addr, ushort value) => master.WriteSingleRegister(UNIT, addr, value);   // FC 0x06
ushort R(ushort addr) => master.ReadHoldingRegisters(UNIT, addr, 1)[0];

// Open the EMS session (Quick Start step 2)
W(11700, 0);                                          // watchdog off while it is configured
W(11701, 60);                                         // watchdog timeout 60 s
W(11702, 1);                                          // action on timeout: self-consumption
try { W(11704, 1); } catch (SlaveException) { }       // recovery AUTO (exception 03 while a LATCH is stored)
W(11700, 1);                                          // watchdog on
W(11060, 1);                                          // EMS dispatch on
W(12002, 1);                                          // remote mode on
W(12026, 1);                                          // heartbeat: repeat every 1-5 s
double ratedKw = R(13034) * 0.01;                     // rated power, kW

const double SocMin = 20.0;                           // %
const double Ramp = 0.5;                              // kW per cycle
W(11108, (ushort)(SocMin * 100));                     // On-Grid minimum SOC
double powerSet = 0.0;

while (true) {
    W(12026, 1);                                      // heartbeat
    double meterKw = Signed16(R(10765)) * 0.01;       // +export / -import
    double soc = R(10671) * 0.01;
    double target = powerSet - meterKw;               // no grid exchange
    powerSet += Math.Clamp(target - powerSet, -Ramp, Ramp);
    powerSet = Math.Clamp(powerSet, -ratedKw, ratedKw);
    if (soc <= SocMin && powerSet > 0) powerSet = 0;
    if (soc >= 99.5 && powerSet < 0) powerSet = 0;
    W(11045, ToUnsigned((int)(powerSet * 100)));
    Console.WriteLine($"Meter:{meterKw:+0.00}kW SOC:{soc:F0}% Set:{powerSet:+0.00}kW");
    Thread.Sleep(1000);
}
```

**Go**

```go
package main

import (
    "encoding/binary"
    "fmt"
    "math"
    "time"

    "github.com/goburrow/modbus"
)

var client modbus.Client

func w(addr, value uint16) error { _, err := client.WriteSingleRegister(addr, value); return err } // FC 0x06
func r(addr uint16) uint16 {
    b, err := client.ReadHoldingRegisters(addr, 1)
    if err != nil { return 0 }
    return binary.BigEndian.Uint16(b)
}
func kw(v uint16) float64 { return float64(int16(v)) * 0.01 }     // signed, 0.01 kW
func raw(k float64) uint16 { return uint16(int16(math.Round(k * 100))) }

// openSession: Quick Start step 2; returns the rated power in kW
func openSession() float64 {
    w(11700, 0)  // watchdog off while it is configured
    w(11701, 60) // watchdog timeout 60 s
    w(11702, 1)  // action on timeout: self-consumption
    w(11704, 1)  // recovery AUTO (exception 03 while a LATCH is stored)
    w(11700, 1)  // watchdog on
    w(11060, 1)  // EMS dispatch on
    w(12002, 1)  // remote mode on
    w(12026, 1)  // heartbeat: repeat every 1-5 s
    return float64(r(13034)) * 0.01
}

func connect() float64 {
    // RTU: handler := modbus.NewRTUClientHandler("/dev/ttyUSB0") (115200 baud, 8N1)
    handler := modbus.NewTCPClientHandler("192.168.1.100:502")
    handler.SlaveId = 1
    if err := handler.Connect(); err != nil { panic(err) }
    client = modbus.NewClient(handler)
    return openSession()
}

func main() {
    ratedKw := connect()
    socMin, ramp := 20.0, 0.5
    w(11108, uint16(socMin*100)) // On-Grid minimum SOC
    powerSet := 0.0
    for {
        w(12026, 1)              // heartbeat
        meterKw := kw(r(10765))  // +export / -import
        soc := float64(r(10671)) * 0.01
        target := powerSet - meterKw // no grid exchange
        powerSet += math.Max(-ramp, math.Min(ramp, target-powerSet))
        powerSet = math.Max(-ratedKw, math.Min(ratedKw, powerSet))
        if soc <= socMin && powerSet > 0 { powerSet = 0 }
        if soc >= 99.5 && powerSet < 0 { powerSet = 0 }
        w(11045, raw(powerSet))
        fmt.Printf("Meter:%+.2fkW SOC:%.0f%% Set:%+.2fkW\n", meterKw, soc, powerSet)
        time.Sleep(time.Second)
    }
}
```

### 6. VPP (Virtual Power Plant) Remote Dispatch (TCP)

A VPP aggregator sends active-power setpoints to a fleet of inverters through its gateway. Prerequisites: EMS control enabled (11060, 12002), the communication watchdog with heartbeat, and logging of every command.

#### Key Registers

- `11060` EMS_Switch_Set: Write 1 to enable EMS
- `12002` Remote_Mode: Write 1 to enable remote control
- `11045` Active_Power_Set: Write, scale 0.01 kW, signed (+discharge/−charge)
- `11700` Comms_Watchdog_Enable: Write 1 after 11701, 11702 and 11704
- `11701` Comms_Watchdog_Timeout: Write seconds, e.g. 60
- `12026` Comms_Heartbeat: Write every 1–5 s, any value except 0x5A5A
- `14044` EMS_Control_Active: Read, 1 = active
- `14039-14040` Last_Cmd_Timestamp: Read, U32_BE, time of the last accepted EMS command (s)
- `14002` PCS_Working_Status: Read current inverter state

1. **WRITE** · Watchdog Setup · `11701–11704` · 60 s / 1 / 1
2. **WRITE** · EMS Enable · `11060` · = 1
3. **WRITE** · Remote Mode · `12002` · = 1
4. **WRITE** · Watchdog On · `11700` · = 1
5. **WRITE** · Power Set · `11045` · kW ±
6. **VERIFY** · EMS Active? · `14044` · = 1
7. **WRITE** · Heartbeat · `12026` · keep-alive
8. **READ** · Timestamp · `14039–14040` · U32 epoch
9. LOOP 2 s

**Python**

```python
from pymodbus.client import ModbusTcpClient
import time

# RTU: from pymodbus.client import ModbusSerialClient
#      client = ModbusSerialClient(port="/dev/ttyUSB0", baudrate=115200)
client = ModbusTcpClient("192.168.1.100", port=502)
client.connect()
UNIT = 1

def signed16(v): return v - 65536 if v >= 32768 else v
def to_unsigned(v): return v + 65536 if v < 0 else v
def w(addr, value): client.write_register(addr, value, slave=UNIT)   # FC 0x06, one register per request
def r(addr): return client.read_holding_registers(addr, 1, slave=UNIT).registers[0]

# Open the EMS session (Quick Start step 2)
w(11700, 0)      # watchdog off while it is configured (11704 is writable only then)
w(11701, 60)     # watchdog timeout 60 s
w(11702, 1)      # action on timeout: self-consumption
w(11704, 1)      # recovery after a timeout: AUTO
w(11700, 1)      # watchdog on
w(11060, 1)      # EMS dispatch on
w(12002, 1)      # remote mode on
w(12026, 1)      # heartbeat: repeat every 1-5 s
rated_kw = r(13034) * 0.01                                  # rated power, kW

# Dispatch 5.00 kW discharge (limited to the rated power)
power_kw = min(5.0, rated_kw)
w(11045, to_unsigned(int(power_kw * 100)))

print("EMS control active:", r(14044) == 1)        # 1 = 11060 and 12002 are both 1
print("Watchdog state:", r(14031))                 # 1 = normal
print("Setpoint in force (kW):", signed16(r(14251)) * 0.01)
hi, lo = client.read_holding_registers(14039, 2, slave=UNIT).registers
print("Last command time (s):", (hi << 16) | lo)   # U32_BE

while True:
    w(12026, 1)                                    # heartbeat every 1-5 s
    if r(14044) != 1:                              # 11060 or 12002 no longer 1, e.g. after an inverter restart
        w(11060, 1)
        w(12002, 1)
        w(11045, to_unsigned(int(power_kw * 100)))  # 11045 reads 0 after a restart
    time.sleep(2)
```

**Node.js**

```javascript
const ModbusRTU = require("modbus-serial");
const client = new ModbusRTU();

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const signed16 = (v) => (v >= 32768 ? v - 65536 : v);
const toUnsigned = (v) => (v < 0 ? v + 65536 : v);
const w = (addr, value) => client.writeRegister(addr, value);            // FC 0x06
const r = async (addr) => (await client.readHoldingRegisters(addr, 1)).data[0];

async function openSession() {                        // Quick Start step 2
    await w(11700, 0);                                // watchdog off while it is configured
    await w(11701, 60);                               // watchdog timeout 60 s
    await w(11702, 1);                                // action on timeout: self-consumption
    await w(11704, 1).catch(() => {});                // recovery AUTO (exception 03 while a LATCH is stored)
    await w(11700, 1);                                // watchdog on
    await w(11060, 1);                                // EMS dispatch on
    await w(12002, 1);                                // remote mode on
    await w(12026, 1);                                // heartbeat: repeat every 1-5 s
}

async function connect() {
    // RTU: await client.connectRTUBuffered("/dev/ttyUSB0", { baudRate: 115200 });
    await client.connectTCP("192.168.1.100", { port: 502 });
    client.setID(1);
    await openSession();
    return (await r(13034)) * 0.01;                   // rated power, kW
}

async function main() {
    const ratedKw = await connect();
    const powerKw = Math.min(5.0, ratedKw);           // 5.00 kW discharge
    await w(11045, toUnsigned(Math.round(powerKw * 100)));
    console.log("EMS control active:", (await r(14044)) === 1);
    console.log("Watchdog state:", await r(14031));   // 1 = normal
    console.log("Setpoint in force (kW):", signed16(await r(14251)) * 0.01);
    for (;;) {
        await w(12026, 1);                            // heartbeat every 1-5 s
        if ((await r(14044)) !== 1) {                 // e.g. after an inverter restart
            await w(11060, 1);
            await w(12002, 1);
            await w(11045, toUnsigned(Math.round(powerKw * 100)));
        }
        await sleep(2000);
    }
}

main().catch((e) => { console.error(e); process.exit(1); });
```

**C#**

```csharp
using NModbus;
using System;
using System.Net.Sockets;
using System.Threading;

// RTU: var port = new System.IO.Ports.SerialPort("/dev/ttyUSB0", 115200); port.Open();
//      var master = new ModbusFactory().CreateRtuMaster(port);
var tcp = new TcpClient("192.168.1.100", 502);
var master = new ModbusFactory().CreateMaster(tcp);
const byte UNIT = 1;

short Signed16(ushort v) => (short)v;
ushort ToUnsigned(int v) => (ushort)(v < 0 ? v + 65536 : v);
void W(ushort addr, ushort value) => master.WriteSingleRegister(UNIT, addr, value);   // FC 0x06
ushort R(ushort addr) => master.ReadHoldingRegisters(UNIT, addr, 1)[0];

// Open the EMS session (Quick Start step 2)
W(11700, 0);                                          // watchdog off while it is configured
W(11701, 60);                                         // watchdog timeout 60 s
W(11702, 1);                                          // action on timeout: self-consumption
try { W(11704, 1); } catch (SlaveException) { }       // recovery AUTO (exception 03 while a LATCH is stored)
W(11700, 1);                                          // watchdog on
W(11060, 1);                                          // EMS dispatch on
W(12002, 1);                                          // remote mode on
W(12026, 1);                                          // heartbeat: repeat every 1-5 s
double ratedKw = R(13034) * 0.01;                     // rated power, kW

double powerKw = Math.Min(5.0, ratedKw);              // 5.00 kW discharge
W(11045, ToUnsigned((int)(powerKw * 100)));
Console.WriteLine($"EMS control active: {R(14044) == 1}");
Console.WriteLine($"Watchdog state: {R(14031)}");     // 1 = normal
Console.WriteLine($"Setpoint in force: {Signed16(R(14251)) * 0.01} kW");

while (true) {
    W(12026, 1);                                      // heartbeat every 1-5 s
    if (R(14044) != 1) {                              // e.g. after an inverter restart
        W(11060, 1);
        W(12002, 1);
        W(11045, ToUnsigned((int)(powerKw * 100)));
    }
    Thread.Sleep(2000);
}
```

**Go**

```go
package main

import (
    "encoding/binary"
    "fmt"
    "math"
    "time"

    "github.com/goburrow/modbus"
)

var client modbus.Client

func w(addr, value uint16) error { _, err := client.WriteSingleRegister(addr, value); return err } // FC 0x06
func r(addr uint16) uint16 {
    b, err := client.ReadHoldingRegisters(addr, 1)
    if err != nil { return 0 }
    return binary.BigEndian.Uint16(b)
}
func kw(v uint16) float64 { return float64(int16(v)) * 0.01 }     // signed, 0.01 kW
func raw(k float64) uint16 { return uint16(int16(math.Round(k * 100))) }

// openSession: Quick Start step 2; returns the rated power in kW
func openSession() float64 {
    w(11700, 0)  // watchdog off while it is configured
    w(11701, 60) // watchdog timeout 60 s
    w(11702, 1)  // action on timeout: self-consumption
    w(11704, 1)  // recovery AUTO (exception 03 while a LATCH is stored)
    w(11700, 1)  // watchdog on
    w(11060, 1)  // EMS dispatch on
    w(12002, 1)  // remote mode on
    w(12026, 1)  // heartbeat: repeat every 1-5 s
    return float64(r(13034)) * 0.01
}

func connect() float64 {
    // RTU: handler := modbus.NewRTUClientHandler("/dev/ttyUSB0") (115200 baud, 8N1)
    handler := modbus.NewTCPClientHandler("192.168.1.100:502")
    handler.SlaveId = 1
    if err := handler.Connect(); err != nil { panic(err) }
    client = modbus.NewClient(handler)
    return openSession()
}

func main() {
    ratedKw := connect()
    powerKw := math.Min(5.0, ratedKw) // 5.00 kW discharge
    w(11045, raw(powerKw))
    fmt.Println("EMS control active:", r(14044) == 1)
    fmt.Println("Watchdog state:", r(14031)) // 1 = normal
    fmt.Println("Setpoint in force (kW):", kw(r(14251)))
    for {
        w(12026, 1) // heartbeat every 1-5 s
        if r(14044) != 1 { // e.g. after an inverter restart
            w(11060, 1)
            w(12002, 1)
            w(11045, raw(powerKw))
        }
        time.Sleep(2 * time.Second)
    }
}
```

### 7. Emergency Stop & Safety Sequence (RTU)

Shut down the inverter in response to a safety event (for example a grid fault, fire detection or a manual emergency stop button) by writing `12021` = 1. The example uses Modbus RTU over RS-485; Modbus TCP works the same way.

#### Key Registers

- `12021` Emergency_Stop: Write 1 to stop power conversion (no unlock required)
- `12000` PowerOn_Switch: reads 0 while the emergency stop is active; `10019` active power falls to 0
- `12001` / `12000`: after operator clearance write 12001 = 1 (clears 12021), then 12000 = 1
- `14100-14199` Alarm registers: Read to check fault codes

1. **READ** · Read State · `14002` · PCS state
2. **WRITE** · Emergency Stop · `12021` · = 1
3. **READ** · Power Switch · `12000` · = 0
4. **VERIFY** · Stopped? · `10019` · 0 kW
5. **READ** · Alarm Codes · `14100+` · Check faults
6. **WRITE** · Clear Stop · `12001` · = 1
7. **WRITE** · Restart · `12000` · = 1

**Python**

```python
from pymodbus.client import ModbusSerialClient   # Modbus RTU over RS-485
# from pymodbus.client import ModbusTcpClient    # Modbus TCP alternative
import time

client = ModbusSerialClient(port="/dev/ttyUSB0", baudrate=115200)
# client = ModbusTcpClient("192.168.1.100", port=502)
client.connect()
UNIT = 1

def signed16(v): return v - 65536 if v >= 32768 else v
def r(addr): return client.read_holding_registers(addr, 1, slave=UNIT).registers[0]

# Emergency stop: one write, no unlock required
client.write_register(12021, 1, slave=UNIT)

# Confirm: 12021 reads 1, 12000 is held at 0 and the AC output falls to 0
time.sleep(2)
print("12021 =", r(12021), "12000 =", r(12000), "P =", signed16(r(10019)) * 0.01, "kW")

# Alarm registers for the diagnosis
rr = client.read_holding_registers(14100, 20, slave=UNIT)
print("Alarm registers with bits set:", [14100 + i for i, v in enumerate(rr.registers) if v != 0])

# Restart only after the operator has cleared the cause:
# client.write_register(12001, 1, slave=UNIT)   # clears the emergency stop (12021 reads 0 again)
# time.sleep(2)
# client.write_register(12000, 1, slave=UNIT)   # power on
```

**Node.js**

```javascript
const ModbusRTU = require("modbus-serial");
const client = new ModbusRTU();
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const signed16 = (v) => (v >= 32768 ? v - 65536 : v);
const r = async (addr) => (await client.readHoldingRegisters(addr, 1)).data[0];

async function emergencyStop() {
    await client.connectRTUBuffered("/dev/ttyUSB0", { baudRate: 115200 });   // Modbus RTU over RS-485
    // await client.connectTCP("192.168.1.100", { port: 502 });             // Modbus TCP alternative
    client.setID(1);

    await client.writeRegister(12021, 1);             // emergency stop, no unlock required

    await sleep(2000);                                // confirm: 12021 = 1, 12000 = 0, output 0 kW
    console.log("12021 =", await r(12021), "12000 =", await r(12000),
                "P =", signed16(await r(10019)) * 0.01, "kW");

    const alarms = await client.readHoldingRegisters(14100, 20);
    console.log("Alarm registers with bits set:",
                alarms.data.map((v, i) => (v ? 14100 + i : null)).filter((a) => a !== null));

    // Restart only after the operator has cleared the cause:
    // await client.writeRegister(12001, 1);          // clears the emergency stop
    // await sleep(2000);
    // await client.writeRegister(12000, 1);          // power on
}
emergencyStop().catch((e) => { console.error(e); process.exit(1); });
```

**C#**

```csharp
using NModbus;
using System;
using System.IO.Ports;
using System.Threading;

var port = new SerialPort("/dev/ttyUSB0", 115200, Parity.None, 8, StopBits.One);   // Modbus RTU over RS-485
port.Open();
var master = new ModbusFactory().CreateRtuMaster(port);
// TCP: var master = new ModbusFactory().CreateMaster(new System.Net.Sockets.TcpClient("192.168.1.100", 502));
const byte UNIT = 1;
ushort R(ushort addr) => master.ReadHoldingRegisters(UNIT, addr, 1)[0];

master.WriteSingleRegister(UNIT, 12021, 1);           // emergency stop, no unlock required

Thread.Sleep(2000);                                   // confirm: 12021 = 1, 12000 = 0, output 0 kW
Console.WriteLine($"12021 = {R(12021)}, 12000 = {R(12000)}, P = {(short)R(10019) * 0.01} kW");

var alarms = master.ReadHoldingRegisters(UNIT, 14100, 20);
for (int i = 0; i < alarms.Length; i++)
    if (alarms[i] != 0) Console.WriteLine($"Alarm register {14100 + i}: 0x{alarms[i]:X4}");

// Restart only after the operator has cleared the cause:
// master.WriteSingleRegister(UNIT, 12001, 1);        // clears the emergency stop
// Thread.Sleep(2000);
// master.WriteSingleRegister(UNIT, 12000, 1);        // power on
```

**Go**

```go
package main

import (
    "encoding/binary"
    "fmt"
    "time"

    "github.com/goburrow/modbus"
)

func main() {
    handler := modbus.NewRTUClientHandler("/dev/ttyUSB0") // Modbus RTU over RS-485
    handler.BaudRate, handler.DataBits, handler.Parity, handler.StopBits = 115200, 8, "N", 1
    handler.SlaveId = 1
    // TCP: handler := modbus.NewTCPClientHandler("192.168.1.100:502")
    if err := handler.Connect(); err != nil { panic(err) }
    defer handler.Close()
    client := modbus.NewClient(handler)
    r := func(addr uint16) uint16 { b, _ := client.ReadHoldingRegisters(addr, 1); return binary.BigEndian.Uint16(b) }

    client.WriteSingleRegister(12021, 1) // emergency stop, no unlock required

    time.Sleep(2 * time.Second) // confirm: 12021 = 1, 12000 = 0, output 0 kW
    fmt.Println("12021 =", r(12021), "12000 =", r(12000), "P =", float64(int16(r(10019)))*0.01, "kW")

    b, _ := client.ReadHoldingRegisters(14100, 20)
    for i := 0; i+1 < len(b); i += 2 {
        if v := binary.BigEndian.Uint16(b[i:]); v != 0 { fmt.Printf("Alarm register %d: 0x%04X\n", 14100+i/2, v) }
    }

    // Restart only after the operator has cleared the cause:
    // client.WriteSingleRegister(12001, 1) // clears the emergency stop
    // time.Sleep(2 * time.Second)
    // client.WriteSingleRegister(12000, 1) // power on
}
```

### 8. SG-Ready Heat Pump Coordination (RTU)

Control an SG Ready heat pump through the MATIC dry-contact relay outputs. SG Ready is specified by **BWP e.V. "Technical Interface Specifications for SG Ready" v1.1 (2025-05-01)** as a three-state dry-contact interface (*blocked / normal / switch-on recommended*). Configure the outputs with `11380–11399` and read their status at `14126–14139`: set `11380 DC_Mode = 1` to enable SG Ready mode, then write the BWP state (1/2/3) to `11355 Heatpump_Hint_Mode`. The inverter maps the value to the contacts as defined in BWP v1.1.

#### Key Registers

- `11355` Heatpump_Hint_Mode: Write 1-3 (drives native dry-contact relays when DC_Mode = 1)    
   1 = Blocked (BWP state 1: EVU-Sperre / utility block)    
   2 = Standard (BWP state 2: default operation)    
   3 = Surplus recommended (BWP state 3: PV/battery surplus available)    
   *When DC_Mode = 1 (SG-Ready), firmware maps this value directly to native dry-contact outputs per BWP v1.1 contact table. No external relay module required.*
- `10367` PV_Total_Power: Read, scale 0.01 kW
- `10765` Meter_Active_Power_Total: Read, scale 0.01 kW, signed (+export/−import)
- `10671` BMS_Bat1_SOC: Read, scale 0.01 %
- `11060` EMS_Switch_Set: Write 1 to enable EMS
- `11380` DC_Mode: Write 1 to enable SG-Ready mode (native dry-contact output)
- `14128` DC_Active_BWP_State: Read, BWP state currently applied to the contacts
- `14129` DC_State_Source: Read, source that currently controls the contacts (0=Uninit, 1=Modbus, 2=Auto, 3=§14a, 4=Watchdog, 5=Fault, 6=EMS Direct)

1. **WRITE** · EMS Enable · `11060` · = 1
2. **READ** · PV Power · `10367` · kW
3. **READ** · Meter · `10765` · kW ±
4. **READ** · Battery SOC · `10671` · %
5. **DECIDE** · BWP State? · 1/2/3
6. **WRITE** · Heatpump Hint · `11355` · State 1-3
7. LOOP 60 s

**Python**

```python
from pymodbus.client import ModbusSerialClient
# from pymodbus.client import ModbusTcpClient
import time

client = ModbusSerialClient(port="/dev/ttyUSB0", baudrate=115200)
# client = ModbusTcpClient("192.168.1.100", port=502)
client.connect()
UNIT = 1

# Enable EMS
client.write_register(11060, 1, slave=UNIT)

# Enable SG-Ready dry-contact output
client.write_register(11380, 1, slave=UNIT)  # DC_Mode = 1 (SG-Ready)

HYSTERESIS_W = 500    # 500 W deadband
HOLD_TIME = 60        # Seconds before mode change
last_mode = 2
last_change = 0

def read_signed(addr):
    rr = client.read_holding_registers(addr, 1, slave=UNIT)
    v = rr.registers[0]
    return (v - 65536 if v > 32767 else v)

while True:
    rr = client.read_holding_registers(10367, 1, slave=UNIT)
    pv_kw = rr.registers[0] * 0.01              # PV generation

    grid_w = read_signed(10765) * 10             # Meter power (W), +export / -import
    surplus_kw = grid_w / 1000.0 if grid_w > 0 else 0

    rr = client.read_holding_registers(10671, 1, slave=UNIT)
    soc = rr.registers[0] * 0.01                # Battery SOC %

    # Heatpump_Hint_Mode state machine (BWP v1.1 3-state model)
    if surplus_kw > (2.0 + HYSTERESIS_W/1000) and soc > 80:
        new_mode = 3   # Surplus recommended (BWP state 3)
    elif surplus_kw < 0.5:
        new_mode = 2   # Standard (BWP state 2)
    else:
        new_mode = last_mode  # Hold current
    # Note: BWP state 1 (Blocked) is set by the DSO / EVU, not by EMS surplus logic

    if new_mode != last_mode and time.time() - last_change > HOLD_TIME:
        client.write_register(11355, new_mode, slave=UNIT)
        last_mode = new_mode
        last_change = time.time()

    time.sleep(10)  # Poll every 10 s
```

**Node.js**

```javascript
const ModbusRTU = require('modbus-serial');
const client = new ModbusRTU();

const HYSTERESIS_KW = 0.5;   // 500 W deadband
const HOLD_TIME_MS = 60000;  // 60 s hold timer
let lastMode = 2, lastChange = 0;

async function sgReadyLoop() {
    await client.connectRTUBuffered("/dev/ttyUSB0", { baudRate: 115200 });
    // await client.connectTCP("192.168.1.100", { port: 502 });
    client.setID(1);
    await client.writeRegister(11060, 1);  // Enable EMS
    await client.writeRegister(11380, 1);  // DC_Mode = 1 (SG-Ready dry-contact output)

    const toSigned = (v) => v > 32767 ? v - 65536 : v;

    setInterval(async () => {
        const pv = await client.readHoldingRegisters(10367, 1);
        const pvKw = pv.data[0] * 0.01;

        const meter = await client.readHoldingRegisters(10765, 1);
        const gridW = toSigned(meter.data[0]) * 10;
        const surplusKw = gridW > 0 ? gridW / 1000 : 0;   // 10765: +export / -import

        const bat = await client.readHoldingRegisters(10671, 1);
        const soc = bat.data[0] * 0.01;

        // Heatpump_Hint_Mode state machine (BWP v1.1 3-state model)
        let newMode = lastMode;
        if (surplusKw > 2.0 + HYSTERESIS_KW && soc > 80) newMode = 3;       // Surplus recommended
        else if (surplusKw < 0.5) newMode = 2;                                // Standard
        // Note: BWP state 1 (Blocked) is set by DSO / EVU, not by EMS surplus logic

        const now = Date.now();
        if (newMode !== lastMode && now - lastChange > HOLD_TIME_MS) {
            await client.writeRegister(11355, newMode);
            console.log(`Heatpump hint: BWP state ${lastMode} -> ${newMode} (SOC: ${soc.toFixed(1)}%)`);
            lastMode = newMode;
            lastChange = now;
        }
    }, 10000); // Poll every 10 s
}
sgReadyLoop().catch(console.error);
```

**C#**

```csharp
using NModbus;
using System.IO.Ports;
// using System.Net.Sockets;

var port = new SerialPort("/dev/ttyUSB0", 115200, Parity.None, 8, StopBits.One);
port.Open();
var master = new ModbusFactory().CreateRtuMaster(port);
// var tcp = new TcpClient("192.168.1.100", 502);
// var master = new ModbusFactory().CreateMaster(tcp);
byte unit = 1;

master.WriteSingleRegister(unit, 11060, 1);  // Enable EMS
master.WriteSingleRegister(unit, 11380, 1);  // DC_Mode = 1 (SG-Ready dry-contact output)

int lastMode = 2;
DateTime lastChange = DateTime.MinValue;
const double HysteresisKw = 0.5;

while (true) {
    var pv = master.ReadHoldingRegisters(unit, 10367, 1);
    double pvKw = pv[0] * 0.01;

    var meter = master.ReadHoldingRegisters(unit, 10765, 1);
    double gridW = (short)meter[0] * 10.0;
    double surplusKw = gridW > 0 ? gridW / 1000 : 0;   // 10765: +export / -import

    var bat = master.ReadHoldingRegisters(unit, 10671, 1);
    double soc = bat[0] * 0.01;

    // Heatpump_Hint_Mode state machine (BWP v1.1 3-state model)
    int newMode = lastMode;
    if (surplusKw > 2.0 + HysteresisKw && soc > 80) newMode = 3;          // Surplus recommended
    else if (surplusKw < 0.5) newMode = 2;                                  // Standard
    // Note: BWP state 1 (Blocked) is set by DSO / EVU, not by EMS surplus logic

    if (newMode != lastMode && (DateTime.Now - lastChange).TotalSeconds > 60) {
        master.WriteSingleRegister(unit, 11355, (ushort)newMode);
        Console.WriteLine($"Heatpump hint: BWP state {lastMode} -> {newMode} (SOC: {soc:F1}%)");
        lastMode = newMode;
        lastChange = DateTime.Now;
    }
    Thread.Sleep(10000);
}
```

**Go**

```go
package main

import (
    "encoding/binary"
    "fmt"
    "time"
    "github.com/goburrow/modbus"
)

func main() {
    handler := modbus.NewRTUClientHandler("/dev/ttyUSB0")
    handler.BaudRate = 115200
    handler.SlaveId = 1
    // handler := modbus.NewTCPClientHandler("192.168.1.100:502")
    handler.Connect()
    defer handler.Close()
    client := modbus.NewClient(handler)

    client.WriteSingleRegister(11060, 1) // Enable EMS
    client.WriteSingleRegister(11380, 1) // DC_Mode = 1 (SG-Ready dry-contact output)

    lastMode, hysteresisKw := 2, 0.5
    lastChange := time.Now().Add(-2 * time.Minute)

    for {
        pv, _ := client.ReadHoldingRegisters(10367, 1)
        pvKw := float64(binary.BigEndian.Uint16(pv)) * 0.01

        meter, _ := client.ReadHoldingRegisters(10765, 1)
        gridW := float64(int16(binary.BigEndian.Uint16(meter))) * 10
        surplusKw := 0.0
        if gridW > 0 { surplusKw = gridW / 1000 } // 10765: +export / -import

        bat, _ := client.ReadHoldingRegisters(10671, 1)
        soc := float64(binary.BigEndian.Uint16(bat)) * 0.01

        // Heatpump_Hint_Mode state machine (BWP v1.1 3-state model)
        newMode := lastMode
        if surplusKw > 2.0+hysteresisKw && soc > 80 {
            newMode = 3   // Surplus recommended
        } else if surplusKw < 0.5 {
            newMode = 2   // Standard
        }
        // Note: BWP state 1 (Blocked) is set by DSO / EVU, not by EMS surplus logic

        if newMode != lastMode && time.Since(lastChange) > 60*time.Second {
            client.WriteSingleRegister(11355, uint16(newMode))
            fmt.Printf("Heatpump hint: BWP state %d -> %d (SOC: %.1f%%, PV: %.1fkW)\n",
                lastMode, newMode, soc, pvKw)
            lastMode = newMode
            lastChange = time.Now()
        }
        time.Sleep(10 * time.Second)
    }
}
```

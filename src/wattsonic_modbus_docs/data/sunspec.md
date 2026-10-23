# MATIC · SunSpec Modbus Interface Specification

> Machine-readable copy of https://modbus.wattsonic.com/sunspec.html (English). Applies to ARM firmware M013V1130B01D05 or later. Edition 2026-10-23. Generated from the published page; the HTML page is authoritative.

SunSpec information models over Modbus TCP, port 502, for the Wattsonic MATIC hybrid inverter series. Applies to main controller firmware M013V1130B01D05 and later. Issued 2026-10-23.

## Overview

The SunSpec Modbus interface publishes the inverter, its PV inputs, the battery and the grid meter as standard SunSpec information models, and accepts supervisory commands from one energy management system: an active-power limit, a power-factor or reactive-power setpoint, and battery charge and discharge commands.

- **Registers**: 479
- **Points**: 314
- **Models**: 9
- **Writable points**: 29

| Item | Content |
|---|---|
| Product | Wattsonic MATIC three-phase hybrid PV and storage inverter (10–25 kW), one battery input. |
| Firmware | Main controller firmware `M013V1130B01D05` and later. The third field of the Common model point `1.Vr` (`V<DC>.<AC>.<main>`) identifies the main controller firmware; it must read 1130 or higher. |
| Register map | SunSpec identifier at `40000`, nine information models (1, 123, 124, 103, 203, 120, 121, 122, 160) and the end model: 479 registers, `40000`–`40478`. |
| Interface | Modbus TCP, port `502`, unit identifier `1` by default. Reads are possible on every Modbus interface; writes only over Modbus TCP port 502, and only while the control gate is open. |
| Issued | 2026-10-23 |

### Relation to the native register map

The SunSpec map is an additional view of the same inverter. The native Wattsonic register map remains available unchanged on the same port and the same connection; it is documented in the [native EMS register map](native.md). Native register numbers quoted on this page (for example *native 10019*) refer to that map.

### Conventions

- Register addresses are 0-based PDU addresses, exactly as transmitted. A client that uses 1-based “4x” notation addresses register `40000` as 40001.
- A point is named by its model number and point name, for example `103.W`. Point names, types and symbols are those of the SunSpec model definitions.
- Hexadecimal values carry the prefix `0x`; all other numbers are decimal.

### Conditions of use

- SunSpec control is disabled when the product leaves the factory. It is enabled on site with the control gate, native register `11790`.
- The interface is not a protective function and must not be used for islanding detection, protection trips or any function on which the safety of persons or of the installation depends. It is not a metering function and is not suitable for billing.
- SunSpec control commands are held in volatile memory: re-send them after every restart of the product. To switch the inverter on or off, use native `12000` in the native register map.

> **NOTICE**
>
> **No authentication.** While the control gate is open, any Modbus TCP client that reaches port 502 can command the inverter, and any client can write the gate register itself. Operate the product on a network segment reserved for the energy management system, and close the gate when SunSpec control is not in use.

## Interface and sessions

Transport, sessions, function codes and the order in which a request is checked.

### Transport and ports

| Interface | Read | Write to the SunSpec map |
|---|---|---|
| Ethernet, Modbus TCP port 502 | Yes | Yes, while the control gate is open and the connection holds write control. |
| Wi-Fi, Modbus TCP port 502 (if fitted) | Yes | Yes, while the control gate is open and the connection holds write control. |
| RS-485, Modbus RTU (EMS port) | Yes | Use Modbus TCP port 502 for writes; writes over RS-485 are answered with exception `0x02`. |
| TCP port 5001 (commissioning tools) | Use port 502 | Use port 502; writes on port 5001 are answered with exception `0x02`. |

Over RS-485 the SunSpec map can be read; writes go to Modbus TCP port 502. **Modbus RTU on RS-485** (115200 baud, 8N1) answers the unit ID set in native `11007`; 0 and 255 are not answered, and 90 cannot be used on RS-485. In the factory setting the port also searches the same bus for a heat pump or boiler: until the first request addressed to the inverter arrives, it listens for 3 s and then probes at 19.2 kbaud for about 1.2 s, so a request sent after a restart can time out. Repeat it: once a request addressed to the inverter has been answered, the port stays with the EMS until the next restart. To reserve the port for the EMS, write native `19074` = 1; the value is stored and applies from the next restart. A port that serves a heat pump or boiler does not answer an EMS.

The SunSpec map and the native register map share port 502 and the same connection. Each request is routed by its start address: a request that starts inside `40000`–`40478` is served from the SunSpec map and must end at or before `40478`; a request that starts below `40000` is served from the native map. One request never covers registers of both maps; use separate requests.

On Ethernet the unit announces itself by mDNS / DNS-SD as service `_modbus._tcp` on port 502. The instance name is the serial number and the TXT record is `protocol=modbus-tcp`.

### Unit identifier

On Modbus TCP the unit identifier must equal the configured device address (native `11007`, factory default 1) or be 0 or 255. A request for any other unit identifier is ignored without any response. On Modbus RTU it must equal native `11007`. The configured address is published at `1.DA`.

### Function codes

| Code | Content |
|---|---|
| `0x03` | Read Holding Registers: 1 to 125 registers. A request that starts in the SunSpec map must not run past `40478`. |
| `0x04` | Read Input Registers: served from the SunSpec map with exactly the same rules as `0x03`. |
| `0x06` | Write Single Register: for every writable point, while the control gate is open. |
| `0x10` | Write Multiple Registers: 1 to 123 registers, all-or-nothing, while the control gate is open. One frame may span several points and several controls. |
| Other | Exception `0x01` ILLEGAL FUNCTION. |

### Sessions and write control

- Ethernet port 502 accepts two concurrent client sessions. Opening a connection does not close the session of the client that holds write control. When both sessions are in use, a new connection replaces a session that has been idle for 30 s or that does not hold write control; if neither session can be replaced, the new connection is refused. While a local firmware transfer is running, new connections are refused.
- **Write control.** On Ethernet port 502 one connection at a time may write. The first connection whose write is executed holds write control; a write from any other connection is answered with exception `0x06` and is not executed. Reads are never restricted. Write control is released when its connection closes, or after 30 s without an executed write; a new connection from the same IP address takes it over at once. Wi-Fi port 502 has its own, independent write control.
- Use only one energy management system for writing, and keep its write interval well below 30 s (the keep-alive of the control interface serves this purpose).
- **Read-only reader.** One IP address can be configured as a read-only reader: native `19024` holds the first two octets and `19025` the last two, one octet per byte, high byte first; 0 (factory default) means no reader. A client at that address always uses the second session, never obtains write control (its writes are answered with exception `0x06`) and never displaces the connection that holds write control.
- TCP port 5001 is the service port of Wattsonic commissioning tools. In the default configuration it has its own sessions and neither takes nor closes a port 502 session. Do not use it for integration.

### Framing, pipelining and timeouts

- On every port 502 connection, Ethernet and Wi-Fi, the unit reassembles a request that is split across TCP segments and processes several complete requests in one segment in order, answering each. A request is processed only when its response can be sent; the remaining data waits under TCP flow control, so no response is lost.
- An incomplete fragment is discarded after 100 ms if no further bytes arrive, or after 5 s if it would be completed by bytes that arrive together with another request. A segment whose MBAP length field is 0 or above 255 (for example function code `0x10` for more than 124 registers) is discarded from that point without a response; after a discarded fragment, write requests in the rest of that segment are dropped without a response.
- Recommended: one outstanding request at a time, and one long-lived session. The device does not close an idle session. Response times are not specified; set the client timeout from measurements on the installed unit and do not repeat a request before its timeout has expired.
- After a lost connection, open a new session and read the SunSpec identifier at `40000` before resuming. After a restart of the product every SunSpec control is released; re-send the commands that are to remain in force.

### Evaluation order and exception responses

A request is checked in the order below; the first condition that applies decides the response. An exception response carries the function code with bit 7 set and the exception code: `0x01` ILLEGAL FUNCTION, `0x02` ILLEGAL DATA ADDRESS, `0x03` ILLEGAL DATA VALUE, `0x04` SERVER DEVICE FAILURE, `0x06` SERVER DEVICE BUSY. Because the gate is checked before the writable points are looked up, every well-formed write inside the map is answered `0x04` while the gate is closed.

| Step | Condition | Response |
|---|---|---|
| 0 | Modbus TCP only: MBAP length field 0 or above 255 (for example function code 0x10 for more than 124 registers); this request and the rest of its TCP segment are discarded. | No response |
| 1 | Modbus TCP only: write request in the remainder of a segment after a discarded incomplete fragment. | No response |
| 2 | Unit identifier not equal to the configured address (native 11007, default 1) and, on Modbus TCP, not 0 or 255; or request PDU shorter than 4 bytes. | No response |
| 3 | Modbus TCP port 502 only: a write (0x06/0x10) addressed to this unit from a connection that does not hold write control (including the configured read-only reader), regardless of the register address. | `0x06` |
| 4 | Function code other than 0x03, 0x04, 0x06 or 0x10. | `0x01` |
| 5 | Read (0x03/0x04) starting inside 40000–40478 with quantity 0 or quantity > 125, or running past 40478. | `0x03` |
| 6 | Read starting after 40478, the last register of the SunSpec map. | `0x02` |
| 7 | Malformed 0x06/0x10 frame: length does not match the function code, byte count is not 2 × quantity, quantity is 0, or quantity > 125. | `0x03` |
| 8 | Write to 40000–40478 over any interface other than Modbus TCP port 502 (Ethernet or Wi-Fi), for example RS-485 or service port 5001. | `0x02` |
| 9 | Write starting after 40478, the last register of the SunSpec map. | `0x02` |
| 10 | Write starting inside the map whose run passes 40478 (the END block). | `0x02` |
| 11 | Control gate closed (native 11790 not 0x5355). | `0x04` |
| 12 | Machine veto (see the Machine veto section). | `0x04` |
| 13 | Registers checked one by one in ascending address order; the first register that fails decides: not writable (read-only point, scale factor, model ID/length, END marker, or a model RW point this unit does not accept) gives 0x02; outside its range, or a fixed-value point written with a value other than the published one, gives 0x03. | `0x02` / `0x03` |
| 14 | RvrtTms not 0 and not greater than WinTms (after merging the frame into the values in force), or one frame that enables both the power-factor and the reactive-power setpoint. | `0x03` |
| 15 | A stored setting (124.WChaMax, 124.MinRsvPct) changed again within 600 s. | `0x06` |
| 16 | All checks passed: the request is executed and a normal response is returned. | Normal response |

## Data representation

Word order, data types, scale factors, not-implemented values and sign conventions.

### Width and word order

Registers are 16 bits wide and are transmitted high byte first. Values that occupy two registers (`acc32`, `uint32`, `bitfield32`) are transmitted most-significant word first, the SunSpec convention. No word swap is applied.

### Data types

| Type | Registers | Definition | Not-implemented value | Points |
|---|---|---|---|---|
| uint16 | 1 | Unsigned 16-bit integer. | `0xFFFF` | 89 |
| int16 | 1 | Signed 16-bit integer, two's complement. | `0x8000` | 66 |
| enum16 | 1 | Unsigned 16-bit enumeration; the values are listed with the model. | `0xFFFF` | 17 |
| bitfield16 | 1 | 16 independent flags. | `0xFFFF` | 5 |
| bitfield32 | 2 | 32 independent flags, most-significant word first. | `0xFFFFFFFF` | 14 |
| uint32 | 2 | Unsigned 32-bit integer, most-significant word first. | `0xFFFFFFFF` | 5 |
| acc32 | 2 | 32-bit accumulator, most-significant word first, monotonically increasing. 0 means not accumulated. | None | 37 |
| acc64 | 4 | 64-bit accumulator, most-significant word first. 0 means not accumulated. | None | 6 |
| sunssf | 1 | Signed 16-bit scale factor, a power of ten. | `0x8000` | 59 |
| string | n | ASCII, two characters per register, high byte first, padded with NUL; trim at the first NUL. | All NUL bytes | 10 |
| count | 1 | Unsigned 16-bit repeat count of a repeating block. | `0xFFFF` | 1 |
| pad | 1 | Alignment register; reads 0x0000. | — | 2 |

### Scale factors

A measured point references a scale factor register of type `sunssf`. The engineering value is the raw value multiplied by ten to the power of the scale factor; for example `103.PhVphA` = 2343 with `V_SF` = −1 is 234.3 V. All scale factors of this device are constants: read them once per session from the device and cache them.

### Implementation status

| Impl. | Content | Points | Registers |
|---|---|---|---|
| Yes | The point carries a value at all times. | 142 | 206 |
| Cond. | The point reads its not-implemented value under the conditions in its description, for example while the meter is lost, while a PV input does not exist on the model, or while no client holds its control. | 67 | 67 |
| No | The point always reads its not-implemented value; an accumulator that is not maintained reads 0. | 102 | 202 |

A point that is not available reads the not-implemented value of its type and must not be displayed as zero or as a measured value. Accumulators have no not-implemented value: an accumulator that is not maintained reads 0.

### Sign conventions and points of measurement

| Points | Content |
|---|---|
| `103.W`, `103.VA` | Positive = AC output of the inverter. Measured at the inverter terminals. |
| `203.W` | Measured by the energy meter at the grid connection point. Positive = export to the grid, negative = import. |
| `203.A`, `203.AphA`–`AphC` | Meter phase currents in 0.1 A; the direction follows `203.W`. |
| `124.OutWRte`, `124.InWRte` | Battery power bounds in percent of `124.WChaMax`; a negative value forces the opposite direction. |
| `124.ChaSt`, native `10346`, `10339` | Positive battery power and current = discharge, as in the native register map. |
| `123.VArMaxPct`, `123.OutPFSet` | The sign is passed unchanged to the native reactive-power and power-factor setpoints; native positive reactive power = leading (capacitive). |
| `120.VArRtgQ1`–`Q4`, `120.PFRtgQ1`–`Q4` | Quadrant signs + + − − (var) and + − + − (power factor). |

## Model chain discovery

Locate every model by walking the model chain from 40000; do not use fixed register addresses.

1. Open one Modbus TCP session to port 502 with the configured unit identifier and keep it open.
2. Read registers `40000` and `40001`. They read `0x5375 0x6E53`, ASCII “SunS”.
3. Walk the chain from `40002`: read the model identifier and the model length L; the next model begins L + 2 registers further on. Repeat until the identifier reads `0xFFFF`. On this firmware the walk visits nine models and ends at `40477`.
4. Address every point from the walk: the address of a point is the address of its model identifier plus the offset in the column *Off.* of the register tables.
5. Read the scale factors once per session and use them to decode the measured values.

> **NOTICE**
>
> **Reads at fixed addresses can return the wrong points without an exception.** The map is served as one contiguous block and model boundaries are not checked: a read that starts in the map and ends at or before 40478 is always answered. Derive the address of every model from the chain in each new session and check the model identifier and length before decoding.

### Model chain

| Identifier at | Model | L | Block | Registers | Content |
|---|---|---|---|---|---|
| `40000` | SunS | — | 40000–40001 | 2 | SunSpec identifier 0x5375 0x6E53 |
| `40002` | 1 | 66 | 40002–40069 | 68 | Model 1 · Common |
| `40070` | 123 | 24 | 40070–40095 | 26 | Model 123 · Immediate controls |
| `40096` | 124 | 24 | 40096–40121 | 26 | Model 124 · Storage |
| `40122` | 103 | 50 | 40122–40173 | 52 | Model 103 · Inverter, three-phase |
| `40174` | 203 | 105 | 40174–40280 | 107 | Model 203 · Meter, three-phase wye |
| `40281` | 120 | 26 | 40281–40308 | 28 | Model 120 · Nameplate |
| `40309` | 121 | 30 | 40309–40340 | 32 | Model 121 · Basic settings |
| `40341` | 122 | 44 | 40341–40386 | 46 | Model 122 · Measurements and status |
| `40387` | 160 | 88 | 40387–40476 | 90 | Model 160 · Multiple MPPT inverter extension |
| `40477` | End | 0 | 40477–40478 | 2 | End model, identifier 0xFFFF |

L counts the data registers of a model; the identifier and length registers are additional. The map ends at `40478`.

### Discovery request

**Discovery: read the SunSpec identifier**

*Request*

```text
00 01 00 00 00 06 01 03 9C 40 00 02
```

*Response*

```text
00 01 00 00 00 07 01 03 04 53 75 6E 53
```

## Polling

Refresh rate of the map and recommended read windows.

The SunSpec map is refreshed from the inverter once per second. Apart from the echo of an accepted write, polling faster than once per second returns unchanged values. Exception: the per-input PV values of model 160 switch to the not-implemented value as soon as the DC converter data are older than 10 s.

Registers read in separate requests may come from different refresh cycles. Read quantities that are evaluated together in a single request; the read windows below are arranged for this purpose. Each window can be read with `0x03` or `0x04`.

| Block | Request | Content | Spare | Interval |
|---|---|---|---|---|
| Control start | `start 40070, count 104` | Model 123 complete; model 124 complete; model 103 complete | 21 | 1 s |
| Four models | `start 40070, count 104`<br>`start 40174, count 107` | As control start, plus model 203 complete | 21 / 18 | 1 s to 5 s |
| Telemetry fast path | `start 40104, count 125` | Model 124 from ChaState to InOutWRte_SF; model 103 complete; model 203 from ID to TotWh_SF | 0 | 1 s |

The start addresses below are derived from the chain on this firmware. Compute each start address from the address of the model identifier of the first model in the window, and each count from the model lengths (L + 2 registers per model). The telemetry fast path is exactly 125 registers, the maximum for one request.

| Model | Request | Content | Interval |
|---|---|---|---|
| Model 1 · Common | `start 40002, count 68` | Identity: manufacturer, model, serial number, firmware version | Once per session |
| Model 120 · Nameplate | `start 40281, count 28` | Ratings | Once per session |
| Model 121 · Basic settings | `start 40309, count 32` | Settings, including the output power cap 121.WMax | Once per session and after a write |
| Model 122 · Measurements and status | `start 40341, count 46` | Connection and control status | 1 s to 5 s |
| Model 160 · Multiple MPPT inverter extension | `start 40387, count 90` | Per-input PV values | 10 s to 60 s |

## Model 1 · Common

Identity of the device: manufacturer, model, serial number, firmware version and Modbus address.

*Registers40000–40069*

Address: 0-based PDU address derived from the chain on this firmware. Off.: offset from the model identifier. Access: RO read-only, RW writable through SunSpec control; a point that the model declares read-write but that this device does not accept is shown RO. Impl.: Yes implemented; Cond. implemented, reads the not-implemented value under the conditions stated; No not implemented. M after a name: mandatory point of the SunSpec model.

| Address | Off. | Name | Type | Units | Scale factor | Access | Impl. | Description |
|---|---|---|---|---|---|---|---|---|
| **SunSpec identifier** |  |  |  |  |  |  |  |  |
| 40000–40001 | 0 | SunS *M* | uint32 |  |  | RO | Yes | SunSpec identifier, ASCII "SunS" (0x53756E53). |
| **Model 1 · Common** |  |  |  |  |  |  |  |  |
| 40002 | 0 | ID *M* | uint16 |  |  | RO | Yes | Model identifier, constant 1. |
| 40003 | 1 | L *M* | uint16 |  |  | RO | Yes | Model length, constant 66. |
| 40004–40019 | 2 | Mn *M* | string |  |  | RO | Yes | Manufacturer, constant "Wattsonic". |
| 40020–40035 | 18 | Md *M* | string |  |  | RO | Yes | Model, constant "WattMatic AIO". |
| 40036–40043 | 34 | Opt | string |  |  | RO | No | Not implemented; all characters NUL. |
| 40044–40051 | 42 | Vr | string |  |  | RO | Yes | Firmware version string "V\<DC>.\<AC>.\<main>": application version of the DC converter (native 13019), of the AC converter (native 13017) and of the main controller (native 13021), updated every second. The third field identifies the firmware that defines this register layout. If a field reads 0 shortly after start-up, read the point again. |
| 40052–40067 | 50 | SN *M* | string |  |  | RO | Yes | Serial number, up to 32 ASCII characters from native 13000–13015, NUL-padded. |
| 40068 | 66 | DA | uint16 |  |  | RO | Yes | Modbus device address as configured in native 11007. The model defines DA as read-write; in this implementation it is read-only. A write is answered with exception 0x02, or with 0x04 while the control gate is closed or a machine veto applies. |
| 40069 | 67 | Pad | pad |  |  | RO | Yes | Pad register; reads 0x0000. |

## Model 123 · Immediate controls

Active-power limit, power-factor and reactive-power setpoints. Writable behind the control gate; see the control interface.

*Registers40070–40095*

Address: 0-based PDU address derived from the chain on this firmware. Off.: offset from the model identifier. Access: RO read-only, RW writable through SunSpec control; a point that the model declares read-write but that this device does not accept is shown RO. Impl.: Yes implemented; Cond. implemented, reads the not-implemented value under the conditions stated; No not implemented. M after a name: mandatory point of the SunSpec model.

| Address | Off. | Name | Type | Units | Scale factor | Access | Impl. | Description |
|---|---|---|---|---|---|---|---|---|
| 40070 | 0 | ID *M* | uint16 |  |  | RO | Yes | Model identifier, constant 123. |
| 40071 | 1 | L *M* | uint16 |  |  | RO | Yes | Model length, constant 24. |
| 40072 | 2 | Conn_WinTms | uint16 | Secs |  | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40073 | 3 | Conn_RvrtTms | uint16 | Secs |  | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40074 | 4 | Conn *M* | enum16 |  |  | RW | Yes | Connection state: 1 while the inverter is switched on (native 12000 not 0), 0 while it is switched off. Writing 1 while the inverter is switched on is acknowledged without effect and writing 0 is refused with exception 0x03; while the inverter is switched off every write to the map is refused with exception 0x04 (machine veto). The point does not switch the inverter.<br>0 DISCONNECT · 1 CONNECT |
| 40075 | 5 | WMaxLimPct *M* | uint16 | % WMax | WMaxLimPct_SF | RW | Yes | Active-power limit in percent of WMax, 0.1 % per count. While the control is released: the limit selected by the native EMS interface (native 11711, 0.01 % per count, divided by 10) while that interface is active with its limit enabled (native 11710), otherwise 100.0 %. While the control is held: the last accepted setpoint (100.0 % if none has been written), or while in force the value reached so far during a ramp. The limit is applied only while the unit operates under EMS control (see Implementation notes). |
| 40076 | 6 | WMaxLimPct_WinTms | uint16 | Secs |  | RW | Cond. | Random start window for the active-power limit, in seconds. Reads 0xFFFF while the active-power limit control is released; while it is held, the value last written since the restart, 0 if none. |
| 40077 | 7 | WMaxLimPct_RvrtTms | uint16 | Secs |  | RW | Cond. | Reversion timeout for the active-power limit, in seconds. Reads 0xFFFF while the active-power limit control is released; while it is held, the value last written since the restart, 0 if none. |
| 40078 | 8 | WMaxLimPct_RmpTms | uint16 | Secs |  | RW | Cond. | Ramp time for the active-power limit, in seconds. Reads 0xFFFF while the active-power limit control is released; while it is held, the value last written since the restart, 0 if none. |
| 40079 | 9 | WMaxLim_Ena *M* | enum16 |  |  | RW | Yes | Active-power limit enable. While the control is released: 1 while the native EMS interface is active with its limit enabled (native 11710), otherwise 0. While the control is held: the value last written by the client.<br>0 DISABLED · 1 ENABLED |
| 40080 | 10 | OutPFSet *M* | int16 | cos() | OutPFSet_SF | RW | Yes | Power-factor setpoint, 0.001 per count. While the control is released: the power-factor setpoint selected for the converter (native 11707 while the native EMS interface is active, native 15135 otherwise), converted from 0.01 to 0.001 per count. While the control is held: the last accepted setpoint rounded to the nearest 0.01 (1.000 if none has been written), or while in force the value reached so far during a ramp. Reads the not-implemented value if the native setpoint cannot be represented. |
| 40081 | 11 | OutPFSet_WinTms | uint16 | Secs |  | RW | Cond. | Random start window for the power-factor setpoint, in seconds. Reads 0xFFFF while the power-factor control is released; while it is held, the value last written since the restart, 0 if none. |
| 40082 | 12 | OutPFSet_RvrtTms | uint16 | Secs |  | RW | Cond. | Reversion timeout for the power-factor setpoint, in seconds. Reads 0xFFFF while the power-factor control is released; while it is held, the value last written since the restart, 0 if none. |
| 40083 | 13 | OutPFSet_RmpTms | uint16 | Secs |  | RW | Cond. | Ramp time for the power-factor setpoint, in seconds. Reads 0xFFFF while the power-factor control is released; while it is held, the value last written since the restart, 0 if none. |
| 40084 | 14 | OutPFSet_Ena *M* | enum16 |  |  | RW | Yes | Power-factor setpoint enable. While the control is released: 1 while the selected native reactive-power mode is fixed power factor (mode 2), otherwise 0. While the control is held: the value last written by the client.<br>0 DISABLED · 1 ENABLED |
| 40085 | 15 | VArWMaxPct | int16 | % WMax | VArPct_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40086 | 16 | VArMaxPct | int16 | % VArMax | VArPct_SF | RW | Cond. | Reactive-power setpoint in percent of the converter's reactive-power reference, 0.1 % per count. While the control is released: the native reactive-power setpoint (native 11708 relative to 11709 while the native EMS interface is active; native 15134 relative to full scale otherwise). While the control is held: the last accepted setpoint (0 % if none has been written), or while in force the value reached so far during a ramp. Reads the not-implemented value while the native EMS interface is active with a zero reactive-power maximum. |
| 40087 | 17 | VArAvalPct | int16 | % VArAval | VArPct_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40088 | 18 | VArPct_WinTms | uint16 | Secs |  | RW | Cond. | Random start window for the reactive-power setpoint, in seconds. Reads 0xFFFF while the reactive-power control is released; while it is held, the value last written since the restart, 0 if none. |
| 40089 | 19 | VArPct_RvrtTms | uint16 | Secs |  | RW | Cond. | Reversion timeout for the reactive-power setpoint, in seconds. Reads 0xFFFF while the reactive-power control is released; while it is held, the value last written since the restart, 0 if none. |
| 40090 | 20 | VArPct_RmpTms | uint16 | Secs |  | RW | Cond. | Ramp time for the reactive-power setpoint, in seconds. Reads 0xFFFF while the reactive-power control is released; while it is held, the value last written since the restart, 0 if none. |
| 40091 | 21 | VArPct_Mod | enum16 |  |  | RO | Yes | Reactive-power reference mode, constant 2 (VArMax). Not writable.<br>0 NONE · 1 WMax · 2 VArMax · 3 VArAval |
| 40092 | 22 | VArPct_Ena *M* | enum16 |  |  | RW | Yes | Reactive-power setpoint enable. While the control is released: 1 while the selected native reactive-power mode is fixed reactive power (mode 1), otherwise 0. While the control is held: the value last written by the client. The factory-default native reactive-power mode is fixed reactive power; this point therefore reads 1 on a factory-default unit while the control is released.<br>0 DISABLED · 1 ENABLED |
| 40093 | 23 | WMaxLimPct_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant -1. |
| 40094 | 24 | OutPFSet_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant -3. |
| 40095 | 25 | VArPct_SF | sunssf |  |  | RO | Yes | Scale factor, constant -1. |

## Model 124 · Storage

Battery settings, state and the storage control (battery charge and discharge bounds).

*Registers40096–40121*

Address: 0-based PDU address derived from the chain on this firmware. Off.: offset from the model identifier. Access: RO read-only, RW writable through SunSpec control; a point that the model declares read-write but that this device does not accept is shown RO. Impl.: Yes implemented; Cond. implemented, reads the not-implemented value under the conditions stated; No not implemented. M after a name: mandatory point of the SunSpec model.

| Address | Off. | Name | Type | Units | Scale factor | Access | Impl. | Description |
|---|---|---|---|---|---|---|---|---|
| 40096 | 0 | ID *M* | uint16 |  |  | RO | Yes | Model identifier, constant 124. |
| 40097 | 1 | L *M* | uint16 |  |  | RO | Yes | Model length, constant 24. |
| 40098 | 2 | WChaMax *M* | uint16 | W | WChaMax_SF | RW | Yes | Maximum charge power setting, 10 W per count: native 11068 (0.01 kW per count). It is the reference of OutWRte and InWRte. A value below 25 000 W also caps the battery charge power (0 W: charging not allowed); values of 25 000 W (factory default) and above do not cap it. While the battery management system requests a protective charge, the setting is not applied. A value written through the SunSpec map takes effect immediately but is not retained after a restart (see Implementation notes). |
| 40099 | 3 | WChaGra *M* | uint16 | % WChaMax/sec | WChaDisChaGra_SF | RW | Yes | Charge ramp limit in percent of WChaMax per second. Reads 100 while the storage control is released; while it is held, the value written by the client (100 if none). 0 and 100 both mean no limit. |
| 40100 | 4 | WDisChaGra *M* | uint16 | % WChaMax/sec | WChaDisChaGra_SF | RW | Yes | Discharge ramp limit in percent of WChaMax per second. Reads 100 while the storage control is released; while it is held, the value written by the client (100 if none). 0 and 100 both mean no limit. |
| 40101 | 5 | StorCtl_Mod *M* | bitfield16 |  |  | RW | Yes | Storage control mode: bit 0 CHARGE enables InWRte, bit 1 DISCHARGE enables OutWRte. Reads 0 while the storage control is released, also after InOutWRte_RvrtTms expiry although the mode is retained internally (see Implementation notes); while it is held, the value written by the client.<br>bit 0 CHARGE · bit 1 DiSCHARGE (symbol as defined in SunSpec model 124) |
| 40102 | 6 | VAChaMax | uint16 | VA | VAChaMax_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40103 | 7 | MinRsvPct | uint16 | % WChaMax | MinRsvPct_SF | RW | Yes | Minimum reserve, 0.01 % per count: native 11108, the minimum state of charge applied while the inverter runs grid-tied. A stored setting. |
| 40104 | 8 | ChaState | uint16 | % AhrRtg | ChaState_SF | RO | Yes | State of charge, 0.01 % per count: native 10671 (battery management system). |
| 40105 | 9 | StorAval | uint16 | AH | StorAval_SF | RO | No | Reads the not-implemented value; skip this point. |
| 40106 | 10 | InBatV | uint16 | V | InBatV_SF | RO | Yes | Battery voltage, 0.1 V per count: native 10337. |
| 40107 | 11 | ChaSt | enum16 |  |  | RO | Yes | Charge status from the sign of the total battery power (native 10346): positive 3 DISCHARGING, negative 4 CHARGING; at zero 6 HOLDING while a storage mode is set, including a mode retained after InOutWRte_RvrtTms expiry (see Implementation notes), otherwise 1 OFF. The values 2 EMPTY, 5 FULL and 7 TESTING are never published.<br>1 OFF · 2 EMPTY · 3 DISCHARGING · 4 CHARGING · 5 FULL · 6 HOLDING · 7 TESTING |
| 40108 | 12 | OutWRte | int16 | % WDisChaMax | InOutWRte_SF | RW | Cond. | Discharge bound in percent of WChaMax, 0.01 % per count: with the DISCHARGE bit of StorCtl_Mod the battery discharge power is limited to WChaMax × OutWRte; a negative value forces charging (see Implementation notes). Reads the not-implemented value while the storage control is released; while it is held, the last accepted value (0 if none has been written), or while in force the value reached so far during a ramp. |
| 40109 | 13 | InWRte | int16 | % WChaMax | InOutWRte_SF | RW | Cond. | Charge bound in percent of WChaMax, 0.01 % per count: with the CHARGE bit of StorCtl_Mod the battery charge power is limited to WChaMax × InWRte; a negative value forces discharging (see Implementation notes). Reads the not-implemented value while the storage control is released; while it is held, the last accepted value (0 if none has been written), or while in force the value reached so far during a ramp. |
| 40110 | 14 | InOutWRte_WinTms | uint16 | Secs |  | RW | Cond. | Random start window for the storage setpoints, in seconds. Reads 0xFFFF while the storage control is released; while it is held, the value last written since the restart, 0 if none. |
| 40111 | 15 | InOutWRte_RvrtTms | uint16 | Secs |  | RW | Cond. | Reversion timeout for the storage setpoints, in seconds. Reads 0xFFFF while the storage control is released; while it is held, the value last written since the restart, 0 if none. |
| 40112 | 16 | InOutWRte_RmpTms | uint16 | Secs |  | RW | Cond. | Ramp time for the storage setpoints, in seconds. Reads 0xFFFF while the storage control is released; while it is held, the value last written since the restart, 0 if none. |
| 40113 | 17 | ChaGriSet | enum16 |  |  | RO | No | Reads the not-implemented value; skip this point. Not writable.<br>0 PV · 1 GRID |
| 40114 | 18 | WChaMax_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40115 | 19 | WChaDisChaGra_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40116 | 20 | VAChaMax_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40117 | 21 | MinRsvPct_SF | sunssf |  |  | RO | Yes | Scale factor, constant -2. |
| 40118 | 22 | ChaState_SF | sunssf |  |  | RO | Yes | Scale factor, constant -2. |
| 40119 | 23 | StorAval_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40120 | 24 | InBatV_SF | sunssf |  |  | RO | Yes | Scale factor, constant -1. |
| 40121 | 25 | InOutWRte_SF | sunssf |  |  | RO | Yes | Scale factor, constant -2. |

## Model 103 · Inverter, three-phase

AC and DC measurements of the inverter, temperatures, operating state and events.

*Registers40122–40173*

Address: 0-based PDU address derived from the chain on this firmware. Off.: offset from the model identifier. Access: RO read-only, RW writable through SunSpec control; a point that the model declares read-write but that this device does not accept is shown RO. Impl.: Yes implemented; Cond. implemented, reads the not-implemented value under the conditions stated; No not implemented. M after a name: mandatory point of the SunSpec model.

| Address | Off. | Name | Type | Units | Scale factor | Access | Impl. | Description |
|---|---|---|---|---|---|---|---|---|
| 40122 | 0 | ID *M* | uint16 |  |  | RO | Yes | Model identifier, constant 103. |
| 40123 | 1 | L *M* | uint16 |  |  | RO | Yes | Model length, constant 50. |
| 40124 | 2 | A *M* | uint16 | A | A_SF | RO | Yes | Total AC current: sum of the three phase currents (native 10026–10028, 0.01 A per count). Reads the not-implemented value if any phase current is unavailable. |
| 40125 | 3 | AphA *M* | uint16 | A | A_SF | RO | Yes | Phase A AC current at the inverter terminals, native 10026, 0.01 A per count. |
| 40126 | 4 | AphB *M* | uint16 | A | A_SF | RO | Yes | Phase B AC current at the inverter terminals, native 10027, 0.01 A per count. |
| 40127 | 5 | AphC *M* | uint16 | A | A_SF | RO | Yes | Phase C AC current at the inverter terminals, native 10028, 0.01 A per count. |
| 40128 | 6 | A_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant -2. |
| 40129 | 7 | PPVphAB | uint16 | V | V_SF | RO | Yes | Line voltage A–B at the inverter terminals, native 10029, 0.1 V per count. |
| 40130 | 8 | PPVphBC | uint16 | V | V_SF | RO | Yes | Line voltage B–C at the inverter terminals, native 10030, 0.1 V per count. |
| 40131 | 9 | PPVphCA | uint16 | V | V_SF | RO | Yes | Line voltage C–A at the inverter terminals, native 10031, 0.1 V per count. |
| 40132 | 10 | PhVphA *M* | uint16 | V | V_SF | RO | Yes | Phase A voltage, native 10023, 0.1 V per count. |
| 40133 | 11 | PhVphB *M* | uint16 | V | V_SF | RO | Yes | Phase B voltage, native 10024, 0.1 V per count. |
| 40134 | 12 | PhVphC *M* | uint16 | V | V_SF | RO | Yes | Phase C voltage, native 10025, 0.1 V per count. |
| 40135 | 13 | V_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant -1. |
| 40136 | 14 | W *M* | int16 | W | W_SF | RO | Yes | AC active power of the inverter, native 10019 (0.01 kW per count); positive is output. |
| 40137 | 15 | W_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40138 | 16 | Hz *M* | uint16 | Hz | Hz_SF | RO | Yes | Grid frequency, native 10022, 0.01 Hz per count. |
| 40139 | 17 | Hz_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant -2. |
| 40140 | 18 | VA | int16 | VA | VA_SF | RO | Yes | AC apparent power, native 10021 (0.01 kVA per count). |
| 40141 | 19 | VA_SF | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40142 | 20 | VAr | int16 | var | VAr_SF | RO | Yes | AC reactive power, native 10020 (0.01 kvar per count). |
| 40143 | 21 | VAr_SF | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40144 | 22 | PF | int16 | Pct | PF_SF | RO | Yes | Power factor in percent: native 10102 (0.01 per count) multiplied by 100 and published with PF_SF −2; a power factor of 0.95 reads 9500 and decodes to 95.00 %. |
| 40145 | 23 | PF_SF | sunssf |  |  | RO | Yes | Scale factor, constant -2. |
| 40146–40147 | 24 | WH *M* | acc32 | Wh | WH_SF | RO | Yes | AC energy delivered by the inverter, 0.1 kWh per count: integrated every second from the positive part of native 10019 and kept in non-volatile memory. On a unit updated from firmware M013V1111B01D05 or earlier, the counter starts at 0 when the update is installed; record a baseline value at commissioning. |
| 40148 | 26 | WH_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 2. |
| 40149 | 27 | DCA | uint16 | A | DCA_SF | RO | No | Reads the not-implemented value. Read native 10339 for the battery current, or model 160 for the PV input currents. |
| 40150 | 28 | DCA_SF | sunssf |  |  | RO | Yes | Scale factor, constant -2. |
| 40151 | 29 | DCV | uint16 | V | DCV_SF | RO | Yes | Internal DC-link (bus) voltage, native 10368, 0.1 V per count. It is neither a PV nor a battery voltage. |
| 40152 | 30 | DCV_SF | sunssf |  |  | RO | Yes | Scale factor, constant -1. |
| 40153 | 31 | DCW | int16 | W | DCW_SF | RO | Yes | Total PV input power, native 10367 (0.01 kW per count). |
| 40154 | 32 | DCW_SF | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40155 | 33 | TmpCab *M* | int16 | C | Tmp_SF | RO | Yes | Internal temperature of the DC converter, native 10380, 0.1 °C per count. |
| 40156 | 34 | TmpSnk | int16 | C | Tmp_SF | RO | Yes | PV heat-sink temperature, native 10382, 0.1 °C per count. |
| 40157 | 35 | TmpTrns | int16 | C | Tmp_SF | RO | No | Reads the not-implemented value. Read 103.TmpCab and 103.TmpSnk for the temperatures. |
| 40158 | 36 | TmpOt | int16 | C | Tmp_SF | RO | No | Reads the not-implemented value. Read 103.TmpCab and 103.TmpSnk for the temperatures. |
| 40159 | 37 | Tmp_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant -1. |
| 40160 | 38 | St *M* | enum16 |  |  | RO | Yes | Operating state derived from the native status registers; the mapping is given in the Implementation notes.<br>1 OFF · 2 SLEEPING · 3 STARTING · 4 MPPT · 5 THROTTLED · 6 SHUTTING_DOWN · 7 FAULT · 8 STANDBY |
| 40161 | 39 | StVnd | enum16 |  |  | RO | No | Reads the not-implemented value; skip this point. |
| 40162–40163 | 40 | Evt1 *M* | bitfield32 |  |  | RO | Yes | Event bits. Bit 4 GRID_DISCONNECT while off-grid (native 14010 not 0); bit 6 MANUAL_SHUTDOWN while the inverter is switched off (native 12000 = 0); bit 7 OVER_TEMP on heat-sink over-temperature (native 14104 bit 1) or thermal derating (native 14022 bits 0 and 6, native 14023 bits 3 and 4). No other bit is set.<br>bit 0 GROUND_FAULT · bit 1 DC_OVER_VOLT · bit 2 AC_DISCONNECT · bit 3 DC_DISCONNECT · bit 4 GRID_DISCONNECT · bit 5 CABINET_OPEN · bit 6 MANUAL_SHUTDOWN · bit 7 OVER_TEMP · bit 8 OVER_FREQUENCY · bit 9 UNDER_FREQUENCY · bit 10 AC_OVER_VOLT · bit 11 AC_UNDER_VOLT · bit 12 BLOWN_STRING_FUSE · bit 13 UNDER_TEMP · bit 14 MEMORY_LOSS · bit 15 HW_TEST_FAILURE |
| 40164–40165 | 42 | Evt2 *M* | bitfield32 |  |  | RO | Yes | Reserved event bits; reads 0. |
| 40166–40167 | 44 | EvtVnd1 | bitfield32 |  |  | RO | Yes | Vendor event bits. Bit 0: PV input voltage derating (native 14023 bit 7). Bit 1: battery charging prohibited by the battery management system (native 14023 bit 8). Bit 2: battery discharging prohibited by the battery management system (native 14023 bit 9). Bits 3 to 16: reserved vendor status bits (native 14023 bits 10, 11, 13 to 15 and native 14022 bits 7 to 15); their meaning is not defined, so do not evaluate them. Bits 17 to 31 are always 0. Derating that limits the active output is reported by 103.St = 5 (THROTTLED) instead. |
| 40168–40169 | 46 | EvtVnd2 | bitfield32 |  |  | RO | No | Reads the not-implemented value; skip this point. |
| 40170–40171 | 48 | EvtVnd3 | bitfield32 |  |  | RO | No | Reads the not-implemented value; skip this point. |
| 40172–40173 | 50 | EvtVnd4 | bitfield32 |  |  | RO | No | Reads the not-implemented value; skip this point. |

## Model 203 · Meter, three-phase wye

Energy meter at the grid connection point. Measured points read the not-implemented value while the meter is lost.

*Registers40174–40280*

Address: 0-based PDU address derived from the chain on this firmware. Off.: offset from the model identifier. Access: RO read-only, RW writable through SunSpec control; a point that the model declares read-write but that this device does not accept is shown RO. Impl.: Yes implemented; Cond. implemented, reads the not-implemented value under the conditions stated; No not implemented. M after a name: mandatory point of the SunSpec model.

| Address | Off. | Name | Type | Units | Scale factor | Access | Impl. | Description |
|---|---|---|---|---|---|---|---|---|
| 40174 | 0 | ID *M* | uint16 |  |  | RO | Yes | Model identifier, constant 203. |
| 40175 | 1 | L *M* | uint16 |  |  | RO | Yes | Model length, constant 105. |
| 40176 | 2 | A *M* | int16 | A | A_SF | RO | Cond. | Total meter current: sum of the meter phase currents (native 10758–10760, 0.1 A per count). Reads the not-implemented value while the energy meter is lost. |
| 40177 | 3 | AphA *M* | int16 | A | A_SF | RO | Cond. | Meter phase A current, native 10758, 0.1 A per count. |
| 40178 | 4 | AphB *M* | int16 | A | A_SF | RO | Cond. | Meter phase B current, native 10759, 0.1 A per count. |
| 40179 | 5 | AphC *M* | int16 | A | A_SF | RO | Cond. | Meter phase C current, native 10760, 0.1 A per count. |
| 40180 | 6 | A_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant -1. |
| 40181 | 7 | PhV *M* | int16 | V | V_SF | RO | Cond. | Mean of the three meter phase voltages (native 10752–10754, 0.1 V per count). Reads the not-implemented value while native 10752 (phase A) reads 0. |
| 40182 | 8 | PhVphA *M* | int16 | V | V_SF | RO | Cond. | Meter phase A voltage, native 10752, 0.1 V per count. Reads the not-implemented value while native 10752 reads 0. |
| 40183 | 9 | PhVphB *M* | int16 | V | V_SF | RO | Cond. | Meter phase B voltage, native 10753, 0.1 V per count. Reads the not-implemented value while native 10752 (phase A) reads 0. |
| 40184 | 10 | PhVphC *M* | int16 | V | V_SF | RO | Cond. | Meter phase C voltage, native 10754, 0.1 V per count. Reads the not-implemented value while native 10752 (phase A) reads 0. |
| 40185 | 11 | PPV *M* | int16 | V | V_SF | RO | Cond. | Mean line voltage from the meter line voltages (native 10755–10757). Reads the not-implemented value when the meter supplies no line voltages (see Implementation notes) or while native 10752 (phase A) reads 0. |
| 40186 | 12 | PhVphAB *M* | int16 | V | V_SF | RO | Cond. | Meter line voltage A–B, native 10755, 0.1 V per count; see Implementation notes. Reads the not-implemented value while native 10752 (phase A) reads 0. |
| 40187 | 13 | PhVphBC *M* | int16 | V | V_SF | RO | Cond. | Meter line voltage B–C, native 10756, 0.1 V per count; see Implementation notes. Reads the not-implemented value while native 10752 (phase A) reads 0. |
| 40188 | 14 | PhVphCA *M* | int16 | V | V_SF | RO | Cond. | Meter line voltage C–A, native 10757, 0.1 V per count; see Implementation notes. Reads the not-implemented value while native 10752 (phase A) reads 0. |
| 40189 | 15 | V_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant -1. |
| 40190 | 16 | Hz *M* | int16 | Hz | Hz_SF | RO | Cond. | Frequency measured by the meter, native 10778, 0.01 Hz per count. |
| 40191 | 17 | Hz_SF | sunssf |  |  | RO | Yes | Scale factor, constant -2. |
| 40192 | 18 | W *M* | int16 | W | W_SF | RO | Cond. | Active power at the grid connection point, native 10041 (0.01 kW per count); positive is export to the grid, negative is import. |
| 40193 | 19 | WphA | int16 | W | W_SF | RO | No | Reads the not-implemented value. Use the total 203.W. |
| 40194 | 20 | WphB | int16 | W | W_SF | RO | No | Reads the not-implemented value. Use the total 203.W. |
| 40195 | 21 | WphC | int16 | W | W_SF | RO | No | Reads the not-implemented value. Use the total 203.W. |
| 40196 | 22 | W_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40197 | 23 | VA | int16 | VA | VA_SF | RO | No | Reads the not-implemented value. Use 203.W and 203.VAR. |
| 40198 | 24 | VAphA | int16 | VA | VA_SF | RO | No | Reads the not-implemented value. Use the total 203.W and 203.VAR. |
| 40199 | 25 | VAphB | int16 | VA | VA_SF | RO | No | Reads the not-implemented value. Use the total 203.W and 203.VAR. |
| 40200 | 26 | VAphC | int16 | VA | VA_SF | RO | No | Reads the not-implemented value. Use the total 203.W and 203.VAR. |
| 40201 | 27 | VA_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40202 | 28 | VAR | int16 | var | VAR_SF | RO | Cond. | Reactive power measured by the meter, native 10769 (0.01 kvar per count). |
| 40203 | 29 | VARphA | int16 | var | VAR_SF | RO | No | Reads the not-implemented value. Use the total 203.VAR. |
| 40204 | 30 | VARphB | int16 | var | VAR_SF | RO | No | Reads the not-implemented value. Use the total 203.VAR. |
| 40205 | 31 | VARphC | int16 | var | VAR_SF | RO | No | Reads the not-implemented value. Use the total 203.VAR. |
| 40206 | 32 | VAR_SF | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40207 | 33 | PF | int16 | Pct | PF_SF | RO | Cond. | Power factor measured by the meter in percent: native 10777 (0.01 per count) published with PF_SF 0. |
| 40208 | 34 | PFphA | int16 | Pct | PF_SF | RO | No | Reads the not-implemented value. Use the total 203.PF. |
| 40209 | 35 | PFphB | int16 | Pct | PF_SF | RO | No | Reads the not-implemented value. Use the total 203.PF. |
| 40210 | 36 | PFphC | int16 | Pct | PF_SF | RO | No | Reads the not-implemented value. Use the total 203.PF. |
| 40211 | 37 | PF_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40212–40213 | 38 | TotWhExp *M* | acc32 | Wh | TotWh_SF | RO | Yes | Energy exported to the grid, 0.1 kWh per count: native 10612–10613, integrated by the inverter every second from the positive part of native 10041 and kept in non-volatile memory. |
| 40214–40215 | 40 | TotWhExpPhA | acc32 | Wh | TotWh_SF | RO | No | Reads 0 (not accumulated). Use the total 203.TotWhExp. |
| 40216–40217 | 42 | TotWhExpPhB | acc32 | Wh | TotWh_SF | RO | No | Reads 0 (not accumulated). Use the total 203.TotWhExp. |
| 40218–40219 | 44 | TotWhExpPhC | acc32 | Wh | TotWh_SF | RO | No | Reads 0 (not accumulated). Use the total 203.TotWhExp. |
| 40220–40221 | 46 | TotWhImp *M* | acc32 | Wh | TotWh_SF | RO | Yes | Energy imported from the grid, 0.1 kWh per count: native 10614–10615, integrated by the inverter every second from the negative part of native 10041. |
| 40222–40223 | 48 | TotWhImpPhA | acc32 | Wh | TotWh_SF | RO | No | Reads 0 (not accumulated). Use the total 203.TotWhImp. |
| 40224–40225 | 50 | TotWhImpPhB | acc32 | Wh | TotWh_SF | RO | No | Reads 0 (not accumulated). Use the total 203.TotWhImp. |
| 40226–40227 | 52 | TotWhImpPhC | acc32 | Wh | TotWh_SF | RO | No | Reads 0 (not accumulated). Use the total 203.TotWhImp. |
| 40228 | 54 | TotWh_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 2. |
| 40229–40230 | 55 | TotVAhExp | acc32 | VAh | TotVAh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40231–40232 | 57 | TotVAhExpPhA | acc32 | VAh | TotVAh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40233–40234 | 59 | TotVAhExpPhB | acc32 | VAh | TotVAh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40235–40236 | 61 | TotVAhExpPhC | acc32 | VAh | TotVAh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40237–40238 | 63 | TotVAhImp | acc32 | VAh | TotVAh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40239–40240 | 65 | TotVAhImpPhA | acc32 | VAh | TotVAh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40241–40242 | 67 | TotVAhImpPhB | acc32 | VAh | TotVAh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40243–40244 | 69 | TotVAhImpPhC | acc32 | VAh | TotVAh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40245 | 71 | TotVAh_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40246–40247 | 72 | TotVArhImpQ1 | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40248–40249 | 74 | TotVArhImpQ1PhA | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40250–40251 | 76 | TotVArhImpQ1PhB | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40252–40253 | 78 | TotVArhImpQ1PhC | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40254–40255 | 80 | TotVArhImpQ2 | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40256–40257 | 82 | TotVArhImpQ2PhA | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40258–40259 | 84 | TotVArhImpQ2PhB | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40260–40261 | 86 | TotVArhImpQ2PhC | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40262–40263 | 88 | TotVArhExpQ3 | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40264–40265 | 90 | TotVArhExpQ3PhA | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40266–40267 | 92 | TotVArhExpQ3PhB | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40268–40269 | 94 | TotVArhExpQ3PhC | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40270–40271 | 96 | TotVArhExpQ4 | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40272–40273 | 98 | TotVArhExpQ4PhA | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40274–40275 | 100 | TotVArhExpQ4PhB | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40276–40277 | 102 | TotVArhExpQ4PhC | acc32 | varh | TotVArh_SF | RO | No | Reads 0 (not accumulated); skip this point. |
| 40278 | 104 | TotVArh_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40279–40280 | 105 | Evt *M* | bitfield32 |  |  | RO | Yes | Meter event bits: bit 7 M_EVENT_Missing_Sensor while the energy meter is lost. No other bit is set.<br>bit 2 M_EVENT_Power_Failure · bit 3 M_EVENT_Under_Voltage · bit 4 M_EVENT_Low_PF · bit 5 M_EVENT_Over_Current · bit 6 M_EVENT_Over_Voltage · bit 7 M_EVENT_Missing_Sensor · bit 8 M_EVENT_Reserved1 · bit 9 M_EVENT_Reserved2 · bit 10 M_EVENT_Reserved3 · bit 11 M_EVENT_Reserved4 · bit 12 M_EVENT_Reserved5 · bit 13 M_EVENT_Reserved6 · bit 14 M_EVENT_Reserved7 · bit 15 M_EVENT_Reserved8 · bit 16 M_EVENT_OEM01 · bit 17 M_EVENT_OEM02 · bit 18 M_EVENT_OEM03 · bit 19 M_EVENT_OEM04 · bit 20 M_EVENT_OEM05 · bit 21 M_EVENT_OEM06 · bit 22 M_EVENT_OEM07 · bit 23 M_EVENT_OEM08 · bit 24 M_EVENT_OEM09 · bit 25 M_EVENT_OEM10 · bit 26 M_EVENT_OEM11 · bit 27 M_EVENT_OEM12 · bit 28 M_EVENT_OEM13 · bit 29 M_EVENT_OEM14 · bit 30 M_EVENT_OEM15 |

## Model 120 · Nameplate

Ratings of the inverter and the battery.

*Registers40281–40308*

Address: 0-based PDU address derived from the chain on this firmware. Off.: offset from the model identifier. Access: RO read-only, RW writable through SunSpec control; a point that the model declares read-write but that this device does not accept is shown RO. Impl.: Yes implemented; Cond. implemented, reads the not-implemented value under the conditions stated; No not implemented. M after a name: mandatory point of the SunSpec model.

| Address | Off. | Name | Type | Units | Scale factor | Access | Impl. | Description |
|---|---|---|---|---|---|---|---|---|
| 40281 | 0 | ID *M* | uint16 |  |  | RO | Yes | Model identifier, constant 120. |
| 40282 | 1 | L *M* | uint16 |  |  | RO | Yes | Model length, constant 26. |
| 40283 | 2 | DERTyp *M* | enum16 |  |  | RO | Yes | DER type, constant 82 (PV_STOR).<br>4 PV · 82 PV_STOR |
| 40284 | 3 | WRtg *M* | uint16 | W | WRtg_SF | RO | Cond. | Rated active power, 10 W per count: native 13034 (0.01 kW per count). Reads the not-implemented value while native 13034 is still 0 after start-up. |
| 40285 | 4 | WRtg_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40286 | 5 | VARtg *M* | uint16 | VA | VARtg_SF | RO | Cond. | Rated apparent power, 10 VA per count, from the built-in table indexed by the device model code (native 13016): 10 kW 11.0 kVA, 12 kW 13.2 kVA, 15 kW 16.5 kVA, 20 kW 22.0 kVA, 25 kW 25.0 kVA. Not-implemented value for an unknown model code. |
| 40287 | 6 | VARtg_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40288 | 7 | VArRtgQ1 *M* | int16 | var | VArRtg_SF | RO | Cond. | Rated reactive power, quadrant 1, 10 var per count: 0.6 × rated apparent power (from the built-in table indexed by the device model code, native 13016). |
| 40289 | 8 | VArRtgQ2 *M* | int16 | var | VArRtg_SF | RO | Cond. | Rated reactive power, quadrant 2: as quadrant 1. |
| 40290 | 9 | VArRtgQ3 *M* | int16 | var | VArRtg_SF | RO | Cond. | Rated reactive power, quadrant 3: negative of quadrant 1. |
| 40291 | 10 | VArRtgQ4 *M* | int16 | var | VArRtg_SF | RO | Cond. | Rated reactive power, quadrant 4: negative of quadrant 1. |
| 40292 | 11 | VArRtg_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40293 | 12 | ARtg *M* | uint16 | A | ARtg_SF | RO | Cond. | Rated AC current, 0.1 A per count, from the built-in table indexed by the device model code (native 13016): 16.5 / 19.1 / 23.8 / 31.9 / 36.2 A for 10 / 12 / 15 / 20 / 25 kW. |
| 40294 | 13 | ARtg_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant -1. |
| 40295 | 14 | PFRtgQ1 *M* | int16 | cos() | PFRtg_SF | RO | Cond. | Minimum power factor, quadrant 1: 0.800 (published +800 with PFRtg_SF −3). |
| 40296 | 15 | PFRtgQ2 *M* | int16 | cos() | PFRtg_SF | RO | Cond. | Minimum power factor, quadrant 2: 0.800 (published −800). |
| 40297 | 16 | PFRtgQ3 *M* | int16 | cos() | PFRtg_SF | RO | Cond. | Minimum power factor, quadrant 3: 0.800 (published +800). |
| 40298 | 17 | PFRtgQ4 *M* | int16 | cos() | PFRtg_SF | RO | Cond. | Minimum power factor, quadrant 4: 0.800 (published −800). |
| 40299 | 18 | PFRtg_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant -3. |
| 40300 | 19 | WHRtg | uint16 | Wh | WHRtg_SF | RO | Cond. | Battery energy rating, 10 Wh per count: native 10688 (0.01 kWh per count) as reported by the battery management system. Not-implemented value while the battery reports 0. |
| 40301 | 20 | WHRtg_SF | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40302 | 21 | AhrRtg | uint16 | AH | AhrRtg_SF | RO | No | Reads the not-implemented value; skip this point. |
| 40303 | 22 | AhrRtg_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40304 | 23 | MaxChaRte | uint16 | W | MaxChaRte_SF | RO | Cond. | Charge power currently permitted by the battery management system, 10 W per count: native 10686 (0.01 kW per count). Not-implemented value while the permitted power is 0 (see Implementation notes). |
| 40305 | 24 | MaxChaRte_SF | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40306 | 25 | MaxDisChaRte | uint16 | W | MaxDisChaRte_SF | RO | Cond. | Discharge power currently permitted by the battery management system, 10 W per count: native 10687. Not-implemented value while the permitted power is 0 (see Implementation notes). |
| 40307 | 26 | MaxDisChaRte_SF | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40308 | 27 | Pad | pad |  |  | RO | Yes | Pad register; reads 0x0000. |

## Model 121 · Basic settings

Maximum output power (writable as an output cap) and reference values.

*Registers40309–40340*

Address: 0-based PDU address derived from the chain on this firmware. Off.: offset from the model identifier. Access: RO read-only, RW writable through SunSpec control; a point that the model declares read-write but that this device does not accept is shown RO. Impl.: Yes implemented; Cond. implemented, reads the not-implemented value under the conditions stated; No not implemented. M after a name: mandatory point of the SunSpec model.

| Address | Off. | Name | Type | Units | Scale factor | Access | Impl. | Description |
|---|---|---|---|---|---|---|---|---|
| 40309 | 0 | ID *M* | uint16 |  |  | RO | Yes | Model identifier, constant 121. |
| 40310 | 1 | L *M* | uint16 |  |  | RO | Yes | Model length, constant 30. |
| 40311 | 2 | WMax *M* | uint16 | W | WMax_SF | RW | Cond. | Maximum output power, 10 W per count. Without a SunSpec cap in force: the rated power, native 13034. With a cap written by a SunSpec client: the cap, limited to the rated power. Not-implemented value while native 13034 is still 0 after start-up. |
| 40312 | 3 | VRef *M* | uint16 | V | VRef_SF | RW | Cond. | Nominal voltage at the grid connection point, 1 V per count, from the configured grid code (native 15000): 220 V for grid code 0, 230 V for grid codes 11–17 and 51; not-implemented value for every other grid code. |
| 40313 | 4 | VRefOfs *M* | int16 | V | VRefOfs_SF | RW | Yes | Offset from the grid connection point to the inverter, constant 0 V. |
| 40314 | 5 | VMax | uint16 | V | VMinMax_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40315 | 6 | VMin | uint16 | V | VMinMax_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40316 | 7 | VAMax | uint16 | VA | VAMax_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40317 | 8 | VArMaxQ1 | int16 | var | VArMax_SF | RO | Cond. | Maximum reactive power, quadrant 1, 10 var per count (VArMax_SF +1): the same value as 120.VArRtgQ1, from the built-in table indexed by the device model code (native 13016). Not-implemented value for an unknown model code. Not writable. |
| 40318 | 9 | VArMaxQ2 | int16 | var | VArMax_SF | RO | Cond. | Maximum reactive power, quadrant 2: as quadrant 1, 10 var per count (VArMax_SF +1); the same value as 120.VArRtgQ2, from the built-in table indexed by the device model code (native 13016). Not-implemented value for an unknown model code. Not writable. |
| 40319 | 10 | VArMaxQ3 | int16 | var | VArMax_SF | RO | Cond. | Maximum reactive power, quadrant 3: negative of quadrant 1, 10 var per count (VArMax_SF +1); the same value as 120.VArRtgQ3, from the built-in table indexed by the device model code (native 13016). Not-implemented value for an unknown model code. Not writable. |
| 40320 | 11 | VArMaxQ4 | int16 | var | VArMax_SF | RO | Cond. | Maximum reactive power, quadrant 4: negative of quadrant 1, 10 var per count (VArMax_SF +1); the same value as 120.VArRtgQ4, from the built-in table indexed by the device model code (native 13016). Not-implemented value for an unknown model code. Not writable. |
| 40321 | 12 | WGra | uint16 | % WMax/sec | WGra_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40322 | 13 | PFMinQ1 | int16 | cos() | PFMin_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40323 | 14 | PFMinQ2 | int16 | cos() | PFMin_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40324 | 15 | PFMinQ3 | int16 | cos() | PFMin_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40325 | 16 | PFMinQ4 | int16 | cos() | PFMin_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40326 | 17 | VArAct | enum16 |  |  | RO | No | Reads the not-implemented value; skip this point. Not writable.<br>1 SWITCH · 2 MAINTAIN |
| 40327 | 18 | ClcTotVA | enum16 |  |  | RO | No | Reads the not-implemented value; skip this point. Not writable.<br>1 VECTOR · 2 ARITHMETIC |
| 40328 | 19 | MaxRmpRte | uint16 | % WGra | MaxRmpRte_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40329 | 20 | ECPNomHz | uint16 | Hz | ECPNomHz_SF | RO | No | Reads the not-implemented value; skip this point. Not writable. |
| 40330 | 21 | ConnPh | enum16 |  |  | RO | No | Reads the not-implemented value; skip this point. Not writable.<br>1 A · 2 B · 3 C |
| 40331 | 22 | WMax_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40332 | 23 | VRef_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40333 | 24 | VRefOfs_SF *M* | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40334 | 25 | VMinMax_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40335 | 26 | VAMax_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40336 | 27 | VArMax_SF | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40337 | 28 | WGra_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40338 | 29 | PFMin_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40339 | 30 | MaxRmpRte_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40340 | 31 | ECPNomHz_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |

## Model 122 · Measurements and status

Connection status of PV, storage and grid, and the active control functions.

*Registers40341–40386*

Address: 0-based PDU address derived from the chain on this firmware. Off.: offset from the model identifier. Access: RO read-only, RW writable through SunSpec control; a point that the model declares read-write but that this device does not accept is shown RO. Impl.: Yes implemented; Cond. implemented, reads the not-implemented value under the conditions stated; No not implemented. M after a name: mandatory point of the SunSpec model.

| Address | Off. | Name | Type | Units | Scale factor | Access | Impl. | Description |
|---|---|---|---|---|---|---|---|---|
| 40341 | 0 | ID *M* | uint16 |  |  | RO | Yes | Model identifier, constant 122. |
| 40342 | 1 | L *M* | uint16 |  |  | RO | Yes | Model length, constant 44. |
| 40343 | 2 | PVConn *M* | bitfield16 |  |  | RO | Yes | PV status bits from the PV input states (native 14005–14008): bits 0 CONNECTED and 1 AVAILABLE when any input is neither 'not connected' nor 'no interface'; bit 2 OPERATING when any input is running.<br>bit 0 CONNECTED · bit 1 AVAILABLE · bit 2 OPERATING · bit 3 TEST |
| 40344 | 3 | StorConn *M* | bitfield16 |  |  | RO | Yes | Storage status bits from the battery state (native 14003): 0 when the battery is not connected; otherwise bits 0 and 1, plus bit 2 while charging or discharging.<br>bit 0 CONNECTED · bit 1 AVAILABLE · bit 2 OPERATING · bit 3 TEST |
| 40345 | 4 | ECPConn *M* | bitfield16 |  |  | RO | Yes | Grid connection: 1 while on-grid (native 14010 = 0), 0 while off-grid.<br>bit 0 DISCONNECTED · bit 1 CONNECTED |
| 40346–40349 | 5 | ActWh | acc64 | Wh |  | RO | No | Reads 0 (not accumulated); skip this point. |
| 40350–40353 | 9 | ActVAh | acc64 | VAh |  | RO | No | Reads 0 (not accumulated); skip this point. |
| 40354–40357 | 13 | ActVArhQ1 | acc64 | varh |  | RO | No | Reads 0 (not accumulated); skip this point. |
| 40358–40361 | 17 | ActVArhQ2 | acc64 | varh |  | RO | No | Reads 0 (not accumulated); skip this point. |
| 40362–40365 | 21 | ActVArhQ3 | acc64 | varh |  | RO | No | Reads 0 (not accumulated); skip this point. |
| 40366–40369 | 25 | ActVArhQ4 | acc64 | varh |  | RO | No | Reads 0 (not accumulated); skip this point. |
| 40370 | 29 | VArAval | int16 | var | VArAval_SF | RO | No | Reads the not-implemented value; skip this point. |
| 40371 | 30 | VArAval_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40372 | 31 | WAval | uint16 | var | WAval_SF | RO | No | Reads the not-implemented value; skip this point. |
| 40373 | 32 | WAval_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |
| 40374–40375 | 33 | StSetLimMsk | bitfield32 |  |  | RO | No | Reads the not-implemented value; skip this point.<br>bit 0 WMax · bit 1 VAMax · bit 2 VArAval · bit 3 VArMaxQ1 · bit 4 VArMaxQ2 · bit 5 VArMaxQ3 · bit 6 VArMaxQ4 · bit 7 PFMinQ1 · bit 8 PFMinQ2 · bit 9 PFMinQ3 · bit 10 PFMinQ4 |
| 40376–40377 | 35 | StActCtl | bitfield32 |  |  | RO | Yes | Active control functions as selected by the controller: bit 0 FixedW while an active-power limit is selected (native EMS interface or SunSpec); bit 1 FixedVAR or bit 2 FixedPF or bit 9 Watt-PF according to the selected reactive-power mode; bit 4 Freq-Watt-Param, bit 7 LVRT, bit 8 HVRT and bit 10 Volt-Watt while the corresponding grid-code function is configured. Describes the selection made by the controller, not an acknowledgement from the power converter.<br>bit 0 FixedW · bit 1 FixedVAR · bit 2 FixedPF · bit 3 Volt-VAr · bit 4 Freq-Watt-Param · bit 5 Freq-Watt-Curve · bit 6 Dyn-Reactive-Current · bit 7 LVRT · bit 8 HVRT · bit 9 Watt-PF · bit 10 Volt-Watt · bit 12 Scheduled · bit 13 LFRT · bit 14 HFRT |
| 40378–40381 | 37 | TmSrc | string |  |  | RO | No | Reads the not-implemented value; skip this point. |
| 40382–40383 | 41 | Tms | uint32 | Secs |  | RO | No | Reads the not-implemented value; skip this point. |
| 40384 | 43 | RtSt | bitfield16 |  |  | RO | No | Reads the not-implemented value; skip this point.<br>bit 0 LVRT_ACTIVE · bit 1 HVRT_ACTIVE · bit 2 LFRT_ACTIVE · bit 3 HFRT_ACTIVE |
| 40385 | 44 | Ris | uint16 | ohms | Ris_SF | RO | No | Reads the not-implemented value; skip this point. |
| 40386 | 45 | Ris_SF | sunssf |  |  | RO | Yes | Scale factor, constant 0. |

## Model 160 · Multiple MPPT inverter extension

Per-input PV voltage, current, power, energy and state for four MPPT modules.

*Registers40387–40478*

Address: 0-based PDU address derived from the chain on this firmware. Off.: offset from the model identifier. Access: RO read-only, RW writable through SunSpec control; a point that the model declares read-write but that this device does not accept is shown RO. Impl.: Yes implemented; Cond. implemented, reads the not-implemented value under the conditions stated; No not implemented. M after a name: mandatory point of the SunSpec model.

| Address | Off. | Name | Type | Units | Scale factor | Access | Impl. | Description |
|---|---|---|---|---|---|---|---|---|
| 40387 | 0 | ID *M* | uint16 |  |  | RO | Yes | Model identifier, constant 160. |
| 40388 | 1 | L *M* | uint16 |  |  | RO | Yes | Model length, constant 88. |
| 40389 | 2 | DCA_SF | sunssf |  |  | RO | Yes | Scale factor, constant -2. |
| 40390 | 3 | DCV_SF | sunssf |  |  | RO | Yes | Scale factor, constant -1. |
| 40391 | 4 | DCW_SF | sunssf |  |  | RO | Yes | Scale factor, constant 1. |
| 40392 | 5 | DCWH_SF | sunssf |  |  | RO | Yes | Scale factor, constant 2. |
| 40393–40394 | 6 | Evt | bitfield32 |  |  | RO | No | Reads the not-implemented value; skip this point.<br>bit 0 GROUND_FAULT · bit 1 INPUT_OVER_VOLTAGE · bit 2 RESERVED_2 · bit 3 DC_DISCONNECT · bit 4 RESERVED_4 · bit 5 CABINET_OPEN · bit 6 MANUAL_SHUTDOWN · bit 7 OVER_TEMP · bit 8 RESERVED_8 · bit 9 RESERVED_9 · bit 10 RESERVED_10 · bit 11 RESERVED_11 · bit 12 BLOWN_FUSE · bit 13 UNDER_TEMP · bit 14 MEMORY_LOSS · bit 15 ARC_DETECTION · bit 16 RESERVED_16 · bit 17 RESERVED_17 · bit 18 RESERVED_18 · bit 19 RESERVED_19 · bit 20 TEST_FAILED · bit 21 INPUT_UNDER_VOLTAGE · bit 22 INPUT_OVER_CURRENT |
| 40395 | 8 | N | count |  |  | RO | Yes | Number of MPPT modules, constant 4. On models with two PV inputs, modules 3 and 4 read the not-implemented value. |
| 40396 | 9 | TmsPer | uint16 |  |  | RO | Yes | Timestamp period, constant 0 (module timestamps are not implemented). |
| **MPPT module 1** |  |  |  |  |  |  |  |  |
| 40397 | 10 | ID | uint16 |  |  | RO | Yes | Module (PV input) number, constant 1. |
| 40398–40405 | 11 | IDStr | string |  |  | RO | No | Not implemented; all characters NUL. |
| 40406 | 19 | DCA | uint16 | A | DCA_SF | RO | Cond. | PV input 1 current, native 10349, 0.01 A per count. Reads the not-implemented value when PV input 1 does not exist on the model (native 14005 = 4) or when the DC converter data are older than 10 s. |
| 40407 | 20 | DCV | uint16 | V | DCV_SF | RO | Cond. | PV input 1 voltage, native 10348, 0.1 V per count. Reads the not-implemented value when PV input 1 does not exist on the model (native 14005 = 4) or when the DC converter data are older than 10 s. |
| 40408 | 21 | DCW | uint16 | W | DCW_SF | RO | Cond. | PV input 1 power, native 10350 (0.01 kW per count); a negative native value is published as 0. Reads the not-implemented value when PV input 1 does not exist on the model (native 14005 = 4) or when the DC converter data are older than 10 s. |
| 40409–40410 | 22 | DCWH | acc32 | Wh | DCWH_SF | RO | Yes | PV input 1 lifetime energy, 0.1 kWh per count: native 10630–10631, kept in non-volatile memory. Reads 0 for an input that does not exist on the model. |
| 40411–40412 | 24 | Tms | uint32 | Secs |  | RO | No | Reads the not-implemented value; skip this point. |
| 40413 | 26 | Tmp | int16 | C |  | RO | No | Reads the not-implemented value; skip this point. |
| 40414 | 27 | DCSt | enum16 |  |  | RO | Cond. | PV input 1 state from native 14005: running 4 MPPT, fault 7 FAULT, stopped or not connected 1 OFF. Reads the not-implemented value when PV input 1 does not exist on the model (native 14005 = 4) or when the DC converter data are older than 10 s.<br>1 OFF · 2 SLEEPING · 3 STARTING · 4 MPPT · 5 THROTTLED · 6 SHUTTING_DOWN · 7 FAULT · 8 STANDBY · 9 TEST · 10 RESERVED_10 |
| 40415–40416 | 28 | DCEvt | bitfield32 |  |  | RO | No | Reads the not-implemented value; skip this point.<br>bit 0 GROUND_FAULT · bit 1 INPUT_OVER_VOLTAGE · bit 2 RESERVED_2 · bit 3 DC_DISCONNECT · bit 4 RESERVED_4 · bit 5 CABINET_OPEN · bit 6 MANUAL_SHUTDOWN · bit 7 OVER_TEMP · bit 8 RESERVED_8 · bit 9 RESERVED_9 · bit 10 RESERVED_10 · bit 11 RESERVED_11 · bit 12 BLOWN_FUSE · bit 13 UNDER_TEMP · bit 14 MEMORY_LOSS · bit 15 ARC_DETECTION · bit 16 RESERVED_16 · bit 17 RESERVED_17 · bit 18 RESERVED_18 · bit 19 RESERVED_19 · bit 20 TEST_FAILED · bit 21 INPUT_UNDER_VOLTAGE · bit 22 INPUT_OVER_CURRENT |
| **MPPT module 2** |  |  |  |  |  |  |  |  |
| 40417 | 30 | ID | uint16 |  |  | RO | Yes | Module (PV input) number, constant 2. |
| 40418–40425 | 31 | IDStr | string |  |  | RO | No | Not implemented; all characters NUL. |
| 40426 | 39 | DCA | uint16 | A | DCA_SF | RO | Cond. | PV input 2 current, native 10353, 0.01 A per count. Reads the not-implemented value when PV input 2 does not exist on the model (native 14006 = 4) or when the DC converter data are older than 10 s. |
| 40427 | 40 | DCV | uint16 | V | DCV_SF | RO | Cond. | PV input 2 voltage, native 10352, 0.1 V per count. Reads the not-implemented value when PV input 2 does not exist on the model (native 14006 = 4) or when the DC converter data are older than 10 s. |
| 40428 | 41 | DCW | uint16 | W | DCW_SF | RO | Cond. | PV input 2 power, native 10354 (0.01 kW per count); a negative native value is published as 0. Reads the not-implemented value when PV input 2 does not exist on the model (native 14006 = 4) or when the DC converter data are older than 10 s. |
| 40429–40430 | 42 | DCWH | acc32 | Wh | DCWH_SF | RO | Yes | PV input 2 lifetime energy, 0.1 kWh per count: native 10632–10633, kept in non-volatile memory. Reads 0 for an input that does not exist on the model. |
| 40431–40432 | 44 | Tms | uint32 | Secs |  | RO | No | Reads the not-implemented value; skip this point. |
| 40433 | 46 | Tmp | int16 | C |  | RO | No | Reads the not-implemented value; skip this point. |
| 40434 | 47 | DCSt | enum16 |  |  | RO | Cond. | PV input 2 state from native 14006: running 4 MPPT, fault 7 FAULT, stopped or not connected 1 OFF. Reads the not-implemented value when PV input 2 does not exist on the model (native 14006 = 4) or when the DC converter data are older than 10 s.<br>1 OFF · 2 SLEEPING · 3 STARTING · 4 MPPT · 5 THROTTLED · 6 SHUTTING_DOWN · 7 FAULT · 8 STANDBY · 9 TEST · 10 RESERVED_10 |
| 40435–40436 | 48 | DCEvt | bitfield32 |  |  | RO | No | Reads the not-implemented value; skip this point.<br>bit 0 GROUND_FAULT · bit 1 INPUT_OVER_VOLTAGE · bit 2 RESERVED_2 · bit 3 DC_DISCONNECT · bit 4 RESERVED_4 · bit 5 CABINET_OPEN · bit 6 MANUAL_SHUTDOWN · bit 7 OVER_TEMP · bit 8 RESERVED_8 · bit 9 RESERVED_9 · bit 10 RESERVED_10 · bit 11 RESERVED_11 · bit 12 BLOWN_FUSE · bit 13 UNDER_TEMP · bit 14 MEMORY_LOSS · bit 15 ARC_DETECTION · bit 16 RESERVED_16 · bit 17 RESERVED_17 · bit 18 RESERVED_18 · bit 19 RESERVED_19 · bit 20 TEST_FAILED · bit 21 INPUT_UNDER_VOLTAGE · bit 22 INPUT_OVER_CURRENT |
| **MPPT module 3** |  |  |  |  |  |  |  |  |
| 40437 | 50 | ID | uint16 |  |  | RO | Yes | Module (PV input) number, constant 3. |
| 40438–40445 | 51 | IDStr | string |  |  | RO | No | Not implemented; all characters NUL. |
| 40446 | 59 | DCA | uint16 | A | DCA_SF | RO | Cond. | PV input 3 current, native 10357, 0.01 A per count. Reads the not-implemented value when PV input 3 does not exist on the model (native 14007 = 4) or when the DC converter data are older than 10 s. |
| 40447 | 60 | DCV | uint16 | V | DCV_SF | RO | Cond. | PV input 3 voltage, native 10356, 0.1 V per count. Reads the not-implemented value when PV input 3 does not exist on the model (native 14007 = 4) or when the DC converter data are older than 10 s. |
| 40448 | 61 | DCW | uint16 | W | DCW_SF | RO | Cond. | PV input 3 power, native 10358 (0.01 kW per count); a negative native value is published as 0. Reads the not-implemented value when PV input 3 does not exist on the model (native 14007 = 4) or when the DC converter data are older than 10 s. |
| 40449–40450 | 62 | DCWH | acc32 | Wh | DCWH_SF | RO | Yes | PV input 3 lifetime energy, 0.1 kWh per count: native 10634–10635, kept in non-volatile memory. Reads 0 for an input that does not exist on the model. |
| 40451–40452 | 64 | Tms | uint32 | Secs |  | RO | No | Reads the not-implemented value; skip this point. |
| 40453 | 66 | Tmp | int16 | C |  | RO | No | Reads the not-implemented value; skip this point. |
| 40454 | 67 | DCSt | enum16 |  |  | RO | Cond. | PV input 3 state from native 14007: running 4 MPPT, fault 7 FAULT, stopped or not connected 1 OFF. Reads the not-implemented value when PV input 3 does not exist on the model (native 14007 = 4) or when the DC converter data are older than 10 s.<br>1 OFF · 2 SLEEPING · 3 STARTING · 4 MPPT · 5 THROTTLED · 6 SHUTTING_DOWN · 7 FAULT · 8 STANDBY · 9 TEST · 10 RESERVED_10 |
| 40455–40456 | 68 | DCEvt | bitfield32 |  |  | RO | No | Reads the not-implemented value; skip this point.<br>bit 0 GROUND_FAULT · bit 1 INPUT_OVER_VOLTAGE · bit 2 RESERVED_2 · bit 3 DC_DISCONNECT · bit 4 RESERVED_4 · bit 5 CABINET_OPEN · bit 6 MANUAL_SHUTDOWN · bit 7 OVER_TEMP · bit 8 RESERVED_8 · bit 9 RESERVED_9 · bit 10 RESERVED_10 · bit 11 RESERVED_11 · bit 12 BLOWN_FUSE · bit 13 UNDER_TEMP · bit 14 MEMORY_LOSS · bit 15 ARC_DETECTION · bit 16 RESERVED_16 · bit 17 RESERVED_17 · bit 18 RESERVED_18 · bit 19 RESERVED_19 · bit 20 TEST_FAILED · bit 21 INPUT_UNDER_VOLTAGE · bit 22 INPUT_OVER_CURRENT |
| **MPPT module 4** |  |  |  |  |  |  |  |  |
| 40457 | 70 | ID | uint16 |  |  | RO | Yes | Module (PV input) number, constant 4. |
| 40458–40465 | 71 | IDStr | string |  |  | RO | No | Not implemented; all characters NUL. |
| 40466 | 79 | DCA | uint16 | A | DCA_SF | RO | Cond. | PV input 4 current, native 10361, 0.01 A per count. Reads the not-implemented value when PV input 4 does not exist on the model (native 14008 = 4) or when the DC converter data are older than 10 s. |
| 40467 | 80 | DCV | uint16 | V | DCV_SF | RO | Cond. | PV input 4 voltage, native 10360, 0.1 V per count. Reads the not-implemented value when PV input 4 does not exist on the model (native 14008 = 4) or when the DC converter data are older than 10 s. |
| 40468 | 81 | DCW | uint16 | W | DCW_SF | RO | Cond. | PV input 4 power, native 10362 (0.01 kW per count); a negative native value is published as 0. Reads the not-implemented value when PV input 4 does not exist on the model (native 14008 = 4) or when the DC converter data are older than 10 s. |
| 40469–40470 | 82 | DCWH | acc32 | Wh | DCWH_SF | RO | Yes | PV input 4 lifetime energy, 0.1 kWh per count: native 10636–10637, kept in non-volatile memory. Reads 0 for an input that does not exist on the model. |
| 40471–40472 | 84 | Tms | uint32 | Secs |  | RO | No | Reads the not-implemented value; skip this point. |
| 40473 | 86 | Tmp | int16 | C |  | RO | No | Reads the not-implemented value; skip this point. |
| 40474 | 87 | DCSt | enum16 |  |  | RO | Cond. | PV input 4 state from native 14008: running 4 MPPT, fault 7 FAULT, stopped or not connected 1 OFF. Reads the not-implemented value when PV input 4 does not exist on the model (native 14008 = 4) or when the DC converter data are older than 10 s.<br>1 OFF · 2 SLEEPING · 3 STARTING · 4 MPPT · 5 THROTTLED · 6 SHUTTING_DOWN · 7 FAULT · 8 STANDBY · 9 TEST · 10 RESERVED_10 |
| 40475–40476 | 88 | DCEvt | bitfield32 |  |  | RO | No | Reads the not-implemented value; skip this point.<br>bit 0 GROUND_FAULT · bit 1 INPUT_OVER_VOLTAGE · bit 2 RESERVED_2 · bit 3 DC_DISCONNECT · bit 4 RESERVED_4 · bit 5 CABINET_OPEN · bit 6 MANUAL_SHUTDOWN · bit 7 OVER_TEMP · bit 8 RESERVED_8 · bit 9 RESERVED_9 · bit 10 RESERVED_10 · bit 11 RESERVED_11 · bit 12 BLOWN_FUSE · bit 13 UNDER_TEMP · bit 14 MEMORY_LOSS · bit 15 ARC_DETECTION · bit 16 RESERVED_16 · bit 17 RESERVED_17 · bit 18 RESERVED_18 · bit 19 RESERVED_19 · bit 20 TEST_FAILED · bit 21 INPUT_UNDER_VOLTAGE · bit 22 INPUT_OVER_CURRENT |
| **End model** |  |  |  |  |  |  |  |  |
| 40477 | 0 | ID *M* | uint16 |  |  | RO | Yes | End marker 0xFFFF: no model follows. |
| 40478 | 1 | L *M* | uint16 |  |  | RO | Yes | End marker length, constant 0. |

## Control interface

How to enable SunSpec control, what each control does, how controls are held and released, and how SunSpec control combines with the native EMS interface.

### Closed loop per control

Each control is handled in the same four steps: preconditions, write sequence, confirmation that the command is in force, and release. The table below gives the details for each control.

| Control | Preconditions | Write sequence | Confirm it is in force | Failure and recovery |
|---|---|---|---|---|
| Active-power limit | Gate open; unit under EMS control (forced storage direction or native EMS external control). | `0x10` from `40075`, count 5: `WMaxLimPct`, `WinTms`, `RvrtTms`, `RmpTms`, `WMaxLim_Ena` = 1. | `14234` high byte 2; `17290` = 4 and `17358` = 2; output bound in W at `17359`. | Keep-alive within `RvrtTms`/3; released on `RvrtTms` expiry, gate closure, machine veto or restart; the unit then applies its own limit. |
| Storage control | Gate open; native `11700` = 0; `124.WChaMax` above 0. | `0x10` from `40108`, count 5: `OutWRte`, `InWRte`, `WinTms`, `RvrtTms`, `RmpTms`; then `0x06` `40101` = `StorCtl_Mod`. | `14240` high byte 2; forced direction: `14245` per-phase setpoint and `17358` = 2; battery power at native `10346`. | Keep-alive: re-write `StorCtl_Mod`; released on `RvrtTms` expiry, gate closure, machine veto or restart; to restart after a reversion, follow the implementation notes. |
| Power-factor setpoint | Gate open; native reactive-power control inactive (native `11700` = 0 or native `11706` = 0). | `0x10` from `40080`, count 5: `OutPFSet`, `WinTms`, `RvrtTms`, `RmpTms`, `OutPFSet_Ena` = 1. | `14236` high byte 2; `14243` power factor selected; `17304` slot: requested value at `17305`, transport state at `17307`; measured PF at `103.PF`. | Keep-alive within `RvrtTms`/3; enabling the reactive-power setpoint disables it; released as for every control. |
| Reactive-power setpoint | Gate open; native reactive-power control inactive (as for the power factor). | `0x06` `40086` = `VArMaxPct`; `0x10` from `40088`, count 3: `WinTms`, `RvrtTms`, `RmpTms`; `0x06` `40092` = 1. | `14238` high byte 2; `14244` setpoint selected; `17298` slot: requested value at `17299`; measured reactive power at `103.VAr`. | Keep-alive within `RvrtTms`/3; enabling the power-factor setpoint disables it; released as for every control. |

### Controls

| Control | Points | Content |
|---|---|---|
| Active-power limit | `123.WMaxLimPct`, `_WinTms`, `_RvrtTms`, `_RmpTms`, `123.WMaxLim_Ena`, `121.WMax` | Upper limit of the AC output in percent of `121.WMax`. Combined with the unit's own limit by taking the lower value: SunSpec can lower a native limit, never raise it. In force only while the unit operates under EMS control; see below. |
| Power-factor setpoint | `123.OutPFSet`, `_WinTms`, `_RvrtTms`, `_RmpTms`, `123.OutPFSet_Ena` | Fixed power factor. Mutually exclusive with the reactive-power setpoint: enabling one disables the other. |
| Reactive-power setpoint | `123.VArMaxPct`, `123.VArPct_WinTms`, `_RvrtTms`, `_RmpTms`, `123.VArPct_Ena` | Fixed reactive power in percent of the converter's reactive-power reference. |
| Storage control | `124.StorCtl_Mod`, `124.OutWRte`, `124.InWRte`, `124.InOutWRte_WinTms`, `_RvrtTms`, `_RmpTms`, `124.WChaGra`, `124.WDisChaGra` | Battery charge and discharge bounds in percent of `124.WChaMax`; a negative bound forces charging or discharging. |
| Stored settings | `124.WChaMax`, `124.MinRsvPct` | Settings of the unit (native `11068`, `11108`), not controls: they have no enable point and no timers, and they are not released. Each may be changed at most once per 600 s. |

### Control gate

- Open the gate by writing `0x5355` (21333) to native `11790` with function code `0x06` or `0x10`. Any other value closes it; the factory default is 0. The value is stored in non-volatile memory and survives a restart.
- The gate governs only SunSpec writes to `40000`–`40478`; reads are never gated. The gate register can be written over any Modbus interface, including the Modbus TCP connection that subsequently sends SunSpec writes (on port 502, subject to write control).
- While the gate is closed, every write to the map is answered with exception `0x04`, unless the frame is already refused by an earlier check in the evaluation order. Closing the gate releases every held control within 1 s and erases their setpoints.
- Native `14233` reads 1 while the gate is open.

### Machine veto

Even with the gate open, SunSpec writes are refused with `0x04` and held controls are released while any of the following applies: the inverter is switched off (native `12000` = 0); emergency stop is set (native `12021` not 0); the unit is not commissioned (native `11124` = 0, factory default 0); the native EMS communication watchdog is in its safe state; the external meter is in its meter-lost safe state.

### Holding and releasing a control

- Each control is either **released** or **held**. A control becomes held with the first accepted write of its enable (the `Ena` point, or `124.StorCtl_Mod` for storage), whether 1 or 0 is written.
- A held control is *waiting* (inside its random start window `WinTms`), *in force*, *outranked* (the native EMS interface holds the quantity; the command and the reversion timer are kept) or *disabled by the client* (`Ena` = 0).
- While a control is held its points publish the command state: the enable as written; a setpoint as the value in force (during a ramp, the value reached so far) or the last accepted value; a timer as the value last written since the restart, 0 if none. While a control is released its points publish the unit's own values (timers `0xFFFF`).
- Writing `Ena` = 0 (or `StorCtl_Mod` = 0) stops the override at once; the control stays held, keeps its setpoints and timers, and its reversion timer no longer runs.
- A control is released by expiry of its reversion timeout `RvrtTms` (only while enabled), closure of the gate, a machine veto or a restart. After `RvrtTms` expires, the last setpoints are retained; writing the enable alone re-activates them. Gate closure and a machine veto erase setpoints, rate limits and the `121.WMax` cap.
- `RvrtTms` is the reversion timeout (fail-safe timer) of each control: it counts seconds from the last accepted write to that control while the control is enabled. Set it for every commanded control; 0 disables the timeout.
- `RmpTms` ramps a setpoint linearly from its current value to the new one; release is never ramped. Re-sending an unchanged command renews `RvrtTms` without restarting a ramp in progress.
- Storage control only: after `RvrtTms` expiry `StorCtl_Mod` reads 0, but the previous mode is kept; the next accepted write to any storage point re-activates storage control with that mode.

### Combination with the native EMS interface

- The native EMS interface is active while its communication watchdog is enabled (native `11700` not 0) and has not tripped. While it is active, the storage control is outranked, and the power-factor and reactive-power setpoints are outranked while native `11706` is not 0 (factory default 1). An outranked control keeps its command and its reversion timer and comes back into force, ramped from neutral, when the native EMS interface becomes inactive.
- The active-power limit is never outranked: it is combined with the native limit (native `11711` while the native EMS interface is active with native `11710` = 1, otherwise 100 %) by taking the lower value.
- SunSpec writes do not count as the heartbeat of the native watchdog (native `12026`). Keep native `11700` = 0 when the energy management system uses SunSpec control only. If `11700` is not 0 and the heartbeat is not renewed in time, the watchdog trips into its safe state; this is a machine veto and releases every SunSpec control.

### When the active-power limit is in force

The active-power limit is effective only while the unit operates under EMS control, the operating mode in which the inverter follows an external active-power setpoint. In that mode, the effective limit is the lower of the native limit and `123.WMaxLimPct` and applies to the AC output; it never limits charging.

To have the limit applied, bring the unit under EMS control. A limit written with `123.WMaxLim_Ena` = 1 is accepted at any time, is shown in the read-back and sets `122.StActCtl` bit 0; while the unit runs its own operating mode, the limit is held but not applied, and the control-truth block reports it as *not applied*. The unit operates under EMS control while one of the following is in force:

- **SunSpec storage control with a forced direction**: `124.StorCtl_Mod` with the DISCHARGE bit and a negative `124.OutWRte` (forced charge), or with the CHARGE bit and a negative `124.InWRte` (forced discharge). Storage bounds of 0 % or more only limit the battery and do not change the operating mode.
- **Native EMS external control**: the native EMS interface is active and has written an active-power setpoint (native `11045`); see the [native EMS register map](native.md). The storage, power-factor and reactive-power controls of SunSpec are then outranked as described above.

To check whether a limit is applied, read the control-truth block (Checking that a command is in force): `17290` = 4 means the limit is applied, 3 means it is requested but not applied.

### Timing and read-back

- An accepted write is echoed into the map immediately, so an immediate read returns the written values. Within 1 s, the map shows the control state: setpoints show the value in force, `OutPFSet` is rounded to 0.01 and `121.WMax` is limited to the rated power.
- Commands are evaluated once per second and passed to the power converter in its next parameter pass (about every 550 ms), so a command reaches the converter within about 1.6 s of the acknowledgement when `WinTms` and `RmpTms` are 0.
- As a fail-safe, if the 1 s command evaluation stops while the converter parameter pass continues, every SunSpec override is released after about 11 s.
- Held controls, timers and rate limits are volatile: after a restart every control is released.

### Keep-alive

SunSpec control needs no separate heartbeat. Re-write the enable (`Ena` = 1, or the same `124.StorCtl_Mod`) at an interval of at most one third of `RvrtTms` and well below 30 s. This restarts the reversion timer, keeps write control on port 502 and re-activates a control after a reversion. For the controls of model 123, a write of `RvrtTms` alone after a reversion is stored but does not re-activate the control.

### Frames and atomicity

Function code `0x10` is all-or-nothing: every register is checked, in ascending address order, before anything changes, and the first register that fails determines the exception code. Within an accepted frame, timers are applied first, then setpoints, then the enable. The longest contiguous writable range is 11 registers, `40074`–`40084` (`123.Conn` to `123.OutPFSet_Ena`). One frame cannot enable both the power-factor and the reactive-power setpoint.

### Writable points

| Address | Name | Range (raw) | Scale factor | Content |
|---|---|---|---|---|
| 40074 | 123.Conn | 0 … 1 | — | Fixed value |
| 40075 | 123.WMaxLimPct | 0 … 1000 | WMaxLimPct_SF | Control |
| 40076 | 123.WMaxLimPct_WinTms | 0 … 65534 | — | Control |
| 40077 | 123.WMaxLimPct_RvrtTms | 0 … 65534 | — | Control |
| 40078 | 123.WMaxLimPct_RmpTms | 0 … 65534 | — | Control |
| 40079 | 123.WMaxLim_Ena | 0 … 1 | — | Control |
| 40080 | 123.OutPFSet | -1000 … 1000 | OutPFSet_SF | Control |
| 40081 | 123.OutPFSet_WinTms | 0 … 65534 | — | Control |
| 40082 | 123.OutPFSet_RvrtTms | 0 … 65534 | — | Control |
| 40083 | 123.OutPFSet_RmpTms | 0 … 65534 | — | Control |
| 40084 | 123.OutPFSet_Ena | 0 … 1 | — | Control |
| 40086 | 123.VArMaxPct | -1000 … 1000 | VArPct_SF | Control |
| 40088 | 123.VArPct_WinTms | 0 … 65534 | — | Control |
| 40089 | 123.VArPct_RvrtTms | 0 … 65534 | — | Control |
| 40090 | 123.VArPct_RmpTms | 0 … 65534 | — | Control |
| 40092 | 123.VArPct_Ena | 0 … 1 | — | Control |
| 40098 | 124.WChaMax | 0 … 3200 | WChaMax_SF | Stored setting |
| 40099 | 124.WChaGra | 0 … 100 | WChaDisChaGra_SF | Control |
| 40100 | 124.WDisChaGra | 0 … 100 | WChaDisChaGra_SF | Control |
| 40101 | 124.StorCtl_Mod | 0 … 3 | — | Control |
| 40103 | 124.MinRsvPct | 0 … 10000 | MinRsvPct_SF | Stored setting |
| 40108 | 124.OutWRte | -10000 … 10000 | InOutWRte_SF | Control |
| 40109 | 124.InWRte | -10000 … 10000 | InOutWRte_SF | Control |
| 40110 | 124.InOutWRte_WinTms | 0 … 65534 | — | Control |
| 40111 | 124.InOutWRte_RvrtTms | 0 … 65534 | — | Control |
| 40112 | 124.InOutWRte_RmpTms | 0 … 65534 | — | Control |
| 40311 | 121.WMax | 0 … 65534 | WMax_SF | Control |
| 40312 | 121.VRef | 0 … 65534 | VRef_SF | Fixed value |
| 40313 | 121.VRefOfs | -32767 … 32767 | VRefOfs_SF | Fixed value |

Accepts only the value it currently reads (other values: 0x03); has no effect.

Writes to every other point, including points that the SunSpec model declares read-write (for example `1.DA`, `123.Conn_WinTms`, `124.VAChaMax`), are answered with exception `0x02`.

## Checking that a command is in force

Three read-only native blocks report what the control layer selected and what was passed to the power converter. They are outside the SunSpec map and are read with function code 0x03 or 0x04 on the same connection.

### Checking whether the active-power limit is applied

Closed loop for an active-power limit of 50 % of the rated power, written with SunSpec. The Python example continues the helpers of step 1 of the [native Quick Start](native.md) (client, unit ID, `read`, `write`, `s16`).

**Preconditions.** The control gate is open, and the unit operates under EMS control while the limit shall apply. Without EMS control the limit is accepted and held, but not applied.

| Function code | Register | Value | Meaning |
|---|---|---|---|
| `0x06` | `11790` | `0x5355` | Open the SunSpec control gate (native register, kept over a restart). |
| `0x03` | `14233` | 1 | Gate open; read it 1 s after the write. |
| `0x03` | `11700` | 0 | Native watchdog off when SunSpec is the only controller: SunSpec writes are not a heartbeat. |
| – | `40101`, `40108` | – | EMS control: a storage control with a forced direction (`124.StorCtl_Mod` with a negative `124.OutWRte` or `124.InWRte`, see Worked examples), or the native EMS session with `11045` written. |

**Write sequence.** One request writes the limit, its timers and the enable; the frames are listed under Worked examples.

| Function code | Register | Count | Value | Meaning |
|---|---|---|---|---|
| `0x10` | `40075` | 5 | 500, 0, 60, 0, 1 | `WMaxLimPct` = 500 (50.0 %, `WMaxLimPct_SF` = −1), `WMaxLimPct_WinTms` = 0, `WMaxLimPct_RvrtTms` = 60 s, `WMaxLimPct_RmpTms` = 0, `WMaxLim_Ena` = 1. |

**Confirmation.** About 2 s after the write, read:

| Function code | Register | Count | Expected value | Meaning |
|---|---|---|---|---|
| `0x03` | `14234` | 1 | High byte 2 | The limit is in force in the control layer; the low byte is the reason (0 = none). |
| `0x03` | `14242` | 1 | 5000 | Limit selected for dispatch, 0.01 % of the rated power. |
| `0x03` | `17284` | 77 | `0xCA12` | One consistent read of the control-truth block: `17285` equals `17360`; otherwise read again. |
| – | `17290` | – | 4 | Taken from the same read: the limit is applied (3 = requested but not applied). |
| – | `17358` | – | 2 | Taken from the same read: the unit operates under EMS control. |
| – | `17359` | – | W | Taken from the same read: upper bound of the AC output in W (S16), including the grid-code power cap `14047`–`14048`. |

**Failure and recovery.**

- `17290` = 3 and `17358` = 1: the limit is held but not applied, because the unit runs its own operating mode. Establish EMS control as listed under the preconditions. For a feed-in cap that holds in every operating mode, use the native export limit `11113` with `11107` = 1.
- Keep-alive: write `WMaxLim_Ena` = 1 (`0x06`, `40079`) at least every 20 s, one third of `WMaxLimPct_RvrtTms` = 60 s. Without it the limit reverts after 60 s: `14234` reads high byte 0, low byte 2 (reversion timeout).
- `14234` low byte 3 (gate closed) or 5 (machine veto: inverter off, emergency stop, native watchdog in its safe state, meter lost): the control is released and its setpoints are erased. Remove the cause, then write the limit again (`0x10`, `40075`).
- After a restart every SunSpec control is released (`11790` is kept): write the limit again.

**py81**

```python
# continues the helpers of step 1 of the native Quick Start (client, UNIT, read, write, s16)
write(11790, 0x5355)                     # open the SunSpec control gate (native register, 0x06)
rr = client.write_registers(40075, [500, 0, 60, 0, 1], **UNIT)   # 0x10: 50.0 %, WinTms 0, RvrtTms 60 s, RmpTms 0, enable
if rr.isError():
    raise IOError("WMaxLimPct: %s" % rr)
time.sleep(2)                            # evaluated once per second, passed to the converter within about 1.6 s
gate = read(14233)[0]                    # 1 = gate open
diag = read(14234)[0]
state, reason = diag >> 8, diag & 0xFF   # state 2 = in force; reason 0 = none
truth = read(17284, 77)                  # control-truth block 17284..17360 in one request
if truth[0] != 0xCA12 or truth[1] != truth[76]:
    raise IOError("inconsistent read of 17284..17360: read again")
effective, mode, bound = truth[6], truth[74], s16(truth[75])   # 17290, 17358, 17359
if state == 2 and effective == 4 and mode == 2:
    print("limit applied, AC output bound", bound, "W")
elif effective == 3:
    print("limit held but not applied: the unit is not under EMS control (17358 = %d)" % mode)
else:
    print("gate", gate, "state", state, "reason", reason)
write(40079, 1)                          # keep-alive: WMaxLim_Ena = 1 at least every 20 s (RvrtTms / 3)
```

1. **SunSpec read-back** (`123`/`124` points, `122.StActCtl`): what the client commanded and what the controller selected. Not an acknowledgement from the power converter.
2. **Control diagnostic block** `14232`–`14247` and its generation-tagged copy `17367`–`17385`: state, reason and remaining reversion time of each control, and the values selected for dispatch.
3. **Control-truth block** `17284`–`17360`: per converter parameter the value requested from the power converter, its transport state and its effective state, and for the active-power limit whether it is applied.

### Control diagnostic block 14232–14247

| Register | Meaning |
|---|---|
| 14232 | Block layout version: reads 0x1112 (not a firmware version). |
| 14233 | Control gate: 1 open, 0 closed. |
| 14234 / 14236 / 14238 / 14240 | Active-power limit / power factor / reactive power / storage control: high byte state (0 released, 1 waiting, 2 in force, 3 outranked, 4 disabled by the client), low byte reason (0 none, 1 disabled by the client, 2 reversion timeout, 3 gate closed, 4 outranked, 5 machine veto, 6 displaced by the other reactive control, 7 storage only: the charge and discharge bounds exclude each other and the battery is held at 0 W). |
| 14235 / 14237 / 14239 / 14241 | Seconds left until reversion; 0xFFFF if RvrtTms = 0. |
| 14242 | Active-power limit selected for dispatch, 0.01 % of the rated power; 0xFFFF if none. |
| 14243 | Power factor selected for dispatch, 0.01; 0x8000 if none. |
| 14244 | Reactive power selected for dispatch, 0.01 %; 0x8000 if none. |
| 14245 | Forced storage setpoint per phase selected for dispatch, 0.01 kW, positive = AC output; 0x8000 if none (also while the storage control only limits the battery). |
| 14246 | Count of refused SunSpec write frames (saturates at 65535). |
| 14247 | Seconds since the last accepted SunSpec write; 0xFFFF if none since the restart. |

The same 16 words are also published, together with a generation number, at `17367`–`17385`: `17367` layout `0xA601`, `17368` generation number (1–65535, never 0, advances every second), `17369`–`17384` the 16 words in the order above, `17385` the generation number again. One `0x03` read of all 19 registers is one consistent generation when `17367` = `0xA601` and `17368` = `17385`.

### Control-truth block 17284–17360

Read all 77 registers in one request. The block is consistent when `17284` = `0xCA12` and `17285` = `17360`. It holds twelve slots of six registers, one per converter parameter.

| Register | Meaning |
|---|---|
| 17284 | Layout identifier, reads 0xCA12. |
| 17285 | Publication sequence number; equals the value at 17360 in a consistent read. |
| 17286–17357 | Twelve slots of six registers, in the order of the table below. |
| 17358 | Operating mode of the latest parameter pass that sent the active-power limit: 0 none since the restart, 1 not under EMS control, 2 under EMS control. |
| 17359 | Under EMS control: upper bound of the AC output in W that results from the active-power limit and the converter's grid-code power cap; 0x8000 otherwise. |
| 17360 | Publication sequence number again. |

| Slot | Registers | Parameter | Meaning |
|---|---|---|---|
| 1 | 17286–17291 | 321 | Active-power limit |
| 2 | 17292–17297 | 410 | Reactive-power mode |
| 3 | 17298–17303 | 453 | Reactive-power setpoint |
| 4 | 17304–17309 | 454 | Power-factor setpoint |
| 5 | 17310–17315 | 300 | Operating mode |
| 6 | 17316–17321 | 322 | Active-power setpoint, phase A |
| 7 | 17322–17327 | 323 | Active-power setpoint, phase B |
| 8 | 17328–17333 | 324 | Active-power setpoint, phase C |
| 9 | 17334–17339 | 362 (DC) | Battery parameter 362 |
| 10 | 17340–17345 | 363 (DC) | Battery parameter 363 |
| 11 | 17346–17351 | 364 (DC) | Battery charge current limit |
| 12 | 17352–17357 | 365 (DC) | Battery discharge current limit |

| Offset in slot | Meaning |
|---|---|
| +0 | Parameter index (bit 14 set for a parameter of the DC converter). |
| +1 | Value requested from the power converter, after the combination of native and SunSpec commands; 0x8000 if none. |
| +2 | Request generation: advances whenever the requested value changes; 0 = never requested since the restart. |
| +3 | Transport state: 0 not yet sent, 1 refused by the transmit queue so far (not yet transmitted), 2 transmitted, 3 the converter's latest parameter read-back equals the requested value. |
| +4 | Effective state: 0 nothing requested, 2 requested, execution not reported by the converter, 3 not applied (active-power limit below 100 % outside EMS control), 4 applied (active-power limit under EMS control). |
| +5 | Native register of the corresponding measurement, for example 10019 for active power; 0x8000 for a mode selector. |

Under EMS control, the converter also reports its grid-code power cap (the lowest of its voltage-, frequency- and ramp-dependent curves) in W at native `14047`–`14048` (int32, most-significant word first); outside EMS control, it reads −1. `17359` already includes this cap.

## Worked examples

Complete Modbus TCP frames in hexadecimal, unit identifier 1. The response to an accepted write echoes the start address and quantity (0x10) or the register and value (0x06).

**Open the control gate (native 11790 = 0x5355)**

*Request*

```text
00 02 00 00 00 06 01 06 2E 0E 53 55
```

*Response*

```text
00 02 00 00 00 06 01 06 2E 0E 53 55
```

**Active-power limit 50.0 %, RvrtTms 60 s, enable (function code 0x10, start 40075, count 5)**

*Request*

```text
00 03 00 00 00 11 01 10 9C 8B 00 05 0A 01 F4 00 00 00 3C 00 00 00 01
```

*Response*

```text
00 03 00 00 00 06 01 10 9C 8B 00 05
```

The limit is applied only while the unit operates under EMS control; check 17290 (4 = applied, 3 = not applied).

**Keep-alive: re-write WMaxLim_Ena = 1 (function code 0x06)**

*Request*

```text
00 04 00 00 00 06 01 06 9C 8F 00 01
```

*Response*

```text
00 04 00 00 00 06 01 06 9C 8F 00 01
```

**Release the active-power limit: WMaxLim_Ena = 0 (function code 0x06)**

*Request*

```text
00 05 00 00 00 06 01 06 9C 8F 00 00
```

*Response*

```text
00 05 00 00 00 06 01 06 9C 8F 00 00
```

**Forced charge at 40 % of WChaMax, RvrtTms 60 s (function code 0x10, start 40108, count 5)**

*Request*

```text
00 06 00 00 00 11 01 10 9C AC 00 05 0A F0 60 00 00 00 00 00 3C 00 00
```

*Response*

```text
00 06 00 00 00 06 01 10 9C AC 00 05
```

**Then select DISCHARGE in StorCtl_Mod (function code 0x06, 40101 = 2): with OutWRte = −40 %, the battery is forced to charge and the unit changes to EMS control**

*Request*

```text
00 07 00 00 00 06 01 06 9C A5 00 02
```

*Response*

```text
00 07 00 00 00 06 01 06 9C A5 00 02
```

**Battery limits only: charge at most 50 %, discharge at most 20 % of WChaMax, RvrtTms 300 s (function code 0x10, start 40108, count 5)**

*Request*

```text
00 08 00 00 00 11 01 10 9C AC 00 05 0A 07 D0 13 88 00 00 01 2C 00 00
```

*Response*

```text
00 08 00 00 00 06 01 10 9C AC 00 05
```

**Then select CHARGE and DISCHARGE (function code 0x06, 40101 = 3): the operating mode of the unit is unchanged; the battery power stays within the bounds**

*Request*

```text
00 09 00 00 00 06 01 06 9C A5 00 03
```

*Response*

```text
00 09 00 00 00 06 01 06 9C A5 00 03
```

**Fixed power factor 0.950, RvrtTms 300 s, enable (function code 0x10, start 40080, count 5)**

*Request*

```text
00 0A 00 00 00 11 01 10 9C 90 00 05 0A 03 B6 00 00 01 2C 00 00 00 01
```

*Response*

```text
00 0A 00 00 00 06 01 10 9C 90 00 05
```

**Reactive-power setpoint 20.0 % (function code 0x06, 40086)**

*Request*

```text
00 0B 00 00 00 06 01 06 9C 96 00 C8
```

*Response*

```text
00 0B 00 00 00 06 01 06 9C 96 00 C8
```

**Reactive-power timers: WinTms 0, RvrtTms 300 s, RmpTms 0 (function code 0x10, start 40088, count 3)**

*Request*

```text
00 0C 00 00 00 0D 01 10 9C 98 00 03 06 00 00 01 2C 00 00
```

*Response*

```text
00 0C 00 00 00 06 01 10 9C 98 00 03
```

**Reactive-power enable (function code 0x06, 40092 = 1)**

*Request*

```text
00 0D 00 00 00 06 01 06 9C 9C 00 01
```

*Response*

```text
00 0D 00 00 00 06 01 06 9C 9C 00 01
```

**Read the control-truth block (function code 0x03, start 17284, count 77)**

*Request*

```text
00 0E 00 00 00 06 01 03 43 84 00 4D
```

**Read the generation-tagged control diagnostic block (function code 0x03, start 17367, count 19)**

*Request*

```text
00 0F 00 00 00 06 01 03 43 D7 00 13
```

**Refused write: gate closed (exception 0x04)**

*Request*

```text
00 10 00 00 00 06 01 06 9C 8F 00 01
```

*Response*

```text
00 10 00 00 00 03 01 86 04
```

## Implementation notes

How to read, write and control specific points precisely on this device, beyond what the SunSpec model definitions state.

| Topic | Points | How to read, write or control it precisely |
|---|---|---|
| Reading DC and battery quantities | `103.DCA`, `103.DCV`, `103.DCW` | Read the total PV input power from `103.DCW` and the per-input PV values from model 160. `103.DCV` is the internal DC-link voltage. For the battery read native `10346` (power) and native `10339` (current); positive = discharge. `103.DCA` reads the not-implemented value, so do not derive power from `103.DCV` × `103.DCA`. |
| AC energy counter | `103.WH` | `103.WH` counts the AC energy delivered by the inverter: the positive part of the AC active power, integrated every second in 0.1 kWh steps and kept over restarts. Use it for AC output energy and `160.DCWH` per input for PV energy. On a unit updated from firmware M013V1111B01D05 or earlier the counter starts at 0 at the update: record a baseline at commissioning. |
| Charge-power setting | `124.WChaMax` | **Preconditions:** control gate open; change the value at most once per 600 s. **Write:** `124.WChaMax` in 10 W steps (native `11068`). A value below 25 000 W caps the battery charge power (0 W: no charging); values of 25 000 W and above do not cap it. The value is also the reference of `124.OutWRte` and `124.InWRte`. **Confirm:** read `124.WChaMax` back. **Recovery:** a value written through SunSpec remains in effect until the next restart; re-write it after every restart, or store it as native `11068` over another interface. During a protective charge requested by the battery management system, the cap is not applied. To read the power the battery permits, read `120.MaxChaRte` and `120.MaxDisChaRte`. |
| Grid voltages from the meter | `203.PPV`, `203.PhVphAB`, `203.PhVphBC`, `203.PhVphCA` | Read the phase voltages `203.PhVphA` to `203.PhVphC`. With the energy meter supported by default, the line-voltage points `203.PPV` and `203.PhVphAB` to `203.PhVphCA` read `0x8000`; in a balanced three-phase grid, the line voltage is approximately √3 (≈ 1.732) × the phase voltage. |
| Operating state | `103.St` | Use `103.W` to determine production, `122.ECPConn` for the grid-connection state, and `103.St` = 7 together with the native fault registers from `14109` to detect faults. `103.St` is derived in this order: any hard-fault register that is not 0 (native 14109–14125, 14139–14151, 14169) gives 7 FAULT; derating that limits the active output (native 14022 bits 0–6, native 14023 bits 0–6 and 12) gives 5 THROTTLED; otherwise native 14002 determines the state: 0 gives 3 STARTING, 1 gives 8 STANDBY, 2 gives 3 STARTING, 3 gives 4 MPPT while native 14027 = 1 and 14010 = 0 (otherwise 3 STARTING), 4 gives 3 STARTING, 5 gives 4 MPPT, any other value gives 2 SLEEPING. Read other derating and battery flags from `103.EvtVnd1`. |
| Storage control | `124.StorCtl_Mod`, `124.OutWRte`, `124.InWRte` | **Preconditions:** control gate open; native EMS interface inactive (native `11700` = 0); `124.WChaMax` above 0. **Write:** `124.OutWRte`, `124.InWRte` and the three timers in one `0x10` frame from `40108` (count 5), then `124.StorCtl_Mod` with `0x06`. To limit the battery, use rates of 0 % or more: with CHARGE, the charge power stays ≤ `WChaMax` × `InWRte`; with DISCHARGE, the discharge power stays ≤ `WChaMax` × `OutWRte`; the unit keeps its own operating mode. To force a direction, select DISCHARGE with a negative `OutWRte` (forced charge) or CHARGE with a negative `InWRte` (forced discharge): the unit changes to EMS control and uses the bound closest to 0 W as the AC active-power setpoint, split equally over the three phases. Bounds that exclude each other hold the battery at 0 W (native `14240` reason 7). **Confirm:** native `14240` high byte 2; for a forced direction, native `14245` shows the per-phase setpoint and `17358` = 2; close the power loop on `203.W`. **Recovery:** expiry of `InOutWRte_RvrtTms` releases the control; gate closure, a machine veto or a restart also release it. |
| Permitted battery power | `120.MaxChaRte`, `120.MaxDisChaRte` | Read the power permitted by the battery management system from `120.MaxChaRte` and `120.MaxDisChaRte`. While `122.StorConn` reports a connected battery, interpret `0xFFFF` on these points as 0 W permitted (for example with a full or empty battery), or read native `10686` and `10687` directly. |
| Reactive-power reference | `123.VArMaxPct`, `123.VArPct_Mod`, `121.VArMaxQ1` | `121.VArMaxQ1` to `Q4` give the rated reactive power. Command reactive power with `123.VArMaxPct` as a percentage of the converter's reactive-power reference and close the loop on `103.VAr` or `203.VAR`. |
| Switching and curtailing | `123.Conn`, `123.Conn_WinTms`, `123.Conn_RvrtTms` | Read `123.Conn` for the switch state (1 switched on, 0 switched off). To curtail the output, use the active-power limit; to switch the inverter on or off, use native `12000` in the native register map. A write of `123.Conn` = 1 while the inverter is switched on is acknowledged without effect; a write of 0 is answered with exception `0x03`. |
| Reactive-power mode on a factory-default unit | `123.VArPct_Ena`, `122.StActCtl` | The factory-default reactive-power mode is fixed reactive power at 0 %, so without a SunSpec command `123.VArPct_Ena` reads 1 and `122.StActCtl` bit 1 is set. Evaluate `123.VArMaxPct` together with the enable: 0 % means no reactive power is commanded. |
| Minimum reserve | `124.MinRsvPct` | Write `124.MinRsvPct` in whole percent (multiples of 100 at 0.01 % per count), at most once per 600 s. It sets the minimum state of charge while the inverter runs grid-tied; off-grid operation uses its own setting. Read it back to confirm. |
| Storage ramp rates | `124.WChaGra`, `124.WDisChaGra` | Write a value from 1 to 99 (%/s) to `124.WChaGra` and `124.WDisChaGra` to limit the rate of change of the storage bounds; 0 and 100 mean no limit. For a fixed ramp duration, use `124.InOutWRte_RmpTms`. |
| Restarting storage control after a reversion | `124.StorCtl_Mod`, `124.InOutWRte_RvrtTms`, `124.ChaSt` | After `124.InOutWRte_RvrtTms` has expired, `124.StorCtl_Mod` reads 0 while the last mode is kept: the next accepted write to any storage point re-activates storage control with that mode, and `124.ChaSt` reads 6 HOLDING at zero battery power. To restart with new values, write `124.StorCtl_Mod` = 0 (`0x06`), then the setpoints and timers (`0x10` from `40108`, count 5), then `124.StorCtl_Mod`. |
| Writing and reading back control points | `123.WMaxLimPct`, `123.OutPFSet`, `123.VArMaxPct`, `124.OutWRte`, `124.InWRte`, `121.WMax` | Write only the points you change, and never write back a block you have read. Write the setpoint, timers and enable in one `0x10` frame where they are adjacent: active-power limit `40075`–`40079`, power factor `40080`–`40084`. While a control is held (also with `Ena` = 0), its points show the command; while it is released, they show the unit's own values and the timers read `0xFFFF`. |
| Power-factor setpoint steps | `123.OutPFSet` | Write `123.OutPFSet` in multiples of 10 (steps of 0.01). Other values are rounded to the nearest 0.01 and read back rounded. |
| Sign of the reactive-power and power-factor setpoints | `123.VArMaxPct`, `123.OutPFSet` | The signs of `123.VArMaxPct` and `123.OutPFSet` are passed unchanged to the native setpoints; native positive reactive power is leading (capacitive). During commissioning, command a small positive `123.VArMaxPct` and, in a separate test, a power factor of 0.95; check the sign of `103.VAr` and `203.VAR` against the intended direction. |
| Active-power limit | `123.WMaxLimPct`, `123.WMaxLim_Ena`, `121.WMax` | **Preconditions:** control gate open; the unit under EMS control, by a forced storage direction (model 124) or by native EMS external control (native `11045`). **Write:** one `0x10` frame from `40075`, count 5: `WMaxLimPct`, `WinTms`, `RvrtTms`, `RmpTms`, `WMaxLim_Ena` = 1. **Confirm:** `17290` = 4 and `17358` = 2; `17359` gives the resulting AC output bound in W. `17290` = 3 means the limit is held while the unit runs its own operating mode. **Recovery:** re-write the enable within one third of `RvrtTms`; on expiry, gate closure, a machine veto or a restart the limit is released. |

## What's new in this edition

The register layout (model order, lengths and addresses) is unchanged from earlier firmware, so existing clients keep their addresses. On earlier firmware, the behavior described in the items below may differ.

| Area | Change |
|---|---|
| Map | 103.St reports THROTTLED only for derating that limits the active output. Other derating flags and the battery charge-prohibited and discharge-prohibited flags are published in 103.EvtVnd1, which is now implemented. |
| Map | 121.VArMaxQ1 to Q4 publish the rated reactive power (10 var per count, VArMax_SF = +1). |
| Map | Power values of 100 W or less are published as measured instead of as 0. |
| Control | Model 124 storage control sets battery power bounds: rates of 0 % or more limit the battery; only a negative rate forces charging or discharging. |
| Control | At values below 25 000 W, 124.WChaMax (native 11068) caps the battery charge power. A value written through SunSpec takes effect immediately but is not retained after a restart. |
| Control | The active-power limit is applied only under EMS control; outside it a limit below 100 % is reported as not applied. |
| Control | Re-sending an unchanged command renews the reversion timer without restarting a ramp in progress. |
| Control | Reversion timeouts count wall-clock seconds. |
| Diagnostics | New read-only control-truth block 17284–17360 and a generation-tagged copy of the control diagnostic block at 17367–17385. Native 14245 now reports only a forced storage setpoint. New storage reason code 7. |
| Transport | Ethernet port 502 accepts two concurrent sessions; a new connection no longer closes the session of the client that holds write control. |
| Transport | Write control: only one connection per interface can write; writes from any other connection are answered with exception 0x06. |
| Transport | On every port 502 connection, including Wi-Fi, the unit reassembles requests split across TCP segments and processes pipelined requests in order; a request is processed only when its response can be sent. |
| Transport | A Modbus TCP request addressed to any other unit identifier is ignored; no response is sent. |
| Transport | The configured read-only reader (native 19024/19025) uses the second session with full framing support; writes from it are answered with exception 0x06. |
| Transport | TCP port 5001 is a separate service port for commissioning tools and no longer shares or closes port 502 sessions. |
| Transport | The unit announces the mDNS / DNS-SD service _modbus._tcp on port 502. |
| Watchdog | If the native EMS watchdog is enabled and the EMS was in control before a restart, the unit starts in the watchdog safe state; an accepted SunSpec write counts as the first EMS write and ends the safe state. |

## Terms and abbreviations

Terms used on this page.

| Term | Definition |
|---|---|
| SunSpec | Information model standard of the SunSpec Alliance for distributed energy resources over Modbus. |
| SF | Scale factor: a power of ten applied to the raw value of a point. |
| NI | Not-implemented value: the value of a type that marks a point as not available. |
| WinTms | Random start window: the control takes effect after a random delay of up to WinTms seconds, fixed per unit. |
| RvrtTms | Reversion timeout: seconds after the last accepted write after which the control is released. |
| RmpTms | Ramp time: seconds over which a setpoint moves linearly to a new value. |
| Control gate | Native register 11790; SunSpec writes are accepted only while it holds 0x5355. |
| Machine veto | Unit condition under which SunSpec writes are refused and held controls are released. |
| Write control | The right of one port 502 connection per interface to execute writes. |
| EMS control | Operating mode in which the inverter follows an external active-power setpoint instead of its own operating mode. |
| Native EMS interface | The EMS functions of the native Wattsonic register map, supervised by its communication watchdog (native 11700). |
| MBAP | Modbus Application Protocol header of a Modbus TCP frame. |

### Native registers referenced on this page

The SunSpec points on this page are computed from, or depend on, these native registers. They are read with function code `0x03` on the same connection and unit identifier.

| Native register | Meaning |
|---|---|
| 10029–10031 | Line voltages A–B, B–C and C–A at the inverter terminals, 0.1 V per count. |
| 10102 | Power factor of the inverter output, 0.01 per count. |
| 10380 | Internal temperature of the DC converter, 0.1 °C per count. |
| 10382 | PV heat-sink temperature, 0.1 °C per count. |
| 10612–10613 | Energy exported to the grid, two registers, high word first, 0.1 kWh per count, kept in non-volatile memory. |
| 10614–10615 | Energy imported from the grid, two registers, high word first, 0.1 kWh per count. |
| 10630–10637 | Lifetime energy of PV inputs 1 to 4, two registers each (input 1 at 10630–10631), high word first, 0.1 kWh per count, kept in non-volatile memory. |
| 10755–10757 | Meter line voltages A–B, B–C and C–A, 0.1 V per count. |
| 11124 | Commissioning state: 0 = not commissioned (factory default). While it is 0, SunSpec writes are refused. |
| 11706–11711 | Values in force of the native EMS controls: 11706 reactive-power mode, 11707 power-factor setpoint (0.01 per count), 11708 reactive-power setpoint, 11709 reactive-power limit, 11710 active-power limit enable, 11711 active-power limit (0.01 % per count). Write them through the native EMS registers 11300–11303 and 11320–11321. |
| 14047–14048 | Grid-code power cap of the converter under EMS control, int32 in W, most-significant word first; −1 outside EMS control. |
| 14109–14125 | Hard-fault registers, bit fields: any value other than 0 means a fault. |
| 14139–14151 | Hard-fault registers, bit fields: any value other than 0 means a fault. |
| 14169 | Hard-fault register, bit field: any value other than 0 means a fault. |
| 15000 | Grid code configured at commissioning. |
| 15134–15135 | Reactive-power setpoint (15134) and power-factor setpoint (15135, 0.01 per count) of the grid settings; used while the native EMS interface is not active. |
| 17367–17385 | Copy of the control diagnostic block with a generation number; see Checking a command. |

### Reference documents

- SunSpec Information Model Specification and the SunSpec model definitions of models 1, 103, 120, 121, 122, 123, 124, 160 and 203 (SunSpec Alliance).
- MODBUS Application Protocol Specification V1.1b3 and MODBUS Messaging on TCP/IP Implementation Guide V1.0b (modbus.org).
- Wattsonic EMS Modbus TCP/IP protocol, MATIC: the [native EMS register map](native.md).

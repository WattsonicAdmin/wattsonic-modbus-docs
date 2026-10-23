"""Client code templates generated from a recipe (Modbus TCP only).

Libraries follow the examples on modbus.wattsonic.com: Python pymodbus (ModbusTcpClient), Node.js modbus-serial,
C# NModbus, Go github.com/goburrow/modbus.  The generated program is a template: review the values, then run it
against your own inverter.  This module only produces text; it never connects anywhere.
"""
from __future__ import annotations

import re

from . import docs

LANGS = ("python", "nodejs", "csharp", "go")
KEEPALIVE_S = 10  # well below 30 s and at most RvrtTms/3 for the documented RvrtTms of 60 s


def _expected_int(e: str) -> int | None:
    e = e.strip()
    if re.fullmatch(r"-?\d+", e):
        return int(e)
    if re.fullmatch(r"0x[0-9A-Fa-f]+", e):
        return int(e, 16)
    return None


def _plan(recipe: dict) -> dict:
    pre = [p for p in recipe["preconditions"] if "read" in p]
    steps, keep = [], []
    for i, s in enumerate(recipe["steps"], 1):
        st = dict(s, n=i)
        if s["op"] == "write":
            if s["function_code"] == "0x10":
                st["vals"] = list(s["values"])
            else:
                v = s["value"] if s["value"] is not None else s.get("example_value")
                st["vals"] = [v]
            st["wire"] = [v & 0xFFFF for v in st["vals"]]
        steps.append(st)
        if s.get("repeat"):
            keep.append(st)
    return {"pre": pre, "steps": steps, "keep": keep, "confirm": recipe["confirm"]}


def _comment_lines(text: str, prefix: str, width: int = 100) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(prefix + cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(prefix + cur)
    return lines


def _header(recipe: dict, c: str) -> list[str]:
    v = docs.version()
    h = ["Recipe %s: %s" % (recipe["id"], recipe["title"]),
         "Wattsonic MATIC, ARM firmware %s or later (documentation edition %s)." % (v["firmware"], v["edition"]),
         "Template generated from the published documentation. It WRITES to a live inverter when run:",
         "check every value against your installation first. Values are raw register values;",
         "negative values are sent as 16-bit two's complement."]
    return [c + x for x in h]


def generate(recipe_id: str, language: str, transport: str = "tcp", host: str = "192.168.1.100",
             unit_id: int = 1) -> dict:
    lang = (language or "").lower().replace(".", "").replace("#", "sharp").replace(" ", "")
    lang = {"py": "python", "node": "nodejs", "js": "nodejs", "javascript": "nodejs", "cs": "csharp",
            "c": "csharp", "golang": "go"}.get(lang, lang)
    if lang not in LANGS:
        return {"error": "language must be one of %s" % ", ".join(LANGS)}
    if (transport or "tcp").lower() != "tcp":
        return {"error": "Only transport='tcp' (Modbus TCP, port 502) is generated."}
    ids = [r["id"] for r in docs.data("recipes.v1130.json")["recipes"]]
    if recipe_id not in ids:
        return {"error": "Unknown recipe id %r; use list_recipes." % recipe_id, "recipes": ids}
    recipe = docs.get_recipe(recipe_id)
    plan = _plan(recipe)
    gen = {"python": _python, "nodejs": _node, "csharp": _csharp, "go": _go}[lang]
    code = gen(recipe, plan, host, int(unit_id))
    return {"recipe": recipe["id"], "language": lang, "transport": "tcp", "code": code,
            "note": "Template only; " + docs.SAFETY + " Library: " + {
                "python": "pymodbus 3.x", "nodejs": "modbus-serial", "csharp": "NModbus",
                "go": "github.com/goburrow/modbus"}[lang] + "."}


# ------------------------------------------------------------------------------------------------ Python
def _python(recipe, plan, host, unit):
    L = ['"""'] + _header(recipe, "") + ['"""', "import inspect", "import time", "",
         "from pymodbus.client import ModbusTcpClient", "",
         'HOST, PORT, UNIT = "%s", 502, %d' % (host, unit),
         "KEEPALIVE_S = %d  # %s" % (KEEPALIVE_S, "well below 30 s and at most RvrtTms/3"), "",
         "client = ModbusTcpClient(HOST, port=PORT)",
         "if not client.connect():", '    raise SystemExit("cannot connect to %s:%d" % (HOST, PORT))',
         "# pymodbus up to 3.9 names the unit 'slave', 3.10 and later 'device_id'",
         '_UNIT_KW = "device_id" if "device_id" in inspect.signature(client.read_holding_registers).parameters else "slave"',
         "", "",
         "def rd(address, count=1):",
         "    r = client.read_holding_registers(address, count=count, **{_UNIT_KW: UNIT})",
         "    if r.isError():",
         '        raise RuntimeError("read %d failed: %s" % (address, r))',
         "    return r.registers", "", "",
         "def wr(address, value):  # function code 0x06",
         "    r = client.write_register(address, value & 0xFFFF, **{_UNIT_KW: UNIT})",
         "    if r.isError():",
         '        raise RuntimeError("write %d failed: %s" % (address, r))', "", "",
         "def wr_block(address, values):  # function code 0x10",
         "    r = client.write_registers(address, [v & 0xFFFF for v in values], **{_UNIT_KW: UNIT})",
         "    if r.isError():",
         '        raise RuntimeError("write %d+%d failed: %s" % (address, len(values), r))', "", ""]
    L.append("# --- preconditions")
    for p in plan["pre"]:
        a, e = p["read"]["address"], p["read"]["expected"]
        L += _comment_lines(p["text"], "# ")
        ei = _expected_int(e)
        L.append("v = rd(%d)[0]" % a)
        if ei is not None:
            L.append("if v != %d:" % (ei & 0xFFFF))
            L.append('    raise SystemExit("precondition %d: read %%d, expected %s" %% v)' % (a, e))
        else:
            L.append('print("%d =", v, "(expected: %s)")' % (a, e.replace('"', "'")))
    L.append("")
    L.append("# --- write sequence")
    for s in plan["steps"]:
        L += _comment_lines("Step %d: %s" % (s["n"], s["description"]), "# ")
        ind = ""
        if s.get("condition"):
            L.append("DO_STEP_%d = False  # set True when: %s" % (s["n"], s["condition"]))
            L.append("if DO_STEP_%d:" % s["n"])
            ind = "    "
        if s.get("wait_before_s"):
            L.append("%stime.sleep(%s)" % (ind, s["wait_before_s"]))
        if s["op"] == "read":
            L.append('%sprint("%d..%d:", rd(%d, %d))  # check: %s' % (ind, s["address"], s["address"] + s.get("count", 1) - 1,
                                                                 s["address"], s.get("count", 1), s["check"]))
        elif s["function_code"] == "0x10":
            L.append("%swr_block(%d, %r)  # check: %s" % (ind, s["address"], s["vals"], s["check"]))
        else:
            rng = (" range %s..%s," % tuple(s["value_range"])) if s.get("value_range") else ""
            L.append("%swr(%d, %d)  #%s check: %s" % (ind, s["address"], s["vals"][0], rng, s["check"]))
        L.append("")
    L.append("# --- confirm")
    L.append("time.sleep(2)")
    for c in plan["confirm"]:
        L.append('print("%d =", rd(%d)[0], "expected: %s (%s)")' % (c["read"], c["read"], c["expected"].replace('"', "'"),
                                                                    c["meaning"].replace('"', "'")))
    if plan["keep"]:
        L += ["", "# --- keep-alive (stop with Ctrl+C)", "try:", "    while True:", "        time.sleep(KEEPALIVE_S)"]
        for s in plan["keep"]:
            if s["function_code"] == "0x10":
                L.append("        wr_block(%d, %r)  # %s" % (s["address"], s["vals"], s["repeat"]["interval"]))
            else:
                L.append("        wr(%d, %d)  # %s" % (s["address"], s["vals"][0], s["repeat"]["interval"]))
        L += ["except KeyboardInterrupt:", "    pass"]
    L += ["", "client.close()", ""]
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ Node.js
def _node(recipe, plan, host, unit):
    L = ["// " + x[2:] if x.startswith("  ") else "// " + x for x in _header(recipe, "")]
    L += ["const ModbusRTU = require('modbus-serial');", "",
          "const HOST = '%s', PORT = 502, UNIT = %d;" % (host, unit),
          "const KEEPALIVE_MS = %d;  // well below 30 s and at most RvrtTms/3" % (KEEPALIVE_S * 1000),
          "const sleep = (ms) => new Promise((r) => setTimeout(r, ms));",
          "const u16 = (v) => v & 0xFFFF;", "",
          "async function main() {",
          "  const client = new ModbusRTU();",
          "  await client.connectTCP(HOST, { port: PORT });",
          "  client.setID(UNIT);",
          "  const rd = async (a, n = 1) => (await client.readHoldingRegisters(a, n)).data;",
          "  const wr = (a, v) => client.writeRegister(a, u16(v));             // 0x06",
          "  const wrBlock = (a, vs) => client.writeRegisters(a, vs.map(u16));  // 0x10", ""]
    L.append("  // --- preconditions")
    for p in plan["pre"]:
        a, e = p["read"]["address"], p["read"]["expected"]
        L += _comment_lines(p["text"], "  // ")
        ei = _expected_int(e)
        if ei is not None:
            L.append("  { const v = (await rd(%d))[0]; if (v !== %d) throw new Error(`precondition %d: read ${v}, expected %s`); }"
                     % (a, ei & 0xFFFF, a, e))
        else:
            L.append("  console.log('%d =', (await rd(%d))[0], '(expected: %s)');" % (a, a, e.replace("'", '"')))
    L.append("")
    L.append("  // --- write sequence")
    for s in plan["steps"]:
        L += _comment_lines("Step %d: %s" % (s["n"], s["description"]), "  // ")
        ind = "  "
        if s.get("condition"):
            L.append("  const DO_STEP_%d = false;  // set true when: %s" % (s["n"], s["condition"]))
            L.append("  if (DO_STEP_%d) {" % s["n"])
            ind = "    "
        if s.get("wait_before_s"):
            L.append("%sawait sleep(%d);" % (ind, int(s["wait_before_s"] * 1000)))
        if s["op"] == "read":
            L.append("%sconsole.log('%d:', await rd(%d, %d));  // check: %s" % (ind, s["address"], s["address"],
                                                                               s.get("count", 1), s["check"]))
        elif s["function_code"] == "0x10":
            L.append("%sawait wrBlock(%d, [%s]);  // check: %s" % (ind, s["address"], ", ".join(map(str, s["vals"])), s["check"]))
        else:
            L.append("%sawait wr(%d, %d);  // check: %s" % (ind, s["address"], s["vals"][0], s["check"]))
        if s.get("condition"):
            L.append("  }")
        L.append("")
    L.append("  // --- confirm")
    L.append("  await sleep(2000);")
    for c in plan["confirm"]:
        L.append("  console.log('%d =', (await rd(%d))[0], 'expected: %s');" % (c["read"], c["read"], c["expected"].replace("'", '"')))
    if plan["keep"]:
        L.append("")
        L.append("  // --- keep-alive")
        L.append("  for (;;) {")
        L.append("    await sleep(KEEPALIVE_MS);")
        for s in plan["keep"]:
            if s["function_code"] == "0x10":
                L.append("    await wrBlock(%d, [%s]);" % (s["address"], ", ".join(map(str, s["vals"]))))
            else:
                L.append("    await wr(%d, %d);  // %s" % (s["address"], s["vals"][0], s["repeat"]["interval"]))
        L.append("  }")
    else:
        L.append("  client.close(() => {});")
    L += ["}", "", "main().catch((e) => { console.error(e); process.exit(1); });", ""]
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ C#
def _csharp(recipe, plan, host, unit):
    L = ["// " + x for x in _header(recipe, "")]
    L += ["using System;", "using System.Net.Sockets;", "using System.Threading;", "using NModbus;", "",
          'const string Host = "%s";' % host, "const byte Unit = %d;" % unit,
          "const int KeepAliveMs = %d;  // well below 30 s and at most RvrtTms/3" % (KEEPALIVE_S * 1000), "",
          "using var tcp = new TcpClient(Host, 502);",
          "var master = new ModbusFactory().CreateMaster(tcp);",
          "ushort U16(int v) => (ushort)(v & 0xFFFF);",
          "ushort[] Rd(ushort a, ushort n = 1) => master.ReadHoldingRegisters(Unit, a, n);",
          "void Wr(ushort a, int v) => master.WriteSingleRegister(Unit, a, U16(v));            // 0x06",
          "void WrBlock(ushort a, int[] vs) => master.WriteMultipleRegisters(Unit, a, Array.ConvertAll(vs, U16));  // 0x10",
          ""]
    L.append("// --- preconditions")
    for p in plan["pre"]:
        a, e = p["read"]["address"], p["read"]["expected"]
        L += _comment_lines(p["text"], "// ")
        ei = _expected_int(e)
        if ei is not None:
            L.append('{ var v = Rd(%d)[0]; if (v != %d) throw new Exception($"precondition %d: read {v}, expected %s"); }'
                     % (a, ei & 0xFFFF, a, e))
        else:
            L.append('Console.WriteLine($"%d = {Rd(%d)[0]} (expected: %s)");' % (a, a, e.replace('"', "'")))
    L.append("")
    L.append("// --- write sequence")
    for s in plan["steps"]:
        L += _comment_lines("Step %d: %s" % (s["n"], s["description"]), "// ")
        ind = ""
        if s.get("condition"):
            L.append("bool doStep%d = false;  // set true when: %s" % (s["n"], s["condition"]))
            L.append("if (doStep%d) {" % s["n"])
            ind = "    "
        if s.get("wait_before_s"):
            L.append("%sThread.Sleep(%d);" % (ind, int(s["wait_before_s"] * 1000)))
        if s["op"] == "read":
            L.append('%sConsole.WriteLine(string.Join(",", Rd(%d, %d)));  // check: %s' % (ind, s["address"], s.get("count", 1), s["check"]))
        elif s["function_code"] == "0x10":
            L.append("%sWrBlock(%d, new[] { %s });  // check: %s" % (ind, s["address"], ", ".join(map(str, s["vals"])), s["check"]))
        else:
            L.append("%sWr(%d, %d);  // check: %s" % (ind, s["address"], s["vals"][0], s["check"]))
        if s.get("condition"):
            L.append("}")
        L.append("")
    L.append("// --- confirm")
    L.append("Thread.Sleep(2000);")
    for c in plan["confirm"]:
        L.append('Console.WriteLine($"%d = {Rd(%d)[0]} (expected: %s)");' % (c["read"], c["read"], c["expected"].replace('"', "'")))
    if plan["keep"]:
        L += ["", "// --- keep-alive", "while (true) {", "    Thread.Sleep(KeepAliveMs);"]
        for s in plan["keep"]:
            if s["function_code"] == "0x10":
                L.append("    WrBlock(%d, new[] { %s });" % (s["address"], ", ".join(map(str, s["vals"]))))
            else:
                L.append("    Wr(%d, %d);  // %s" % (s["address"], s["vals"][0], s["repeat"]["interval"]))
        L.append("}")
    L.append("")
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ Go
def _go(recipe, plan, host, unit):
    L = ["// " + x for x in _header(recipe, "")]
    L += ["package main", "", "import (", '\t"encoding/binary"', '\t"fmt"', '\t"log"', '\t"time"', "",
          '\t"github.com/goburrow/modbus"', ")", "",
          'const host = "%s:502"' % host, "const unit = %d" % unit,
          "const keepAlive = %d * time.Second // well below 30 s and at most RvrtTms/3" % KEEPALIVE_S, "",
          "func main() {",
          "\th := modbus.NewTCPClientHandler(host)",
          "\th.SlaveId = unit",
          "\th.Timeout = 5 * time.Second",
          "\tif err := h.Connect(); err != nil {", "\t\tlog.Fatal(err)", "\t}", "\tdefer h.Close()",
          "\tc := modbus.NewClient(h)",
          "\trd := func(a, n uint16) []uint16 {",
          "\t\tb, err := c.ReadHoldingRegisters(a, n)",
          "\t\tif err != nil {", "\t\t\tlog.Fatalf(\"read %d: %v\", a, err)", "\t\t}",
          "\t\tout := make([]uint16, n)",
          "\t\tfor i := range out {", "\t\t\tout[i] = binary.BigEndian.Uint16(b[2*i:])", "\t\t}",
          "\t\treturn out", "\t}",
          "\twr := func(a uint16, v int) { // 0x06",
          "\t\tif _, err := c.WriteSingleRegister(a, uint16(v&0xFFFF)); err != nil {",
          "\t\t\tlog.Fatalf(\"write %d: %v\", a, err)", "\t\t}", "\t}",
          "\twrBlock := func(a uint16, vs []int) { // 0x10",
          "\t\tb := make([]byte, 2*len(vs))",
          "\t\tfor i, v := range vs {", "\t\t\tbinary.BigEndian.PutUint16(b[2*i:], uint16(v&0xFFFF))", "\t\t}",
          "\t\tif _, err := c.WriteMultipleRegisters(a, uint16(len(vs)), b); err != nil {",
          "\t\t\tlog.Fatalf(\"write %d: %v\", a, err)", "\t\t}", "\t}",
          "\t_, _, _ = rd, wr, wrBlock", "\t_ = fmt.Sprint", ""]
    L.append("\t// --- preconditions")
    for p in plan["pre"]:
        a, e = p["read"]["address"], p["read"]["expected"]
        L += _comment_lines(p["text"], "\t// ")
        ei = _expected_int(e)
        if ei is not None:
            L.append("\tif v := rd(%d, 1)[0]; v != %d {" % (a, ei & 0xFFFF))
            L.append('\t\tlog.Fatalf("precondition %d: read %%d, expected %s", v)' % (a, e))
            L.append("\t}")
        else:
            L.append('\tfmt.Println("%d =", rd(%d, 1)[0], "(expected: %s)")' % (a, a, e.replace('"', "'")))
    L.append("")
    L.append("\t// --- write sequence")
    for s in plan["steps"]:
        L += _comment_lines("Step %d: %s" % (s["n"], s["description"]), "\t// ")
        ind = "\t"
        if s.get("condition"):
            L.append("\tdoStep%d := false // set true when: %s" % (s["n"], s["condition"]))
            L.append("\tif doStep%d {" % s["n"])
            ind = "\t\t"
        if s.get("wait_before_s"):
            L.append("%stime.Sleep(%d * time.Millisecond)" % (ind, int(s["wait_before_s"] * 1000)))
        if s["op"] == "read":
            L.append("%sfmt.Println(%d, rd(%d, %d)) // check: %s" % (ind, s["address"], s["address"], s.get("count", 1), s["check"]))
        elif s["function_code"] == "0x10":
            L.append("%swrBlock(%d, []int{%s}) // check: %s" % (ind, s["address"], ", ".join(map(str, s["vals"])), s["check"]))
        else:
            L.append("%swr(%d, %d) // check: %s" % (ind, s["address"], s["vals"][0], s["check"]))
        if s.get("condition"):
            L.append("\t}")
        L.append("")
    L.append("\t// --- confirm")
    L.append("\ttime.Sleep(2 * time.Second)")
    for c in plan["confirm"]:
        L.append('\tfmt.Println("%d =", rd(%d, 1)[0], "expected: %s")' % (c["read"], c["read"], c["expected"].replace('"', "'")))
    if plan["keep"]:
        L += ["", "\t// --- keep-alive", "\tfor {", "\t\ttime.Sleep(keepAlive)"]
        for s in plan["keep"]:
            if s["function_code"] == "0x10":
                L.append("\t\twrBlock(%d, []int{%s})" % (s["address"], ", ".join(map(str, s["vals"]))))
            else:
                L.append("\t\twr(%d, %d) // %s" % (s["address"], s["vals"][0], s["repeat"]["interval"]))
        L.append("\t}")
    L += ["}", ""]
    return "\n".join(L)

"""Read-only access to the embedded Wattsonic MATIC Modbus documentation data.

Pure functions over the packaged data files (no network, no device access).  The MCP server (server.py) exposes
them as tools; the tests call them directly.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources
from typing import Any

DATA_FILES = {
    "native.md": "text/markdown",
    "sunspec.md": "text/markdown",
    "llms.txt": "text/plain",
    "registers.v1130.json": "application/json",
    "sunspec-models.v1130.json": "application/json",
    "recipes.v1130.json": "application/json",
    "VERSION.json": "application/json",
}
SAFETY = "Documentation only: this server never connects to a device and never writes registers."


def _read(name: str) -> str:
    return resources.files("wattsonic_modbus_docs").joinpath("data", name).read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def text(name: str) -> str:
    if name not in DATA_FILES:
        raise KeyError(name)
    return _read(name)


@lru_cache(maxsize=None)
def data(name: str) -> Any:
    return json.loads(text(name))


def version() -> dict:
    return data("VERSION.json")


# --------------------------------------------------------------------------------------------- indexes
@lru_cache(maxsize=None)
def native_index() -> dict[int, dict]:
    idx: dict[int, dict] = {}
    regs = data("registers.v1130.json")
    for r in regs["registers"]:
        for a in range(r["address"], r.get("address_end", r["address"]) + 1):
            idx[a] = dict(r, interface="native")
    for s in regs["supplementary_registers"]:
        idx.setdefault(s["address"], dict(s, interface="native", supplementary=True))
    return idx


@lru_cache(maxsize=None)
def sunspec_index() -> dict[int, dict]:
    """address -> point record (model id, point name, instance) for every register a SunSpec point occupies."""
    idx: dict[int, dict] = {}
    models = data("sunspec-models.v1130.json")
    for m in models["models"]:
        g = m["group"]
        for p in g["points"]:
            rec = _ss_rec(m, p, None)
            for a in range(p["device"]["address"], p["device"]["address"] + p["size"]):
                idx[a] = rec
        for sg in g.get("groups", []):
            tmpl = {p["name"]: p for p in sg["points"]}
            for inst in sg["device"]["instances"]:
                for ip in inst["points"]:
                    p = dict(tmpl[ip["name"]], device=ip["device"])
                    rec = _ss_rec(m, p, "%s[%d]" % (sg["name"], inst["index"]))
                    for a in range(p["device"]["address"], p["device"]["address"] + p["size"]):
                        idx[a] = rec
    m0 = models["marker"]
    for a in (m0["address"], m0["address"] + 1):
        idx[a] = {"interface": "sunspec", "model": 0, "point": "SunS", "qualified": "SunS", "address": m0["address"],
                  "type": "uint32", "size": 2, "access": "R", "device": {"address": m0["address"], "writable": False,
                                                                         "description": m0.get("description", "")}}
    end = [c for c in models["chain"] if c["model"] == "END"][0]
    for a in (end["id_address"], end["id_address"] + 1):
        idx[a] = {"interface": "sunspec", "model": "END", "point": "ID" if a == end["id_address"] else "L",
                  "qualified": "END", "address": a, "type": "uint16", "size": 1, "access": "R",
                  "device": {"address": a, "writable": False, "description": "End model: ID 0xFFFF, L 0."}}
    return idx


def _ss_rec(m: dict, p: dict, inst: str | None) -> dict:
    q = "%d.%s%s" % (m["id"], (inst + ".") if inst else "", p["name"])
    r = {k: v for k, v in p.items()}
    r.update({"interface": "sunspec", "model": m["id"], "model_name": m["group"].get("label", m["group"]["name"]),
              "point": p["name"], "qualified": q, "address": p["device"]["address"]})
    if inst:
        r["group_instance"] = inst
    return r


def _sf_value(rec: dict) -> int | None:
    sfa = rec.get("device", {}).get("sf_address")
    if sfa is None:
        return None
    sf = sunspec_index().get(sfa)
    return sf.get("device", {}).get("constant_value") if sf else None


# --------------------------------------------------------------------------------------------- registers
def _brief(r: dict) -> dict:
    if r["interface"] == "native":
        out = {"interface": "native", "address": r["address"], "name": r["name"], "description": r["description"],
               "type": r["type"], "access": r["access"]}
        for k in ("address_end", "unit", "scale", "min", "max"):
            if r.get(k) is not None:
                out[k] = r[k]
        if r.get("supplementary"):
            out["supplementary"] = True
        return out
    d = r["device"]
    out = {"interface": "sunspec", "address": d["address"], "point": r["qualified"], "type": r["type"],
           "size": r["size"], "access": "RW" if d.get("writable") else "R", "implemented": d.get("implemented")}
    if r.get("units"):
        out["units"] = r["units"]
    if r.get("sf"):
        out["sf"] = r["sf"]
    return out


def search_registers(query: str, interface: str | None = None, limit: int = 20) -> dict:
    q = (query or "").strip()
    if not q:
        return {"query": query, "results": [], "note": "Empty query."}
    iface = (interface or "").lower() or None
    if iface not in (None, "native", "sunspec"):
        return {"error": "interface must be 'native', 'sunspec' or omitted"}
    toks = [t for t in re.split(r"[\s_./]+", q.lower()) if t]
    scored = []
    seen = set()
    if iface in (None, "native"):
        for a, r in native_index().items():
            if r["address"] in seen:
                continue
            seen.add(r["address"])
            hay = " ".join(str(r.get(k, "")) for k in ("name", "description", "values", "group", "unit")).lower()
            scored.append((_score(q, toks, r["address"], r.get("address_end"), r["name"], hay), r))
    if iface in (None, "sunspec"):
        seen_q = set()
        for a, r in sunspec_index().items():
            if r["qualified"] in seen_q:
                continue
            seen_q.add(r["qualified"])
            d = r["device"]
            hay = " ".join([r["qualified"], r.get("label", ""), r.get("desc", ""), d.get("description", "")]).lower()
            scored.append((_score(q, toks, d["address"], d["address"] + r["size"] - 1, r["qualified"], hay), r))
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda s: (-s[0], s[1]["address"]))
    return {"query": q, "interface": iface or "all", "count": len(scored),
            "results": [_brief(r) for _, r in scored[:max(1, min(limit, 100))]]}


def _score(q: str, toks: list[str], a0: int, a1: int | None, name: str, hay: str) -> int:
    s = 0
    if q.isdigit():
        n = int(q)
        if n == a0:
            s += 100
        elif a1 is not None and a0 <= n <= a1:
            s += 80
        return s
    nl = name.lower()
    if q.lower() == nl or nl.endswith("." + q.lower()):
        s += 60
    hit = miss = 0
    for t in toks:
        if t in nl:
            s += 10
            hit += 1
        elif t in hay:
            s += 3
            hit += 1
        else:
            miss += 1
    if hit == 0:
        return 0
    return max(1, s - 4 * miss)


def _parse_address(address: Any) -> tuple[int | None, str | None]:
    if isinstance(address, int):
        return address, None
    s = str(address).strip()
    if re.fullmatch(r"\d+", s):
        return int(s), None
    if re.fullmatch(r"0x[0-9a-fA-F]+", s):
        return int(s, 16), None
    return None, s


def get_register(address: int | str) -> dict:
    a, name = _parse_address(address)
    if a is None:
        # "123.WMaxLimPct" or a native register name
        m = re.fullmatch(r"(\d+)\.(.+)", name or "")
        if m:
            return get_sunspec_point(int(m.group(1)), m.group(2))
        for r in native_index().values():
            if r["name"].lower() == (name or "").lower():
                return _full_native(r)
        return {"error": "No register named %r. Use search_registers." % address}
    if a in native_index():
        return _full_native(native_index()[a], a)
    if a in sunspec_index():
        r = sunspec_index()[a]
        out = dict(r)
        if r["address"] != a:
            out["note"] = "Address %d is word %d of the %d-register point %s starting at %d." % (
                a, a - r["address"] + 1, r["size"], r["qualified"], r["address"])
        sf = _sf_value(r)
        if sf is not None:
            out["sf_value"] = sf
        return out
    models = data("sunspec-models.v1130.json")
    if models["base_address"] <= a <= models["map_end"]:
        return {"error": "Address %d is inside the SunSpec map but not on a documented point." % a}
    hint = ""
    if a in (12007, 12008):
        hint = (" 12008 requests a reset of operating parameters and 12007 is not the emergency stop: do not write "
                "them. Emergency stop is 12021 = 1.")
    return {"error": "Address %d is not in the documented register map.%s" % (a, hint)}


def _full_native(r: dict, a: int | None = None) -> dict:
    out = dict(r)
    if a is not None and r.get("address_end") and a != r["address"]:
        out["note"] = "Address %d belongs to the block %d-%d (%s)." % (a, r["address"], r["address_end"], r["name"])
    return out


# --------------------------------------------------------------------------------------------- SunSpec
def list_sunspec_models() -> dict:
    d = data("sunspec-models.v1130.json")
    models = []
    for m in d["models"]:
        g = m["group"]
        n = len(g["points"]) + sum(len(sg["points"]) * sg["device"]["count"] for sg in g.get("groups", []))
        models.append({"id": m["id"], "name": g["name"], "label": g.get("label", ""), "id_address": m["device"]["id_address"],
                       "length": m["device"]["length"], "points": n,
                       "writable_points": [p["name"] for p in g["points"] if p["device"].get("writable")]})
    return {"base_address": d["base_address"], "marker": d["marker"], "map_end": d["map_end"], "chain": d["chain"],
            "models": models, "transport": d["transport"], "conventions": d["conventions"]}


def get_sunspec_point(model: int | str, point: str) -> dict:
    d = data("sunspec-models.v1130.json")
    try:
        mid = int(model)
    except (TypeError, ValueError):
        return {"error": "model must be a number such as 123"}
    ms = [m for m in d["models"] if m["id"] == mid]
    if not ms:
        return {"error": "Model %s is not in this device's chain (%s)." % (model, ", ".join(str(m["id"]) for m in d["models"]))}
    m = ms[0]
    pt = (point or "").strip()
    mi = re.fullmatch(r"(\w+)\[(\d+)\]\.(\w+)", pt)
    hits = []
    for r in {id(v): v for v in sunspec_index().values()}.values():
        if r.get("model") != mid:
            continue
        if mi:
            if r.get("group_instance") == "%s[%s]" % (mi.group(1), mi.group(2)) and r["point"].lower() == mi.group(3).lower():
                hits.append(r)
        elif r["point"].lower() == pt.lower():
            hits.append(r)
    if not hits:
        names = [p["name"] for p in m["group"]["points"]]
        for sg in m["group"].get("groups", []):
            names += ["%s[n].%s" % (sg["name"], p["name"]) for p in sg["points"]]
        return {"error": "Point %r not in model %d." % (point, mid), "points": names}
    hits.sort(key=lambda r: r["address"])
    outs = []
    for r in hits:
        o = dict(r)
        sf = _sf_value(r)
        if sf is not None:
            o["sf_value"] = sf
        outs.append(o)
    return outs[0] if len(outs) == 1 else {"model": mid, "point": pt, "instances": outs}


# --------------------------------------------------------------------------------------------- recipes
def list_recipes() -> dict:
    d = data("recipes.v1130.json")
    return {"recipes": [{"id": r["id"], "title": r["title"], "interface": r["interface"], "summary": r["summary"]}
                        for r in d["recipes"]], "transport": d["transport"],
            "firmware_applicability": d["firmware_applicability"]}


def get_recipe(task: str) -> dict:
    d = data("recipes.v1130.json")
    t = (task or "").strip().lower()
    for r in d["recipes"]:
        if r["id"].lower() == t:
            return r
    syn = {"reboot": "restart", "wlim": "limit", "e-stop": "emergency", "estop": "emergency", "tou": "eco",
           "schedule": "eco", "keepalive": "heartbeat", "session": "session", "pf": "reactive", "var": "reactive"}
    toks = [syn.get(x, x) for x in re.split(r"[\s_./,]+", t) if x]
    best, score = None, 0
    for r in d["recipes"]:
        idw = set(re.split(r"[._]", r["id"].lower()))
        head = (r["id"].replace("_", " ") + " " + r["title"]).lower()
        hay = " ".join([r["summary"]] + [str(a) for a in r["registers"]]).lower()
        s = sum(5 if x in idw else (3 if x in head else (1 if x in hay else 0)) for x in toks)
        if s > score:
            best, score = r, s
    if best is None:
        return {"error": "No recipe matches %r." % task, "recipes": [r["id"] for r in d["recipes"]]}
    return best


# --------------------------------------------------------------------------------------------- validate_write
def _fc(function_code: Any) -> str | None:
    s = str(function_code).strip().lower().replace("fc", "")
    try:
        n = int(s, 16) if s.startswith("0x") else int(s)
    except ValueError:
        return None
    return {6: "0x06", 16: "0x10"}.get(n) or ("0x%02X" % n)


def _signed(raw: int) -> int:
    return raw - 65536 if raw > 32767 else raw


def validate_write(address: int | str, value: float | int, function_code: str | int = "0x06",
                   value_is_engineering: bool = False) -> dict:
    a, name = _parse_address(address)
    if a is None:
        reg = get_register(address)
        if "error" in reg:
            return {"verdict": "reject", "errors": [reg["error"]], "note": SAFETY}
        a = reg.get("address") if reg.get("interface") == "native" else reg.get("device", {}).get("address")
    fc = _fc(function_code)
    res: dict[str, Any] = {"address": a, "function_code": fc, "errors": [], "warnings": [], "preconditions": [],
                           "confirm_by": [], "note": SAFETY}
    if fc not in ("0x06", "0x10"):
        res["errors"].append("Function code %s does not write; use 0x06 (single register) or 0x10 (multiple)." % function_code)
    if a in native_index():
        _validate_native(native_index()[a], a, value, fc, value_is_engineering, res)
    elif a in sunspec_index():
        _validate_sunspec(sunspec_index()[a], a, value, fc, value_is_engineering, res)
    else:
        res["errors"].append(get_register(a).get("error", "Unknown address %d." % a))
    res["verdict"] = "reject" if res["errors"] else ("ok_with_warnings" if res["warnings"] else "ok")
    return res


def _to_raw(value: float | int, scale: float | None, engineering: bool, res: dict) -> int | None:
    if engineering:
        if not scale:
            res["errors"].append("This register has no scale; pass the raw value.")
            return None
        raw = round(float(value) / scale)
        if abs(raw * scale - float(value)) > abs(scale) / 2 + 1e-9:
            res["warnings"].append("Value %s is not a multiple of the scale %s; it is sent as %d." % (value, scale, raw))
        return raw
    if isinstance(value, float) and not float(value).is_integer():
        res["errors"].append("Raw register values are integers; pass value_is_engineering=true to convert %s." % value)
        return None
    return int(value)


def _validate_native(r: dict, a: int, value, fc, eng, res) -> None:
    res.update({"interface": "native", "register": r["name"], "description": r["description"], "type": r["type"]})
    if r["access"] == "RO":
        res["errors"].append("%d %s is read-only." % (a, r["name"]))
        return
    raw = _to_raw(value, r.get("scale"), eng, res)
    if raw is None:
        return
    signed = r["type"].upper().startswith("S")
    if signed and raw > 32767:
        raw = _signed(raw)
    if not (-32768 <= raw <= 65535):
        res["errors"].append("Value %d does not fit a 16-bit register." % raw)
        return
    res["raw_value"] = raw
    res["wire_value"] = raw & 0xFFFF
    if r.get("scale"):
        res["engineering_value"] = round(raw * r["scale"], 6)
        if r.get("unit"):
            res["unit"] = r["unit"]
    wf = r.get("write_function", {})
    if fc == "0x10" and wf.get("single_write_required"):
        res["errors"].append("%d must be written with 0x06, one register per request: %s" % (a, wf.get("note", "")))
    lo, hi = r.get("min"), r.get("max")
    if lo is not None and hi is not None and not (lo <= raw <= hi):
        if a == 11045:
            res["warnings"].append("Outside -2500..+2500: accepted without an exception and clamped to %d; 14253 reads 1."
                                   % max(-2500, min(2500, raw)))
        else:
            res["errors"].append("Value %d outside the documented range %d..%d (expect exception 0x03)." % (raw, lo, hi))
    if a == 11151 and 7 <= raw <= 20:
        res["errors"].append("11151 values 7-20 are reserved: write only 0-6.")
    if a == 12026 and raw & 0xFFFF == 0x5A5A:
        res["warnings"].append("0x5A5A on 12026 trips the watchdog on purpose (14042 = 2); use any other heartbeat value.")
    if a == 11301 and raw % 10:
        res["warnings"].append("Stored with 0.01 resolution: %d reads back as %d." % (raw, int(raw / 10) * 10))
    if a == 11790 and raw != 0x5355:
        res["warnings"].append("Any value other than 0x5355 closes the SunSpec control gate and releases held SunSpec controls.")
    if a == 11703:
        res["preconditions"].append("Must be lower than 11701 (or than an 11701 value in the same 0x10 frame).")
    if a == 12021 and raw == 1:
        res["warnings"].append("Emergency stop: all power conversion stops and latches until 12001 = 1, then 12000 = 1 restarts.")
    if a == 12000 and raw == 0:
        res["warnings"].append("Switches the inverter off; SunSpec writes are then refused with 0x04.")
    res["preconditions"] += r.get("effective_when", [])
    res["confirm_by"] = r.get("confirm_by", [])
    if r.get("persistence"):
        res["persistence"] = r["persistence"]


def _validate_sunspec(r: dict, a: int, value, fc, eng, res) -> None:
    d = r["device"]
    res.update({"interface": "sunspec", "register": r["qualified"], "type": r["type"],
                "description": d.get("description", "")})
    if r["address"] != a:
        res["errors"].append("%d is inside the point %s (starts at %d)." % (a, r["qualified"], r["address"]))
        return
    if not d.get("writable"):
        res["errors"].append("%s is not writable on this device (exception 0x02)." % r["qualified"])
        return
    sf = _sf_value(r)
    raw = _to_raw(value, (10 ** sf) if sf is not None else None, eng, res)
    if raw is None:
        return
    if r["type"].startswith("int") and raw > 32767:
        raw = _signed(raw)
    res["raw_value"] = raw
    res["wire_value"] = raw & 0xFFFF
    if sf is not None:
        res["engineering_value"] = round(raw * 10 ** sf, 6)
        if r.get("units"):
            res["unit"] = r["units"]
    lo, hi = d["write_range"]
    if not (lo <= raw <= hi):
        res["errors"].append("Value %d outside the accepted range %d..%d (exception 0x03)." % (raw, lo, hi))
    kind = d.get("write_kind")
    if kind == "fixed_value":
        res["warnings"].append("Fixed-value point: accepts only the value it currently reads (other values: 0x03); no effect.")
    if kind == "stored_setting":
        res["preconditions"].append("Stored setting: change it at most once per 600 s (otherwise exception 0x06).")
    if r["point"] == "OutPFSet" and raw % 10:
        res["warnings"].append("Write multiples of 10 (0.01 steps); the value is rounded and reads back rounded.")
    if r["point"] == "MinRsvPct" and raw % 100:
        res["warnings"].append("Write whole percent (multiples of 100 at 0.01 % per count).")
    if r["point"].endswith("RvrtTms") and raw:
        res["preconditions"].append("RvrtTms must be 0 or greater than the WinTms in force, otherwise exception 0x03.")
    res["preconditions"] = [
        "Control gate open: native 11790 = 0x5355 (14233 = 1); otherwise exception 0x04.",
        "Write over Modbus TCP port 502 (Ethernet or Wi-Fi) from the connection that holds write control; other "
        "interfaces answer 0x02, other connections 0x06.",
        "No machine veto: inverter switched on (12000), no emergency stop (12021), unit commissioned, native watchdog "
        "not in SAFE_STATE, external meter not in its meter-lost safe state; otherwise 0x04.",
    ] + res["preconditions"]
    if r["model"] == 123 and r["point"].startswith("WMaxLim"):
        res["preconditions"].append("The limit is applied only under EMS control (17358 = 2); check 17290 = 4.")
        res["confirm_by"] = [{"address": 14234, "expect": "high byte 2"}, {"address": 17290, "expect": "4"}]
    if r["model"] == 124 and r["point"] in ("StorCtl_Mod", "OutWRte", "InWRte"):
        res["preconditions"].append("Native EMS interface inactive (11700 = 0); 124.WChaMax above 0.")
        res["confirm_by"] = [{"address": 14240, "expect": "high byte 2"}, {"address": 14245, "expect": "forced setpoint per phase"}]


# --------------------------------------------------------------------------------------------- docs
def _page(page: str) -> str | None:
    p = (page or "").lower().strip()
    if p in ("native", "native.md", "index", "index.html", "wattsonic_ems_modbus_protocol.html", "ems"):
        return "native.md"
    if p in ("sunspec", "sunspec.md", "sunspec.html"):
        return "sunspec.md"
    return None


def headings(page: str) -> list[str]:
    name = _page(page)
    if not name:
        return []
    return [re.sub(r"^(?:>\s*)*", "", l) for l in text(name).splitlines() if re.match(r"(?:>\s*)*#{1,4} ", l)]


def get_doc_section(page: str, section: str) -> dict:
    name = _page(page)
    if not name:
        return {"error": "page must be 'native' or 'sunspec'"}
    lines = text(name).splitlines()
    want = (section or "").strip().lower()
    heads = []
    for i, l in enumerate(lines):
        m = re.match(r"((?:>\s*)*)(#{1,4}) (.*)$", l)
        if m:
            heads.append((i, len(m.group(2)), m.group(3).strip(), bool(m.group(1))))
    pick = None
    for h in heads:
        if h[2].lower() == want:
            pick = h
            break
    if pick is None:
        cands = [h for h in heads if want and want in h[2].lower()]
        if cands:
            pick = min(cands, key=lambda h: (h[1], len(h[2])))
    if pick is None:
        return {"error": "Section %r not found in %s." % (section, name),
                "sections": ["#" * h[1] + " " + h[2] for h in heads]}
    i0, lvl, title, quoted = pick
    end = len(lines)
    for i, l2, _, q2 in heads:
        if i > i0 and l2 <= lvl and q2 == quoted:
            end = i
            break
    body = "\n".join(lines[i0:end]).strip()
    return {"page": name, "section": title, "markdown": body,
            "source": "https://modbus.wattsonic.com/" + ("sunspec.html" if name == "sunspec.md"
                                                          else "Wattsonic_EMS_Modbus_Protocol.html")}

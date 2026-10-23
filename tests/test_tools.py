import json
import py_compile
import shutil
import subprocess

import pytest

from wattsonic_modbus_docs import codegen, docs


# ------------------------------------------------------------------ data / version
def test_version_and_data_files():
    v = docs.version()
    assert v["firmware"] == "M013V1130B01D05"
    assert v["data_version"].startswith("M013V1130B01D05+")
    for name in docs.DATA_FILES:
        assert docs.text(name).strip()


# ------------------------------------------------------------------ search_registers
def test_search_by_address_native_first():
    r = docs.search_registers("11045")
    assert r["results"][0]["address"] == 11045
    assert r["results"][0]["name"] == "Active_Power_Set"


def test_search_by_words_and_interface_filter():
    r = docs.search_registers("battery power", interface="native")
    assert any(x["address"] == 10346 for x in r["results"])
    assert all(x["interface"] == "native" for x in r["results"])
    s = docs.search_registers("WMaxLimPct", interface="sunspec")
    assert s["results"][0]["point"] == "123.WMaxLimPct"


def test_search_rejects_bad_interface_and_empty():
    assert "error" in docs.search_registers("x", interface="cloud")
    assert docs.search_registers("")["results"] == []


# ------------------------------------------------------------------ get_register
def test_get_register_native_fields():
    r = docs.get_register(11321)
    assert r["write_function"]["single_write_required"] is True
    assert r["persistence"]["class"] == "volatile_over_tcp"
    assert any(c["address"] == 17290 for c in r["confirm_by"])
    assert r["applies_from_firmware"] == "M013V1130B01D05"


def test_get_register_supplementary_and_block_and_name():
    assert docs.get_register(14250)["supplementary"] is True
    gate = docs.get_register(11790)                      # a register-map entry (native Settings table)
    assert not gate.get("supplementary") and gate["name"] == "SunSpec_Control_Gate"
    assert any(c["address"] == 14233 for c in gate["confirm_by"])
    assert docs.get_register(11254)["write_function"]["single_write_required"] is True
    assert "block" in docs.get_register(11194)["note"]
    assert docs.get_register("Active_Power_Set")["address"] == 11045


def test_get_register_sunspec_and_unknown():
    r = docs.get_register(40075)
    assert r["qualified"] == "123.WMaxLimPct" and r["sf_value"] == -1
    assert "error" in docs.get_register(19999)
    assert "12021" in docs.get_register(12008)["error"]
    assert docs.get_register("123.OutWRte" if False else "124.OutWRte")["device"]["address"] == 40108


# ------------------------------------------------------------------ SunSpec
def test_list_sunspec_models_chain():
    m = docs.list_sunspec_models()
    assert [x["id"] for x in m["models"]] == [1, 123, 124, 103, 203, 120, 121, 122, 160]
    assert m["base_address"] == 40000 and m["map_end"] == 40478
    assert "WMaxLimPct" in [x for x in m["models"] if x["id"] == 123][0]["writable_points"]


def test_get_sunspec_point_and_repeating_group():
    p = docs.get_sunspec_point(124, "StorCtl_Mod")
    assert p["device"]["address"] == 40101 and p["device"]["write_range"] == [0, 3]
    allm = docs.get_sunspec_point(160, "DCW")
    assert len(allm["instances"]) == 4
    one = docs.get_sunspec_point(160, "module[2].DCW")
    assert one["device"]["address"] == allm["instances"][1]["device"]["address"]
    assert "error" in docs.get_sunspec_point(126, "X")
    assert "points" in docs.get_sunspec_point(123, "Nope")


# ------------------------------------------------------------------ recipes
def test_list_and_get_recipes():
    ids = [r["id"] for r in docs.list_recipes()["recipes"]]
    for need in ("native.ems_session_start", "native.active_power_setpoint", "native.active_power_limit_pct",
                 "native.reactive_power", "native.eco_schedule", "sunspec.open_write_gate",
                 "sunspec.active_power_limit", "sunspec.forced_charge", "sunspec.forced_discharge",
                 "native.recover_safe_state", "native.resume_after_restart", "native.emergency_stop"):
        assert need in ids
    assert docs.get_recipe("native.emergency_stop")["steps"][0]["address"] == 12021
    assert docs.get_recipe("forced discharge")["id"] == "sunspec.forced_discharge"
    assert "error" in docs.get_recipe("zzzz qqqq")


# ------------------------------------------------------------------ validate_write
def test_validate_ok():
    r = docs.validate_write(11321, 700, "0x06")
    assert r["verdict"] in ("ok", "ok_with_warnings") and r["engineering_value"] == 70.0
    assert r["confirm_by"]


def test_validate_rejects_out_of_range():
    r = docs.validate_write(11321, 1500, "0x06")
    assert r["verdict"] == "reject" and "outside" in r["errors"][0]
    r2 = docs.validate_write(40075, 1001, "0x10")
    assert r2["verdict"] == "reject"


def test_validate_rejects_read_only():
    assert docs.validate_write(10019, 1, "0x06")["verdict"] == "reject"
    assert docs.validate_write(40072, 5, "0x06")["verdict"] == "reject"  # 123.Conn_WinTms not writable
    assert docs.validate_write(14031, 1, 6)["verdict"] == "reject"


def test_validate_rejects_fc16_on_single_write_registers():
    for a in (11300, 11302, 11320, 11321, 11330, 11254):
        r = docs.validate_write(a, 1, "0x10")
        assert r["verdict"] == "reject", a
    assert docs.validate_write(11300, 1, "FC06")["verdict"] != "reject"


def test_validate_function_code_and_unknown_address():
    assert docs.validate_write(11060, 1, "0x03")["verdict"] == "reject"
    assert docs.validate_write(19999, 1, "0x06")["verdict"] == "reject"


def test_validate_scale_signed_and_side_effects():
    r = docs.validate_write(11045, -10.0, "0x06", value_is_engineering=True)
    assert r["raw_value"] == -1000 and r["wire_value"] == 0xFC18
    r = docs.validate_write(11045, 3000, "0x06")
    assert r["verdict"] == "ok_with_warnings" and "clamped" in r["warnings"][0]
    assert docs.validate_write(12026, 0x5A5A)["verdict"] == "ok_with_warnings"
    assert docs.validate_write(11301, 994)["warnings"]
    assert docs.validate_write(11151, 9)["verdict"] == "reject"
    assert docs.validate_write(11045, 1.5)["verdict"] == "reject"  # raw values are integers
    r = docs.validate_write(40108, -4000, "0x10")
    assert r["verdict"] == "ok" and any("11790" in p for p in r["preconditions"])
    assert docs.validate_write(40074, 1)["warnings"]  # fixed value point
    assert any("600 s" in p for p in docs.validate_write(40098, 100)["preconditions"])


# ------------------------------------------------------------------ generate_client_code
@pytest.mark.parametrize("rid", [r["id"] for r in docs.list_recipes()["recipes"]])
def test_generate_python_compiles(rid, tmp_path):
    out = codegen.generate(rid, "python")
    p = tmp_path / "c.py"
    p.write_text(out["code"])
    py_compile.compile(str(p), doraise=True)
    rec = docs.get_recipe(rid)
    for s in rec["steps"]:
        assert str(s["address"]) in out["code"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("rid", ["native.ems_session_start", "sunspec.forced_charge", "native.recover_safe_state"])
def test_generate_node_syntax(rid, tmp_path):
    p = tmp_path / "c.js"
    p.write_text(codegen.generate(rid, "nodejs")["code"])
    assert subprocess.run(["node", "--check", str(p)], capture_output=True).returncode == 0


@pytest.mark.skipif(shutil.which("gofmt") is None, reason="gofmt not installed")
@pytest.mark.parametrize("rid", ["native.ems_session_start", "native.eco_schedule"])
def test_generate_go_syntax(rid, tmp_path):
    p = tmp_path / "main.go"
    p.write_text(codegen.generate(rid, "go")["code"])
    r = subprocess.run(["gofmt", "-e", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_generate_csharp_and_errors():
    c = codegen.generate("native.active_power_setpoint", "csharp")["code"]
    assert "WriteSingleRegister" in c and "11045" in c and c.count("{") == c.count("}")
    assert "error" in codegen.generate("native.ems_session_start", "rust")
    assert "error" in codegen.generate("native.ems_session_start", "python", transport="rtu")
    assert "error" in codegen.generate("no.such_recipe_xyz", "python")


def test_generate_uses_0x10_where_recipe_does():
    c = codegen.generate("sunspec.active_power_limit", "python")["code"]
    assert "wr_block(40075, [500, 0, 60, 0, 1])" in c
    c = codegen.generate("native.reactive_power", "python")["code"]
    assert "wr_block(113" not in c  # 11300-11303 stay single-register writes


# ------------------------------------------------------------------ get_doc_section
def test_get_doc_section():
    s = docs.get_doc_section("sunspec", "Control gate")
    assert "0x5355" in s["markdown"]
    n = docs.get_doc_section("native", "Controlling the inverter")
    assert "14250" in n["markdown"]
    miss = docs.get_doc_section("native", "No such chapter")
    assert "sections" in miss
    assert "error" in docs.get_doc_section("cloud", "x")


def test_outputs_have_no_internal_content():
    blob = "".join(docs.text(n) for n in docs.DATA_FILES)
    for bad in ("firmware_src", "INTERNAL", "notes_internal", "\"macro\"", "wt_v1130"):
        assert bad not in blob
    json.loads(docs.text("recipes.v1130.json"))


def test_integer_address_accepted():
    from wattsonic_modbus_docs import server
    a = server.get_register(11045)
    b = server.get_register("11045")
    assert a == b
    v = server.validate_write(11045, 0)
    assert v["verdict"] in ("ok", "ok_with_warnings", "reject")

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import convert_core  # noqa: E402

QSF = """\
set_global_assignment -name FAMILY "Cyclone V"
set_global_assignment -name DEVICE 5CSEBA6U23I7
set_global_assignment -name DEVICE_FILTER_PACKAGE UFBGA
set_global_assignment -name LAST_QUARTUS_VERSION "17.0.2 Lite Edition"
# set_global_assignment -name FAMILY "Cyclone V"
set_global_assignment -name TOP_LEVEL_ENTITY sys_top
"""

CORE_RTL = """\
module emu();
altera_pll #(.reference_clock_frequency("50.0 MHz")) pll_i();
altddio_out ddio();
(* ramstyle = "M10K" *) reg [7:0] mem[256];
endmodule
"""


def make_core(root):
    core = root / "Test_MiSTer"
    (core / "sys").mkdir(parents=True)
    (core / "rtl").mkdir()
    (core / "Test.qsf").write_text(QSF)
    (core / "rtl" / "core.sv").write_text(CORE_RTL)
    # Cyclone V code inside sys/ is the framework's job, not the core's.
    (core / "sys" / "sys_top.v").write_text("cyclonev_hps_interface_mpu_general_purpose h();\n")
    (core / "sys" / "sys.tcl").write_text(
        'set_global_assignment -name FAMILY "Cyclone V"\n'
        "set_global_assignment -name DEVICE 5CSEBA6U23I7\n")
    (core / "rtl" / "pll.qip").write_text(
        'set_global_assignment -entity "pll" -name IP_TARGETED_DEVICE_FAMILY "Cyclone V"\n')
    return core


class ConvertCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.core = make_core(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_qsf_retargeted(self):
        text, changes = convert_core.convert_qsf_text(QSF)
        self.assertIn('-name FAMILY "Agilex 5"', text)
        self.assertIn("-name DEVICE A5EB013BB23BE4SR1", text)
        self.assertIn("# [DE25] set_global_assignment -name DEVICE_FILTER_PACKAGE", text)
        self.assertIn("# [DE25] set_global_assignment -name LAST_QUARTUS_VERSION", text)
        self.assertIn('# set_global_assignment -name FAMILY "Cyclone V"', text)
        self.assertIn("-name TOP_LEVEL_ENTITY sys_top", text)
        self.assertEqual(len(changes), 4)

    def test_analyze_ignores_sys(self):
        cats = sorted(f.category for f in convert_core.analyze(self.core))
        self.assertEqual(cats, ["ddio", "family", "pll", "ramstyle"])

    def test_convert_leaves_source_untouched(self):
        out = self.root / "out"
        subprocess.run([sys.executable, str(ROOT / "tools" / "convert_core.py"),
                        "convert", str(self.core), str(out)], check=True,
                       capture_output=True)
        self.assertEqual((self.core / "Test.qsf").read_text(), QSF)
        self.assertIn("Agilex 5", (out / "Test.qsf").read_text())
        self.assertIn("A5EB013BB23BE4SR1", (out / "sys" / "sys.tcl").read_text())
        report = (out / "DE25_PORT_REPORT.md").read_text()
        self.assertIn("altddio", report)
        self.assertIn("will not build", report)

    def test_convert_refuses_existing_output(self):
        out = self.root / "out"
        out.mkdir()
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "convert_core.py"),
                                 "convert", str(self.core), str(out)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)


if __name__ == "__main__":
    unittest.main()

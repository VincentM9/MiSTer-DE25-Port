# sys_de25

Drop-in replacement for a MiSTer core's `sys/` folder, targeting the DE25-Nano.

It must expose the **same `emu` module interface** as upstream
[`Template_MiSTer/sys`](https://github.com/MiSTer-devel/Template_MiSTer/tree/master/sys)
so cores build without changes to their own RTL.

`tools/convert_core.py convert` copies this folder into the converted core as `sys/`.
Until the modules below exist, the converter keeps the core's original `sys/` and marks
the output as not buildable.

## Modules to implement

| Upstream file | Purpose | Status |
|---|---|---|
| `sys_top.v` | Board top level, instantiates `emu` | todo |
| `sys.qip` / `sys_analog.tcl` / `sys_dual_sdram.tcl` | Project file lists and pin assignments | todo -> `sys.qip`, `de25_pins.tcl` |
| `pll*.v`, `pll_cfg/` | Clock generation and reconfiguration | todo (Agilex 5 IOPLL) |
| `hps_io.sv` | HPS command channel | todo |
| `ddr_svc.sv`, `sysmem.sv` | Shared DDR access | todo |
| `ascal.vhd`, `video_*.sv`, `scandoubler.v` | Scaler and video pipeline | todo (mostly portable RTL) |
| `audio_out.v`, `i2s.v`, `spdif.v` | Audio output | todo |
| `osd.v`, `vga_out.sv`, `yc_out.sv` | OSD and analog/YC output | todo |

Portable RTL (no vendor primitives) should be copied from upstream unchanged and only
the vendor-specific parts rewritten.

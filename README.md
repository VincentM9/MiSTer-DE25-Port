# MiSTer-DE25-Port

A porting layer that lets [MiSTer FPGA](https://github.com/MiSTer-devel) cores and the
MiSTer framework run on the **Terasic DE25-Nano** (Intel/Altera Agilex 5 SoC) instead of
the original **DE10-Nano** (Cyclone V SoC).

> **Status: early scaffold.** Nothing here boots a core yet. The repository currently
> contains the plan, a hardware mapping, and a core-analysis/conversion tool that tells
> you exactly what in a given core needs to change.

## Why a "port" and not a simple converter

MiSTer cores are not portable bitstreams. Each core is a Quartus project that is tied to
the DE10-Nano in three places, and all three change on the DE25-Nano:

| Layer | DE10-Nano (today) | DE25-Nano (target) |
|---|---|---|
| FPGA fabric | Cyclone V SE `5CSEBA6U23I7` | Agilex 5 E-series `A5EB013BB23BE4SR1` |
| Toolchain | Quartus Prime **Lite/Standard** 17.0 | Quartus Prime **Pro** (Agilex 5 is Pro-only) |
| HPS CPU | 2x Cortex-A9 (ARMv7, 32-bit) | 2x Cortex-A76 + 2x Cortex-A55 (ARMv8, 64-bit) |
| HPS <-> FPGA | `cyclonev_hps_interface_*` atoms, F2H/H2F bridges | Agilex 5 HPS EMIF/bridges via Platform Designer |
| Memory | 1 GB DDR3 (HPS, shared), SDRAM add-on board | 1 GB LPDDR4 HPS (shared) + 1 GB LPDDR4 FPGA + 128 MB SDRAM on board |
| Video out | HDMI via ADV7513 | HDMI 2.0 |

So the work splits into three pieces, which map to this repo's layout:

1. **`sys_de25/` — FPGA framework shim.** Every MiSTer core includes a shared `sys/`
   folder (`sys_top.v`, `hps_io`, `ascal`, `pll_*`, `ddr_svc`, `sysmem`, audio/video
   output, etc.). Cores talk to the board only through the `emu` module interface that
   `sys/` provides. If we re-implement `sys/` for Agilex 5 while keeping the `emu`
   interface identical, most cores' own RTL can stay unchanged. This is the real
   "translation layer".
2. **`tools/convert_core.py` — per-core converter.** Swaps a core's `sys/` for
   `sys_de25/`, rewrites the `.qsf` device/family settings, and flags anything inside
   the core itself that uses Cyclone V-only primitives (PLLs, `altddio`, `cyclonev_*`
   atoms, device-specific memory IP) so it can be regenerated for Agilex 5.
3. **HPS software (planned).** `Main_MiSTer` and the MiSTer Linux image must be rebuilt
   for 64-bit ARM, and the FPGA programming / HPS-FPGA bridge code updated for Agilex 5.

See [`docs/porting-plan.md`](docs/porting-plan.md) and
[`docs/hardware-mapping.md`](docs/hardware-mapping.md) for details.

## Using the converter

Requires Python 3.9+ (standard library only).

```sh
# Analyse a core and print what needs porting (no files are changed)
python3 tools/convert_core.py analyze path/to/SNES_MiSTer

# Produce a DE25 copy of the core: rewritten .qsf, sys/ replaced by sys_de25/
python3 tools/convert_core.py convert path/to/SNES_MiSTer out/SNES_DE25
```

`convert` never modifies the source core. Anything it can't translate automatically is
listed in `out/<core>/DE25_PORT_REPORT.md`.

## Roadmap

- [x] Hardware comparison and porting plan
- [x] Core analysis / project-settings conversion tool
- [ ] `sys_de25`: board top level, pin assignments, clocks (Agilex 5 IOPLL)
- [ ] `sys_de25`: HPS <-> FPGA bridge and `hps_io` command channel
- [ ] `sys_de25`: DDR access (`ddr_svc`/`sysmem`) on HPS LPDDR4
- [ ] `sys_de25`: video scaler (`ascal`) and HDMI output
- [ ] `sys_de25`: audio, SDRAM controller timing for on-board SDRAM
- [ ] `Main_MiSTer` aarch64 build + Agilex 5 FPGA manager support
- [ ] Linux image / SD card layout
- [ ] First booting core (suggested: `Template_MiSTer`, then `Menu_MiSTer`)

## Licence

MiSTer's framework and most cores are GPL-3.0 (some GPL-2.0). Because `sys_de25/` is a
derivative of MiSTer's `sys/`, this project should be released under **GPL-3.0**.
Each converted core keeps its original licence.

## Disclaimer

Not affiliated with the MiSTer project or Terasic. Converted cores are not guaranteed to
work until the matching parts of `sys_de25/` are implemented and timing-closed.

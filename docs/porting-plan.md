# Porting plan

The goal is to keep every core's `emu` module untouched and move all board-specific work
into `sys_de25/` and the HPS software. The steps are ordered so each one can be tested on
real hardware before the next starts.

## Phase 1 — Bring-up with a blinky
- Create a minimal Quartus Pro project for `A5EB013BB23BE4SR1` with the DE25-Nano pin
  file from the Terasic System CD.
- Prove clocks, LEDs, buttons and FPGA programming from Linux on the HPS.

## Phase 2 — `sys_de25` skeleton
- Port `sys_top.v` to the DE25 top-level ports. Keep the `emu` instantiation identical.
- Replace `pll_hdmi`, `pll_audio` and the core PLL wrapper with Agilex 5 IOPLLs.
- Stub `hps_io` so `Template_MiSTer` builds and outputs a test pattern over HDMI.

## Phase 3 — HPS link
- Build the HPS system in Platform Designer with the lightweight H2F bridge and an
  F2SDRAM port.
- Port the `hps_io` command protocol (it is a 16-bit GPIO-style handshake; keep the wire
  protocol unchanged so `Main_MiSTer` logic carries over).

## Phase 4 — `Main_MiSTer` on aarch64
- Cross-compile `Main_MiSTer` for 64-bit ARM. Fix 32-bit assumptions (pointer casts,
  `mmap` of `/dev/mem` offsets, struct packing).
- Replace the Cyclone V FPGA manager register code with the Linux FPGA manager
  framework (`/sys/class/fpga_manager`) for Agilex 5.
- Update physical addresses of the bridges and shared memory windows.

## Phase 5 — Memory, video, audio
- `ddr_svc` / `sysmem` on HPS LPDDR4; verify bandwidth for `ascal` framebuffer.
- `ascal` scaler and HDMI output; this is the most timing-sensitive block.
- On-board SDRAM controller timing for cores that use `SDRAM_*`.
- Audio output path.

## Phase 6 — Cores
- `Menu_MiSTer`, then simple cores (Template, NES), then demanding ones (SNES, Genesis,
  PSX). Run `tools/convert_core.py convert` on each and work through its report.
- Track status per core in `docs/core-status.md`.

## Known risks
- **Quartus Pro** is required for Agilex 5; the free Pro edition licence may limit some
  devices, so confirm the DE25 part is covered.
- MiSTer's `sys/` changes regularly upstream. Keep `sys_de25/` as a fork that tracks
  upstream `sys/` so fixes can be merged.
- Timing on Agilex 5 is different; cores that barely close timing on Cyclone V may need
  fresh constraints, not just a recompile.

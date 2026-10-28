# Cyclone V -> Agilex 5 mapping

What each Cyclone V-specific thing used by MiSTer cores becomes on the DE25-Nano.
`tools/convert_core.py` uses the same categories when it reports on a core.

## Project settings (`.qsf`)

| Setting | DE10-Nano | DE25-Nano |
|---|---|---|
| `FAMILY` | `"Cyclone V"` | `"Agilex 5"` |
| `DEVICE` | `5CSEBA6U23I7` | `A5EB013BB23BE4SR1` |
| Toolchain | Quartus Lite/Standard | Quartus Prime Pro |
| `LAST_QUARTUS_VERSION` | `17.0.x` | Pro version used for the build |

The converter rewrites `FAMILY` and `DEVICE`, and comments out assignments tied to the
Cyclone V part (`DEVICE_FILTER_*`, `MIN/MAX_CORE_JUNCTION_TEMP`,
`LAST_QUARTUS_VERSION`). Quartus Pro may still reject other Standard-edition settings;
fix those by hand when the first Pro compile reports them.

## Primitives and IP

| Found in core | Why it breaks | Agilex 5 replacement |
|---|---|---|
| `altera_pll` / PLL IP generated for Cyclone V (`pll.qip`, `pll_*.v`) | Cyclone V fractional PLL | Regenerate as **IOPLL** IP in Quartus Pro; keep the same output frequencies |
| `altera_pll_reconfig` / `pll_cfg` | Different reconfig interface | IOPLL dynamic reconfiguration (handled in `sys_de25`) |
| `cyclonev_*` atoms (e.g. `cyclonev_hps_interface_*`, `cyclonev_clkena`) | Device atoms don't exist on Agilex 5 | `sys_de25` equivalents; for `clkena` use the Agilex clock-control IP |
| `altddio_out` / `altddio_in` | Not supported on Agilex 5 | GPIO IP in DDR mode |
| `altsyncram` / `altdpram` with `intended_device_family = "Cyclone V"` | Usually fine, but family param is wrong | Change the family string, or infer RAM in plain RTL |
| `altera_mult_add`, `altmult_add` with Cyclone V DSP settings | DSP block differs | Infer multipliers or regenerate DSP IP |
| M10K-specific `ramstyle` attributes | Agilex 5 has M20K | Use `"M20K"` or let Quartus choose |

## Board resources (handled in `sys_de25`, not in cores)

| Resource | DE10-Nano | DE25-Nano |
|---|---|---|
| HPS <-> FPGA command channel (`hps_io`) | GPIO over the lightweight H2F bridge | Agilex 5 lightweight H2F bridge |
| Shared DDR (`ddr_svc`, `sysmem`) | F2H SDRAM ports on DDR3 | F2SDRAM bridge on HPS LPDDR4 |
| SDRAM (`SDRAM_*` ports) | Add-on board on GPIO header | 128 MB on-board SDRAM (new pinout and timing) |
| Video | ADV7513 HDMI transmitter over I2C | HDMI 2.0 output (new transmitter driver) |
| Audio | I2S to ADV7513 + 1-bit DAC on I/O board | TBD once the HDMI transmitter is confirmed |
| User I/O, I/O board, SNAC | Arduino header / GPIO | 2x 40-pin DE-GPIO headers (pinout adapter needed) |

Pin locations come from the Terasic DE25-Nano System CD and should go in
`sys_de25/de25_pins.tcl` once verified against the schematic.

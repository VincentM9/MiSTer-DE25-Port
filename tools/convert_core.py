#!/usr/bin/env python3
"""Analyse a MiSTer core and convert its Quartus project for the DE25-Nano.

  convert_core.py analyze <core_dir>
  convert_core.py convert <core_dir> <out_dir> [--force]

`analyze` only reads. `convert` copies the core to <out_dir>, rewrites the
.qsf for Agilex 5, swaps in sys_de25/ when it is ready, and writes
DE25_PORT_REPORT.md listing everything that still needs manual work.
"""

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

TARGET_FAMILY = "Agilex 5"
TARGET_DEVICE = "A5EB013BB23BE4SR1"

REPO_ROOT = Path(__file__).resolve().parent.parent
SYS_DE25 = REPO_ROOT / "sys_de25"

HDL_SUFFIXES = {".v", ".sv", ".vh", ".svh", ".vhd", ".vhdl", ".qip", ".tcl", ".sdc"}
SKIP_DIRS = {".git", "db", "incremental_db", "output_files", "qdb", "tmp-clearbox"}

# (category, regex, advice) applied line by line to the core's own sources.
PATTERNS = [
    ("pll", re.compile(r"\baltera_pll\b|\baltera_pll_reconfig\b"),
     "Cyclone V PLL: regenerate as an Agilex 5 IOPLL with the same output clocks."),
    ("atom", re.compile(r"\bcyclonev_\w+"),
     "Cyclone V device atom: replace with the Agilex 5 equivalent or a sys_de25 wrapper."),
    ("ddio", re.compile(r"\baltddio_(?:in|out|bidir)\b"),
     "altddio is not supported on Agilex 5: use the GPIO IP in DDR mode."),
    ("family", re.compile(r"(?:intended|ip_targeted|ip_generated)_device_family\W+"
                          r"\{?Cyclone V", re.I),
     f'Change intended_device_family to "{TARGET_FAMILY}" or infer the RAM in RTL.'),
    ("ramstyle", re.compile(r"ramstyle\s*=\s*\"?M10K", re.I),
     'Agilex 5 has M20K blocks: use "M20K" or drop the attribute.'),
    ("dsp", re.compile(r"\balt(?:era_)?mult_add\b|\baltmult_accum\b"),
     "Cyclone V DSP IP: infer the multiplier in RTL or regenerate the DSP IP."),
]

# .qsf assignments that are tied to the Cyclone V part and are dropped.
QSF_DROP = re.compile(
    r"-name\s+(DEVICE_FILTER_\w+|MIN_CORE_JUNCTION_TEMP|MAX_CORE_JUNCTION_TEMP"
    r"|LAST_QUARTUS_VERSION)\b")
QSF_FAMILY = re.compile(r"(-name\s+FAMILY\s+)(\"[^\"]*\"|\S+)")
QSF_DEVICE = re.compile(r"(-name\s+DEVICE\s+)(\S+)")


@dataclass
class Finding:
    category: str
    path: Path
    line: int
    text: str
    advice: str


def iter_files(root):
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def is_sys_path(root, path):
    return path.relative_to(root).parts[0] == "sys"


def sys_de25_ready():
    return (SYS_DE25 / "sys_top.v").is_file()


def analyze(core):
    findings = []
    for path in iter_files(core):
        if path.suffix.lower() not in HDL_SUFFIXES or is_sys_path(core, path):
            continue
        text = path.read_text(errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            for category, pattern, advice in PATTERNS:
                if pattern.search(line):
                    findings.append(Finding(category, path.relative_to(core), lineno,
                                            line.strip(), advice))
    return findings


def find_qsf(core):
    return [p for p in iter_files(core) if p.suffix.lower() == ".qsf"]


def find_settings(core):
    """Files holding project-wide assignments: the .qsf files plus sys/sys.tcl,
    which is where upstream MiSTer cores set FAMILY and DEVICE."""
    files = find_qsf(core)
    if (core / "sys" / "sys.tcl").is_file():
        files.append(core / "sys" / "sys.tcl")
    return files


def convert_qsf_text(text):
    """Return (new_text, changes) with the project retargeted to the DE25-Nano."""
    out, changes = [], []
    for lineno, line in enumerate(text.splitlines(keepends=True), 1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            out.append(line)
            continue
        if QSF_DROP.search(line):
            out.append("# [DE25] " + line)
            changes.append(f"line {lineno}: commented out `{line.strip()}`")
        elif QSF_FAMILY.search(line):
            new = QSF_FAMILY.sub(rf'\g<1>"{TARGET_FAMILY}"', line)
            out.append(new)
            changes.append(f"line {lineno}: FAMILY -> \"{TARGET_FAMILY}\"")
        elif QSF_DEVICE.search(line):
            new = QSF_DEVICE.sub(rf"\g<1>{TARGET_DEVICE}", line)
            out.append(new)
            changes.append(f"line {lineno}: DEVICE -> {TARGET_DEVICE}")
        else:
            out.append(line)
    return "".join(out), changes


def print_findings(core, findings):
    qsfs = find_qsf(core)
    print(f"Core: {core}")
    print(f"  .qsf files: {', '.join(str(q.relative_to(core)) for q in qsfs) or 'none found'}")
    print(f"  sys/ folder: {'present' if (core / 'sys').is_dir() else 'MISSING'}")
    print(f"  sys_de25 ready: {'yes' if sys_de25_ready() else 'no (sys/ will be kept)'}")
    if not findings:
        print("  No Cyclone V-specific code found outside sys/.")
        return
    print(f"  {len(findings)} item(s) need porting outside sys/:")
    for f in findings:
        print(f"    [{f.category}] {f.path}:{f.line}: {f.text[:100]}")
    print("\nAdvice:")
    for category, _, advice in PATTERNS:
        if any(f.category == category for f in findings):
            print(f"  [{category}] {advice}")


def write_report(out, core, findings, qsf_changes, sys_swapped):
    lines = [f"# DE25 port report for `{core.name}`", ""]
    lines += ["## Project settings", ""]
    if qsf_changes:
        for qsf, changes in qsf_changes.items():
            lines.append(f"`{qsf}`:")
            lines += [f"- {c}" for c in changes] or ["- no changes"]
            lines.append("")
    else:
        lines += ["No .qsf or sys/sys.tcl found: create a Quartus Pro project manually.", ""]
    lines += ["## Framework", ""]
    lines.append("sys/ replaced with sys_de25/." if sys_swapped else
                 "sys_de25/ is not implemented yet, so the original Cyclone V sys/ was "
                 "kept. **This output will not build for the DE25-Nano yet.**")
    lines += ["", "## Core sources needing manual work", ""]
    if findings:
        lines += ["| Category | Location | Code | What to do |", "|---|---|---|---|"]
        for f in findings:
            code = f.text[:80].replace("|", "\\|")
            lines.append(f"| {f.category} | `{f.path}:{f.line}` | `{code}` | {f.advice} |")
    else:
        lines.append("None found.")
    lines.append("")
    (out / "DE25_PORT_REPORT.md").write_text("\n".join(lines))


def convert(core, out, force):
    if out.resolve().is_relative_to(core.resolve()):
        sys.exit("error: output directory must not be inside the core directory")
    if out.exists():
        if not force:
            sys.exit(f"error: {out} already exists (use --force to replace it)")
        shutil.rmtree(out)

    shutil.copytree(core, out, ignore=shutil.ignore_patterns(*SKIP_DIRS))

    sys_swapped = False
    if sys_de25_ready():
        if (out / "sys").exists():
            shutil.rmtree(out / "sys")
        shutil.copytree(SYS_DE25, out / "sys", ignore=shutil.ignore_patterns("README.md"))
        sys_swapped = True

    qsf_changes = {}
    for qsf in find_settings(out):
        text = qsf.read_text(errors="replace")
        new_text, changes = convert_qsf_text(text)
        qsf.write_text(new_text)
        qsf_changes[str(qsf.relative_to(out))] = changes

    findings = analyze(out)
    write_report(out, core, findings, qsf_changes, sys_swapped)
    print(f"Converted {core} -> {out}")
    print(f"  {sum(len(c) for c in qsf_changes.values())} project-setting change(s), "
          f"{len(findings)} item(s) for manual porting")
    print(f"  Report: {out / 'DE25_PORT_REPORT.md'}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="report what a core needs for the DE25-Nano")
    a.add_argument("core", type=Path)
    c = sub.add_parser("convert", help="write a DE25 copy of a core")
    c.add_argument("core", type=Path)
    c.add_argument("out", type=Path)
    c.add_argument("--force", action="store_true", help="replace an existing output dir")
    args = parser.parse_args(argv)

    if not args.core.is_dir():
        sys.exit(f"error: {args.core} is not a directory")
    if args.cmd == "analyze":
        print_findings(args.core, analyze(args.core))
    else:
        convert(args.core, args.out, args.force)


if __name__ == "__main__":
    main()

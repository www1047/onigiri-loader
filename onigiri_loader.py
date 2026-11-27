"""
Onigiri Loader - a mod manager for GTA V (single player) built around the
NaturalVision Enhanced "onigiri" folder layout.

How it works
------------
* Mods are installed (zip or folder) into a private library:
      %APPDATA%\\OnigiriLoader\\library\\<mod name>\\...
* Enabling a mod deploys its files into the onigiri folder
  (default: <GTA V>\\onigiri) using this topology:
      common\\data\\{ai,effects,levels\\gta5\\weather,materials,timecycle}
      dlcpacks\\
      platform\\{data\\{effects,metadata,tune},levels\\gta5\\cloudhats,textures}
* .asi plugins and scripts\\ must sit in the game root to be loaded by the
  ASI loader, so those are routed there instead.
* Load order = list order. When two mods touch the same file, the one lower
  in the list wins. Files are hard-linked when possible (no extra disk use),
  copied otherwise. Anything overwritten is backed up and restored on disable.

Script mods (.NET .dll/.cs/.vb) install into <game>\\scripts; needs ScriptHookVDotNet.\nDark theme by default (switch in the window).\nCombines mods that edit the same text file (three-way merge; existing onigiri files such as NVE's\nare used as the baseline). .asi plugins and their .ini files install next to the game exe.\nLegacy (old game) files such as dinput8.dll are only used when the Enhanced equivalent (xinput1_4.dll) is absent.\nMods that ship labeled branches (a 'legacy' folder next to an 'enhanced' folder) install only the Enhanced branch.\nOpenIV package files (.oiv) and OpenIV support files (openiv.asi / openrpf.asi) are never installed -
they cause compatibility issues and crashes.\nLearns where loose files belong from mods already installed.\nReads a mod's README to place files that have no folder structure.
Supports .zip, .7z and .rar. 7z/rar use an installed program: 7-Zip or WinRAR (free 7-zip.org),
or the tar that ships with newer Windows. Archives are recognised by content, not just the extension.
Run:  python onigiri_loader.py        (Python 3.9+, Windows, tkinter included)
The app asks for administrator rights (UAC) on launch; GTA V is often in
Program Files, where writing mod files needs them.
A 'Reset all' button (bottom row, with an 'Are you sure?' prompt) unloads every
mod, deletes the library and backups, and returns the loader to a fresh
first-time state.
"""
import difflib
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
import zlib
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "OnigiriLoader"
LIB_DIR = APP_DIR / "library"
BACKUP_DIR = APP_DIR / "backup"
BASE_DIR = APP_DIR / "base"        # vanilla copies used as merge bases (onigiri layout)
MERGE_DIR = APP_DIR / "merged"     # generated merged files
STATE_FILE = APP_DIR / "state.json"

# Folder topology of the onigiri folder (taken from a working install).
# Only the top-level folders are enforced; mods may add their own subfolders.
TOPOLOGY = {
    "common": {"data": {"ai": {}, "effects": {}, "levels": {"gta5": {"weather": {}}},
                        "materials": {}, "timecycle": {}}},
    "dlcpacks": {},
    "platform": {"data": {"effects": {}, "metadata": {}, "tune": {}},
                 "levels": {"gta5": {"cloudhats": {}}},
                 "textures": {}},
}
ROOTS = set(TOPOLOGY) | {"platform2"}   # onigiri.asi also mounts onigiri:/platform2/


# .rpf archives whose home is known by file name (anything else asks the user)
KNOWN_RPF = {"v_clouds.rpf": "platform/levels/gta5/cloudhats"}
# Where files live in a working NaturalVision Enhanced onigiri folder (names only).
# Used to place loose files before any other mod has been installed.
KNOWN_FILES = {
    "common/data": [
        "cloudkeyframes.xml", "clouds.xml", "dlclist.xml", "gameconfig.xml", "gtxd.meta",
        "lensflare_f.xml", "lensflare_m.xml", "lensflare_t.xml", "visualsettings.dat",
        "watertune.xml"],
    "common/data/ai": [
        "weapons.meta"],
    "common/data/effects": [
        "bloodfx.dat", "decals.dat", "entityfx.dat", "explosionfx.dat", "firefx.dat",
        "liquidfx.dat", "vfxlightningsettings.xml", "wheelfx.dat"],
    "common/data/levels/gta5": [
        "gta5.meta", "time.xml", "water.xml", "weather.xml"],
    "common/data/levels/gta5/weather": [
        "blizzard_emitter_mist.xml", "blizzard_render_drop.xml", "blizzard_render_mist.xml",
        "clearing_render_drop.xml", "clearing_render_ground.xml",
        "desert_emitter_ground.xml", "desert_emitter_ground_heavy.xml",
        "desert_render_ground.xml", "desert_render_ground_heavy.xml",
        "firefly_emitter_drop.xml", "firefly_render_drop.xml", "pollen_emitter_drop.xml",
        "pollen_render_drop.xml", "rainstorm_emitter_drop.xml",
        "rainstorm_emitter_ground.xml", "rainstorm_emitter_mist.xml",
        "rainstorm_render_drop.xml", "rainstorm_render_ground.xml",
        "rainstorm_render_mist.xml", "snowheavy_emitter_ground.xml",
        "snowheavy_emitter_mist.xml", "snowheavy_render_ground.xml",
        "snowheavy_render_mist.xml", "snowlight_emitter_drop.xml",
        "snowlight_render_drop.xml", "thunder_emitter_drop.xml",
        "thunder_emitter_ground.xml", "thunder_render_drop.xml", "thunder_render_ground.xml"],
    "common/data/materials": [
        "procedural.meta"],
    "common/data/timecycle": [
        "timecycle_mods_1.xml", "timecycle_mods_2.xml", "timecycle_mods_3.xml",
        "timecycle_mods_4.xml", "timecycle_mods_5.xml", "underwater_deep.xml",
        "w_blizzard.xml", "w_clear.xml", "w_clearing.xml", "w_clouds.xml",
        "w_extrasunny.xml", "w_foggy.xml", "w_halloween.xml", "w_neutral.xml",
        "w_overcast.xml", "w_rain.xml", "w_rainhalloween.xml", "w_smog.xml", "w_snow.xml",
        "w_snowhalloween.xml", "w_snowlight.xml", "w_thunder.xml", "w_xmas.xml"],
    "platform/data": [
        "carcols.ymt"],
    "platform/data/effects": [
        "lensartefacts.ymt", "vfxfogvolumeinfo.ymt", "vfxregioninfo.ymt",
        "vfxvehicleinfo.ymt"],
    "platform/data/metadata": [
        "explosion.ymt"],
    "platform/levels/gta5": [
        "zonebind.ymt"],
    "platform/levels/gta5/cloudhats": [
        "v_clouds.rpf"],
    "platform/textures": [
        "frontend.ytd", "fxweather.ytd", "graphics.ytd", "mapdetail.ytd",
        "peddamagedecals.ytd", "skydome.ytd"],
}

# Registry files that sit at the root of the onigiri folder. Mods add <Item> entries to them.
_EMPTY_REGISTRY = ('<?xml version="1.0" encoding="UTF-8"?>\r\n<CDataFileMgr__ContentsOfDataFileXml>\r\n'
                   '    <dataFiles>\r\n    </dataFiles>\r\n</CDataFileMgr__ContentsOfDataFileXml>')
BUILTIN_BASES = {"after_level.xml": _EMPTY_REGISTRY, "before_level.xml": _EMPTY_REGISTRY}
ROOT_FILES = set(BUILTIN_BASES)
RPF_ENCRYPTION = {0x4E45504F: "unencrypted (OPEN)", 0x0FFFFFF9: "AES-encrypted",
                  0x0FEFFFFF: "NG-encrypted", 0: "unencrypted"}


# ---- script mods (ScriptHookVDotNet) ----------------------------------------
SCRIPT_CODE_EXT = {".dll", ".cs", ".vb"}                 # script code (loaded from <game>\\scripts)
SCRIPT_CFG_EXT = {".ini", ".xml", ".json", ".cfg"}       # config files that live beside a script
FRAMEWORK_DLLS = ("scripthookv", "minhook", "reshade", "dxgi", "d3d", "xinput")
IGNORED_DIRS = {"docs", "doc", "documentation", "licenses", "license", "debug",
                "screenshots", "images", "preview", "previews"}
OPTIONAL_CORE = {"ScriptHookVDotNet.asi"}
# Files made for the old (legacy) game and the Enhanced file that replaces them.
# The Enhanced file always wins when it is present; the legacy file is only used
# as a fallback (see legacy_status / _scan / _desired).
LEGACY_FILES = {
    "dinput8.dll": "xinput1_4.dll",     # ASI loader: old game vs Enhanced
    "opencamerav.asi": None,            # no Enhanced equivalent
}
# Labels that mark which game version a branch of a mod's structure is for, e.g.
# 'GTA V Legacy' next to 'GTA V Enhanced'. When both labels are present, only the
# Enhanced branch is installed (see _labeled_branches).
LEGACY_LABEL = "legacy"
ENHANCED_LABEL = "enhanced"
NEVER_DEPLOY_EXT = {".oiv"}    # OpenIV package files: the game can't read them; never installed
NEVER_DEPLOY_NAMES = {"openiv.asi", "openrpf.asi"}   # OpenIV support files: cause compatibility issues and crashes; never installed


def is_managed_dll(path):
    """True for a .NET assembly (script mods are .NET DLLs), False for a native DLL."""
    try:
        with open(path, "rb") as f:
            head = f.read(64)
            if head[:2] != b"MZ":
                return False
            pe = struct.unpack_from("<I", head, 0x3C)[0]
            f.seek(pe)
            hdr = f.read(264)                            # PE signature + COFF + optional header
        if hdr[:4] != b"PE\0\0":
            return False
        magic = struct.unpack_from("<H", hdr, 24)[0]
        dirs = 24 + (96 if magic == 0x10B else 112)      # start of the data directories
        rva, size = struct.unpack_from("<II", hdr, dirs + 14 * 8)   # entry 14 = CLR (.NET) header
        return rva != 0 and size != 0
    except Exception:
        return False


# ---- reading unencrypted RPF7 archives (read-only) --------------------------------
_RPF_OPEN = 0x4E45504F
_DLC_BOILERPLATE = {"content.xml", "setup2.xml", "_manifest.ymf"}
DLCLIST_REL = Path("common/data/dlclist.xml")
_dlc_cache, _hash_cache = {}, {}


class _Rpf:
    """Table of contents of one unencrypted (OPEN) RPF7 archive. Raises ValueError for anything
    else: encrypted archives need the game's keys, which this loader never uses."""

    def __init__(self, f, base=0):
        f.seek(base)
        h = f.read(16)
        if len(h) < 16 or h[:4] != b"7FPR":
            raise ValueError("not an RPF7 archive")
        n, nl, enc = struct.unpack("<III", h[4:16])
        if enc != _RPF_OPEN:
            raise ValueError("encrypted")
        if n > 500000 or nl > (64 << 20):
            raise ValueError("not an RPF7 archive")
        ents, names = f.read(n * 16), f.read(nl)
        if len(ents) < n * 16:
            raise ValueError("truncated archive")
        self.f, self.base, self.e = f, base, []
        for i in range(n):
            b = ents[i * 16:(i + 1) * 16]
            if struct.unpack("<I", b[4:8])[0] == 0x7FFFFF00:                 # directory entry
                n0, _x, idx, cnt = struct.unpack("<IIII", b)
                self.e.append({"kind": "dir", "name": self._name(names, n0), "idx": idx, "cnt": cnt})
            else:
                n0 = struct.unpack("<H", b[:2])[0]
                size = int.from_bytes(b[2:5], "little")
                off = int.from_bytes(b[5:8], "little")
                res = bool(off & 0x800000)
                self.e.append({"kind": "res" if res else "bin", "name": self._name(names, n0),
                               "off": (off & 0x7FFFFF) * 512, "size": size,
                               "usize": size if res else struct.unpack("<I", b[8:12])[0]})

    @staticmethod
    def _name(names, o):
        try:
            return names[o:names.index(b"\0", o)].decode("latin-1")
        except ValueError:
            return ""

    def walk(self, i=0, prefix="", depth=0):
        if i >= len(self.e) or depth > 64:
            return
        e = self.e[i]
        if e["kind"] == "dir":
            here = prefix + (e["name"] + "/" if e["name"] else "")
            for c in range(e["idx"], min(e["idx"] + e["cnt"], len(self.e))):
                yield from self.walk(c, here, depth + 1)
        else:
            yield prefix + e["name"], e

    def read(self, e):
        self.f.seek(self.base + e["off"])
        return self.f.read(e["size"] or e["usize"])


def _xml_text(raw):
    for fn in (lambda b: b, lambda b: zlib.decompress(b, -15)):
        try:
            s = fn(raw).decode("utf-8-sig")
            if s.lstrip().startswith("<"):
                return s
        except Exception:
            pass
    return None


def dlc_info(path):
    """What a DLC pack says about itself (its setup2.xml) and every path inside it, including
    nested archives ('inner.rpf!/file'). {'readable': False, 'reason': ...} for encrypted or
    unreadable archives; 'is_pack' is True only if the archive has a setup2.xml."""
    p = Path(path)
    try:
        st = p.stat()
    except OSError:
        return {"readable": False, "reason": "missing", "is_pack": False, "name": "", "order": None, "paths": {}}
    key = (str(p), st.st_size, st.st_mtime_ns)
    if key in _dlc_cache:
        return _dlc_cache[key]
    info = {"readable": False, "reason": "", "is_pack": False, "name": "", "device": "",
            "order": None, "paths": {}, "nested": []}
    try:
        with open(p, "rb") as f:
            root = _Rpf(f)
            paths, setup = {}, None

            def go(r, prefix, depth):
                for pth, e in r.walk():
                    paths[(prefix + pth).lower()] = e["usize"] or e["size"]
                    if e["kind"] == "bin" and pth.lower().endswith(".rpf") and depth < 3:
                        try:
                            go(_Rpf(f, r.base + e["off"]), prefix + pth + "!/", depth + 1)
                        except ValueError:
                            pass
            go(root, "", 0)
            for pth, e in root.walk():
                if pth.lower() == "setup2.xml":
                    setup = _xml_text(root.read(e))
                    break
            info.update(readable=True, paths=paths,
                        nested=sorted(k for k in paths if k.endswith(".rpf") and "!" not in k))
            if setup:
                def tag(t):
                    m = re.search(rf"<{t}>\s*(.*?)\s*</{t}>", setup, re.S | re.I)
                    return m.group(1) if m else ""
                m = re.search(r'<order\s+value="(\d+)"', setup)
                info.update(is_pack=True, device=tag("deviceName"), name=tag("nameHash"),
                            order=int(m.group(1)) if m else None)
    except (ValueError, OSError) as e:
        info["reason"] = str(e)
    _dlc_cache[key] = info
    return info


def files_identical(a, b):
    a, b = Path(a), Path(b)
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
    except OSError:
        return False

    def digest(p):
        st = p.stat()
        k = (str(p), st.st_size, st.st_mtime_ns)
        if k not in _hash_cache:
            h = hashlib.sha1()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            _hash_cache[k] = h.digest()
        return _hash_cache[k]
    return digest(a) == digest(b)


def rpf_info(path):
    """Read the 16-byte RPF7 header. Returns {'entries', 'encryption'} or None if the
    file is not an RPF7 archive. (The loader never decrypts; .rpf files are deployed as-is.)"""
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return None
    if len(head) < 16 or head[:4] != b"7FPR":           # 'RPF7' stored little-endian
        return None
    entries, _names, enc = struct.unpack("<III", head[4:16])
    return {"entries": entries,
            "encryption": RPF_ENCRYPTION.get(enc, f"unknown (0x{enc:08X})")}


def topology_paths():
    """Every folder in the topology as 'common/data/timecycle' style paths."""
    out = []
    def walk(tree, prefix):
        for n, sub in tree.items():
            out.append(prefix + n)
            walk(sub, prefix + n + "/")
    walk(TOPOLOGY, "")
    return out


# ---- README reading ---------------------------------------------------------
README_STEM = re.compile(r"^(read[\s_-]*me|install(ation)?|instructions?|how[\s_-]*to)", re.I)
README_EXT = {".txt", ".md", ".rtf", ""}
PATH_RE = re.compile(r"(?<![\w.])(?:onigiri|nve|mods|update(?:\.rpf)?|x64|common|platform2?|dlcpacks)"
                     r"(?:[\\/][\w.\-]+)+", re.I)
FILE_RE = re.compile(r"[\w\-]+\.(?:rpf|asi|dll|ini|xml|meta|dat|ytd|ydr|yft|ydd|ymt|ytyp|ymap|awc|rel|gfx|bik)\b", re.I)
ACTION_RE = re.compile(r"\b(move|copy|place|put|paste|drag|navigate|goes?\s+to|extract|install|replace)\b", re.I)
NOT_GAME_FILES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".txt", ".md",
                  ".pdf", ".rtf", ".url", ".html", ".htm", ".pdb"}


def read_text(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1", errors="replace")


def _readme_dest(path_str):
    """Turn install-instruction text such as 'Grand Theft Auto V Enhanced\\x64\\audio\\sfx' into
    ('platform/audio/sfx', endfile) using the same root/alias rules as file routing.
    Returns None if the text is not an onigiri location."""
    parts = [x for x in re.split(r"[\\/]+", path_str) if x]
    endfile = None
    if len(parts) > 1 and re.search(r"\.[A-Za-z0-9]{2,4}$", parts[-1]) \
            and parts[-1].lower() != "update.rpf":
        endfile = parts.pop().lower()
    low = [x.lower() for x in parts]
    for i, x in enumerate(low[:6]):
        nxt = low[i + 1] if i + 1 < len(low) else ""
        if x in ROOTS:
            root = x
        elif x in ALIASES and nxt not in ROOTS:
            root = ALIASES[x]
        else:
            continue
        return "/".join([root] + low[i + 1:]), endfile
    return None


def readme_candidates(text):
    """Find folder locations mentioned in install instructions.
    Returns [{'dest', 'score', 'files', 'line'}]; 'files' are file names the same line
    refers to (empty = the instruction applies to the mod's files in general)."""
    out = []
    for raw in text.splitlines():
        if re.match(r"\W*uninstall", raw, re.I):
            break                                   # ignore uninstall instructions
        line = re.sub(r"https?://\S+", "", raw)
        for m in PATH_RE.finditer(line):
            r = _readme_dest(m.group().rstrip(".,;:"))
            if not r:
                continue
            dest, endfile = r
            files = [f.lower() for f in FILE_RE.findall(PATH_RE.sub(" ", line))]
            if endfile:
                files.append(endfile)
            score = 1 + (3 if "onigiri" in line.lower() else 0) + (1 if ACTION_RE.search(line) else 0)
            out.append({"dest": dest, "score": score, "files": files, "line": raw.strip()})
    return out


# ---- three-way merge --------------------------------------------------------
MERGEABLE_EXT = {".xml", ".meta", ".dat", ".txt", ".ini", ".cfg", ".json"}
BASE_DIR_NAMES = {"original files", "originals", "original"}   # vanilla copies shipped in mods
MAX_MERGE_BYTES = 20 * 1024 * 1024


def merge3(base, a, b):
    """Line-based three-way merge of lists of lines.
    Changes that do not overlap are combined, and two pure insertions at the same spot
    are both kept (entries added to a list). Where both sides change the same lines
    differently, `b` (the later / higher-priority mod) wins.
    Returns (merged_lines, number_of_conflicting_spots)."""
    def changes(x, tag):
        sm = difflib.SequenceMatcher(None, base, x, autojunk=False)
        return [(i1, i2, tag, x[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]

    allc = sorted(changes(a, "a") + changes(b, "b"), key=lambda c: (c[0], c[1]))
    out, pos, conflicts, i = [], 0, 0, 0

    def apply(subset, cs, ce):
        res, p = [], cs
        for s_, e_, _t, rp in subset:
            res += base[p:s_] + rp
            p = e_
        return res + base[p:ce]

    while i < len(allc):
        cs, cend = allc[i][0], allc[i][1]
        cluster = [allc[i]]
        has_ins_at_end = allc[i][0] == allc[i][1]
        i += 1
        while i < len(allc):
            s2, e2 = allc[i][0], allc[i][1]
            touching_ins = s2 == cend and s2 == e2 and has_ins_at_end
            if s2 < cend or touching_ins:
                cluster.append(allc[i])
                if e2 > cend:
                    cend = e2
                    has_ins_at_end = False
                if s2 == e2 and e2 == cend:
                    has_ins_at_end = True
                i += 1
            else:
                break
        out += base[pos:cs]
        sub_a = [c for c in cluster if c[2] == "a"]
        sub_b = [c for c in cluster if c[2] == "b"]
        if sub_a and sub_b and cs == cend and all(c[0] == c[1] for c in cluster):
            # both mods only ADD lines at the same spot (e.g. entries in a list): keep both
            la = [x for c in sub_a for x in c[3]]
            lb = [x for c in sub_b for x in c[3]]
            out += la if la == lb else la + lb
        elif sub_a and sub_b:
            ra, rb = apply(sub_a, cs, cend), apply(sub_b, cs, cend)
            if ra != rb:
                conflicts += 1
            out += rb
        else:
            out += apply(cluster, cs, cend)
        pos = cend
    return out + base[pos:], conflicts


def _text_lines(raw: bytes):
    return raw.decode("utf-8", errors="surrogateescape").replace("\r\n", "\n").split("\n")


def topology_text():
    lines = ["onigiri"]
    def walk(tree, prefix):
        items = list(tree.items())
        for i, (name, sub) in enumerate(items):
            last = i == len(items) - 1
            lines.append(f"{prefix}{'\\---' if last else '+---'}{name}")
            walk(sub, prefix + ("    " if last else "|   "))
    walk(TOPOLOGY, "")
    return "\n".join(lines)


def _make_dirs(base: Path, tree):
    for name, sub in tree.items():
        (base / name).mkdir(parents=True, exist_ok=True)
        _make_dirs(base / name, sub)


GAME_ROOT_DIRS = {"scripts", "reshade", "reshade-shaders"}   # folders that belong in the game root
GAME_ROOT_EXT = {".asi", ".dll", ".ini"}                     # root-level files that go to the game root
# The game folder's own x64\\... is onigiri's platform\\... (READMEs and mod folders use the game-folder name)
ALIASES = {"x64": "platform"}
# Folders that are never deployed from a mod (vanilla backups); 'optionals' is split off
# into separate, individually switchable mods.
EXCLUDE_DIRS = {"original files", "originals", "original", "backup", "backups"}
OPTIONAL_DIRS = {"optionals", "optional"}
WRAPPERS = {"onigiri", "nve", "naturalvision enhanced", "gta v", "grand theft auto v",
            "grand theft auto v enhanced"}
SKIP_ROOT_EXT = {".txt", ".md", ".url", ".jpg", ".jpeg", ".png", ".pdf", ".rtf"}
CORE_FILES = ["onigiri.asi", "ScriptHookV.dll"]  # plus the ASI loader, xinput1_4.dll

GAME_EXES = ("GTA5_Enhanced.exe",)
GAME_CANDIDATES = [
    r"C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V Enhanced",
    r"C:\Program Files\Rockstar Games\Grand Theft Auto V Enhanced",
    r"C:\Program Files\Epic Games\GTAVEnhanced",
    r"D:\SteamLibrary\steamapps\common\Grand Theft Auto V Enhanced",
]


def is_game_dir(p):
    return any((Path(p) / e).exists() for e in GAME_EXES)


def find_game_dir():
    try:
        import winreg
        for key in (r"SOFTWARE\WOW6432Node\Rockstar Games\Grand Theft Auto V",
                    r"SOFTWARE\Rockstar Games\Grand Theft Auto V"):
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
                    p = winreg.QueryValueEx(k, "InstallFolder")[0]
                    if is_game_dir(p):
                        return p
            except OSError:
                pass
    except ImportError:
        pass
    for p in GAME_CANDIDATES:
        if is_game_dir(p):
            return p
    return ""


CORE_SCAN_FILES = ("onigiri.asi", "ScriptHookV.dll", "xinput1_4.dll", "ScriptHookVDotNet.asi")

_SKIP_SCAN_DIRS = {"windows", "system volume information", "$recycle.bin", "programdata",
                   "perflogs", "recovery", "$winreagent", "appdata", "old files", "lost found"}


def _fixed_drives():
    """Letters of the fixed local drives (Windows); [] elsewhere."""
    try:
        import ctypes
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        out = []
        for i in range(26):
            if not (mask & (1 << i)):
                continue
            letter = chr(ord("A") + i)
            try:
                fixed = ctypes.windll.kernel32.GetDriveTypeW(
                    f"{letter}:\\".encode("utf-16-le")) == 3   # DRIVE_FIXED
            except Exception:
                fixed = True
            if fixed:
                out.append(letter)
        return out
    except Exception:
        return []


def scan_for_core(drives=None, extra_roots=(), time_budget=25.0, max_depth=4, registry=True):
    """Look for GTA V folders and report which core files sit next to the game exe.

    Checks the registry, the well-known install locations and (as a fallback)
    does a bounded walk of each fixed drive. Returns a list of
    {"dir", "exe", "core": {file: present}} sorted best-first (Enhanced first,
    most core files present first). The disk walk stops after `time_budget`
    seconds, so this is safe to call from the GUI.
    """
    found, seen = [], set()

    def note(d, exe):
        d = str(d).rstrip("\\")
        if not d or d.lower() in seen:
            return
        seen.add(d.lower())
        found.append({"dir": d, "exe": exe,
                      "core": {f: (Path(d) / f).exists() for f in CORE_SCAN_FILES}})

    if registry:
        p = find_game_dir()
        if p:
            note(p, "GTA5_Enhanced.exe")

    if drives is None:
        drives = _fixed_drives()
    deadline = time.monotonic() + time_budget

    def walk(root, depth):
        if depth > max_depth or time.monotonic() > deadline:
            return True
        try:
            with os.scandir(root) as it:
                entries = list(it)
        except OSError:
            return False
        names = {e.name.lower() for e in entries}
        if "gta5_enhanced.exe" in names:
            note(root, "GTA5_Enhanced.exe")
            return False                     # no need to walk into a game folder
        if "gta5.exe" in names:
            note(root, "GTA5.exe")
            return False
        if depth == max_depth:
            return False
        for e in entries:
            if e.name.lower() in _SKIP_SCAN_DIRS:
                continue
            try:
                if not e.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            if walk(e.path, depth + 1):
                return True
        return False

    for r in [Path(f"{d}:\\") for d in drives] + [Path(p) for p in extra_roots]:
        try:
            if not r.exists():
                continue
        except OSError:
            continue
        if walk(r, 0):
            break

    found.sort(key=lambda c: (0 if c["exe"].lower() == "gta5_enhanced.exe" else 1,
                              -sum(c["core"].values())))
    return found


# --------------------------------------------------------------------------
# Core logic (no GUI) so it can be tested / reused
# --------------------------------------------------------------------------
class Loader:
    def __init__(self, log=print):
        self.log = log
        LIB_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.state = {"config": {"game_dir": "", "onigiri_dir": ""},
                      "mods": [], "deployed": {}}
        if STATE_FILE.exists():
            try:
                self.state.update(json.loads(STATE_FILE.read_text("utf-8")))
            except Exception as e:
                self.log(f"Could not read state file, starting fresh: {e}")
        if not self.cfg["game_dir"]:
            self.cfg["game_dir"] = find_game_dir()
        # migrate the old (wrong) default <GTA V>\\NVE\\onigiri
        if self.cfg["game_dir"] and self.cfg["onigiri_dir"] == str(
                Path(self.cfg["game_dir"]) / "NVE" / "onigiri"):
            self.cfg["onigiri_dir"] = ""
        if self.cfg["game_dir"] and not self.cfg["onigiri_dir"]:
            self.cfg["onigiri_dir"] = str(Path(self.cfg["game_dir"]) / "onigiri")

    # -- properties --------------------------------------------------------
    @property
    def cfg(self): return self.state["config"]
    @property
    def mods(self): return self.state["mods"]
    @property
    def deployed(self): return self.state["deployed"]

    def save(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.state, indent=2), "utf-8")

    def set_paths(self, game_dir, onigiri_dir=None):
        self.cfg["game_dir"] = game_dir
        self.cfg["onigiri_dir"] = onigiri_dir or str(Path(game_dir) / "onigiri")
        self.save()

    def core_status(self):
        g = Path(self.cfg["game_dir"] or ".")
        status = {n: (g / n).exists() for n in CORE_FILES}
        status["xinput1_4.dll (ASI loader)"] = (g / "xinput1_4.dll").exists()
        status["ScriptHookVDotNet.asi"] = (g / "ScriptHookVDotNet.asi").exists()
        return status

    # -- library -----------------------------------------------------------
    @staticmethod
    def _normalize_root(p: Path) -> Path:
        """Strip wrapper folders (e.g. 'MyMod/onigiri/common/...')."""
        known = ROOTS | GAME_ROOT_DIRS
        for _ in range(8):
            kids = list(p.iterdir())
            dirs = [k for k in kids if k.is_dir()]
            wrap = [d for d in dirs if d.name.lower() in WRAPPERS]
            if wrap:
                p = wrap[0]; continue
            if any(d.name.lower() in known for d in dirs):
                return p
            if any(k.suffix.lower() in GAME_ROOT_EXT for k in kids if k.is_file()):
                return p
            if len(kids) == 1 and kids[0].is_dir():
                p = kids[0]; continue
            return p
        return p

    @staticmethod
    def _archive_kind(src: Path):
        """'zip' / '7z' / 'rar', judged by the file signature (falls back to the extension)."""
        try:
            with open(src, "rb") as f:
                head = f.read(8)
        except OSError:
            head = b""
        if head[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
            return "zip"
        if head[:6] == b"7z\xbc\xaf\x27\x1c":
            return "7z"
        if head[:6] == b"Rar!\x1a\x07":                 # RAR 4 and RAR 5
            return "rar"
        return {".zip": "zip", ".7z": "7z", ".rar": "rar"}.get(src.suffix.lower())

    @staticmethod
    def _external_tools(kind):
        """Installed programs that can open this archive kind: [(label, command builder, ok codes)]."""
        pf = [os.environ.get("ProgramFiles", r"C:\Program Files"),
              os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]

        def first(names, paths=()):
            for n in names:
                w = shutil.which(n)
                if w:
                    return w
            return next((x for x in paths if os.path.exists(x)), None)

        tools = []
        z = first(["7z", "7za", "7zr"], [os.path.join(d, "7-Zip", "7z.exe") for d in pf])
        if z:                                           # 7-Zip: opens zip, 7z and RAR/RAR5
            tools.append(("7-Zip", lambda s, d, z=z: [z, "x", "-y", f"-o{d}", str(s)], (0, 1)))
        if kind == "rar":
            u = first(["unrar", "UnRAR", "rar"],
                      [os.path.join(d, "WinRAR", n) for d in pf for n in ("UnRAR.exe", "Rar.exe")])
            if u:
                tools.append(("WinRAR/UnRAR", lambda s, d, u=u: [u, "x", "-y", "-o+", str(s), str(d) + os.sep], (0,)))
        t = first(["bsdtar"])
        if not t and sys.platform == "win32":           # tar.exe that ships with Windows 10/11
            w = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "tar.exe")
            t = w if os.path.exists(w) else None
        if not t and sys.platform == "darwin":
            t = shutil.which("tar")                     # macOS tar is bsdtar
        if t:
            tools.append(("tar (libarchive)", lambda s, d, t=t: [t, "-xf", str(s), "-C", str(d)], (0,)))
        un = first(["unar"])
        if un:
            tools.append(("unar", lambda s, d, un=un: [un, "-q", "-D", "-o", str(d), str(s)], (0,)))
        return tools

    @classmethod
    def _extract_external(cls, src: Path, dest: Path, kind: str):
        """Open an archive with a program that is already installed. Tries each in turn."""
        tools = cls._external_tools(kind)
        if not tools:
            raise ValueError(f"To open .{kind} mods, install 7-Zip (free, 7-zip.org)"
                             + (" or WinRAR" if kind == "rar" else "")
                             + ".")
        errors = []
        for label, build, ok in tools:
            try:
                r = subprocess.run(build(src, dest), capture_output=True, text=True,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except OSError as e:
                errors.append(f"{label}: {e}")
                continue
            if r.returncode in ok and any(dest.iterdir()):
                return label
            errors.append(f"{label}: failed (exit code {r.returncode})")
            for x in list(dest.iterdir()):              # clear partial output before the next try
                shutil.rmtree(x, ignore_errors=True) if x.is_dir() else x.unlink()
        raise ValueError(f"Could not open the .{kind} archive ({'; '.join(errors)}). "
                         "Try 7-Zip (7-zip.org) or WinRAR.")

    @classmethod
    def _extract_archive(cls, src: Path, dest: Path):
        kind = cls._archive_kind(src)
        if kind == "zip":
            with zipfile.ZipFile(src) as zf:
                root = dest.resolve()
                for member in zf.namelist():
                    target = (dest / member).resolve()
                    if root not in target.parents and target != root:
                        raise ValueError(f"Unsafe path in archive: {member}")
                zf.extractall(dest)
        elif kind == "7z":
            try:
                import py7zr
            except ImportError:
                py7zr = None
            if py7zr:
                try:
                    with py7zr.SevenZipFile(src) as z:
                        root = dest.resolve()
                        for member in z.getnames():
                            target = (dest / member).resolve()
                            if root not in target.parents and target != root:
                                raise ValueError(f"Unsafe path in archive: {member}")
                        z.extractall(dest)
                    return
                except ValueError:
                    raise
                except Exception:
                    pass                                # fall back to an installed program
            cls._extract_external(src, dest, "7z")
        elif kind == "rar":
            cls._extract_external(src, dest, "rar")
        else:
            raise ValueError("Supported: .zip, .7z and .rar archives, .rpf files, or a folder.")

    def legacy_status(self, name):
        """A mod's legacy (old game) files as (skipped, fallback). `skipped`: legacy
        files whose Enhanced twin is in the same mod, so the Enhanced one is used.
        `fallback`: legacy files with no Enhanced twin in the mod, so they will be used."""
        base = LIB_DIR / name
        names = {f.lower() for _r, _d, fs in os.walk(base) for f in fs}
        skipped, fallback = [], []
        for f in sorted(names & set(LEGACY_FILES)):
            (skipped if LEGACY_FILES[f] and LEGACY_FILES[f] in names else fallback).append(f)
        return skipped, fallback

    @staticmethod
    def _labeled_branches(top: Path):
        """Branches of a mod's structure labeled for the old (legacy) game vs the Enhanced
        game (e.g. 'GTA V Legacy' next to 'GTA V Enhanced').
        Returns (excluded, legacy_seen, enhanced_seen): excluded is the set of absolute
        paths of legacy-labeled directories that are not installed because an
        Enhanced-labeled sibling directory exists at the same level."""
        excluded = set()
        legacy_seen = enhanced_seen = False
        for root, dirs, _files in os.walk(top):
            low = [d.lower() for d in dirs]
            e = any(ENHANCED_LABEL in d for d in low)
            l = any(LEGACY_LABEL in d for d in low)
            enhanced_seen = enhanced_seen or e
            legacy_seen = legacy_seen or l
            if e and l:
                for d in dirs:
                    dl = d.lower()
                    if LEGACY_LABEL in dl and ENHANCED_LABEL not in dl:
                        excluded.add(Path(root) / d)
        return excluded, legacy_seen, enhanced_seen

    @staticmethod
    def _sibling_items(top: Path, content: Path):
        """Files/folders that sit beside a stripped wrapper folder (README, .asi, scripts...)."""
        items = []
        try:
            chain = content.relative_to(top).parts
        except ValueError:
            return items
        cur = top
        for part in chain:
            items += [it for it in cur.iterdir() if it.name != part]
            cur = cur / part
        return items

    def install(self, source: str, name: str = None):
        """Install a mod. Vanilla-backup folders are dropped, and each entry of an
        'optionals' folder becomes its own mod ('<name> - <option>')."""
        src = Path(source)
        name = (name or src.stem).strip()
        tmp = None
        try:
            if src.is_dir():
                content = self._normalize_root(src)
            else:
                tmp = Path(tempfile.mkdtemp(prefix="onigiri_"))
                self._extract_archive(src, tmp)
                content = self._normalize_root(tmp)

            comps = [(name, content)]
            for d in sorted(content.iterdir()):
                if d.is_dir() and d.name.lower() in OPTIONAL_DIRS:
                    comps += [(f"{name} - {o.name}", o) for o in sorted(d.iterdir()) if o.is_dir()]
            for n, _ in comps:
                if any(m["name"] == n for m in self.mods):
                    raise ValueError(f"A mod named '{n}' already exists.")

            skip = EXCLUDE_DIRS | OPTIONAL_DIRS
            top = src if src.is_dir() else tmp
            excluded, legacy_seen, enhanced_seen = self._labeled_branches(top)
            def ignored(d, names):
                out = []
                for x in names:
                    p = Path(d) / x
                    if not p.is_dir():
                        continue
                    if x.lower() in skip or any(e == p or e in p.parents for e in excluded):
                        out.append(x)
                return out
            dropped = [d.name for d in content.rglob("*")
                       if d.is_dir() and d.name.lower() in EXCLUDE_DIRS]
            self._harvest_bases(content)
            for n, folder in comps:
                shutil.copytree(folder, LIB_DIR / n, ignore=ignored)
                if n == name:                       # keep what sat beside a stripped wrapper folder
                    for it in self._sibling_items(top, content):
                        if any(e == it for e in excluded):
                            continue                # legacy branch: not installed (Enhanced branch present)
                        dst = LIB_DIR / n / it.name
                        if dst.exists() or it.name.lower() in (EXCLUDE_DIRS | OPTIONAL_DIRS):
                            continue
                        if it.is_dir():
                            shutil.copytree(it, dst, ignore=ignored)
                        else:
                            shutil.copy2(it, dst)
                self.mods.append({"name": n, "enabled": False})
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
        self.save()
        for n, _ in comps:
            self._place_dlc_packs(n)
            self._apply_readme(n)
            self._infer_placement(n)
            skipped, fallback = self.legacy_status(n)
            if skipped:
                self.log(f"  Enhanced version used: skipped {', '.join(skipped)} (legacy, old game).")
            if fallback:
                self.log(f"  WARNING: {', '.join(fallback)} is legacy (old game); no Enhanced version "
                         f"found in this mod, so it will be used.")
            if excluded:
                self.log(f"  Enhanced branch present - legacy branch(es) not installed: "
                         + ", ".join(sorted("/".join(e.relative_to(top).parts) for e in excluded)))
            elif legacy_seen:
                self.log("  WARNING: this mod is labeled for the old (legacy) game and has no Enhanced "
                         "branch; the legacy files will be used.")
            ok, bad = self._scan(n)
            per = {}
            for _, rel, kind in ok:
                k = "game root" if kind == "game" else rel.parts[0]
                per[k] = per.get(k, 0) + 1
            summary = ", ".join(f"{k}: {v}" for k, v in sorted(per.items())) or "none"
            self.log(f"Installed '{n}' - {len(ok)} deployable files ({summary}).")
            bad = [b for b in bad if b.suffix.lower() not in NOT_GAME_FILES]   # docs/images are fine
            if bad:
                self.log(f"  WARNING: {len(bad)} file(s) don't fit the onigiri folders and "
                         f"will be ignored, e.g. {bad[0].as_posix()}")
            for src_p, rel, _k in ok:
                if rel.suffix.lower() == ".rpf":
                    info = rpf_info(src_p)
                    if info:
                        self.log(f"  RPF {rel.name}: {info['entries']} entries, {info['encryption']}")
                    else:
                        self.log(f"  WARNING: {rel.name} is not a valid RPF7 archive.")
            if not ok:
                self.log("  WARNING: nothing here matches common / dlcpacks / platform.")
        if dropped:
            self.log(f"Skipped vanilla-backup folder(s): {', '.join(sorted(set(dropped)))}")
        if len(comps) > 1:
            self.log(f"{len(comps) - 1} optional component(s) installed as separate mods.")
        self.log("Tick a mod to enable it.")

    def install_rpf(self, source, dest_rel, name=None):
        """Install a loose .rpf file. `dest_rel` is its folder inside onigiri, e.g.
        'platform/levels/gta5/cloudhats' or 'dlcpacks/grassfix'. The file is stored
        in the library under that path and deployed unchanged."""
        src = Path(source)
        if src.suffix.lower() != ".rpf":
            raise ValueError("Not an .rpf file.")
        info = rpf_info(src)
        if info is None:
            raise ValueError("This is not a valid RPF7 archive (header check failed).")
        parts = [x for x in re.split(r"[\\/]+", dest_rel.strip(" \\/")) if x]
        if not parts or parts[0].lower() not in ROOTS:
            raise ValueError("Destination must start with one of: "
                             + ", ".join(sorted(ROOTS)))
        parts = [parts[0].lower()] + (parts[1:] if parts[0].lower() == "dlcpacks" else [x.lower() for x in parts[1:]])
        is_pack = dlc_info(src)["is_pack"]
        if (src.name.lower() == "dlc.rpf" or is_pack) and (len(parts) < 2 or parts[0] != "dlcpacks"):
            raise ValueError("A DLC pack must go in a pack folder, e.g. dlcpacks/mypack")
        fname = "dlc.rpf" if is_pack else src.name
        name = (name or src.stem).strip()
        if any(m["name"] == name for m in self.mods):
            raise ValueError(f"A mod named '{name}' already exists.")
        target = LIB_DIR / name / Path(*parts)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target / fname)
        self.mods.append({"name": name, "enabled": False})
        self.save()
        self.log(f"Installed '{name}': {fname} -> onigiri/{'/'.join(parts)}/ "
                 f"({info['entries']} entries, {info['encryption']}). Tick it to enable.")

    def _harvest_bases(self, content: Path):
        """Keep vanilla copies shipped in 'original files' folders as merge bases."""
        saved = 0
        for d in content.rglob("*"):
            if not (d.is_dir() and d.name.lower() in BASE_DIR_NAMES):
                continue
            for f in d.rglob("*"):
                if not f.is_file() or f.suffix.lower() not in MERGEABLE_EXT:
                    continue
                r = self._route(f.relative_to(d))
                if not r or r[0] != "onigiri":
                    continue
                target = BASE_DIR / r[1]
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, target)
                    saved += 1
        if saved:
            self.log(f"Saved {saved} vanilla file(s) as merge bases (from the mod's original files).")

    def find_readmes(self, name):
        """README / install-instruction files in a mod (top two folder levels)."""
        base = LIB_DIR / name
        found = []
        for root, dirs, files in os.walk(base):
            depth = len(Path(root).relative_to(base).parts)
            if depth > 2:
                dirs[:] = []
                continue
            for f in files:
                p = Path(f)
                if p.suffix.lower() in README_EXT and README_STEM.match(p.stem):
                    found.append((depth, str(Path(root) / f)))
        return [Path(x) for _, x in sorted(found)]

    def _apply_readme(self, name):
        """Place files that match no layout rule using the folder named in the README."""
        _ok, bad = self._scan(name)
        loose = [r for r in bad if r.suffix.lower() not in NOT_GAME_FILES]
        if not loose:
            return
        cands = []
        for rd in self.find_readmes(name):
            for c in readme_candidates(read_text(rd)):
                c["readme"] = rd.name
                cands.append(c)
        if not cands:
            return
        generic = {}
        for c in cands:
            if not c["files"]:
                old = generic.get(c["dest"])
                if old is None or c["score"] > old["score"]:
                    generic[c["dest"]] = c
        top = None
        if generic:
            best = max(c["score"] for c in generic.values())
            tops = [d for d, c in generic.items() if c["score"] == best]
            if len(tops) == 1:
                top = generic[tops[0]]
            else:
                self.log(f"  README mentions several folders ({', '.join(sorted(tops))}); "
                         f"can't tell which applies - move the files yourself.")
        base = LIB_DIR / name
        placed = {}
        for rel in loose:
            named = [c for c in cands if rel.name.lower() in c["files"]]
            pick = max(named, key=lambda c: c["score"]) if named else top
            if not pick:
                continue
            target = base / Path(*pick["dest"].split("/")) / rel
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(base / rel), str(target))
            placed.setdefault((pick["dest"], pick["readme"], pick["line"]), []).append(rel.name)
            parent = (base / rel).parent
            while parent != base and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
        for (dest, rd, line), names in placed.items():
            self.log(f"  README ({rd}) says: \"{line[:80]}\"")
            self.log(f"  -> placed {len(names)} file(s) in onigiri/{dest}/: {', '.join(names[:4])}"
                     + (" ..." if len(names) > 4 else ""))

    # -- placement inference (learn from what is already installed) --------
    def _placement_index(self, exclude=None):
        """Where do files live? Built from other mods, saved vanilla bases, known
        archives, and whatever is already in the onigiri folder."""
        names, exts = {}, {}

        def add(folder, fname, w=1):
            if not folder or folder == "." or folder.split("/")[0].lower() not in ROOTS:
                return
            names.setdefault(fname.lower(), {})
            names[fname.lower()][folder] = names[fname.lower()].get(folder, 0) + w
            e = Path(fname).suffix.lower()
            exts.setdefault(e, {})
            exts[e][folder] = exts[e].get(folder, 0) + w

        for m in self.mods:
            if m["name"] == exclude:
                continue
            for _s, rel, kind in self._mod_files(m["name"]):
                if kind == "onigiri":
                    add(rel.parent.as_posix(), rel.name)
        for root_dir in (BASE_DIR, Path(self.cfg["onigiri_dir"] or ".")):
            if root_dir.is_dir():
                for f in root_dir.rglob("*"):
                    if f.is_file():
                        add(f.relative_to(root_dir).parent.as_posix().lower(), f.name)
        for fname, folder in KNOWN_RPF.items():
            add(folder, fname)
        for folder, fnames in KNOWN_FILES.items():      # built-in knowledge (weaker than installed)
            for fname in fnames:
                add(folder, fname, 0.5)
        return names, exts

    @staticmethod
    def _leaf_map(names):
        """folder name -> set of full onigiri paths that end in that name."""
        paths = set(topology_paths())
        for dirs in names.values():
            for d in dirs:
                parts = d.split("/")
                paths.update("/".join(parts[:i]) for i in range(1, len(parts) + 1))
        leaf = {}
        for pth in paths:
            leaf.setdefault(pth.split("/")[-1].lower(), set()).add(pth)
        return leaf

    def _infer_placement(self, name):
        """Place files that have no folder structure and no README guidance by
        looking at where similar files already live."""
        _ok, bad = self._scan(name)
        loose = [r for r in bad if r.suffix.lower() not in NOT_GAME_FILES]
        if not loose:
            return
        names, exts = self._placement_index(exclude=name)
        leaf = self._leaf_map(names)
        base = LIB_DIR / name
        placed, hints, ambiguous = {}, [], []
        for rel in loose:
            dest = why = None
            found = names.get(rel.name.lower())
            if found:                                   # 1. same file name used elsewhere
                best = max(found.values())
                tops = [d for d, c in found.items() if c == best]
                if len(tops) == 1:
                    dest, why = tops[0], "same file name is already used there"
                else:
                    ambiguous.append(rel.name)
            if not dest:                                # 2. partial folder structure
                parts = list(rel.parts[:-1])
                for i in range(len(parts) - 1, -1, -1):
                    c = leaf.get(parts[i].lower())
                    if c and len(c) == 1:
                        full = next(iter(c))
                        dest = "/".join([full] + [x.lower() for x in parts[i + 1:]])
                        why = f"folder '{parts[i]}' belongs in onigiri/{full}"
                        break
            if dest:
                target = base / Path(*dest.split("/")) / rel.name
                if target.exists():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(base / rel), str(target))
                placed.setdefault((dest, why), []).append(rel.name)
                parent = (base / rel).parent
                while parent != base and parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
            else:                                       # 3. hint only
                e = exts.get(rel.suffix.lower(), {})
                tot = sum(e.values())
                if tot >= 3:
                    d, c = max(e.items(), key=lambda t: t[1])
                    if c / tot >= 0.8:
                        hints.append((rel.name, d, c, tot))
        for (dest, why), fl in placed.items():
            self.log(f"  Inferred placement: {len(fl)} file(s) -> onigiri/{dest}/ ({why}): "
                     + ", ".join(fl[:4]) + (" ..." if len(fl) > 4 else ""))
        if ambiguous:
            self.log(f"  Could not decide between several folders for: {', '.join(ambiguous[:4])}")
        for fname, d, c, tot in hints[:4]:
            self.log(f"  Hint: {fname} - {c:g} of {tot:g} similar files live in onigiri/{d} "
                     f"(not moved; place it yourself if that fits).")

    def remove(self, name):
        self.set_enabled(name, False)
        self.state["mods"] = [m for m in self.mods if m["name"] != name]
        shutil.rmtree(LIB_DIR / name, ignore_errors=True)
        self.save()
        self.log(f"Removed '{name}'.")

    def move(self, name, delta):
        i = next(i for i, m in enumerate(self.mods) if m["name"] == name)
        j = max(0, min(len(self.mods) - 1, i + delta))
        self.mods.insert(j, self.mods.pop(i))
        self.save()
        self.apply()

    def set_enabled(self, name, enabled):
        for m in self.mods:
            if m["name"] == name:
                m["enabled"] = enabled
        self.save()
        self.apply()

    def reset_all(self):
        """Return the loader to a pristine first-launch state.

        Unloads every mod (restoring the original game files from the
        backups), deletes the whole library and all backups / merge data,
        and resets the state file so the next launch is exactly like the
        very first one. Cannot be undone - the GUI asks for confirmation.
        """
        # 1) unload everything while the game folder is still known
        if self.mods:
            for m in self.mods:
                m["enabled"] = False
            self.save()
            try:
                self.apply()          # removes the mod files, restores the originals
            except Exception as e:
                self.log(f"Reset: unloading hit a problem (continuing): {e}")
        # 2) wipe the private data folders
        for d in (LIB_DIR, BACKUP_DIR, BASE_DIR, MERGE_DIR):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True, exist_ok=True)
        # 3) fresh state, as on the very first launch (paths + settings cleared)
        self.state = {"config": {"game_dir": "", "onigiri_dir": ""},
                      "mods": [], "deployed": {}}
        self.save()
        self.log("Loader reset: all mods unloaded, library and backups deleted, "
                 "settings back to defaults.")

    # -- routing / deploy --------------------------------------------------
    @staticmethod
    def _route(rel: Path, path=None):
        """Map a file inside a mod to ('onigiri'|'game', path under that base),
        or None if it does not fit the onigiri folder topology.

        Understands: script mods (.NET .dll / .cs / .vb -> <game>\\scripts), .asi plugins anywhere in a mod (-> game folder; their .ini files are
        handled in _scan), onigiri layout (common/, platform/, dlcpacks/),
        game-folder paths (update.rpf/common/..., x64/... -> platform/...),
        stray wrapper folders, and bare dlc.rpf packs (-> dlcpacks/<pack>/dlc.rpf).
        """
        parts = rel.parts
        low = [x.lower() for x in parts]
        if low[-1].endswith(".asi"):                      # ASI plugins load only from next to the exe
            return "game", Path(parts[-1])
        if low[-1] in LEGACY_FILES:                       # legacy (old game) loader file: beside the exe
            return "game", Path(parts[-1])
        ext = rel.suffix.lower()
        if "scripts" in low[:-1]:                         # script mods live in <game>\\scripts
            return "game", Path("scripts", *parts[low.index("scripts") + 1:])
        if ext == ".dll" and low[-1].startswith(FRAMEWORK_DLLS):   # framework DLLs stay beside the exe
            return "game", Path(parts[-1])
        if ext in (".cs", ".vb"):                         # source scripts compiled by ScriptHookVDotNet
            return "game", Path("scripts", parts[-1])
        if ext == ".dll" and path is not None and is_managed_dll(path):   # .NET script or library
            return "game", Path("scripts", parts[-1])
        if low[0] in GAME_ROOT_DIRS or (len(parts) == 1 and ext in GAME_ROOT_EXT):
            return "game", rel
        for i, x in enumerate(low[:-1][:5]):       # tolerate wrapper folders
            nxt = low[i + 1] if i + 1 < len(low) - 1 else ""
            if x in ROOTS:
                root = x
            elif x in ALIASES and nxt not in ROOTS:   # x64/ -> platform/ (but not x64/dlcpacks)
                root = ALIASES[x]
            else:
                continue
            rest = list(parts[i + 1:])
            keep = 1 if root == "dlcpacks" else 0          # a DLC pack folder keeps its own spelling
            dirs = rest[:-1]
            rest = dirs[:keep] + [d.lower() for d in dirs[keep:]] + rest[-1:]   # folders lowercase, file name untouched
            return "onigiri", Path(root, *rest)
        if low[-1] in ROOT_FILES:                          # registry files live at the onigiri root
            return "onigiri", Path(parts[-1])
        if low[-1] == "dlc.rpf" and len(parts) >= 2:      # bare DLC pack
            return "onigiri", Path("dlcpacks", parts[-2], parts[-1])
        if low[-1] in KNOWN_RPF:                          # e.g. v_clouds.rpf
            return "onigiri", Path(*KNOWN_RPF[low[-1]].split("/"), parts[-1])
        return None

    def _scan(self, name):
        """(deployable [(src, rel, kind)], unrecognized [rel])"""
        base = LIB_DIR / name
        ok, bad = [], []
        # a legacy-labeled branch next to an Enhanced one is not installed; .oiv files never
        excluded, _legacy_seen, _enhanced_seen = self._labeled_branches(base)
        allf = []
        for root, _, files in os.walk(base):
            for f in files:
                p = Path(root) / f
                if p.suffix.lower() in NEVER_DEPLOY_EXT or f.lower() in NEVER_DEPLOY_NAMES:
                    continue                                   # .oiv packages / OpenIV support files: never installed
                if any(e == p or e in p.parents for e in excluded):
                    continue                                   # legacy branch (Enhanced branch present)
                allf.append((p, p.relative_to(base)))
        routes = {rel: self._route(rel, p) for p, rel in allf}
        names = {rel.name.lower() for _p, rel in allf}
        asi_dirs = {rel.parent for _p, rel in allf if rel.suffix.lower() == ".asi"}
        asi_stems = {rel.stem.lower() for _p, rel in allf if rel.suffix.lower() == ".asi"}
        # script mods: config files go beside their script
        script_files = [rel for _p, rel in allf if routes[rel] and routes[rel][0] == "game"
                        and routes[rel][1].parts[0] == "scripts" and rel.suffix.lower() in SCRIPT_CODE_EXT]
        script_dirs = {rel.parent for rel in script_files if rel.parent != Path(".")}
        script_stems = {rel.stem.lower() for rel in script_files}
        for p, rel in allf:
            lf = rel.name.lower()
            if lf in LEGACY_FILES and LEGACY_FILES[lf] in names:
                continue                                   # Enhanced twin present; legacy is fallback only
            r = routes[rel]
            ext, stem = rel.suffix.lower(), rel.stem.lower()
            if ext == ".ini" and (r is None or len(rel.parts) == 1) and \
                    (rel.parent in asi_dirs or stem in asi_stems):
                r = ("game", Path(rel.name))               # .ini of an .asi plugin
            elif ext in SCRIPT_CFG_EXT and (r is None or (len(rel.parts) == 1 and r[0] == "game")) and \
                    (stem in script_stems or rel.parent in script_dirs):
                r = ("game", Path("scripts", rel.name))    # config of a script
            if r:
                ok.append((p, r[1], r[0]))
            elif any(x.lower() in IGNORED_DIRS for x in rel.parts[:-1]):
                continue                                   # docs / licences / debug symbols
            elif not (len(rel.parts) == 1 and ext in SKIP_ROOT_EXT):
                bad.append(rel)
        return ok, bad

    def _mod_files(self, name):
        return self._scan(name)[0]

    def _dest_abs(self, kind, rel: Path) -> Path:
        base = self.cfg["game_dir"] if kind == "game" else self.cfg["onigiri_dir"]
        return Path(base) / rel

    @staticmethod
    def _key(p: Path) -> str:
        return os.path.normcase(str(p))        # case-insensitive on Windows

    def create_structure(self):
        if self.cfg["onigiri_dir"]:
            _make_dirs(Path(self.cfg["onigiri_dir"]), TOPOLOGY)
            self.log(f"Folder structure ready in {self.cfg['onigiri_dir']}")

    def _desired(self):
        self.report = {"merged": [], "nobase": []}
        contrib = {}
        for m in self.mods:                       # later in list = higher priority
            if not m["enabled"]:
                continue
            for src, rel, kind in self._mod_files(m["name"]):
                key = self._key(self._dest_abs(kind, rel))
                contrib.setdefault(key, []).append((m["name"], str(src), rel, kind))
        desired, used = {}, set()
        for key, lst in contrib.items():
            name, src, rel, kind = lst[-1]
            if (len(lst) > 1 and self.cfg.get("merge", True) and kind == "onigiri"
                    and rel.suffix.lower() in MERGEABLE_EXT):
                merged = self._merge(lst, rel)
                if merged:
                    used.add(merged.parent.name)
                    desired[key] = (" + ".join(x[0] for x in lst), str(merged))
                    continue
            desired[key] = (name, src)
        # a legacy (old game) file loses to the Enhanced twin, whatever mod provides it,
        # or when the user has the Enhanced file in the game folder themselves
        base_names = {Path(k).name.lower() for k in desired}
        gdir = self.cfg.get("game_dir")

        def foreign(twin):
            if not gdir:
                return False
            p = Path(gdir) / twin
            # only count files the user placed there - not ones we deploy or are
            # about to remove in this pass
            return p.exists() and self._key(p) not in self.deployed

        dropped = []
        for key in list(desired):
            n = Path(key).name.lower()
            twin = LEGACY_FILES.get(n)
            if twin and (twin in base_names or foreign(twin)):
                del desired[key]
                dropped.append(n)
        if dropped:
            self.report["legacy_skipped"] = sorted(set(dropped))
        self._register_dlc(contrib, desired, used)
        if MERGE_DIR.exists():                    # drop merged files no longer needed
            for d in MERGE_DIR.iterdir():
                if d.name not in used:
                    shutil.rmtree(d, ignore_errors=True)
        return desired

    def _existing_original(self, rel: Path):
        """The file that was in the onigiri folder before the loader touched it (for example
        NaturalVision Enhanced's version). Treated as the 'vanilla' baseline for merging."""
        dest = self._dest_abs("onigiri", rel)
        info = self.deployed.get(self._key(dest))
        if info:
            bk = info.get("backup")
            return Path(bk) if bk and Path(bk).exists() else None
        return dest if dest.exists() else None

    def _merge(self, lst, rel: Path):
        """Merge every enabled mod's version of one file. Returns the merged file's
        path, or None when it can't be merged (then the last mod simply wins)."""
        srcs = [Path(x[1]) for x in lst]
        raws = []
        for sp in srcs:
            if sp.stat().st_size > MAX_MERGE_BYTES:
                return None
            raws.append(sp.read_bytes())
        if any(b"\x00" in r for r in raws) or len(set(raws)) == 1:
            return None                           # binary, or all identical
        base_file = BASE_DIR / rel
        base_raw = None
        orig = self._existing_original(rel)       # NVE's (or any pre-existing) file = the baseline
        if orig is not None and orig.stat().st_size <= MAX_MERGE_BYTES:
            raw0 = orig.read_bytes()
            if b"\x00" not in raw0:
                base_raw = raw0
        if base_raw is not None:
            pass
        elif base_file.exists():
            base_raw = base_file.read_bytes()
        elif rel.as_posix().lower() in BUILTIN_BASES:
            base_raw = BUILTIN_BASES[rel.as_posix().lower()].encode("utf-8")
        else:
            self.report["nobase"].append((rel.as_posix(), lst[-1][0]))
            return None
        digest = hashlib.sha1(rel.as_posix().encode() + base_raw
                              + b"".join(hashlib.sha1(r).digest() for r in raws)).hexdigest()[:16]
        out_dir = MERGE_DIR / digest
        out_file, info_file = out_dir / rel.name, out_dir / "info.json"
        names = [x[0] for x in lst]
        if out_file.exists() and info_file.exists():
            conflicts = json.loads(info_file.read_text("utf-8")).get("conflicts", 0)
        else:
            base = _text_lines(base_raw)
            cur, conflicts = _text_lines(raws[0]), 0
            for raw in raws[1:]:
                cur, c = merge3(base, cur, _text_lines(raw))
                conflicts += c
            text = "\n".join(cur)
            if b"\r\n" in base_raw:
                text = text.replace("\n", "\r\n")
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file.write_bytes(text.encode("utf-8", errors="surrogateescape"))
            info_file.write_text(json.dumps({"conflicts": conflicts, "mods": names}), "utf-8")
        self.report["merged"].append((rel.as_posix(), names, conflicts))
        return out_file

    # -- DLC packs: dlcpacks/<pack>/dlc.rpf, registered in dlclist.xml -----------------
    @staticmethod
    def _pack_rel(rel: Path):
        """The pack folder name if `rel` is dlcpacks/<pack>/dlc.rpf, else None."""
        p = rel.parts
        return p[1] if len(p) == 3 and p[0].lower() == "dlcpacks" and p[2].lower() == "dlc.rpf" else None

    def _pack_name_from_readme(self, name):
        for rd in self.find_readmes(name):
            t = read_text(rd)
            m = re.search(r"dlcpacks:/([\w.\-]+)/", t) or re.search(r'folder\s+"([\w.\-]+)"', t, re.I)
            if m:
                return m.group(1)
        return None

    def _place_dlc_packs(self, name):
        """Loose DLC pack archives go to dlcpacks/<pack>/dlc.rpf. Any readable .rpf that has a
        setup2.xml is a pack, whatever it is called; its own nameHash is the pack name. An
        encrypted dlc.rpf cannot be read, so its name comes from the README instead."""
        _ok, bad = self._scan(name)
        base = LIB_DIR / name
        for rel in bad:
            if rel.suffix.lower() != ".rpf":
                continue
            src = base / rel
            info = dlc_info(src)
            pack = why = None
            if info["is_pack"] and info["name"]:
                pack, why = info["name"], "its setup2.xml"
            elif rel.name.lower() == "dlc.rpf":
                pack, why = self._pack_name_from_readme(name), "the README"
                if not pack:
                    self.log(f"  WARNING: {rel.name} looks like a DLC pack but is encrypted, so its name "
                             f"cannot be read. Use Add archive on the .rpf and type the pack folder name.")
            if not pack:
                continue
            pack = re.sub(r'[\\/:*?"<>|]+', "_", pack).strip()
            target = base / "dlcpacks" / pack / "dlc.rpf"
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(target))
            extra = (f"{len(info['paths'])} files, load order {info['order']}" if info["is_pack"]
                     else "contents are encrypted")
            self.log(f"  DLC pack '{pack}' (name taken from {why}) in {rel.name}: "
                     f"placed at onigiri/dlcpacks/{pack}/dlc.rpf ({extra}).")
            parent = src.parent
            while parent != base and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

    def _register_dlc(self, contrib, desired, used):
        """The game only loads DLC packs that dlclist.xml lists. Add a line for every enabled pack
        that is missing, using the file already in the onigiri folder as the baseline (it is never
        invented: a list with only our packs would replace the game's own)."""
        self.report["dlc_registered"], self.report["dlc_nobase"] = [], []
        packs = {}
        for lst in contrib.values():
            mod, src, rel, kind = lst[-1]
            folder = self._pack_rel(rel) if kind == "onigiri" else None
            if folder:
                packs[folder] = mod
        if not packs:
            return
        key = self._key(self._dest_abs("onigiri", DLCLIST_REL))
        if key in desired:                                    # a mod ships its own dlclist.xml
            raw = Path(desired[key][1]).read_bytes()
        else:
            orig = self._existing_original(DLCLIST_REL)
            if orig is None:
                self.report["dlc_nobase"] = sorted(packs)
                return
            raw = orig.read_bytes()
        text = raw.decode("utf-8", errors="surrogateescape")
        order = {m["name"]: i for i, m in enumerate(self.mods)}
        missing = [f for f in sorted(packs, key=lambda f: (order.get(packs[f], 0), f.lower()))
                   if not re.search(r"dlcpacks:/" + re.escape(f) + r"/", text, re.I)]
        if not missing:
            return
        ends = list(re.finditer(r"</Paths>", text, re.I))
        if not ends:
            self.report["dlc_nobase"] = sorted(packs)
            return
        nl = "\r\n" if "\r\n" in text else "\n"
        indents = re.findall(r"^([ \t]*)<Item>", text, re.M)
        ind = indents[-1] if indents else ""                  # match the file's own indentation
        add = "".join(f"{ind}<Item>dlcpacks:/{f}/</Item>{nl}" for f in missing)
        at = ends[-1].start()
        ls = text.rfind("\n", 0, at) + 1
        if text[ls:at].strip():                               # </Paths> shares its line with other text
            text = text[:at] + nl + add + text[at:]
        else:
            text = text[:ls] + add + text[ls:]
        data = text.encode("utf-8", errors="surrogateescape")
        digest = hashlib.sha1(data).hexdigest()[:16]
        out = MERGE_DIR / digest / DLCLIST_REL.name
        if not out.exists():
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
        used.add(digest)
        desired[key] = ("DLC registration", str(out))
        self.report["dlc_registered"] = missing

    def dlc_registered_in_list(self, folder):
        """True / False if the dlclist.xml in the onigiri folder lists this pack, None if there is none."""
        p = Path(self.cfg["onigiri_dir"]) / DLCLIST_REL
        if not p.exists():
            return None
        t = p.read_text("utf-8", errors="replace")
        return bool(re.search(r"dlcpacks:/" + re.escape(folder) + r"/", t, re.I))

    def dlc_packs(self, enabled_only=True):
        out = []
        for m in self.mods:
            if enabled_only and not m["enabled"]:
                continue
            for src, rel, kind in self._mod_files(m["name"]):
                folder = self._pack_rel(rel) if kind == "onigiri" else None
                if folder:
                    out.append({"mod": m["name"], "folder": folder, "src": src, "info": dlc_info(src)})
        return out

    def dlc_report(self):
        """Conflicts and warnings between the installed DLC packs. Each finding is
        {'level': conflict|warning|info, 'title', 'detail', 'fixes': [(label, op)]};
        see apply_dlc_fix for the ops."""
        packs = self.dlc_packs()
        order = {m["name"]: i for i, m in enumerate(self.mods)}
        pname = lambda p: p["info"].get("name") or p["folder"]
        pid = lambda p: (p["mod"], p["folder"])
        out, handled = [], set()

        def disables(group):
            return [(f"Disable '{q['mod']}'", ("disable", q["mod"])) for q in group]

        def mark(group):
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    handled.add(frozenset((pid(group[i]), pid(group[j]))))

        by_folder = {}
        for p in packs:
            by_folder.setdefault(p["folder"].lower(), []).append(p)
        for folder, grp in sorted(by_folder.items()):
            if len(grp) < 2:
                continue
            grp.sort(key=lambda p: order[p["mod"]])
            mark(grp)
            mods = ", ".join(f"'{p['mod']}'" for p in grp)
            if all(files_identical(grp[0]["src"], q["src"]) for q in grp[1:]):
                out.append({"level": "conflict", "title": f"Pack '{folder}' is installed twice (identical copies)",
                            "detail": f"{mods} all install the same dlcpacks/{folder}/dlc.rpf. Only one copy is "
                                      f"used, so the extra ones do nothing.", "fixes": disables(grp[1:])})
                continue
            names = {(p["info"].get("name") or "").lower() for p in grp}
            if len(names) == 1 and "" not in names:
                out.append({"level": "conflict", "title": f"Two versions of pack '{folder}' are installed",
                            "detail": f"{mods} install different files for the same pack. They overwrite each "
                                      f"other and only '{grp[-1]['mod']}' (lowest in the list) is used.",
                            "fixes": disables(grp)})
                continue
            fixes, taken = [], set(by_folder)
            for q in grp:
                nm = q["info"].get("name") or ""
                if nm and nm.lower() != folder and nm.lower() not in taken:
                    fixes.append((f"Rename the folder of '{q['mod']}' to '{nm}'",
                                  ("rename_pack", q["mod"], q["folder"], nm)))
                    taken.add(nm.lower())
            out.append({"level": "conflict", "title": f"Different packs share the folder name '{folder}'",
                        "detail": f"{mods} put different packs into dlcpacks/{folder}/. They overwrite each other: "
                                  f"only '{grp[-1]['mod']}' is used. Renaming a folder lets both load "
                                  f"(each pack is registered under its own name).",
                        "fixes": fixes + disables(grp[1:])})

        by_name = {}
        for p in packs:
            nm = (p["info"].get("name") or "").lower()
            if nm:
                by_name.setdefault(nm, []).append(p)
        for nm, grp in sorted(by_name.items()):
            if len({p["folder"].lower() for p in grp}) < 2:
                continue
            grp.sort(key=lambda p: order[p["mod"]])
            mark(grp)
            out.append({"level": "conflict", "title": f"Pack '{nm}' is installed under different folder names",
                        "detail": ", ".join(f"'{p['mod']}' ({p['folder']})" for p in grp)
                                  + ". The game would load the same pack twice.", "fixes": disables(grp[1:])})

        readable = [p for p in packs if p["info"].get("readable") and p["info"].get("is_pack")]
        for i in range(len(readable)):
            for j in range(i + 1, len(readable)):
                a, b = readable[i], readable[j]
                if frozenset((pid(a), pid(b))) in handled:
                    continue
                same = sorted(x for x in a["info"]["paths"]
                              if x in b["info"]["paths"] and x.split("/")[-1] not in _DLC_BOILERPLATE)
                if not same:
                    continue
                oa, ob = a["info"].get("order"), b["info"].get("order")
                fixes = []
                if oa is not None and ob is not None and oa != ob:
                    late, early = (a, b) if oa > ob else (b, a)
                    why = (f"'{pname(late)}' (load order {max(oa, ob)}) loads after '{pname(early)}' "
                           f"(load order {min(oa, ob)}) and wins where they overlap. That order is stored inside "
                           f"each pack and cannot be changed from outside.")
                else:
                    why = ("Both packs have the same load order, so the one listed later in dlclist.xml should "
                           "win. The loader lists packs in the order of your mod list.")
                    for x, y in ((a, b), (b, a)):
                        if x["mod"] != y["mod"] and order[x["mod"]] < order[y["mod"]]:
                            fixes.append((f"Make '{pname(x)}' win (move '{x['mod']}' below '{y['mod']}')",
                                          ("move_after", x["mod"], y["mod"])))
                fixes += disables([a] if a["mod"] != b["mod"] else []) + disables([b] if a["mod"] != b["mod"] else [])
                out.append({"level": "warning",
                            "title": f"Packs '{pname(a)}' and '{pname(b)}' contain {len(same)} file(s) with the same path",
                            "detail": f"For example: {', '.join(same[:3])}. {why}", "fixes": fixes})

        unread = [p for p in packs if not p["info"].get("readable")]
        if unread:
            out.append({"level": "info", "title": f"{len(unread)} pack(s) cannot be inspected",
                        "detail": "These archives are encrypted, so only folder-name checks are possible for: "
                                  + ", ".join(f"'{p['mod']}' ({p['folder']})" for p in unread) + ".", "fixes": []})
        nb = getattr(self, "report", {}).get("dlc_nobase")
        if nb:
            out.append({"level": "warning", "title": "DLC packs could not be registered",
                        "detail": "There is no dlclist.xml in the onigiri folder to add them to (the loader never "
                                  "invents one, because it would replace the game's own list): " + ", ".join(nb)
                                  + ". Put your dlclist.xml in common/data of the onigiri folder.", "fixes": []})
        for p in packs:
            orig = self._existing_original(Path("dlcpacks") / p["folder"] / "dlc.rpf")
            if orig is not None and not files_identical(orig, p["src"]):
                out.append({"level": "info", "title": f"Pack '{p['folder']}' replaces a file that is already there",
                            "detail": f"'{p['mod']}' replaces the existing dlcpacks/{p['folder']}/dlc.rpf. The "
                                      f"original is kept as a backup and put back when you disable the mod.",
                            "fixes": []})
        rank = {"conflict": 0, "warning": 1, "info": 2}
        return sorted(out, key=lambda f: rank[f["level"]])

    def apply_dlc_fix(self, op):
        """Run one correction offered by dlc_report()."""
        if op[0] == "disable":
            self.set_enabled(op[1], False)
        elif op[0] == "rename_pack":
            self.rename_dlc_pack(op[1], op[2], op[3])
        elif op[0] == "move_after":
            names = [m["name"] for m in self.mods]
            ia, ib = names.index(op[1]), names.index(op[2])
            if ia < ib:
                self.mods.insert(ib, self.mods.pop(ia))
            self.save()
            self.apply()
        else:
            raise ValueError(f"Unknown fix: {op[0]}")

    def rename_dlc_pack(self, mod, old, new):
        """Rename a pack's folder. The pack is found by where its dlc.rpf really is in the library,
        so this works whether it was stored as dlcpacks/<pack>/ or arrived as <pack>/dlc.rpf."""
        folder = None
        for src, rel, kind in self._mod_files(mod):
            f = self._pack_rel(rel) if kind == "onigiri" else None
            if f and f.lower() == old.lower():
                folder = Path(src).parent
                break
        if folder is None or folder.name.lower() != old.lower():
            raise ValueError(f"'{mod}' has no pack folder '{old}' that can be renamed.")
        target = folder.with_name(new)
        if target.exists() and target.resolve() != folder.resolve():
            raise ValueError(f"'{mod}' already has a folder named '{new}'.")
        shutil.move(str(folder), str(target))
        self.log(f"Renamed the pack folder of '{mod}': {old} -> {new}.")
        self.apply()

    def mod_summary(self, name):
        """Where a mod's files will go, for display: {'per': {...}, 'unplaced': n, 'readmes': [...]}"""
        ok, bad = self._scan(name)
        per = {}
        for _s, rel, kind in ok:
            if kind == "game":
                k = "game folder/scripts" if rel.parts[0] == "scripts" else "game folder (next to the exe)"
            elif len(rel.parts) == 1:
                k = "onigiri (top level)"
            else:
                k = "onigiri/" + rel.parts[0]
            per[k] = per.get(k, 0) + 1
        bad = [b for b in bad if b.suffix.lower() not in NOT_GAME_FILES]
        dlc = sorted({self._pack_rel(rel) for _s, rel, kind in ok if kind == "onigiri" and self._pack_rel(rel)})
        return {"per": per, "unplaced": len(bad), "readmes": [p.name for p in self.find_readmes(name)], "dlc": dlc}

    def shared_details(self, name):
        """{file: [other enabled mods that also provide it]} for one mod."""
        mine = {self._key(self._dest_abs(kind, rel)): rel.as_posix()
                for _s, rel, kind in self._mod_files(name)}
        out = {}
        for m in self.mods:
            if m["name"] == name or not m["enabled"]:
                continue
            for _s, rel, kind in self._mod_files(m["name"]):
                k = self._key(self._dest_abs(kind, rel))
                if k in mine:
                    out.setdefault(mine[k], []).append(m["name"])
        return out

    def conflicts(self):
        """{mod name: number of files overridden by a later mod}"""
        owners, result = {}, {m["name"]: 0 for m in self.mods}
        for m in self.mods:
            if not m["enabled"]:
                continue
            for _, rel, kind in self._mod_files(m["name"]):
                d = self._key(self._dest_abs(kind, rel))
                if d in owners:
                    result[owners[d]] += 1
                owners[d] = m["name"]
        return result

    @staticmethod
    def _link_or_copy(src, dest):
        try:
            os.link(src, dest)
        except OSError:
            shutil.copy2(src, dest)

    def apply(self):
        if not self.cfg["game_dir"] or not Path(self.cfg["game_dir"]).exists():
            self.log("Set your GTA V folder first.")
            return
        self.create_structure()
        desired = self._desired()
        scripts_key = self._key(Path(self.cfg["game_dir"]) / "scripts") + os.sep
        needs = [d for d in desired if d.startswith(scripts_key) and d.lower().endswith(tuple(SCRIPT_CODE_EXT))]
        have = (Path(self.cfg["game_dir"]) / "ScriptHookVDotNet.asi").exists() or \
            any(d.lower().endswith("scripthookvdotnet.asi") for d in desired)
        if needs and not have:
            self.log(f"{len(needs)} script file(s) need ScriptHookVDotNet to run, and it is not installed. "
                     f"Add the ScriptHookVDotNet (Enhanced) package with Add archive.")
        rp = self.report
        if rp["merged"]:
            tot = sum(c for _, _, c in rp["merged"])
            self.log(f"Merged {len(rp['merged'])} shared file(s) from several mods"
                     + (f"; {tot} spot(s) where mods edit the same lines were resolved "
                        f"in favour of the mod lower in the list." if tot else ", no conflicts."))
            for rel, names, c in rp["merged"][:6]:
                self.log(f"  {rel}  ({' + '.join(names)}){f'  [{c} conflict(s)]' if c else ''}")
        if rp["nobase"]:
            self.log(f"{len(rp['nobase'])} shared file(s) could not be merged because there is no existing or "
                     f"saved original copy to compare against; the mod lower in the list wins. e.g. {rp['nobase'][0][0]}")
            self.log("  Put an original copy in the onigiri folder or the base folder (button: Open base folder).")
        if rp.get("legacy_skipped"):
            self.log(f"Legacy (old game) file(s) not installed because the Enhanced version is present: "
                     f"{', '.join(rp['legacy_skipped'])}")
        if rp.get("dlc_registered"):
            self.log(f"Registered {len(rp['dlc_registered'])} DLC pack(s) in dlclist.xml: "
                     f"{', '.join(rp['dlc_registered'])}")
        if rp.get("dlc_nobase"):
            self.log(f"{len(rp['dlc_nobase'])} DLC pack(s) could not be registered: there is no dlclist.xml in "
                     f"the onigiri folder to add them to ({', '.join(rp['dlc_nobase'])}).")
        probs = [f for f in self.dlc_report() if f["level"] in ("conflict", "warning")]
        if probs:
            self.log(f"DLC packs: {len(probs)} conflict(s) or warning(s). Open 'DLC packs' to see them and fix them.")
        carry = {}
        removed = added = 0

        for dest, info in list(self.deployed.items()):
            want = desired.get(dest)
            if want and want[1] == info["src"]:
                continue
            p = Path(dest)
            if p.exists() or p.is_symlink():
                p.unlink()
            bk = info.get("backup")
            if bk and want:
                carry[dest] = bk              # file will be redeployed; keep backup
            elif bk and Path(bk).exists():
                shutil.move(bk, dest)         # restore original
            del self.deployed[dest]
            removed += 1
            self._prune(p.parent)

        kept = []
        for dest, (mod, src) in desired.items():
            if dest in self.deployed:
                continue
            p = Path(dest)
            if p.suffix.lower() == ".ini" and p.exists() and \
                    Path(self.cfg["onigiri_dir"]) not in p.parents:
                kept.append(p.name)                # game-folder settings file: keep the user's
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            bk = carry.get(dest)
            if p.exists():                    # a foreign file is in the way
                h = hashlib.md5(dest.encode()).hexdigest()[:12]
                bk = str(BACKUP_DIR / f"{h}_{p.name}")
                shutil.move(str(p), bk)
            self._link_or_copy(src, p)
            self.deployed[dest] = {"mod": mod, "src": src, "backup": bk}
            added += 1

        self.save()
        if kept:
            self.log(f"Kept your existing settings file(s), not overwritten: {', '.join(sorted(set(kept)))}")
        self.log(f"Applied: {added} files deployed, {removed} removed.")

    def _prune(self, folder: Path):
        root = Path(self.cfg["onigiri_dir"])
        try:
            while folder != root and root in folder.parents and not any(folder.iterdir()):
                folder.rmdir()
                folder = folder.parent
        except OSError:
            pass

    def install_core(self, files):
        names = {Path(f).name.lower() for f in files}
        for f in files:
            n = Path(f).name.lower()
            if n.endswith(".oiv"):
                self.log(f"Skipped {Path(f).name}: .oiv is an OpenIV package file - this loader never installs them.")
                continue
            if n in NEVER_DEPLOY_NAMES:
                self.log(f"Skipped {Path(f).name}: OpenIV support files (openiv.asi / openrpf.asi) are not "
                         f"installed by this loader - they cause compatibility issues and crashes.")
                continue
            twin = LEGACY_FILES.get(n)
            if twin and twin in names:
                self.log(f"Skipped {Path(f).name} (legacy, old game): the Enhanced {twin} was selected instead.")
                continue
            if n in LEGACY_FILES:
                if twin:
                    self.log(f"WARNING: {Path(f).name} is made for the old (legacy) game - the Enhanced version "
                             f"uses {twin}. No Enhanced version was selected, so the legacy file is installed.")
                else:
                    self.log(f"WARNING: {Path(f).name} is made for the old (legacy) game and has no Enhanced "
                             f"equivalent. It is installed because no Enhanced version is present.")
            shutil.copy2(f, Path(self.cfg["game_dir"]) / Path(f).name)
            self.log(f"Copied {Path(f).name} to game folder.")


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------
# ---- themes -----------------------------------------------------------------
THEMES = {
    "dark": {"name": "dark", "bg": "#1c1e24", "surface": "#23262d", "field": "#2b2f37", "head": "#2c303a",
             "btn": "#303541", "btn_hover": "#3b4150", "btn_press": "#262a34", "fg": "#e6e8ec",
             "muted": "#9ba3af", "border": "#3d424d", "accent": "#2f7d3c", "accent_fg": "#ffffff",
             "sel": "#2f4f7f", "sel_fg": "#ffffff", "log_bg": "#15171c", "log_fg": "#cdd3dc",
             "tip_bg": "#2f333d", "tip_fg": "#e6e8ec", "tip_border": "#5a606c", "warn": "#ff7b6e", "ok": "#57d364"},
    "light": {"name": "light", "bg": "#f0f0f0", "surface": "#ffffff", "field": "#ffffff", "head": "#e1e1e1",
              "btn": "#e1e1e1", "btn_hover": "#e5f1fb", "btn_press": "#cce4f7", "fg": "#000000",
              "muted": "#555555", "border": "#adadad", "accent": "#0078d7", "accent_fg": "#ffffff",
              "sel": "#cce8ff", "sel_fg": "#000000", "log_bg": "#1e1e1e", "log_fg": "#d4d4d4",
              "tip_bg": "#ffffe1", "tip_fg": "#000000", "tip_border": "#000000", "warn": "#c0392b", "ok": "#1a7f37"},
}
THEME = dict(THEMES["light"])          # the palette currently in use (read by popups and dialogs)


def set_dark_titlebar(window, dark=True):
    """Windows 10/11: use the dark title bar. Best effort; silently ignored elsewhere."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        val = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):          # DWMWA_USE_IMMERSIVE_DARK_MODE (Win10 2004+/11, then older Win10)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val),
                                                          ctypes.sizeof(val)) == 0:
                break
    except Exception:
        pass


# ---- tooltips ---------------------------------------------------------------
HEADER_TIPS = {
    "on": "Enabled: [x] means this mod's files are installed in your game.\n"
          "Double-click a row (or use Enable / Disable) to switch a mod on or off.",
    "name": "Your mods, in load order (top to bottom).\n"
            "When two mods change the same file, the one lower in the list wins any spot they both edit. "
            "Use Move up / Move down to change the order.",
    "files": "How many files in this mod will be installed, into the onigiri folder or next to the game exe.\n"
             "Readmes, images and 'original files' backup folders are not counted.",
    "conf": "Shared files: how many of this mod's files a mod lower in the list also provides.\n"
            "Text files (xml, meta, dat...) are merged where the mods edit different places; "
            "other files (.rpf, .ytd...) are won by the lower mod. Hover a row's number for details.",
}
TIPS = {
    "game_dir": "Your GTA V Enhanced folder, the one containing GTA5_Enhanced.exe.\n"
                ".asi plugins and their .ini files are installed here, next to the game exe.\n"
                "The onigiri and scripts folders are automatically set inside this folder.",
    "onigiri_dir": "Where mod files are installed: the 'onigiri' folder that onigiri.asi reads.\n"
                   "It is set automatically from your GTA V folder, so this field is read-only.",
    "browse_game": "Choose your GTA V folder (the one that contains GTA5_Enhanced.exe).\n"
                   "The onigiri and scripts folders are set to this folder automatically.",
    "scan": "Search this PC for your GTA V folder (registry, common install locations and a quick\n"
            "scan of your drives) and show which core files are present. The best match is used\n"
            "automatically; missing core files can be added with Install core files.",
    "merge": "When two mods edit the same text file in different places, combine both edits instead of "
             "letting one mod replace the other.\nThe existing file in the onigiri folder (for example "
             "NVE's version) is used as the baseline. Where both edit the same lines, the lower mod wins.",
    "core": "Files the game needs next to the exe:\n  onigiri.asi - redirects the game to the onigiri folder\n"
            "  ScriptHookV.dll - lets .asi plugins run\n  xinput1_4.dll - the ASI loader that loads .asi files\n"
            "  ScriptHookVDotNet.asi - optional; runs .NET script mods from the scripts folder\n"
            "Only the Enhanced loader (xinput1_4.dll) is used; the legacy dinput8.dll is a fallback only.\n"
            "Green ✓ = installed. Red ✗ = not in your GTA V folder yet (see Install core files).",
    "dark": "Switch between the dark and light look. Your choice is remembered.",
    "log": "Activity log: what was installed, merged, placed or skipped, plus any warnings.",
    "warn": "These mods are for single player only. Do not use them in GTA Online; you risk a ban.",
    "btn": {
        "Add archive": "Install a mod from a .zip, .7z or .rar archive, or from a single .rpf file.\n"
                       "The loader reads the folder layout (or the README) to work out where each file goes.",
        "Enable / Disable": "Switch the selected mod on or off.\nEnabling installs its files; disabling removes "
                            "them and restores anything it replaced.",
        "Move up": "Move the selected mod up. Mods higher in the list lose when two mods edit the same lines.",
        "Move down": "Move the selected mod down. Mods lower in the list win when two mods edit the same lines.",
        "Remove": "Uninstall the selected mod from the game and delete it from the library.",
        "Re-apply": "Redeploy every enabled mod now. Use it after changing folders or editing the library by hand.",
        "Install core files": "Copy onigiri.asi, ScriptHookV.dll or the ASI loader (xinput1_4.dll) into your GTA V folder.\n"
                              "A file with the same name is overwritten.\n"
                              "If both the legacy loader (dinput8.dll) and xinput1_4.dll are selected, only xinput1_4.dll is installed.",
        "Folder guide": "Show the folder layout that mods should follow.",
        "Open onigiri folder": "Open the onigiri folder in File Explorer.",
        "View README": "Read the selected mod's README and see which folders the loader found in it.",
        "DLC packs": "Show the DLC packs (.rpf) your mods install, whether each is listed in dlclist.xml, and any "
                     "conflicts between them, with one-click fixes.",
        "Reset all": "Unloads every mod (restoring the original game files), deletes the whole mod "
                     "library and all backups, and returns the loader to a fresh first-time state.\n"
                     "An 'Are you sure?' prompt is required. This cannot be undone.",
        "Open base folder": "Open the folder of saved original files. They are the merge baseline when the "
                            "onigiri folder has no copy of a file.",
    },
}


def cell_tip(L, name, col):
    """Hover text for one cell of the mod list (None if there is nothing to say)."""
    try:
        enabled = next(m["enabled"] for m in L.mods if m["name"] == name)
    except StopIteration:
        return None
    if col == "on":
        return ("Enabled: this mod's files are installed in your game.\nDouble-click the row to switch it off."
                if enabled else
                "Disabled: nothing from this mod is installed.\nDouble-click the row to switch it on.")
    if col in ("name", "files"):
        sm = L.mod_summary(name)
        lines = [name] if col == "name" else ["Files this mod will install:"]
        lines += [f"  {k}: {v}" for k, v in sorted(sm["per"].items())] or ["  (nothing matched the onigiri folders)"]
        if sm["unplaced"]:
            lines.append(f"{sm['unplaced']} file(s) could not be placed and are ignored.")
        if col == "name":
            if sm["readmes"]:
                lines.append("README: " + ", ".join(sm["readmes"][:3]) + " (button: View README)")
            if sm.get("dlc"):
                lines.append("DLC pack: " + ", ".join(sm["dlc"]) + " (listed in dlclist.xml automatically)")
            lines.append("Double-click to enable or disable.")
        else:
            lines.append("Readmes, images and backup folders are not counted.")
        return "\n".join(lines)
    if col == "conf":
        sh = L.shared_details(name)
        if not sh:
            return "None of this mod's files is also provided by another enabled mod."
        order = {m["name"]: i for i, m in enumerate(L.mods)}
        lines = [f"{len(sh)} file(s) are also provided by other enabled mods:"]
        for rel, others in list(sh.items())[:8]:
            tags = ", ".join(f"{o} ({'later' if order[o] > order[name] else 'earlier'})" for o in others)
            lines.append(f"  {rel} - {tags}")
        if len(sh) > 8:
            lines.append(f"  ...and {len(sh) - 8} more")
        lines.append("Text files are merged where the mods edit different places; otherwise the later mod wins.")
        return "\n".join(lines)
    return None


def make_tooltip_classes(tk, colors=None):
    """Hover tooltips for tkinter widgets and for Treeview headers/cells.
    `colors` is an optional function returning the current palette (for dark mode)."""
    def popup(widget, text, x, y):
        c = colors() if colors else {}
        tw = tk.Toplevel(widget)
        tw.wm_overrideredirect(True)
        tw.configure(bg=c.get("tip_border", "#000000"))
        tk.Label(tw, text=text, justify="left", bg=c.get("tip_bg", "#ffffe1"),
                 fg=c.get("tip_fg", "#000000"), wraplength=340, padx=6, pady=4,
                 font=("Segoe UI", 9)).pack(padx=1, pady=1)
        tw.update_idletasks()
        x = max(0, min(x, tw.winfo_screenwidth() - tw.winfo_reqwidth() - 8))
        if y + tw.winfo_reqheight() > tw.winfo_screenheight() - 8:
            y = max(0, y - tw.winfo_reqheight() - 40)
        tw.wm_geometry(f"+{int(x)}+{int(y)}")
        return tw

    class Tooltip:
        """Show `text` (a string, or a function returning one) after the pointer rests on a widget."""
        def __init__(self, widget, text, delay=500):
            self.widget, self.text, self.delay = widget, text, delay
            self.tw = self.job = None
            widget.bind("<Enter>", self.schedule, add="+")
            widget.bind("<Leave>", self.hide, add="+")
            widget.bind("<ButtonPress>", self.hide, add="+")

        def schedule(self, _e=None):
            self.hide()
            self.job = self.widget.after(self.delay, self.show)

        def show(self):
            self.job = None
            txt = self.text() if callable(self.text) else self.text
            if txt and not self.tw:
                self.tw = popup(self.widget, txt, self.widget.winfo_rootx() + 14,
                                self.widget.winfo_rooty() + self.widget.winfo_height() + 6)

        def hide(self, _e=None):
            if self.job:
                self.widget.after_cancel(self.job)
                self.job = None
            if self.tw:
                self.tw.destroy()
                self.tw = None

    class TreeTip:
        """Tooltips for a Treeview: one text per column header and per cell. `text_for(key)`
        gets ('h', column) for headers or ('c', row, column) for cells."""
        def __init__(self, tree, text_for, delay=500):
            self.tree, self.text_for, self.delay = tree, text_for, delay
            self.key = self.job = self.tw = None
            self.pos = (0, 0)
            tree.bind("<Motion>", self.motion, add="+")
            tree.bind("<Leave>", self.hide, add="+")
            tree.bind("<ButtonPress>", self.hide, add="+")

        def motion(self, e):
            region = self.tree.identify_region(e.x, e.y)
            col = self.tree.identify_column(e.x)
            if region == "heading":
                key = ("h", col)
            elif region == "cell":
                key = ("c", self.tree.identify_row(e.y), col)
            else:
                key = None
            self.pos = (e.x_root + 14, e.y_root + 18)
            if key != self.key:
                self.hide()
                self.key = key
                if key:
                    self.job = self.tree.after(self.delay, self.show)

        def show(self):
            self.job = None
            txt = self.text_for(self.key) if self.key else None
            if txt and not self.tw:
                self.tw = popup(self.tree, txt, *self.pos)

        def hide(self, _e=None):
            if self.job:
                self.tree.after_cancel(self.job)
                self.job = None
            if self.tw:
                self.tw.destroy()
                self.tw = None
            if _e is not None:
                self.key = None

    return Tooltip, TreeTip


# ---- window icon (the onigiri; also embedded in the .exe via --icon=onigiri.ico)
ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAACEklEQVR4nO1aPUsDQRDdixc7bRIDAa1UgoKWgoUg2vo/Uvg3/AH6g/zuLBQshOBXoSDE2Ghn/OrW2cUd5zZ7TMLMq/a42b25x3u7s3tnjEIhGlnZD6jmle9B+vc/vkrNsVLm4KMA8QQkl5cv+Zenjm1P1OeC/d56N3/GjVfHnLjUlhCvACWAOwFuJPET9D30vDG470OA84GPWrNl2ynmA/EKEE9AlITuzg+dpa4+M23bMZIvAmiPrZ22c+9k76Dw+4hXgHgCoizgV3vv/U9Sv1C1Fwt/tZicmlcLFIUSwJ0AN8ieSV3tlQG4c6RWieIVIJ4AsgVen6+tBagHG//FUlBkPBhL3TSJV4B4ApJbYFhAXRHEK0AJ4E6AG+gcAKs/6o6vbMTsKLMs0zkgBPEE5PAC+6zFhRSVpf9ecFkUrwAlgDsBbjjLQ+xhJwZYks6uLZL63J5e2fbq9rpz73h3v3AO2OGpeAWIJyDDqr3QV1p/KVrYWLLtxnIjZX6me9l1rqE9MItSvzCLV4B4ApxKEJMNFgdlmdoC/njwWVi+1IpRvAKUAO4EuOHMAb2HR+cm/PMDixtG3F8c2XboPYxRBSgBjgV8qYSkjknKr9wGXRb98SAwK8IcsTjxChBPQA7Px2rNlnMe0Dn73XtTJeUDk3BqhHJsrWw6cXomCKAEcCfAjaifpEYB+pMUEeIJUCgUsvEDBoW4QD7NJFkAAAAASUVORK5CYII="
)


def run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, simpledialog

    root = tk.Tk()
    root.title("Onigiri Loader - GTA V")
    root.geometry("1180x660")
    try:
        root.iconphoto(True, tk.PhotoImage(data=ICON_B64))
    except Exception:
        pass

    # --- left side panel with the GTA V artwork --------------------------------
    side = tk.Frame(root, bg="#101010")
    side.pack(side="left", fill="y")
    art = None
    try:
        art = tk.PhotoImage(data=ARTWORK_B64.replace("\n", ""))
        tk.Label(side, image=art, bg="#101010", bd=0).pack(padx=10, pady=(10, 6))
    except Exception:
        pass  # artwork is cosmetic; never block the app on it
    tk.Label(side, text="ONIGIRI LOADER", bg="#101010", fg="#ffffff",
             font=("Segoe UI", 14, "bold")).pack(pady=(4, 0))
    tk.Label(side, text="GTA V Enhanced mod manager", bg="#101010", fg="#9aa0a6",
             font=("Segoe UI", 9)).pack()
    warn_lbl = tk.Label(side, text="Single player only", bg="#101010", fg="#c0392b",
                        font=("Segoe UI", 9, "bold"))
    warn_lbl.pack(side="bottom", pady=10)

    main = ttk.Frame(root)
    main.pack(side="left", fill="both", expand=True)

    logbox = tk.Text(main, height=9, state="disabled", bg="#1e1e1e", fg="#d4d4d4")

    def log(msg):
        logbox.config(state="normal")
        logbox.insert("end", msg + "\n")
        logbox.see("end")
        logbox.config(state="disabled")
        root.update_idletasks()

    L = Loader(log)
    Tooltip, TreeTip = make_tooltip_classes(tk, lambda: THEME)

    # --- theme (dark by default; the switch is remembered) ------------------------
    style = ttk.Style()
    native_theme = style.theme_use()
    light_bg = root.cget("bg")

    def apply_theme(dark):
        pal = THEMES["dark" if dark else "light"]
        THEME.clear()
        THEME.update(pal)
        if dark:
            style.theme_use("clam")                  # 'clam' lets every colour be customised
            style.configure(".", background=pal["bg"], foreground=pal["fg"], fieldbackground=pal["field"],
                            bordercolor=pal["border"], lightcolor=pal["border"], darkcolor=pal["border"],
                            troughcolor=pal["surface"], focuscolor=pal["bg"], insertcolor=pal["fg"],
                            selectbackground=pal["sel"], selectforeground=pal["sel_fg"])
            style.configure("TButton", background=pal["btn"], foreground=pal["fg"], padding=(8, 4))
            style.map("TButton", background=[("pressed", pal["btn_press"]), ("active", pal["btn_hover"]),
                                             ("disabled", pal["surface"])],
                      foreground=[("disabled", pal["muted"])])
            style.configure("TEntry", fieldbackground=pal["field"], foreground=pal["fg"],
                            insertcolor=pal["fg"])
            style.map("TEntry", bordercolor=[("focus", pal["accent"])])
            style.configure("TCheckbutton", background=pal["bg"], foreground=pal["fg"],
                            indicatorbackground=pal["field"], indicatorforeground=pal["accent_fg"])
            style.map("TCheckbutton", background=[("active", pal["bg"])],
                      indicatorbackground=[("selected", pal["accent"]), ("pressed", pal["btn_press"])])
            style.configure("TCombobox", fieldbackground=pal["field"], background=pal["btn"],
                            foreground=pal["fg"], arrowcolor=pal["fg"],
                            selectbackground=pal["field"], selectforeground=pal["fg"])
            style.map("TCombobox", fieldbackground=[("readonly", pal["field"])],
                      background=[("active", pal["btn_hover"])])
            style.configure("Treeview", background=pal["surface"], fieldbackground=pal["surface"],
                            foreground=pal["fg"], rowheight=24, bordercolor=pal["border"])
            style.map("Treeview", background=[("selected", pal["sel"])],
                      foreground=[("selected", pal["sel_fg"])])
            style.configure("Treeview.Heading", background=pal["head"], foreground=pal["fg"],
                            relief="flat", padding=(6, 4))
            style.map("Treeview.Heading", background=[("active", pal["btn_hover"])])
            style.configure("TScrollbar", background=pal["btn"], troughcolor=pal["surface"],
                            arrowcolor=pal["fg"], bordercolor=pal["border"])
            style.map("TScrollbar", background=[("active", pal["btn_hover"])])
        else:
            style.theme_use(native_theme)
        style.configure("Muted.TLabel", foreground=pal["muted"])
        style.configure("CoreOk.TLabel", foreground=pal["ok"])
        style.configure("CoreBad.TLabel", foreground=pal["warn"])
        root.configure(bg=pal["bg"] if dark else light_bg)
        # plain tk widgets created later (simple dialogs, dropdown lists) pick these up
        for pat, val in (("*Background", pal["bg"]), ("*Foreground", pal["fg"]),
                         ("*Entry.Background", pal["field"]), ("*Entry.Foreground", pal["fg"]),
                         ("*Button.Background", pal["btn"]), ("*Button.Foreground", pal["fg"]),
                         ("*TCombobox*Listbox.background", pal["field"]),
                         ("*TCombobox*Listbox.foreground", pal["fg"]),
                         ("*TCombobox*Listbox.selectBackground", pal["sel"]),
                         ("*TCombobox*Listbox.selectForeground", pal["sel_fg"])):
            root.option_add(pat, val)
        logbox.configure(bg=pal["log_bg"], fg=pal["log_fg"], insertbackground=pal["fg"])
        warn_lbl.configure(fg=pal["warn"])
        set_dark_titlebar(root, dark)

    def toggle_dark():
        L.cfg["dark"] = bool(dark_var.get())
        L.save()
        apply_theme(L.cfg["dark"])
        refresh_paths()
    apply_theme(L.cfg.get("dark", True))
    _tips = []                                        # keep references alive

    def tip(widget, text):
        _tips.append(Tooltip(widget, text))
    tip(warn_lbl, TIPS["warn"])
    tip(logbox, TIPS["log"])

    top = ttk.Frame(main, padding=8); top.pack(fill="x")
    game_var, oni_var = tk.StringVar(), tk.StringVar()
    ttk.Label(top, text="GTA V folder:").grid(row=0, column=0, sticky="w")
    game_entry = ttk.Entry(top, textvariable=game_var, width=70)
    game_entry.grid(row=0, column=1, padx=4)
    tip(game_entry, TIPS["game_dir"])
    ttk.Label(top, text="Onigiri folder:").grid(row=1, column=0, sticky="w")
    oni_entry = ttk.Entry(top, textvariable=oni_var, width=70, state="readonly")
    oni_entry.grid(row=1, column=1, padx=4)
    tip(oni_entry, TIPS["onigiri_dir"])
    merge_var = tk.BooleanVar(value=L.cfg.get("merge", True))
    merge_cb = ttk.Checkbutton(top, text="Merge non-conflicting changes when mods edit the same file",
                               variable=merge_var, command=lambda: toggle_merge())
    merge_cb.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))
    tip(merge_cb, TIPS["merge"])
    dark_var = tk.BooleanVar(value=L.cfg.get("dark", True))
    dark_cb = ttk.Checkbutton(top, text="Dark mode", variable=dark_var, command=toggle_dark)
    dark_cb.grid(row=3, column=2, sticky="e", pady=(4, 0))
    tip(dark_cb, TIPS["dark"])
    core_frame = ttk.Frame(top)
    core_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))
    tip(core_frame, TIPS["core"])

    def refresh_paths():
        game_var.set(L.cfg["game_dir"]); oni_var.set(L.cfg["onigiri_dir"])
        st = L.core_status()
        for w in core_frame.winfo_children():
            w.destroy()
        ttk.Label(core_frame, text="Core files:", style="Muted.TLabel").grid(row=0, column=0, padx=(0, 10))
        for i, (n, ok) in enumerate(st.items()):
            ttk.Label(core_frame, text=("✓ " if ok else "✗ ") + n +
                      (" (optional, for .NET scripts)" if n in OPTIONAL_CORE else ""),
                      style="CoreOk.TLabel" if ok else "CoreBad.TLabel").grid(row=0, column=i + 1, padx=(0, 14))

    def browse_game():
        d = filedialog.askdirectory(title="Select your GTA V Enhanced folder (contains GTA5_Enhanced.exe)")
        if d:
            L.set_paths(d); refresh_paths(); refresh_list()

    def scan():
        log("Scanning for GTA V and core files...")
        root.update_idletasks()
        t0 = time.monotonic()
        report = scan_for_core()
        dt = time.monotonic() - t0
        if not report:
            log(f"Scan ({dt:.1f}s): no GTA V folder found. Use Browse... to select it manually.")
            return
        cur = (L.cfg.get("game_dir") or "").lower()
        best = next((c for c in report if c["dir"].lower() == cur), report[0])
        L.set_paths(best["dir"])
        log(f"Scan ({dt:.1f}s): using {best['dir']}  [{best['exe']}]")
        for f in CORE_SCAN_FILES:
            ok = best["core"][f]
            log(f"  {'✓' if ok else '✗'} {f}" + ("" if ok else "   (missing - see Install core files)"))
        refresh_paths(); refresh_list()

    bg_btn = ttk.Button(top, text="Browse...", command=browse_game)
    bg_btn.grid(row=0, column=2)
    tip(bg_btn, TIPS["browse_game"])
    sc_btn = ttk.Button(top, text="Scan", command=scan)
    sc_btn.grid(row=0, column=3)
    tip(sc_btn, TIPS["scan"])

    cols = ("on", "name", "files", "conf")
    tree = ttk.Treeview(main, columns=cols, show="headings", selectmode="browse")
    for c, t, w in (("on", "Enabled", 70), ("name", "Mod (load order, top to bottom)", 460),
                    ("files", "Files", 80), ("conf", "Shared files", 90)):
        tree.heading(c, text=t); tree.column(c, width=w, anchor="w")
    tree.pack(fill="both", expand=True, padx=8)

    def refresh_list():
        sel = tree.selection()
        tree.delete(*tree.get_children())
        conf = L.conflicts()
        for m in L.mods:
            tree.insert("", "end", iid=m["name"], values=(
                "[x]" if m["enabled"] else "[ ]",
                m["name"],
                len(L._mod_files(m["name"])), conf.get(m["name"], 0) or ""))
        if sel and tree.exists(sel[0]):
            tree.selection_set(sel[0])

    def selected():
        s = tree.selection()
        return s[0] if s else None

    def guard(fn):
        def wrapped(*a):
            try:
                fn(*a)
            except Exception as e:
                messagebox.showerror("Onigiri Loader", str(e))
            refresh_list(); refresh_paths()
        return wrapped

    @guard
    def toggle(*_):
        n = selected()
        if n:
            cur = next(m for m in L.mods if m["name"] == n)["enabled"]
            L.set_enabled(n, not cur)

    def ask_destination(fname):
        """Small dialog: where inside onigiri does this loose .rpf belong?"""
        is_dlc = fname.lower() == "dlc.rpf"
        win = tk.Toplevel(root)
        win.configure(bg=THEME["bg"])
        set_dark_titlebar(win, THEME["name"] == "dark")
        win.title("Where does this .rpf go?")
        win.transient(root); win.grab_set()
        out = {}
        ttk.Label(win, padding=8, text=f"{fname}").pack(anchor="w")
        var, pack = tk.StringVar(value=KNOWN_RPF.get(fname.lower(), "")), tk.StringVar()
        if is_dlc:
            ttk.Label(win, text="DLC pack folder name (for example: grassfix)",
                      padding=(8, 0)).pack(anchor="w")
            ttk.Entry(win, textvariable=pack, width=40).pack(padx=8, pady=4)
        else:
            ttk.Label(win, text="Folder inside onigiri (pick one or type your own):",
                      padding=(8, 0)).pack(anchor="w")
            ttk.Combobox(win, textvariable=var, values=topology_paths(),
                         width=46).pack(padx=8, pady=4)

        def ok():
            if is_dlc:
                if not pack.get().strip():
                    messagebox.showerror("Onigiri Loader", "Enter a pack folder name.", parent=win)
                    return
                out["d"] = "dlcpacks/" + pack.get().strip()
            elif var.get().strip():
                out["d"] = var.get().strip()
            else:
                messagebox.showerror("Onigiri Loader", "Choose a folder.", parent=win)
                return
            win.destroy()

        row = ttk.Frame(win, padding=8); row.pack()
        ttk.Button(row, text="OK", command=ok).pack(side="left", padx=4)
        ttk.Button(row, text="Cancel", command=win.destroy).pack(side="left", padx=4)
        root.wait_window(win)
        return out.get("d")

    @guard
    def add_archive():
        """Add a mod from a .zip/.7z/.rar archive or a single .rpf file."""
        f = filedialog.askopenfilename(
            title="Add mod archive",
            filetypes=[("Mod archive or .rpf", "*.zip *.7z *.rar *.rpf")])
        if not f:
            return
        if f.lower().endswith(".rpf"):
            info = dlc_info(f)
            if info["is_pack"] and info["name"]:
                dest, default = "dlcpacks/" + info["name"], info["name"]      # the pack names itself
            else:
                dest = ask_destination(Path(f).name)
                default = Path(dest).name if dest and Path(f).name.lower() == "dlc.rpf" else Path(f).stem
            if dest:
                name = simpledialog.askstring("Mod name", "Name for this mod:",
                                              initialvalue=default)
                if name:
                    L.install_rpf(f, dest, name)
            return
        name = simpledialog.askstring("Mod name", "Name for this mod:",
                                      initialvalue=Path(f).stem)
        if name:
            L.install(f, name)

    @guard
    def remove():
        n = selected()
        if n and messagebox.askyesno("Remove", f"Remove '{n}' from the library?"):
            L.remove(n)

    @guard
    def move(delta):
        n = selected()
        if n:
            L.move(n, delta)

    @guard
    def core():
        fs = filedialog.askopenfilenames(
            title="Select onigiri.asi, ScriptHookV.dll, xinput1_4.dll ...")
        if fs:
            L.install_core(fs)

    def view_readme():
        n = selected()
        if not n:
            messagebox.showinfo("README", "Select a mod first.")
            return
        files = L.find_readmes(n)
        if not files:
            messagebox.showinfo("README", f"No README found in '{n}'.")
            return
        win = tk.Toplevel(root)
        win.configure(bg=THEME["bg"])
        set_dark_titlebar(win, THEME["name"] == "dark")
        win.title(f"README - {n}")
        text = tk.Text(win, wrap="word", width=96, height=30, bg=THEME["log_bg"], fg=THEME["log_fg"],
                       insertbackground=THEME["fg"], relief="flat", padx=8, pady=6)
        sb = ttk.Scrollbar(win, command=text.yview)
        text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        body = ""
        for f in files:
            body += f"===== {f.name} =====\n{read_text(f)}\n\n"
        found = {}
        for f in files:
            for c in readme_candidates(read_text(f)):
                found.setdefault(c["dest"], c["line"])
        body += "===== Folders detected by Onigiri Loader =====\n"
        body += ("\n".join(f"onigiri/{d}   <-  {l[:90]}" for d, l in found.items())
                 if found else "(none)")
        text.insert("1.0", body)
        text.configure(state="disabled")

    def open_base():
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(BASE_DIR) if sys.platform == "win32" else subprocess.run(["xdg-open", str(BASE_DIR)])

    def toggle_merge():
        L.cfg["merge"] = merge_var.get()
        L.save()
        guard(L.apply)()

    def open_dlc():
        win = tk.Toplevel(root)
        win.configure(bg=THEME["bg"])
        set_dark_titlebar(win, THEME["name"] == "dark")
        win.title("DLC packs")
        win.geometry("800x580")
        txt = tk.Text(win, wrap="word", bg=THEME["log_bg"], fg=THEME["log_fg"], insertbackground=THEME["fg"],
                      relief="flat", padx=10, pady=8)
        sb = ttk.Scrollbar(win, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        for tag, color in (("conflict", THEME["warn"]), ("warning", "#e0b050"),
                           ("info", THEME["muted"]), ("h", THEME["fg"])):
            txt.tag_configure(tag, foreground=color, font=("Segoe UI", 10, "bold"))

        def do_fix(op):
            try:
                L.apply_dlc_fix(op)
            except Exception as e:
                messagebox.showerror("DLC packs", str(e), parent=win)
            refresh_list()
            refresh_paths()
            render()

        def render():
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            packs = L.dlc_packs()
            txt.insert("end", f"DLC packs installed by enabled mods: {len(packs)}\n", "h")
            for p in packs:
                i = p["info"]
                reg = L.dlc_registered_in_list(p["folder"])
                state = ("listed in dlclist.xml" if reg else
                         "NOT listed in dlclist.xml" if reg is False else "no dlclist.xml found")
                detail = (f"{len(i['paths'])} files, load order {i['order']}" if i.get("readable")
                          else "encrypted (contents cannot be read)")
                txt.insert("end", f"\n  {p['folder']}   from '{p['mod']}'\n      {detail}; {state}\n")
            findings = L.dlc_report()
            txt.insert("end", "\n" + ("Conflicts and warnings:" if findings else "No conflicts found.") + "\n", "h")
            for f in findings:
                txt.insert("end", f"\n[{f['level'].upper()}] {f['title']}\n", f["level"])
                txt.insert("end", f["detail"] + "\n")
                for label, op in f["fixes"]:
                    b = ttk.Button(txt, text=label, command=lambda op=op: do_fix(op))
                    txt.window_create("end", window=b)
                    txt.insert("end", "  ")
                txt.insert("end", "\n")
            txt.configure(state="disabled")
        render()

    def open_onigiri():
        p = Path(L.cfg["onigiri_dir"]); p.mkdir(parents=True, exist_ok=True)
        os.startfile(p) if sys.platform == "win32" else subprocess.run(["xdg-open", str(p)])

    def reset_all_gui():
        if not messagebox.askyesno(
                "Reset Onigiri Loader",
                "This unloads ALL mods from your GTA V folder (restoring the original game files),\n"
                "deletes the entire mod library and all backups, and clears all settings.\n\n"
                "The loader will be back to a fresh first-time state. This cannot be undone.\n\n"
                "Are you sure?",
                icon="warning", parent=root):
            return
        try:
            L.reset_all()
        except Exception as e:
            messagebox.showerror("Onigiri Loader", f"Reset failed: {e}")
            return
        refresh_paths(); refresh_list()
        messagebox.showinfo(
            "Onigiri Loader",
            "Done. The loader is now fresh: no mods, no library, default settings.\n"
            "Scan for or browse to your GTA V folder to start over.")

    bar = ttk.Frame(main, padding=8); bar.pack(fill="x")
    bar2 = ttk.Frame(main, padding=(8, 0, 8, 8)); bar2.pack(fill="x")
    bar3 = ttk.Frame(main, padding=(8, 0, 8, 8)); bar3.pack(fill="x")
    for idx, (text, cmd) in enumerate((("Add archive", add_archive),
                      ("Enable / Disable", toggle), ("Move up", lambda: move(-1)),
                      ("Move down", lambda: move(1)), ("Remove", remove),
                      ("Re-apply", guard(L.apply)), ("Install core files", core),
                      ("Folder guide", lambda: messagebox.showinfo(
                          "Mod folder layout",
                          "Mods must use this layout inside the onigiri folder:\n\n"
                          + topology_text()
                          + "\n\nafter_level.xml / before_level.xml sit at the top of the onigiri folder."
                          + "\n.rpf files go in the matching folder. DLC packs go in dlcpacks\\<pack>\\dlc.rpf and are"
                          + "\nadded to dlclist.xml for you."
                          + "\n.asi plugins (with their .ini files) and scripts\\ go next to the game exe.")),
                      ("Open onigiri folder", open_onigiri),
                      ("View README", view_readme),
                      ("Open base folder", open_base),
                      ("DLC packs", open_dlc),
                      ("Reset all", reset_all_gui))):
        btn = ttk.Button(bar if idx < 6 else bar2 if idx < 12 else bar3, text=text, command=cmd)
        btn.pack(side="left", padx=2)
        tip(btn, TIPS["btn"].get(text, ""))

    logbox.pack(fill="x", padx=8, pady=(0, 8))
    tree.bind("<Double-1>", toggle)
    _cols = {"#1": "on", "#2": "name", "#3": "files", "#4": "conf"}

    def tree_text(key):
        if key[0] == "h":
            return HEADER_TIPS.get(_cols.get(key[1]))
        return cell_tip(L, key[1], _cols.get(key[2])) if key[1] else None
    _tips.append(TreeTip(tree, tree_text))
    refresh_paths(); refresh_list()
    if not L.cfg["game_dir"]:
        log("GTA V folder not found automatically - use Scan or Browse...")
    log("Single-player only. Do not run mods in GTA Online.")
    root.mainloop()


ARTWORK_B64 = """
iVBORw0KGgoAAAANSUhEUgAAAVQAAAGhCAMAAAAJE7wtAAADAFBMVEX////8/v7//9v+/f39/P78/Pz7/Pz9/O77+/n87eX+8a3+
6Yr94Jj+3oD+2pT+2IX8zJ7+1YL91G39zHz9yFf29vbr9fjs7/Hu7O7q6ury5PHo6enp6ebl5OTu79Xt6rvj4uLg4ODu4bfq2+ru
2tPh3N3o0djqyMbw0qDz0HXvw57uwm3V7/jP6e/O5eHU3uHN3sLW1dbM0tPSyNPP07HLxLO75Pe24PS43Oi6ys63xqep1eGuv6GZ
y9h+xNrvuaLxt4fYuKzqrpPopIzSpqy4t7q2uJy8qr22qZq6nqj4t0D9swD6rwD5rwD3rgDxoW/zqCfis2vhp2XSqWbgnFrMnF7n
k2rkiWbTjHjikUfig0/SikS8ko67hYXCi0vAgEXSeVvVeTjTakLCd0rCaEO0dmOzaFe1cDOzYTSet8OZrb6Zso+ipK6QpLmZoYuc
l6CPk6CUiKaTkXqThHBzt8x8n5x7j4SAg5Nuho15gm1gssg4qcldjX40jZOgeJSJeId4eHuaaYqCZ4afcUZ+clehYT+GYUVod4Bp
bnZocV1kY2hlYVFTcF1UX1lEbUMiaofOVDG2UzKsUjSbVz6aTD2bUieaSCZ8V2J7S1eMUi57UimDRyawPieQPyWtJh6FPyqDMB9x
O011OiFyMCNwLhRwJBpZWVlXUVdJUldbVURZTT9KTUZaRFVIRklBQ0ZcQi5NQjVBQDlYOUBaMjxCNTphLhtGMiBhJRpWJBtHIxxN
GxdGFBEsUmQuRE84OzsoO0Q0NDc1MiwrMzMgMzwwK0IwLCo0KR8tKSEmKy4mKSMcKi4sIyQiIiQqHB8sHhQsFxMdIiMWISUbGx4T
Gh8YGhUWFxUyEw8mEhAiEhEiEQ4ZExAVExIWEQoxDQosCAQhCggYCwoYBQUPExUPERAMDRAQDwsODAoMCgkOCAcICAcPAwMJAwMF
ExgFBwkGBgYEBgYGBgQFBQcGBQQFBAQGBAIEBAMDBAMEAwMFAgEDAwQDAwMCAgEBAgIDAQEAAQMAAACWlMXGAAEAAElEQVR42uz9
CViTV9r4jzMyWkXq8vpScRQrViuCzgioFdQWRRTe73WNEyBKZRGFAMoqqQTsKJE1hFIFBASkICCrbAphRyISNxalyOZCUhcgTKka
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
A/pIRxcD1cXLEFVV37BZQBVKAKqlmxvVxISaJoWajB1AqO/lA5sP1Pt68Vr4yqHuluimZIUKKvpNgqshRpUjqGkZ5ZCkdo46UTmo
2Lkiqt2dQq9p+bb/bakQ6oBo4I9qqkh0TUVTtgJ4wYRAhaCKiGt4TQVeV+H/bgJUI5Ho7nhNBahrkaIuHqX6UWSw3srZeoiqq1sM
1YSaKIEaKllOYV/sv8Gn0T2vs1fAVwY1VmrwJqNnpFhWlpVjRS3PTE8vT2nt6RoLVRakOqUOoJf7V/be/7beCYHq1fhABcZo+Ieg
qnoTRLuWwWjHjmqWUqjkspED/u9EEzWVIPS1J0Bdt3jKR4vXrFm++KPFaxcjqDMKyhysVq6ERNUpBnR1b2xaZiqGmixZ+RNSuD4n
17cVMZ0MKrldsq6UqUkRClHlWNLTMyog8R+jp4C4txfnAd1S6RSYZdnutP4f24lQFwQGBi7S/wNQVVX0AwO9NeWnabMm0VS8+odB
jIOqqqLl4+O9QH+ipoKOLlsDsnjxmsVrZgDVRZFFDpD9W1H3xqEdKkJTQVGx+acnJ5eVJyfTInLai7lo6y8B/6nilOqUNDaNQg2r
SIEYRUJNS0vvHAuV39XTWFLCbZZAJXW2u9uj2NpaAVQVTTThpm8g98f89jwVLrHIYMkkFZUEKlochRepbfYfBxUuqr9g4QJ9RVAX
T0FM1+gvXgMqi8LVdGYRGlilUGPj0Xof5FRTEzHU9LJ0NAt4pziyuFnQLxC03lWc/MfJAr6JhCmtEiVTALQCQY1P449RU35jYUlj
SeNNXms3dq6kHxAUeyf9z9ck1DE+lZyi1pj2h/JUNLWtoaq89h/VVDyADJo6Hiq5N66G3EVGzX/xR2vWYqprIKlaA8oKVDlUKwcr
h+T0tPjU1HSc+4cmoylWPHZdWRLpm9ss7BcK8pqUrqKWOVUsVpXpaHOq8szyqqryzDS3sr5OedO/yS3JL2nmdvG7u+SgCn1Zrv/z
9dcKoH6wQ+XfMKAi01RyIe/BjZvB/N+MhaqwQ0X0FqCC1RsjqGsB6kcfrVkHWKf7VrpQTUxjMzMzACXqBU4Oxe0AoKlFrbxc3wCu
UCgQ8Ot/Gp1OlYMqLnPev28f6knbSTb42FRmYqiZKQAVEquU1nvyinozv7SRy+Xm5LdKoHbi8N9iVvQ1kv/3UPH88WbG+6cvn/5a
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
x4ts6W3mC7ubmwk/90buTZ6Q25zvnsvNfyJWuIOa7yyTefNMnKJN1NRmzJgSkrdsxlcO+5z27LGWE7TVp5vT1q1DeKp0dJ9vfQ0D
eB36vxHqkL6+9nJtuR2jxjdKq46HilaeM2UVh8ddTBXtdhnpteajNe5rFxv7blqLldV3u3sAHTGNfLgEJWB9CnZ6Ew0Qj5agjOBn
KdOnbLiefhMByEdT4DaAusl4rV99drOgmCdobu4UNLe+vm6c/5h3U9iaXeIVwCsuUVJRJTk5uYaGhjqpq6l9OiUid9kKU1tbGVJL
JJAPWDvujnVxdBkaeSUiGMsN9A0kom/2auTOb4UqMtLSXyR3Hs30BcuXjykUNRnjNbVwZCRwkSZKYqdNU1UxuEMgf8kmnj7c7usF
GEPcQWHdt/uGePkGeHnRgWlAbpOGyvRr4qcKN9AbgN+HCuP9VdIBXL88fbrK8jZiQDRMvG0iJzZL6rKAKbxV19kRpVH5Al5rZ7eA
LyQCIp7cvMnn5wdk5fKKC0oeK07+E5Gl7zJxslRTW1ocslR3J8pSJWY/qqp79jhlOLu9GnlFrpPuewLy6NGTJ31PRb8RqsHIyJ22
O97yx4RqjztMoQ1q3QLNMVAJIlB27M10FbOBPgOVaZptI8Td7e6+axav9dq0ZlOAF+RTSFOBKQlVQy41HwtVHIgOAnrfjqFynumr
TJvfCEzfQU5hvHbNmrU47wcxXpufm9+ZG9HC5bXyBx/3PM71vdcMtSo3MoDb2dnM6xQqLlODTUAZKSaOceo6PN+lW3cCSlu0pAKP
rZyMJjdpRbdjy9Lx+w7F8pjRdPFvhSoZUJFTXgWN0pNAVUGRjKtBbl8X9dGmgAAvFJsAbwBUWgEk1Mg7C1RVS0YPih+nqT5os9w3
ZKh6yoQron2x3z7xWyuJ+IDU3X37dmPjOr/u4tyu1tJeoaC/L8rLPesxr0vYxSstBc7NN7mPle31h/rbKSZuwVy7pVstIWg5kStU
oqNPnty352uoBfagnVVioqNTyRXD6CyZAjabzcIfbObC5b8RKh76k4c6MDKCLiiTupFJoaqqLkRudbpKNqSTke5rjdEEs1eAuzuk
p0A2JCAEKlTQZRWmbAvh8WO1UIoyiGdPENOWJvz+DIlGBvzAiUqhbgdxN950PaoEHGq3QNhc3MJ/HPXd6+ZmIf8mj9fb3dlaWlr6
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
"""


def is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    """Re-run this program elevated (UAC prompt). Returns True if launched."""
    import ctypes
    if getattr(sys, "frozen", False):          # built .exe
        exe, params = sys.executable, ""
    else:                                      # plain python script
        exe = sys.executable.replace("python.exe", "pythonw.exe")
        params = f'"{os.path.abspath(sys.argv[0])}"'
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return rc > 32


if __name__ == "__main__":
    if sys.platform == "win32" and not is_admin():
        if relaunch_as_admin():
            sys.exit(0)
        # UAC declined: carry on without admin (may fail in Program Files)
    run_gui()

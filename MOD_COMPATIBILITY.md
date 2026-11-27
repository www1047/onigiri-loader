# Making Mods Compatible with Onigiri Loader

**Best practices for mod authors and repackers**

Onigiri Loader is a mod manager for **GTA V Enhanced (single player)** built around the
NaturalVision Enhanced `onigiri` folder layout. Mods are added as archives
(`.zip`, `.7z`, `.rar`, or a single `.rpf`), kept in a private library, and deployed
into the game folder when enabled. This document describes the rules the loader applies
and how to structure your mod so it works the first time.

Mods sit on top of an **onigiri foundation** — either a NaturalVision Enhanced (NVE)
install (the usual baseline) or a stock-GTA V setup of core files plus a skeleton
onigiri folder (see §8). Either way, mods follow the same layout and the loader
treats them the same.

> **Single player only.** Modded files used in GTA Online risk a ban.
> Do not ship, or recommend, online use of your mod.

---

## 1. Use the onigiri folder layout

The loader deploys files into this topology (only the top level is enforced —
you are free to add your own subfolders):

```
onigiri/
├── after_level.xml            ← level-registry files sit at the top of the onigiri folder
├── before_level.xml
├── common/
│   └── data/
│       ├── ai/
│       ├── effects/
│       ├── levels/gta5/weather/
│       ├── materials/
│       └── timecycle/
│          (dlclist.xml, gameconfig.xml and similar live here too)
├── platform/
│   ├── data/{effects, metadata, tune}/
│   ├── levels/gta5/cloudhats/
│   └── textures/
└── dlcpacks/
    └── <pack name>/
        └── dlc.rpf
```

- If your README or mod folder references `x64\...` (the old game-folder name),
  the loader maps it to `platform\...` automatically.
- `after_level.xml` / `before_level.xml` belong at the top of the onigiri folder.
  When several mods provide them, the loader three-way merges them
  (an existing onigiri file, e.g. NVE's, is the merge baseline).

## 2. Target GTA V Enhanced — and label legacy branches clearly

The loader's policy is **Enhanced first, legacy only as a fallback**:

| Situation in your mod | What the loader does |
|---|---|
| Sibling folders labeled "Enhanced" and "Legacy" (e.g. `GTA V Enhanced/` next to `GTA V Legacy/`) | Installs the Enhanced branch only; the Legacy branch is skipped |
| Both `dinput8.dll` and `xinput1_4.dll` present | Installs `xinput1_4.dll` (Enhanced ASI loader) only |
| `openiv.asi` or `openrpf.asi` present | **Never installed** — OpenIV support files cause compatibility issues and crashes |
| `opencamerav.asi` | Flagged — it has no Enhanced equivalent |
| Any `.oiv` file (OpenIV package) | **Never installed** — the game cannot read them anyway |

Best practice:

- Ship the **Enhanced** version of every file as your primary content.
- If you still include files for the old game (for legacy users), put them in a
  folder clearly labeled **legacy** so the loader can skip them when an
  Enhanced equivalent is present.
- **Do not ship `.oiv` packages.** If your users need an OpenIV package,
  provide the already-extracted files instead.
- **Do not include `openiv.asi` / `openrpf.asi`.** The loader never installs
  OpenIV support files — they cause compatibility issues and crashes.

## 3. Put each file type where it belongs

The loader routes files based on where they sit inside your mod:

| Content | Ship it at | Deployed to |
|---|---|---|
| `common/`, `platform/`, `dlcpacks/` trees | anywhere (wrapper folders are stripped) | `<game>\onigiri\...` |
| `.asi` plugins | top level of the mod | `<game>\` (game root) |
| A plugin's config (`.ini`) | beside its `.asi` | game root, next to the `.asi` |
| .NET script code (`.dll`, `.cs`, `.vb`) | in a `scripts/` folder | `<game>\scripts` (needs ScriptHookVDotNet) |
| A script's config (`.ini` / `.xml` / `.json` / `.cfg`) | beside its script | `<game>\scripts`, next to the script |
| `reshade/`, `reshade-shaders/` | anywhere | game root |
| Loose files with a known onigiri destination | stated in the README (see §5) | that destination |

## 4. Package it cleanly

- **Archive formats:** `.zip` always works. `.7z` / `.rar` work if the user has
  7-Zip or WinRAR installed. Archives are recognised by content, not just extension.
- **Name the archive after the mod** — that name is offered as the mod's library name.
- **Wrapper folders are fine.** `MyMod/onigiri/common/...` is unwrapped
  automatically (wrappers such as `onigiri`, `NVE`, `GTA V Enhanced`, or your mod
  name are recognised, up to 8 levels deep).
- **Do not include vanilla backups.** Folders named `original files`, `originals`,
  `original`, `backup`, `backups` are discarded — they would otherwise be deployed
  into the game as if they were mod content.
- **Variants → `optionals/`.** Put each variant in its own subfolder of
  `optionals/` (or `optional/`). Each subfolder becomes a separate,
  individually switchable mod named `<YourMod> - <variant>`.
- **Docs and images are fine.** Root-level `.txt`/`.md` (README), images, PDFs,
  and folders such as `docs/`, `screenshots/`, `licenses/`, `debug/` are ignored
  when the loader collects mod files.

## 5. Write a README the loader can read

The loader parses your README (`.txt`/`.md`) to learn where loose files belong.
It looks for install-instruction lines that contain a destination path, and
prefers lines that also name the file(s) concerned:

```
Copy clouds.xml to onigiri/common/data
Copy mytexture.dds into onigiri/platform/textures/
```

Tips:

- Keep **one file/destination per line** — that is the form the parser handles best.
- Use the onigiri names (`common`, `platform`, `dlcpacks`) — or `x64`,
  which maps to `platform`.
- Everything after an **"Uninstall"** heading is ignored.
- **Encrypted DLC packs:** the loader cannot read the pack name out of an encrypted
  archive, so state the pack folder name in the README — the loader uses it to
  place and register the pack.

## 6. DLC packs

- Ship them as `dlcpacks/<pack name>/dlc.rpf`.
- Include a **`setup2.xml`** inside the pack. That makes the pack self-naming:
  the loader detects it, places it, and registers it in `common/data/dlclist.xml`.
- The loader maintains `dlclist.xml` for you and reports packs that are not
  registered, with one-click fixes. If two mods ship the same pack, the
  conflict is reported with a fix.
- Unencrypted (OPEN) packs can be inspected for conflict checking —
  prefer that where it is possible.

## 7. Play well with other mods

The loader runs many mods side by side:

- Files that several mods edit are **three-way merged** (the existing onigiri file
  is the baseline). Where a merge cannot be resolved, **the lower mod in the
  list takes precedence**.
- Best practice:
  - **Add new files** rather than editing shared ones where possible
    (a new texture in its own folder beats editing a shared material).
  - Keep edits to shared text files **small and localised** — they merge cleanly
    and are easy to resolve.
  - Do not ship modified copies of core onigiri files unless your mod genuinely
    requires them.
  - If your mod is known to conflict with another, document the recommended
    list order (the lower position takes precedence).

## 8. The onigiri foundation and core files

Mods in this ecosystem sit on top of an onigiri foundation. There are two
supported ways to build one:

1. **NaturalVision Enhanced (NVE) — the usual baseline.** Install NVE; it
   provides the onigiri folder and its engine. Mods are built on top of NVE,
   and the loader uses NVE's existing files as the merge baseline when
   combining several mods.
2. **Stock GTA V — core files + a skeleton onigiri folder.** Without a full NVE
   install, the foundation is the core files below plus the skeleton onigiri
   folder (`common/`, `platform/`, `dlcpacks/`, with `after_level.xml` /
   `before_level.xml` at the top) — the loader creates that skeleton
   automatically the first time any mod is enabled.

Declare the files your mod depends on in your README. The loader can install
and show the status of:

| File | Role |
|---|---|
| `onigiri.asi` | redirects the game to the onigiri folder |
| `nve.asi` | the NaturalVision Enhanced engine plugin (game root) — part of the NVE baseline or the stock-GTA V foundation |
| `ScriptHookV.dll` | the `.asi` plugin engine — required for `.asi` plugins to run |
| `xinput1_4.dll` | the Enhanced ASI loader — the loader installs this one, never `dinput8.dll` |
| `ScriptHookVDotNet.asi` | optional — required for .NET scripts in `scripts\` |

(`dinput8.dll` is the ASI loader for the old, legacy game — the loader only
uses it as a fallback when `xinput1_4.dll` is absent.)

If you bundle your own loader/ScriptHook builds, include the **Enhanced** ones
(`xinput1_4.dll`). If both versions are present, the loader picks the Enhanced
file and tells you the legacy one was skipped.

## 9. Pre-release checklist

- [ ] onigiri layout: `common/`, `platform/`, `dlcpacks/` (+ `after_level.xml` / `before_level.xml` at the top)
- [ ] Enhanced version of every file as the primary content; legacy content clearly under a `legacy`-labeled folder
- [ ] no `.oiv` files and no `openiv.asi` / `openrpf.asi`
- [ ] `xinput1_4.dll`, not `dinput8.dll` (if you ship an ASI loader)
- [ ] `.asi` plugins at the top level with their `.ini` beside; .NET scripts under `scripts/`
- [ ] README with explicit `onigiri/...` destination lines, and the pack name for any encrypted DLC
- [ ] no `originals` / `backup` folders; variants under `optionals/`
- [ ] DLC as `dlcpacks/<name>/dlc.rpf` with a `setup2.xml`
- [ ] minimal, localised edits to shared files
- [ ] archive named after the mod

## 10. Testing your mod in the loader

1. Add the archive with **Add archive** and give it a mod name.
2. **Enable** it and read the activity log — it records what was deployed, merged,
   skipped (including skipped legacy branches and `.oiv` files), and any conflicts.
3. Open **DLC packs** (bottom row) — your packs should appear as
   "listed in dlclist.xml".
4. **Disable** the mod and confirm the original game files were restored
   (the loader keeps backups and rolls them back).
5. **Reset all** (with its confirmation prompt) returns the loader to a fresh
   first-launch state for a clean re-test.

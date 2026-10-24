# Cocoon Save Converter (Game Pass → Steam)

A small Python script that converts your **Cocoon** save files from the **Game Pass / Microsoft Store** version into a format the **Steam** version accepts.

> Unofficial tool, not affiliated with the game's developers or publisher. Use it at your own risk and always keep backups.

## Why a conversion is needed

The two versions of the game store progress differently:

| | Game Pass | Steam |
|---|---|---|
| Progress save | plain JSON | **encrypted** |
| Settings save | plain JSON | plain JSON |
| Version check | `buildVersion` inside the save | `buildVersion` inside the save |

On Steam the game also compares the save's `buildVersion` with its own version. If they differ, **the save is silently discarded and a new one is created**. So the script does two things: it changes `buildVersion` to the one your Steam install uses, and it encrypts the progress save the way the Steam version expects.

## What you need

- **Python 3.8+** ([python.org](https://www.python.org/downloads/)). In the installer, **tick "Add python.exe to PATH"** on the first screen, otherwise the commands below won't work.
- The `pycryptodome` library (installed in the "First-time setup" below)
- Your two **Game Pass save files** (random names, no extension): one is the progress save, the other is the settings save. The script tells them apart by their contents.
- The **build version** of your Steam install (step 1 below).
- The game opened **at least once on Steam**, so its save folder exists.

## Step by step

### 1. Find your build version

The build version looks like `universe-2023-09-27-142621-r22586-WIN`. Use one of these:

- **From `build_info.txt`:** if your game folder contains a file called `build_info.txt`, open it and copy the value after `UNIVERSE_BUILD_VERSION:`. *This file is not guaranteed to exist in every install.*
- **From a save the game created itself (most reliable):** launch the game on Steam, play until it creates a save (or just reach the first autosave), then close it. Copy `UniverseProgressSave.far` from your Steam save folder (see step 5) **into the script's folder**. The script reads the version from it and offers it to you automatically.

> The build version changes whenever the game is updated. After an update, repeat this step and convert again.

### 2. Prepare

1. Close the game on both platforms.
2. Disable **Steam Cloud** for the game (Steam → game → Properties → General), otherwise it may overwrite the converted save.
3. Put `cocoon_save_converter.py` in an empty folder of your choice.

### 3. Copy your Game Pass saves

The Game Pass (Microsoft Store) version keeps its saves here:

```
%LOCALAPPDATA%\Packages\AnnapurnaInteractive.UniverseProject_c96c51jf6wkvm\SystemAppData\wgs\
```

Paste that path into the Windows Explorer address bar. Inside you will find sub-folders and index files; the save files are the ones with **long random names and no extension**. If you open one in a text editor, the right ones show readable JSON starting with `{"fileName":"UniverseProgressSave"...` (progress) or `{"fileName":"UniverseSettingsSave"...` (settings).

**Copy** (don't move) those two files into the same folder as the script. Keep their original names. Never edit or delete anything inside the `wgs` folder.

### 4. Run the script

#### First-time setup (only once)

1. **Open a terminal** (Command Prompt or PowerShell). The easiest way: press `Win + R`, type `cmd` and press Enter.
2. Check that Python is installed:
   ```
   python --version
   ```
   It should print something like `Python 3.12.x`. If Windows says "python is not recognized", try `py --version`; if that works, use `py` instead of `python` in every command below. If neither works, reinstall Python and tick "Add python.exe to PATH".
3. Install the library:
   ```
   pip install pycryptodome
   ```
   (or `py -m pip install pycryptodome`).

> Use a normal terminal. Do **not** type these commands into the Python interactive shell (the window with `>>>`) or IDLE.

#### Running it

1. **Open a terminal inside the script's folder.** Open the folder in Windows Explorer, click the address bar, type `cmd` and press Enter. A terminal opens already in that folder. (Alternatively, in the terminal use `cd "C:\path\to\the\folder"`.)
2. Run:
   ```
   python cocoon_save_converter.py
   ```
   The script asks for the build version when it needs it.

   Or pass the version directly:
   ```
   python cocoon_save_converter.py --build universe-2023-09-27-142621-r22586-WIN
   ```
3. *Alternative:* double-clicking `cocoon_save_converter.py` also works if Python is installed. A window opens, asks for the build version and stays open until you press Enter, so you can read the result.

The script will:

1. Find the progress and settings saves among the files in its folder.
2. Show a short summary (`gameState`, `maxGameState`, `secrets`, current `buildVersion`).
3. Ask for the build version, unless you passed `--build`.
4. Create `backup-<timestamp>/` with copies of your input files, checked byte by byte.
5. Create `output-<timestamp>/` with:
   - `UniverseProgressSave.far` — encrypted, `buildVersion` replaced
   - `UniverseSettingsSave.far` — plain JSON, `buildVersion` replaced
6. Read the generated files back to verify them. If verification fails, the output is deleted.

Your original files are never modified, and the script never reads or writes outside its own folder.

### 5. Copy the result to Steam

Your Steam save folder is:

```
%USERPROFILE%\AppData\LocalLow\GeometricInteractive\Cocoon\<your SteamID64>\
```

(`<Developer>` and `<Game>` are the names Unity uses for the game; the last folder is a long number.)

1. **Back up** the files already in that folder.
2. Copy the two files from `output-<timestamp>/` into it, replacing the existing ones. Keep the exact names.
3. Launch the game and load your save.

## Troubleshooting

- **The game starts a new game / ignores the save:** the `buildVersion` doesn't match your install. Re-check step 1 (the value stored in a save created by the game itself is the one that counts).
- **"python is not recognized" / "pip is not recognized":** Python isn't on your PATH. Try `py` instead of `python` (and `py -m pip` instead of `pip`), or reinstall Python with "Add python.exe to PATH" ticked.
- **"Missing library 'pycryptodome'":** run `pip install pycryptodome` again, using the same Python you use to run the script.
- **The window closes immediately when double-clicking:** run the script from a terminal instead, as shown above, so you can read any error message.
- **"No Game Pass progress save found":** the files aren't in the script's folder, or the progress file you copied isn't the real save.
- **"Already encrypted (Steam format)":** the progress file in the folder is a Steam save; this tool only converts Game Pass → Steam.
- **Save reverted after launching:** Steam Cloud overwrote it. Disable it and copy the files again.
- **Weird controls after converting:** the settings file may carry key bindings from the Xbox version. Delete the settings file from the Steam folder (the game recreates it) or reconfigure controls in-game.

## Good to know

- **Achievements are not transferred.** In the game's code, achievements are only unlocked by in-game events (collecting a moon, finishing a boss, and so on), never by reading the save. Loading a converted save will not unlock them.
- **The settings save is optional.** If it is missing, only the progress save is converted.
- **Platform differences:** the converted save comes from a different build or platform, so rarely something may behave oddly. Keep your originals.

## Technical details

- Progress save format on Steam: `[16-byte random IV][AES-256-CBC, PKCS7 padding, JSON in UTF-8]`.
- The key is derived with PBKDF2-HMAC-SHA1 (1000 iterations) from constants found in the game's own code. The IV is random per save and stored in the first 16 bytes of the file.
- Save JSON structure: `fileName`, `buildVersion`, `saveVersion`, `savedData` (`gameState`, `maxGameState`, `secrets`, `switches`).

## Limitations

- **Steam → Game Pass is not supported.**
- Requires Python; there is no standalone `.exe`.

---

> <sub>~~**Steam → Game Pass**~~ &nbsp;·&nbsp; *disabled, untested, not in use*</sub>
>
> <sub>*Kept here only as a record of what was found. Nothing in the script uses it.*</sub>
>
> - <sub>*Known from the game's code: the Game Pass save handler does not encrypt, so the file would have to be plain JSON.*</sub>
> - <sub>*Its `buildVersion` would have to match the Game Pass build, or the game discards the save.*</sub>
> - <sub>*Unknown: whether the Microsoft Store save container (`...\SystemAppData\wgs\`, with its index files) accepts a replaced file, and whether Xbox cloud sync overwrites or rejects it.*</sub>
> - <sub>*A commented-out sketch of the file conversion is at the bottom of `cocoon_save_converter.py`. Putting the result back into the `wgs` folder would be a manual, unverified step.*</sub>

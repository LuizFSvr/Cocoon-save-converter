#!/usr/bin/env python3
"""
Cocoon save converter: Game Pass -> Steam

The script only reads and writes inside ITS OWN FOLDER. It does not search the
rest of your computer and never touches the game's folders.

Quick usage (see README.md for the full guide):
  1. pip install pycryptodome
  2. Copy your two Game Pass save files (random names, no extension) into the
     same folder as this script.
  3. python cocoon_save_converter.py [--build universe-YYYY-MM-DD-HHMMSS-rNNNNN-WIN]
  4. Copy the files from the new "output-..." folder into your Steam save folder.

Every run creates:
  backup-<timestamp>/   copies of the input files, checked byte by byte
  output-<timestamp>/   UniverseProgressSave.far  (encrypted, buildVersion fixed)
                        UniverseSettingsSave.far  (plain JSON, buildVersion fixed)
"""
import sys, re, json, shutil, hashlib, time
from pathlib import Path

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    sys.exit("Missing library 'pycryptodome'. Install it with:\n  pip install pycryptodome")

PROGRESS_NAME = "UniverseProgressSave"
SETTINGS_NAME = "UniverseSettingsSave"
MAX_SIZE = 1_000_000  # saves are tiny; larger files are ignored
BUILD_RE = re.compile(r"^universe-\d{4}-\d{2}-\d{2}-\d{6}-r\d+-[A-Za-z]+$")

# Key: always the same (PBKDF2-SHA1, 1000 iterations, constants taken from the game's code).
# IV: NOT fixed. Every save has a random 16-byte IV stored at the start of the file.
PASSWORD = b"ThisKeyIsSuperSecret"
SALT = bytes([223, 194, 39, 5, 26, 48, 172, 58, 40, 168, 207, 104, 210, 180, 228, 249,
              216, 120, 67, 111, 14, 96, 34, 169, 195, 76, 178, 31, 184, 91, 112, 143])
KEY = hashlib.pbkdf2_hmac("sha1", PASSWORD, SALT, 1000, 32)


def decrypt(data: bytes) -> str:
    if len(data) < 32 or (len(data) - 16) % 16:
        raise ValueError("invalid size")
    iv, ct = data[:16], data[16:]
    return unpad(AES.new(KEY, AES.MODE_CBC, iv).decrypt(ct), 16).decode("utf-8")


def encrypt(text: str) -> bytes:
    iv = get_random_bytes(16)
    return iv + AES.new(KEY, AES.MODE_CBC, iv).encrypt(pad(text.encode("utf-8"), 16))


def read_save(path: Path):
    """Returns (json_object, was_encrypted) or None if the file is not a game save."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    for encrypted in (False, True):
        try:
            text = decrypt(raw) if encrypted else raw.decode("utf-8-sig")
            obj = json.loads(text)
        except Exception:
            continue
        if isinstance(obj, dict) and "savedData" in obj and "buildVersion" in obj:
            return obj, encrypted
    return None


def find_saves(folder: Path):
    """All game saves directly inside the folder (sub-folders are ignored)."""
    me = Path(__file__).resolve()
    found = []
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.resolve() == me or f.suffix.lower() in (".py", ".pyc", ".md"):
            continue
        if f.stat().st_size > MAX_SIZE:
            continue
        res = read_save(f)
        if res and res[0].get("fileName") in (PROGRESS_NAME, SETTINGS_NAME):
            found.append((f, res[0], res[1]))
    return found


def pick(items, label):
    if len(items) == 1:
        return items[0]
    print(f"More than one {label} file found:")
    for i, (f, o, _) in enumerate(items, 1):
        print(f"  {i}) {f.name}  buildVersion={o['buildVersion']}")
    while True:
        c = input("Which one? Number: ").strip()
        if c.isdigit() and 1 <= int(c) <= len(items):
            return items[int(c) - 1]


def get_build(args, suggested):
    value = None
    for i, a in enumerate(args):
        if a.startswith("--build="):
            value = a.split("=", 1)[1]
        elif a == "--build" and i + 1 < len(args):
            value = args[i + 1]
    if value is None:
        print("\nEnter the game version used by your Steam install (see README, step 1).")
        print("Example: universe-2023-09-27-142621-r22586-WIN")
        if suggested:
            print(f"Found in the Steam save placed in this folder: {suggested}")
            value = input("buildVersion [Enter = use the one above]: ").strip() or suggested
        else:
            value = input("buildVersion: ")
    value = value.strip().strip('"').strip("'")
    if not BUILD_RE.match(value):
        print(f"\nWarning: '{value}' does not look like a valid build version.")
        if input("Use it anyway? [y/N] ").strip().lower() != "y":
            sys.exit("Cancelled. Nothing was generated.")
    return value


def make_backup(folder: Path, files, stamp: str):
    backup = folder / f"backup-{stamp}"
    backup.mkdir()
    for f in files:
        dst = backup / f.name
        shutil.copy2(f, dst)
        if dst.read_bytes() != f.read_bytes():
            raise OSError(f"Failed to back up {f.name}.")
    return backup


def main():
    folder = Path(__file__).resolve().parent
    print(f"Working folder: {folder}\n")
    saves = find_saves(folder)
    progress = [s for s in saves if s[1]["fileName"] == PROGRESS_NAME and not s[2]]
    settings = [s for s in saves if s[1]["fileName"] == SETTINGS_NAME and not s[2]]
    steam_refs = [s for s in saves if s[1]["fileName"] == PROGRESS_NAME and s[2]]

    if not progress:
        if steam_refs:
            sys.exit("The progress save in this folder is already encrypted (Steam format).\n"
                     "This tool converts Game Pass -> Steam only. Nothing to do.")
        sys.exit("No Game Pass progress save found in this folder.\n"
                 "Copy your two Game Pass save files here (random names, no extension).")

    p_file, p_obj, _ = pick(progress, "progress save")
    d = p_obj["savedData"]
    print(f"Progress: {p_file.name}")
    print(f"gameState={d.get('gameState')}  maxGameState={d.get('maxGameState')}  "
          f"secrets={d.get('secrets')}  buildVersion={p_obj['buildVersion']}")

    s_file = s_obj = None
    if settings:
        s_file, s_obj, _ = pick(settings, "settings save")
        print(f"Settings: {s_file.name}  buildVersion={s_obj['buildVersion']}")
    else:
        print("Settings: no file found (only the progress save will be converted).")

    suggested = steam_refs[0][1]["buildVersion"] if steam_refs else None
    build = get_build(sys.argv[1:], suggested)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = make_backup(folder, [f for f in (p_file, s_file) if f], stamp)
    print(f"\nBackup created: {backup.name}/")

    out_dir = folder / f"output-{stamp}"
    out_dir.mkdir()
    try:
        p_obj["buildVersion"] = build
        p_out = out_dir / (PROGRESS_NAME + ".far")
        p_out.write_bytes(encrypt(json.dumps(p_obj, separators=(",", ":"))))
        chk = read_save(p_out)
        if not chk or not chk[1] or chk[0] != p_obj:
            raise ValueError("Verification of the generated progress save failed.")

        if s_obj is not None:
            s_obj["buildVersion"] = build
            s_out = out_dir / (SETTINGS_NAME + ".far")
            s_out.write_text(json.dumps(s_obj, separators=(",", ":")), encoding="utf-8")  # NOT encrypted
            chk = read_save(s_out)
            if not chk or chk[1] or chk[0] != s_obj:
                raise ValueError("Verification of the generated settings save failed.")
    except Exception:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise

    print(f"Output created: {out_dir.name}/")
    for f in sorted(out_dir.iterdir()):
        print(f"  {f.name}")
    print("\nCopy these files into your Steam save folder (the one named with your SteamID64),")
    print("after backing up the saves that are already there. Disable Steam Cloud while testing.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, EOFError) as e:
        print(f"\nError: {e}")
    if sys.stdin.isatty():
        input("\nPress Enter to exit.")


# =============================================================================
# NOT SUPPORTED / UNTESTED: Steam -> Game Pass
# -----------------------------------------------------------------------------
# What the game's code tells us (Xbox handler: ShouldEncryptSave = false):
#   - the Game Pass save must be PLAIN JSON (no encryption);
#   - its "buildVersion" must equal the Game Pass build, or the game discards it;
#   - the Steam progress save is encrypted, the Steam settings save is plain JSON.
# What is NOT known (could not be tested):
#   - whether Game Pass accepts a replaced file inside its save container
#     (Microsoft Store "wgs" folder with container index files), or whether
#     the Xbox cloud sync overwrites/rejects the change.
# The sketch below would do the file conversion only (placing the result into
# the Game Pass container would still be manual). Kept commented out on purpose.
#
# def steam_to_gamepass(folder, gamepass_build):
#     progress = folder / "UniverseProgressSave.far"      # encrypted (Steam)
#     settings = folder / "UniverseSettingsSave.far"      # plain JSON (Steam)
#     out_dir = folder / "output-gamepass"
#     out_dir.mkdir(exist_ok=True)
#
#     obj = json.loads(decrypt(progress.read_bytes()))
#     obj["buildVersion"] = gamepass_build
#     (out_dir / "UniverseProgressSave.json").write_text(
#         json.dumps(obj, separators=(",", ":")), encoding="utf-8")
#
#     if settings.exists():
#         s = json.loads(settings.read_text(encoding="utf-8-sig"))
#         s["buildVersion"] = gamepass_build
#         (out_dir / "UniverseSettingsSave.json").write_text(
#             json.dumps(s, separators=(",", ":")), encoding="utf-8")
#     # Manual step (unverified): copy the content of these files over the two
#     # randomly named Game Pass save files, keeping their original names. They live in
#     # %LOCALAPPDATA%\Packages\AnnapurnaInteractive.UniverseProject_c96c51jf6wkvm\SystemAppData\wgs\
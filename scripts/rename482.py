from pathlib import Path
import uuid

folder = Path("notariorum_output_482")

prefix = "ASG-NA-0482-01"
extension = ".jpg"

old_start = 586
old_end = 909
new_start = 289

# Run first with True to preview.
# Change to False after checking the printed output.
dry_run = False


def filename(number: int, suffix: int = 1) -> str:
    return f"{prefix}-{number:04d}-{suffix:02d}{extension}"


def target_for_old_number(old_number: int) -> tuple[int, int]:
    """
    Convert old single-image numbering into paired new numbering.

    0586 -> 0289-01
    0587 -> 0289-02
    0588 -> 0290-01
    0589 -> 0290-02
    ...
    0908 -> 0440-01
    0909 -> 0440-02
    """
    offset = old_number - old_start

    new_number = new_start + (offset // 2)
    new_suffix = 1 if offset % 2 == 0 else 2

    return new_number, new_suffix


renames = []

for old_number in range(old_start, old_end + 1):
    new_number, new_suffix = target_for_old_number(old_number)

    old_path = folder / filename(old_number, 1)
    new_path = folder / filename(new_number, new_suffix)

    renames.append((old_path, new_path))


# ---------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------

missing = [old_path for old_path, new_path in renames if not old_path.exists()]

if missing:
    print("Missing source files:")
    for path in missing:
        print(f"  {path.name}")
    raise FileNotFoundError("Some source files are missing. No files were renamed.")


source_paths = {old_path.resolve() for old_path, new_path in renames}

collisions = [
    new_path
    for old_path, new_path in renames
    if new_path.exists() and new_path.resolve() not in source_paths
]

if collisions:
    print("These target files already exist and are not part of the rename sequence:")
    for path in collisions:
        print(f"  {path.name}")
    raise FileExistsError("Target collision detected. No files were renamed.")


# ---------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------

for old_path, new_path in renames:
    print(f"{old_path.name}  →  {new_path.name}")


# ---------------------------------------------------------------------
# Rename using temporary filenames first
# ---------------------------------------------------------------------

if not dry_run:
    print("\nRenaming files...")

    temp_renames = []

    # Stage 1: rename all source files to temporary filenames
    for old_path, final_path in renames:
        temp_path = old_path.with_name(
            f"__TEMP_RENAME__{uuid.uuid4().hex}{old_path.suffix}"
        )
        old_path.rename(temp_path)
        temp_renames.append((temp_path, final_path))

    # Stage 2: rename temporary files to final filenames
    for temp_path, final_path in temp_renames:
        if final_path.exists():
            raise FileExistsError(f"Target already exists: {final_path.name}")

        temp_path.rename(final_path)

    print("Done.")
from pathlib import Path
import uuid

folder = Path("00108")

prefix = "ASG-SG-00108-01"
extension = ".jpg"

# Run first with True to preview.
# Change to False after checking the printed output.
dry_run = False


def filename(number: int, suffix: int = 1) -> str:
    return f"{prefix}-{number:04d}-{suffix:02d}{extension}"


def pair_target(old_number: int, old_start: int, new_start: int) -> tuple[int, int]:
    """
    Convert old single-image numbering into paired new numbering.

    Example:
    old_start=5, new_start=3

    0005 -> 0003-01
    0006 -> 0003-02
    0007 -> 0004-01
    0008 -> 0004-02
    """
    offset = old_number - old_start

    new_number = new_start + (offset // 2)
    new_suffix = 1 if offset % 2 == 0 else 2

    return new_number, new_suffix


renames = []

# ---------------------------------------------------------------------
# Section 1:
# 0005-01 -> 0003-01
# 0006-01 -> 0003-02
# ...
# 0034-01 -> 0017-02
# ---------------------------------------------------------------------

for old_number in range(5, 35):
    new_number, new_suffix = pair_target(
        old_number=old_number,
        old_start=5,
        new_start=3,
    )

    renames.append(
        (
            folder / filename(old_number, 1),
            folder / filename(new_number, new_suffix),
        )
    )


# ---------------------------------------------------------------------
# Section 2:
# Target numbers 0018 through 0038 are skipped.
#
# 0035-01 -> 0039-01
# 0036-01 -> 0039-02
# ...
# 0055-01 -> 0049-01
# 0056-01 -> 0049-02
# ---------------------------------------------------------------------

for old_number in range(35, 57):
    new_number, new_suffix = pair_target(
        old_number=old_number,
        old_start=35,
        new_start=39,
    )

    renames.append(
        (
            folder / filename(old_number, 1),
            folder / filename(new_number, new_suffix),
        )
    )


# ---------------------------------------------------------------------
# Section 3:
# Special four-image group:
#
# 0057-01 -> 0049-03
# 0058-01 -> 0049-04
# ---------------------------------------------------------------------

renames.append(
    (
        folder / filename(57, 1),
        folder / filename(49, 3),
    )
)

renames.append(
    (
        folder / filename(58, 1),
        folder / filename(49, 4),
    )
)


# ---------------------------------------------------------------------
# Section 4:
# 0059-01 -> 0050-01
# 0060-01 -> 0050-02
# 0061-01 -> 0051-01
# 0062-01 -> 0051-02
# ...
# 0088-01 -> 0064-02
# ---------------------------------------------------------------------

for old_number in range(59, 89):
    new_number, new_suffix = pair_target(
        old_number=old_number,
        old_start=59,
        new_start=50,
    )

    renames.append(
        (
            folder / filename(old_number, 1),
            folder / filename(new_number, new_suffix),
        )
    )


# ---------------------------------------------------------------------
# Section 5:
# Target numbers 0065 through 0086 are skipped.
#
# 0089-01 -> 0087-01
# 0090-01 -> 0087-02
# 0091-01 -> 0088-01
# ...
# 0184-01 -> 0134-02
# ---------------------------------------------------------------------

for old_number in range(89, 185):
    new_number, new_suffix = pair_target(
        old_number=old_number,
        old_start=89,
        new_start=87,
    )

    renames.append(
        (
            folder / filename(old_number, 1),
            folder / filename(new_number, new_suffix),
        )
    )


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
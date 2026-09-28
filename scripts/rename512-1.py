from pathlib import Path

# Folder containing the files
folder = Path("notariorum_output_512")

# File-name constants
prefix = "ASG-NA-0512-01"

# Original numbering range
old_start = 8
old_end = 562

# New numbering starts at 0003
new_start = 3

# Set to False once you have checked the preview
dry_run = False


def make_new_name(old_number: int, original_suffix: str, extension: str) -> str:
    """
    Convert an old file number into the new paired numbering system.

    Example:
    0008 -> 0003-01
    0009 -> 0003-02
    0010 -> 0004-01
    0011 -> 0004-02
    """

    offset = old_number - old_start

    new_number = new_start + (offset // 2)
    new_suffix = 1 if offset % 2 == 0 else 2

    return f"{prefix}-{new_number:04d}-{new_suffix:02d}{extension}"


for path in folder.iterdir():
    if not path.is_file():
        continue

    stem = path.stem
    extension = path.suffix

    parts = stem.split("-")

    # Expected pattern:
    # ASG-NA-0512-01-0008-01
    if len(parts) != 6:
        continue

    if "-".join(parts[:4]) != prefix:
        continue

    try:
        old_number = int(parts[4])
        original_suffix = parts[5]
    except ValueError:
        continue

    if old_number < old_start or old_number > old_end:
        continue

    new_name = make_new_name(old_number, original_suffix, extension)
    new_path = path.with_name(new_name)

    print(f"{path.name}  →  {new_name}")

    if not dry_run:
        if new_path.exists():
            raise FileExistsError(f"Cannot rename {path.name}: {new_name} already exists")

        path.rename(new_path)
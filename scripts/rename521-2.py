from pathlib import Path
import uuid

folder = Path("notariorum_output_512")

prefix = "ASG-NA-0512-01"

start_number = 21
start_suffix = 1

end_number = 238
end_suffix = 2

# Set to True first if you want only a preview
dry_run = False


def filename(number: int, suffix: int, extension: str = ".jpg") -> str:
    return f"{prefix}-{number:04d}-{suffix:02d}{extension}"


def previous_slot(number: int, suffix: int) -> tuple[int, int]:
    """
    Move one slot backward in the paired numbering system.

    0021-01 -> 0020-02
    0021-02 -> 0021-01
    0022-01 -> 0021-02
    0022-02 -> 0022-01
    """
    if suffix == 1:
        return number - 1, 2
    else:
        return number, 1


# Build the list of source files in order
sources = []

for number in range(start_number, end_number + 1):
    for suffix in (1, 2):
        if number == start_number and suffix < start_suffix:
            continue
        if number == end_number and suffix > end_suffix:
            continue

        old_path = folder / filename(number, suffix)
        new_number, new_suffix = previous_slot(number, suffix)
        new_path = folder / filename(new_number, new_suffix)

        sources.append((old_path, new_path))


# Check that all source files exist
missing = [old_path for old_path, new_path in sources if not old_path.exists()]

if missing:
    print("Missing source files:")
    for path in missing:
        print(f"  {path.name}")
    raise FileNotFoundError("Some source files are missing. No files were renamed.")


# Check for dangerous target collisions outside the rename set
source_paths = {old_path.resolve() for old_path, new_path in sources}

collisions = [
    new_path
    for old_path, new_path in sources
    if new_path.exists() and new_path.resolve() not in source_paths
]

if collisions:
    print("These target files already exist and are not part of the rename sequence:")
    for path in collisions:
        print(f"  {path.name}")
    raise FileExistsError("Target collision detected. No files were renamed.")


# Preview
for old_path, new_path in sources:
    print(f"{old_path.name}  →  {new_path.name}")


if not dry_run:
    print("\nRenaming files...")

    temp_renames = []

    # Stage 1: rename sources to temporary names
    for old_path, final_path in sources:
        temp_path = old_path.with_name(
            f"__TEMP_RENAME__{uuid.uuid4().hex}{old_path.suffix}"
        )
        old_path.rename(temp_path)
        temp_renames.append((temp_path, final_path))

    # Stage 2: rename temporary names to final names
    for temp_path, final_path in temp_renames:
        if final_path.exists():
            raise FileExistsError(f"Target already exists: {final_path.name}")

        temp_path.rename(final_path)

    print("Done.")
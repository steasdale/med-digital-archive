from pathlib import Path
import re
import uuid

# Folder containing the files
folder = Path("temp")

# Preview changes first.
# Change to False after confirming the displayed mappings.
DRY_RUN = False

SOURCE_START = 2
SOURCE_END = 289
TARGET_START = 98

# These numbers are absent from the source sequence.
EXCLUDED_SOURCE_NUMBERS = {135, 136}

pattern = re.compile(
    r"^ASG-SG-36857-01-(\d{4})-01(?P<extension>\.[^.]+)?$",
    re.IGNORECASE,
)

if not folder.is_dir():
    raise FileNotFoundError(
        f"Folder not found: {folder.resolve()}"
    )

# Index all matching files by their four-digit source number.
files_by_number = {}

for path in folder.iterdir():
    if not path.is_file():
        continue

    match = pattern.fullmatch(path.name)

    if not match:
        continue

    source_number = int(match.group(1))

    if source_number in files_by_number:
        raise RuntimeError(
            f"More than one file matches source number "
            f"{source_number:04d}:\n"
            f"  {files_by_number[source_number].name}\n"
            f"  {path.name}"
        )

    files_by_number[source_number] = path

# Build the ordered source sequence, omitting 0135 and 0136.
source_numbers = [
    number
    for number in range(SOURCE_START, SOURCE_END + 1)
    if number not in EXCLUDED_SOURCE_NUMBERS
]

rename_operations = []
missing_numbers = []

for position, source_number in enumerate(source_numbers):
    source = files_by_number.get(source_number)

    if source is None:
        missing_numbers.append(source_number)
        continue

    # Every pair receives the same target number.
    target_number = TARGET_START + position // 2

    # Alternate between 01 and 02.
    target_part = position % 2 + 1

    extension = source.suffix

    destination_name = (
        f"ASG-SG-36857-01-"
        f"{target_number:04d}-"
        f"{target_part:02d}"
        f"{extension}"
    )

    destination = folder / destination_name
    rename_operations.append((source, destination))

if not rename_operations:
    print("No matching files were found.")
    raise SystemExit

# Report missing expected files.
if missing_numbers:
    print("Warning: the following expected source files were not found:")

    for number in missing_numbers:
        print(f"  ASG-SG-36857-01-{number:04d}-01")

    print()

# Ensure that target filenames are unique.
destination_paths = [
    destination.resolve()
    for _, destination in rename_operations
]

if len(destination_paths) != len(set(destination_paths)):
    raise RuntimeError(
        "The renaming pattern produces duplicate destination filenames."
    )

# Destination names may currently belong to source files included in this
# operation. Unrelated existing destination files must not be overwritten.
source_paths = {
    source.resolve()
    for source, _ in rename_operations
}

for source, destination in rename_operations:
    if destination.exists() and destination.resolve() not in source_paths:
        raise FileExistsError(
            f"Cannot rename {source.name}:\n"
            f"{destination.name} already exists and is not part of "
            f"the renaming operation."
        )

print("Planned renaming:\n")

for source, destination in rename_operations:
    print(f"{source.name} --> {destination.name}")

print(f"\nTotal files found: {len(rename_operations)}")
print(f"Total files expected: {len(source_numbers)}")

if DRY_RUN:
    print(
        "\nPreview only. Change DRY_RUN to False to perform the renaming."
    )
    raise SystemExit

# Stage 1: rename every source file to a unique temporary filename.
# This prevents collisions because some destination names overlap with
# existing source names.
temporary_operations = []

try:
    for source, destination in rename_operations:
        temporary_path = folder / (
            f".rename-{uuid.uuid4().hex}{source.suffix}"
        )

        source.rename(temporary_path)
        temporary_operations.append((temporary_path, destination))

    # Stage 2: assign the final filenames.
    for temporary_path, destination in temporary_operations:
        temporary_path.rename(destination)

except Exception:
    print(
        "\nAn error occurred. Some files may have temporary names "
        "beginning with '.rename-'."
    )
    raise

print(f"\nSuccessfully renamed {len(rename_operations)} files.")
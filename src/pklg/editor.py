import os
import subprocess
import tempfile

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from .kicad import PartInfo


def edit_part_info(
    part: PartInfo, footprint: str, symbol_name: str, target_library: str
) -> tuple[PartInfo, str] | None:
    """Open part info in $EDITOR as TOML. Returns updated (PartInfo, footprint) or None if aborted."""
    content = f"""\
# Review and edit before adding to library.
# Lines starting with # are ignored.
# Save and close to continue. Delete all content to abort.

symbol_name = "{symbol_name}"
target_library = "{target_library}"

[part]
name = "{part.name}"
package = "{part.package}"
manufacturer = "{part.manufacturer}"
mpn = "{part.mpn}"
datasheet = "{part.datasheet}"
description = "{part.description}"
footprint = "{footprint}"

[distributor]
distributor_1_link = "{part.distributor_1_link}"
distributor_1_part_number = "{part.distributor_1_part_number}"
distributor_2_link = "{part.distributor_2_link}"
distributor_2_part_number = "{part.distributor_2_part_number}"
"""

    editor = os.environ.get("EDITOR", "vi")

    with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as f:
        f.write(content)
        tmp_path = f.name

    try:
        subprocess.run([editor, tmp_path], check=True)

        with open(tmp_path, "r") as f:
            edited = f.read()

        # Strip comments
        lines = [line for line in edited.splitlines() if not line.strip().startswith("#")]
        stripped = "\n".join(lines).strip()

        if not stripped:
            return None

        parsed = tomllib.loads(stripped)

        part_data = parsed.get("part", {})
        dist_data = parsed.get("distributor", {})
        edited_footprint = part_data.pop("footprint", footprint)

        updated_part = PartInfo(
            name=part_data.get("name", part.name),
            package=part_data.get("package", part.package),
            manufacturer=part_data.get("manufacturer", part.manufacturer),
            mpn=part_data.get("mpn", part.mpn),
            datasheet=part_data.get("datasheet", part.datasheet),
            description=part_data.get("description", part.description),
            distributor_1_link=dist_data.get("distributor_1_link", part.distributor_1_link),
            distributor_1_part_number=dist_data.get("distributor_1_part_number", part.distributor_1_part_number),
            distributor_2_link=dist_data.get("distributor_2_link", part.distributor_2_link),
            distributor_2_part_number=dist_data.get("distributor_2_part_number", part.distributor_2_part_number),
        )

        return updated_part, edited_footprint
    finally:
        os.unlink(tmp_path)

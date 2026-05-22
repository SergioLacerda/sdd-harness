"""
Binary Artifact Inspector: Quick diagnostic tool for SDD v3.0 MessagePack artifacts.
"""

import json
import sys
from pathlib import Path

try:
    import msgpack
except ImportError:
    msgpack = None


def inspect(file_path: Path) -> None:
    """Read and display metadata/structure of a compiled SDD artifact"""
    if not msgpack:
        print("ERROR: msgpack not installed. Run 'pip install msgpack'")  # noqa: T201
        return

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")  # noqa: T201
        return

    print(f"🔍 Inspecting: {file_path.name}")  # noqa: T201
    print("=" * 40)  # noqa: T201

    try:
        with open(file_path, "rb") as f:
            data = msgpack.unpackb(f.read(), raw=False)

        # Print basic stats
        print(f"Keys found: {list(data.keys())}")  # noqa: T201

        if "metadata" in data:
            print(f"Metadata: {json.dumps(data['metadata'], indent=2)}")  # noqa: T201

        if "items" in data:
            items = data["items"]
            print(f"Total Items: {len(items)}")  # noqa: T201
            types: dict[str, int] = {}
            for it in items:
                t = it.get("type", "unknown")
                types[t] = types.get(t, 0) + 1
            print(f"Breakdown: {types}")  # noqa: T201

        if "string_pool" in data:
            print(f"String Pool Size: {len(data['string_pool'])} unique strings")  # noqa: T201

    except Exception as e:
        print(f"ERROR: Failed to decode msgpack: {e}")  # noqa: T201


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bin_inspector.py <path_to_msgpack_file>")  # noqa: T201
    else:
        inspect(Path(sys.argv[1]))

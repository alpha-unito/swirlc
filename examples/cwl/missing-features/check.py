"""Check the default job's cwltool result manifest."""

import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


def main():
    result = json.loads(Path(sys.argv[1]).read_text())
    assert result["ok"] is True
    assert result["code"] == 1  # Accepted by successCodes, not silently treated as zero.
    file = result["report"]
    path = Path(file["path"]) if "path" in file else Path(unquote(urlsplit(file["location"]).path))
    assert json.loads(path.read_text()) == {
        "text": "one:seed", "meta": "meta", "messages": ["generated"], "marker": "expected",
    }
    print("PASS")


if __name__ == "__main__":
    main()

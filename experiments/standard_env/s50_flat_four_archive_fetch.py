"""R archive transport: pin provider metadata AND independently hash ZIP bytes.

GitHub token stays in gh environment, no Java/Node or S producer is executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import subprocess
import zipfile
from pathlib import Path


def fetch(repo: str, run_id: int, head: str, artifact: int,
          expected: str, destination: Path) -> dict:
    def api(path: str) -> dict:
        return json.loads(subprocess.check_output(["gh", "api", f"repos/{repo}/{path}"]))
    run = api(f"actions/runs/{run_id}")
    meta = api(f"actions/artifacts/{artifact}")
    if not (run["head_sha"] == head and run["run_attempt"] == 1
            and meta["workflow_run"]["id"] == run_id and not meta["expired"]
            and meta["digest"] == "sha256:" + expected):
        raise ValueError("provider run/head/artifact identity mismatch")
    destination.mkdir()
    archive = destination / "provider-original.zip"
    with archive.open("xb") as out:
        subprocess.run(["gh", "api", f"repos/{repo}/actions/artifacts/{artifact}/zip"],
                       stdout=out, check=True)
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("downloaded provider ZIP bytes differ from pinned digest")
    extracted = destination / "extracted"
    extracted.mkdir()
    with zipfile.ZipFile(archive) as source:
        names = set()
        for item in source.infolist():
            path = Path(item.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in item.filename
                    or item.filename in names or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError("unsafe archive path/type/duplicate")
            names.add(item.filename)
        source.extractall(extracted)
    result = {"run_id": run_id, "head": head, "run_conclusion": run["conclusion"],
              "artifact_id": artifact, "provider_digest": meta["digest"],
              "independent_zip_sha256": actual, "archive_members": len(names)}
    (destination / "r-transport.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True)
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--artifact", type=int, required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--destination", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(fetch(a.repo, a.run_id, a.head, a.artifact, a.sha256, a.destination)))


if __name__ == "__main__":
    main()

# Release packaging and PyPI publishing

All maintained source code and the canonical skill live in this repository. End users install the CLI from PyPI or public GitHub release assets, so they do not need a checkout. FFmpeg and FFprobe are supplied by a platform-wheel dependency; model weights are installed separately. PyPI installs dependencies according to package metadata; the release runtime constraints reproduce versions exported from `uv.lock`.

## Build and validate

From a clean checkout:

```bash
uv run --locked pytest
uv run --locked ruff check .
python scripts/build_release.py /tmp/local-transcription-release
uvx --from twine==7.0.0 twine check --strict /tmp/local-transcription-release/*.whl /tmp/local-transcription-release/*.tar.gz
```

The builder creates a wheel, source archive, `runtime-constraints.txt`, a self-contained `local-transcription-skill.zip`, and `SHA256SUMS`. It refuses an existing output directory. Only the wheel and source archive are uploaded to PyPI. The source archive has an explicit allowlist; personal media, model weights, caches, and transcripts are excluded. The skill archive includes only its entry point and Markdown references.

Before publishing, install the wheel into a fresh uv tool environment and verify the command and native imports outside the checkout. Check both ordinary dependency resolution and the supplied runtime constraints. Validate the skill and source archive, and ensure README links work on PyPI. Runtime behavior changes also require the relevant speech checks.

## First publication: Trusted Publishing

In the owner's PyPI account, open https://pypi.org/manage/account/publishing/ and register a pending GitHub publisher with:

| Field | Value |
|---|---|
| PyPI project name | `local-transcription` |
| GitHub owner | `ihoru` |
| Repository | `local-transcription` |
| Workflow filename | `publish.yml` |
| Environment | `pypi` |

The owner completes PyPI login and any required account verification. No API token is committed or stored in GitHub. The publishing job requests a short-lived OIDC identity restricted by PyPI's configured repository, workflow, and environment. The build job has no publishing permission.

Commit and push the reviewed release source. After the publisher is registered, publish a GitHub release targeting that exact commit. A draft release can hold the assets until account setup is complete; publishing it triggers the workflow. Alternatively, use `gh workflow run publish.yml --repo ihoru/local-transcription --ref main` for a manual publication or retry, but do not also publish a new GitHub release for the same successful upload. The workflow tests and builds the exact selected commit before uploading its wheel and source archive. Successful first publication creates the PyPI project and converts the pending publisher into a normal publisher. Verify the PyPI version and install from the actual index before announcing success.

## Subsequent releases

Update `pyproject.toml`, `src/local_transcription/__init__.py`, and the version commands in README and the skill installation reference together; regenerate `uv.lock`. Commit and push, then publish a GitHub release targeting that exact commit. A published release triggers the same PyPI workflow. Do not also dispatch it manually for that version: PyPI rejects duplicate uploads. Verify that the release tag matches the package version before publishing.

Never replace existing published distribution files. Make a new version for corrections. GitHub hosts the skill archive and optional exact-runtime constraints alongside the Python distributions; download and verify the release checksums after upload. A public repository does not by itself select an open-source license for the code.

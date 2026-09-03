# Release packaging

All maintained source code and the canonical skill live in this repository. End users install release assets, so they do not need a checkout. The release wheel contains the CLI package; its Python dependencies are constrained to runtime versions exported from `uv.lock`. FFmpeg and model weights are installed separately.

From a clean checkout, run tests and build into a new directory:

```bash
uv run --locked pytest
uv run --locked ruff check .
python scripts/build_release.py /tmp/local-transcription-release
```

The builder creates a wheel, `runtime-constraints.txt`, a self-contained `local-transcription-skill.zip`, and `SHA256SUMS`. It refuses an existing output directory. The constraints exclude development tools and local source paths. The skill archive includes only its entry point and Markdown references. Personal media, model weights, and transcripts are never packaged.

Before publishing, install the wheel with the supplied constraints into a fresh uv tool environment, verify `--version` and `doctor`, and run a speech smoke check from outside the checkout. Validate the extracted skill, including all reference links. Commit and push the reviewed source, then publish the assets on a private GitHub release targeting that exact commit. Download the uploaded assets and verify their checksums.

For a new version, update `pyproject.toml`, `src/local_transcription/__init__.py`, and the release/version commands in README and the skill's installation reference together; regenerate `uv.lock`. Never replace assets on an existing published version. Access to private release assets requires repository access; distributing the skill does not grant that access.

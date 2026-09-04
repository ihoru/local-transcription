# Install the local-transcription skill

This skill guides your AI coding agent through local audio/video transcription and proofreading, producing raw and proofread TXT/SRT files.

## Install through your coding agent

Copy this prompt into your AI coding agent:

```text
Install the local-transcription skill for my coding agent by following https://github.com/ihoru/local-transcription/blob/main/skills/local-transcription/INSTALL.md
```

Installation adds only the skill and its supporting documents. The skill handles CLI and model setup when you first ask it to transcribe a recording.

## Instructions for the installing agent

1. Identify the current agent's skill installation directory. For Codex, use `~/.agents/skills/`. For another agent, use its supported skill directory. Inspect any existing `local-transcription` directory or symlink before making changes; reuse a complete installation and preserve local modifications.
2. Download `local-transcription-skill.zip` and `SHA256SUMS` from the [v0.1.4 release](https://github.com/ihoru/local-transcription/releases/tag/v0.1.4), the release documented in the [runtime installation reference](references/install.md). Verify the ZIP's SHA-256 digest against its entry in `SHA256SUMS` before extracting it. If the assets are unavailable or verification fails, report the failure.
3. Extract the verified archive into the skill installation directory. The archive already contains a `local-transcription/` folder; avoid adding another nesting level. Install `SKILL.md` and the entire `references/` directory together. An existing maintained checkout can instead use the symlink alternative below.
4. Confirm that the installed `local-transcription/SKILL.md` and `references/install.md`, `references/usage.md`, `references/proofreading.md`, and `references/summary.md` are present and readable. Report the installation location and how to invoke the skill. Complete installation here; CLI installation, model downloads, and transcription belong to first use.

## Install manually

### From a release archive

Download `local-transcription-skill.zip` and `SHA256SUMS` from the [v0.1.4 release](https://github.com/ihoru/local-transcription/releases/tag/v0.1.4). Verify the archive's SHA-256 checksum against its entry in `SHA256SUMS`, then extract it into your agent's skill directory (`~/.agents/skills/` for Codex). Inspect an existing destination before replacing it.

The resulting layout must contain `local-transcription/SKILL.md` and `local-transcription/references/`, with all four reference documents listed above. You can discard the downloaded archive after installation.

### From an existing checkout

For Codex, run these commands from the repository root after checking that `~/.agents/skills/local-transcription` is available:

```sh
mkdir -p "$HOME/.agents/skills"
ln -s "$PWD/skills/local-transcription" "$HOME/.agents/skills/local-transcription"
```

Keep the checkout in place: the symlink uses it as the source of truth, and pulling updates also updates the installed skill. A correct existing symlink needs no replacement.

## Use the installed skill

Installation and transcription are separate requests. In Codex, for example:

```text
Use $local-transcription to transcribe /absolute/path/to/recording.mp4 and produce raw and proofread TXT and SRT files.
```

On first use, the skill locates or installs the CLI and prepares missing models. It completes all four transcript files, then offers a practical summary. Audio inference runs locally; the invoking agent reads the transcript into its context. See the [runtime installation reference](references/install.md) for setup requirements.

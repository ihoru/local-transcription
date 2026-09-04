"""Ship native macOS executables in correctly tagged platform wheels."""

import importlib.util
from pathlib import Path
import platform

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if platform.system() != "Darwin":
            return
        spec = importlib.util.spec_from_file_location(
            "build_macos_ffmpeg", Path(self.root) / "scripts/build_macos_ffmpeg.py"
        )
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        bundle = builder.build(self.root)
        build_data["pure_python"] = False
        build_data["tag"] = f"py3-none-macosx_13_0_{platform.machine()}"
        if version == "editable":
            # Editable installs import source files, so include the native tools there.
            import shutil
            shutil.copytree(bundle, Path(self.root) / "src/local_transcription/_bin",
                            dirs_exist_ok=True)
        else:
            build_data["force_include"][str(bundle)] = "local_transcription/_bin"

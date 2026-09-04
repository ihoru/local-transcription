# Model sources and third-party notices

Models are downloaded or imported during explicit setup and stored outside Git. Their hashes live in `local_transcription.models`; downloads that fail verification are not installed. The default registry uses these existing local-pipeline assets:

| Component | Source | Purpose |
|---|---|---|
| Whisper large-v3, CTranslate2 conversion | [Systran/faster-whisper-large-v3](https://huggingface.co/Systran/faster-whisper-large-v3), revision `edaa852ec7e145841d8ffdb056a99866b5f0a478` | Multilingual transcription |
| Pyannote segmentation 3.0 ONNX | [Sherpa-ONNX model release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-segmentation-models), converted from [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) | Speech/speaker segmentation |
| WeSpeaker VoxCeleb ResNet34 LM ONNX | [Sherpa-ONNX speaker model release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models) | Voice embeddings |

Whisper and faster-whisper publish MIT-licensed code. The downloaded Pyannote ONNX archive includes an MIT notice, copyright 2022 CNRS. Sherpa-ONNX and WeSpeaker publish Apache-2.0-licensed code. Model weights, training datasets, and conversion artifacts can carry their own terms: consult the linked upstream distributions before redistributing weights or using them under additional constraints. This repository does not bundle those weights or grant rights to training data.

The earlier experimental Reverb model is not part of the default registry or runtime. Its local distribution identifies a non-commercial restriction; the reusable pipeline does not require it.

## Pyannote archive notice

MIT License

Copyright (c) 2022 CNRS

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Packaged media tools

On Linux and Windows, the pinned [ffmpeg-binaries-compat 1.1.0](https://pypi.org/project/ffmpeg-binaries-compat/1.1.0/) dependency supplies FFmpeg/FFprobe executables as separate platform wheels. Its Python wrapper is MIT-licensed; FFmpeg binaries have their own license terms. The inspected Linux wheel contains FFmpeg 6.0 static binaries from John Van Sickle and includes `GPLv3.txt` and its build readme. See the [upstream package](https://github.com/MatteoH2O1999/ffmpeg-binaries) and [FFmpeg licensing information](https://ffmpeg.org/legal.html). Linux/Windows installations reference this dependency instead of repackaging its binaries. System FFmpeg takes precedence when available.

macOS wheels bundle separate native FFmpeg 9.0.1 executables built from the [official source archive](https://ffmpeg.org/releases/ffmpeg-9.0.1.tar.xz), pinned to SHA-256 `cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635`. These builds disable external library autodetection, GPL, nonfree, version3, and networking. They statically link FFmpeg libraries and depend only on macOS system libraries. The resulting FFmpeg executables use LGPL-2.1-or-later. Each Mac wheel carries the full corresponding unmodified source archive, LGPL notice, build options, and rebuild script in `local_transcription/_bin/`. The application's Python code invokes these tools as separate processes. See `scripts/build_macos_ffmpeg.py` for the pinned build recipe.

The WeSpeaker download is `wespeaker_en_voxceleb_resnet34_LM.onnx` in the upstream speaker model release. It is stored locally as `wespeaker-voxceleb-resnet34.onnx` for compatibility with existing installations; its SHA-256 remains `e9848563da86f263117134dfd7ad63c92355b37de492b55e325400c9d9c39012`.

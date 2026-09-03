# Model sources and third-party notices

Models are downloaded or imported during explicit setup and stored outside Git. Their hashes live in `local_transcription.models`; downloads that fail verification are not installed. The default registry uses these existing local-pipeline assets:

| Component | Source | Purpose |
|---|---|---|
| Whisper large-v3, CTranslate2 conversion | [Systran/faster-whisper-large-v3](https://huggingface.co/Systran/faster-whisper-large-v3), revision `edaa852ec7e145841d8ffdb056a99866b5f0a478` | Multilingual transcription |
| Pyannote segmentation 3.0 ONNX | [Sherpa-ONNX model release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-segmentation-models), converted from [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0) | Speech/speaker segmentation |
| WeSpeaker VoxCeleb ResNet34 ONNX | [Sherpa-ONNX speaker model release](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models) | Voice embeddings |

Whisper and faster-whisper publish MIT-licensed code. The downloaded Pyannote ONNX archive includes an MIT notice, copyright 2022 CNRS. Sherpa-ONNX and WeSpeaker publish Apache-2.0-licensed code. Model weights, training datasets, and conversion artifacts can carry their own terms: consult the linked upstream distributions before redistributing weights or using them under additional constraints. This repository does not bundle those weights or grant rights to training data.

The earlier experimental Reverb model is not part of the default registry or runtime. Its local distribution identifies a non-commercial restriction; the reusable pipeline does not require it.

## Pyannote archive notice

MIT License

Copyright (c) 2022 CNRS

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

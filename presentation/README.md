# ScamShield AI presentation builder

`build.py` produces an editable 10-slide PowerPoint, a 180-second English-narrated
720p MP4, and a combined ZIP. Visuals illustrate project workflows and architecture;
they are **not a live website or deployment recording**. Test counts describe the
recorded development checks, not tests run by this media builder.

## Build locally

Use Python 3.11+, Linux DejaVu fonts under `/usr/share/fonts/truetype/dejavu/`,
and install the separate presentation dependencies:

```sh
python -m pip install --target .presentation-tools -r presentation/requirements.txt
```

Supply three authorized English narration recordings at:

- `presentation/audio/part-1.mp3`: overview, problem and architecture (slides 1–3)
- `presentation/audio/part-2.mp3`: scanners and family privacy (slides 4–7)
- `presentation/audio/part-3.mp3`: deployment, validation and roadmap (slides 8–10)

Each segment is padded or modestly accelerated to 60 seconds. Keep recordings near
one minute each. The generated version uses AI-generated narration. Narration
synthesis is not part of this script; do not interpret an absent audio file as a
configured speech service.

```sh
PYTHONPATH=.presentation-tools python presentation/build.py
```

Outputs appear under `presentation/deliverables/`. The builder uses the FFmpeg
binary supplied by `imageio-ffmpeg`; review installation/download requirements for
your environment. Review all outputs before presenting. Cloud hosting, live SMTP,
provider inference, model installation and physical-camera verification are not
performed by the builder.

## Distribution

Generated audio, frames, media archives and local tool installations are ignored
by Git. MP4 and PPTX files are distributed through Google Drive separately, not
committed to the repository. Do not commit private Drive links or credentials.
No application runtime code or database schema is changed by this presentation.

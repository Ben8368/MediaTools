# MediaTools Workflow

> [中文版](./WORKFLOW.zh.md)

Recommended production pipeline: `yt-dlp + subtitle analysis + FFmpeg slicing + workbench review`.

## 1. Launch

```powershell
python app.py
```

- Workstation: `http://127.0.0.1:7860`
- API docs: `http://127.0.0.1:7860/docs`

Set `API_SECRET_KEY` before binding to non-localhost.

## 2. Workspace

Workspace state stored in `runtime/workspace.json`. Recommended structure:

```
projects/default/
├── downloads/      # Videos and original subtitles
├── subtitles/      # Analyzable subtitles
├── analysis/       # AI analysis results
├── clips/          # Auto-sliced clips
├── exports/        # Workbench export results
├── decrypted/      # Decrypted output
├── assets/         # Curated assets
└── transcoded/     # Transcoded output
```

## 3. Main Pipeline: Download → Analyze → Slice

1. Set workspace in web workstation
2. Download video and subtitles (prefer SRT)
3. Use AI assistant or workbench to analyze for highlights
4. Auto-export clips via FFmpeg
5. Review and fine-tune in workbench

AI assistant example:
```
Download this video, get subtitles, find top 3 segments, export to current workspace.
https://www.youtube.com/watch?v=xxxx
```

## 4. Transcoding and Manual Slicing

```powershell
python -m cli.main encoder to-h265 input.mp4 --crf 28
python -m cli.main encoder extract-audio input.mp4
python -m cli.main encoder slice input.mp4 --start 00:00:10 --end 00:00:25
```

## 5. Decryption

```powershell
python -m cli.main decryptor run -i song.ncm
python -m cli.main decryptor run -i .\encrypted_music\ -o .\projects\default\decrypted\
```

## 6. Asset and File Management

Asset management indexes the current workspace. Scan the entire workspace:

```powershell
projects/default/
```

## 7. Adobe and Extended Tools

Adobe, auditing, WeChat moments, and capcut-mate depend on local environment. Verify:
- Software installed and automation allowed
- Tools in `vendor/` or `bin/`
- Ports and permissions correct

Prefer FFmpeg for stable exports; capcut-mate is experimental.

## 8. CLI Usage

CLI for batch processing, debugging, and status checks. Prefer Web workstation for daily workflows.

```powershell
python -m cli.main --help
python -m cli.main fetcher ytdlp status
python -m cli.main photoshop status
```

## 9. Troubleshooting

1. Check task center and logs in web UI
2. Verify API at `http://127.0.0.1:7860/docs`
3. Check `.env` configuration
4. Verify tools in `bin/` or system `PATH`
5. Run module `status` command
6. Run relevant tests

## 10. Boundaries

- Subtitle analysis quality depends on original subtitle quality
- Auto-padding helps, but critical segments need human review
- `vendor/` documentation belongs to upstream projects

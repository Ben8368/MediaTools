# MediaTools Workflow

> [中文版](./WORKFLOW.zh.md) · Chinese

This document describes the currently recommended real-world workflows. Old Gradio/GUI documentation, early proposals, and third-party tool guides are no longer primary entry points; consult `docs/README.md` when looking for specialized materials.

## 1. Launch the Workstation

```powershell
python app.py
```

Default URLs:

- Workstation: `http://127.0.0.1:7860`
- API docs: `http://127.0.0.1:7860/docs`

During development, you can also run the frontend simultaneously:

```powershell
cd frontend
npm run dev
```

Set `API_SECRET_KEY` before binding the backend to a non-localhost address.

## 2. Set Up Workspace

MediaTools uses a "current workspace" to organize downloads, analysis, exports, and asset scan results. The workspace state is stored in:

```text
runtime/workspace.json
```

Recommended structure:

```text
projects/default/
├── inputs/
├── downloads/
├── decrypted/
├── transcoded/
├── clips/
├── subtitles/
├── analysis/
├── assets/
├── imports/
├── cache/
├── logs/
├── manifests/
└── exports/
```

Common conventions:

- `downloads/`: downloaded videos and original subtitles
- `subtitles/`: analyzable and reusable subtitles
- `analysis/`: AI analysis JSON or segment suggestions
- `clips/`, `exports/`: auto-sliced clips and workbench export results
- `decrypted/`: decrypted output
- `assets/`: curated reusable assets

## 3. Main Pipeline: Download, Analyze, Slice

The most stable production pipeline is:

```text
Set workspace
-> Download video and subtitles
-> Clean / transform subtitles
-> AI analysis of segment highlights
-> FFmpeg auto-slicing
-> Workbench review
-> Export clips
```

Recommended practice:

1. Enter the video URL in the downloader / media acquisition section.
2. Download both video and subtitles simultaneously; prefer SRT format.
3. Use the AI assistant or workbench to generate segment suggestions.
4. Let the system auto-pad edges and export via FFmpeg.
5. Check timestamps, original text, and Chinese summaries in the workbench.
6. Fine-tune manually and re-export if necessary.

The AI assistant can handle tasks like:

```text
Download this video, get analyzable subtitles, find the top 3 most worthwhile segments, and export them to the current workspace.
https://www.youtube.com/watch?v=xxxx
```

## 4. Workbench Review

The workbench turns subtitle analysis results into a reviewable segment list.

Typical operations:

1. Load the current workspace's video and subtitles.
2. Set segment count.
3. Analyze subtitles and generate segment suggestions.
4. Review suggestion JSON, segment tables, and timeline overview.
5. Adjust start time, end time, Chinese summary, and original text.
6. Batch export.

When the automated pipeline completes but human judgment is needed for rhythm, semantics, or boundaries, always return to the workbench for review.

## 5. Transcoding and Manual Slicing

FFmpeg capabilities are provided by the `encoder` module and backend media services.

CLI examples:

```powershell
python main.py encoder to-h265 input.mp4 --crf 28
python main.py encoder extract-audio input.mp4
python main.py encoder slice input.mp4 --start 00:00:10 --end 00:00:25
```

Suitable for:

- Standalone transcoding
- Audio extraction
- Quick export of a precise time range
- Manual recovery when the auto pipeline fails

## 6. Music / Media Decryption

Decryption is handled by the `decryptor` module and `services/media_decrypt.py`.

CLI examples:

```powershell
python main.py decryptor run -i song.ncm
python main.py decryptor run -i .\encrypted_music\ -o .\projects\default\decrypted\
```

Copy or output successfully decrypted materials to the workspace `assets/` or `decrypted/`, then scan them via asset management.

## 7. Asset and File Management

Asset management functions as a "current workspace indexer," not a heavy asset database.

It is recommended to scan the entire workspace rather than just `assets/`:

```text
projects/default/
```

This way you can simultaneously see:

- Download results
- Subtitles and analysis files
- Transcoded outputs
- Clips and exports
- Decrypted materials

File management and preview capabilities are used for browsing workspaces, selecting paths, and inspecting output files.

## 8. Adobe and Extended Capabilities

Adobe, Photoshop, After Effects, asset auditing, WeChat moments image generation, and capcut-mate capabilities are already integrated but depend on the local environment.

Before use, verify:

- Whether the relevant software is installed and automation is allowed
- Whether tools exist in `vendor/` or `bin/`
- Whether ports and permissions are correct
- Whether API/plugin configurations are complete

`capcut-mate` remains an experimental link; prefer FFmpeg for stable exports.

## 9. CLI Positioning

CLI is suitable for batch processing, debugging, tool status checks, and scripted tasks. For complete daily workflows, prefer the Web workstation.

```powershell
python main.py --help
python main.py fetcher ytdlp status
python main.py photoshop status
python main.py auditor status
```

## 10. Troubleshooting Order

When encountering issues, follow this order:

1. Check the Web task center and logs.
2. Open `http://127.0.0.1:7860/docs` to verify API availability.
3. Check model, API, port, and workspace configurations in `.env`.
4. Check `ffmpeg`, `ffprobe`, `yt-dlp`, and `um-cli` in `bin/` or system `PATH`.
5. Run the corresponding module's `status` or minimal CLI command.
6. Run relevant tests.

## 11. Known Boundaries

- Subtitle analysis heavily depends on the quality of the original subtitles.
- Auto-padding reduces truncation, but critical segments still benefit from human review.
- CLI and Web capabilities are converging; the latest complete pipeline usually appears in the Web service layer first.
- Third-party tool documentation in `vendor/` represents upstream projects only.

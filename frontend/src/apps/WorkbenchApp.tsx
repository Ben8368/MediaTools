import { useEffect, useRef, useState } from 'react'

import { AppLayout } from '@/AppLayout'
import {
  analyzeWorkbenchSubtitle,
  exportWorkbenchClips,
  fetchWorkbenchMedia,
} from '@/api'
import { WORKBENCH_PREFILL_STORAGE_KEY, type WorkbenchPrefillPayload } from '@/apps/workbench/prefill'
import {
  Field,
  PathInput,
  PrimaryButton,
  ResultBox,
  ToolbarButton,
} from '@/apps/mediatools/primitives'
import type { AnyRecord } from '@/types'

export function WorkbenchApp() {
  const [media, setMedia] = useState<AnyRecord | null>(null)
  const [videoPath, setVideoPath] = useState('')
  const [subtitlePath, setSubtitlePath] = useState('')
  const [clipCount, setClipCount] = useState(5)
  const [clipsJson, setClipsJson] = useState('')
  const [burnSubtitles, setBurnSubtitles] = useState(true)
  const [result, setResult] = useState<unknown>('等待分析字幕')
  const [exportResult, setExportResult] = useState<unknown>('等待导出片段')

  const prefillAnalyzeRef = useRef<HTMLElement>(null)
  const prefillExportRef = useRef<HTMLElement>(null)
  const videos: AnyRecord[] = media?.video_rows || []
  const subtitles: AnyRecord[] = media?.subtitle_rows || []
  const exports: AnyRecord[] = media?.export_rows || []

  async function refreshMedia() {
    const data = await fetchWorkbenchMedia()
    setMedia(data)
  }

  async function analyze() {
    const data = await analyzeWorkbenchSubtitle({ subtitle_path: subtitlePath, clip_count: clipCount })
    setResult(data)
    if (data.clips_json) setClipsJson(data.clips_json)
  }

  async function exportClips() {
    setExportResult(await exportWorkbenchClips({
      video_path: videoPath,
      subtitle_path: subtitlePath,
      clips_json: clipsJson,
      burn_subtitles: burnSubtitles,
    }))
  }

  useEffect(() => { void refreshMedia() }, [])

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(WORKBENCH_PREFILL_STORAGE_KEY)
      if (!raw) return
      sessionStorage.removeItem(WORKBENCH_PREFILL_STORAGE_KEY)
      const data = JSON.parse(raw) as WorkbenchPrefillPayload
      if (data.subtitlePath) setSubtitlePath(data.subtitlePath)
      if (data.videoPath) setVideoPath(data.videoPath)
      if (typeof data.clipCount === 'number' && Number.isFinite(data.clipCount) && data.clipCount > 0) {
        setClipCount(Math.floor(data.clipCount))
      }
      const target =
        data.highlight === 'export' ? prefillExportRef : data.highlight === 'analyze' ? prefillAnalyzeRef : null
      requestAnimationFrame(() => {
        target?.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      })
    } catch {
      /* 忽略损坏的预填数据 */
    }
  }, [])

  return (
    <AppLayout>
      <div className="wb-app">
        <section className="wb-hero">
          <div>
            <div className="wb-eyebrow">Highlight Workbench</div>
            <h2>高光工作台</h2>
            <p>从工作区媒体中选择视频和字幕，分析高光片段，再批量导出适合二创、剪辑和复盘的片段。</p>
          </div>
          <div className="wb-ready">
            <span>{videos.length}</span>
            <small>可用视频</small>
          </div>
        </section>

        <div className="wb-metrics">
          <div className="wb-metric"><span>视频</span><strong>{videos.length}</strong></div>
          <div className="wb-metric"><span>字幕</span><strong>{subtitles.length}</strong></div>
          <div className="wb-metric"><span>最近导出</span><strong>{exports.length}</strong></div>
          <div className="wb-metric"><span>片段上限</span><strong>{clipCount}</strong></div>
        </div>

        <div className="wb-workspace">
          <section ref={prefillAnalyzeRef} className="wb-panel">
            <div className="wb-section-head">
              <div>
                <h3>素材选择</h3>
                <p>也可以手动输入任意本地路径。</p>
              </div>
              <ToolbarButton onClick={() => void refreshMedia()}>刷新素材</ToolbarButton>
            </div>
            <Field label="视频路径"><PathInput value={videoPath} onChange={setVideoPath} mode="file" /></Field>
            <Field label="字幕路径"><PathInput value={subtitlePath} onChange={setSubtitlePath} mode="file" /></Field>
            <div className="wb-inline">
              <Field label="高光数量"><input type="number" value={clipCount} onChange={(event) => setClipCount(Number(event.target.value) || 5)} /></Field>
              <label className="wb-check"><input type="checkbox" checked={burnSubtitles} onChange={(event) => setBurnSubtitles(event.target.checked)} /> 烧录字幕</label>
            </div>
            <div className="wb-actions">
              <PrimaryButton onClick={analyze} disabled={!subtitlePath}>分析字幕</PrimaryButton>
              <ToolbarButton onClick={exportClips} disabled={!videoPath || !clipsJson}>导出片段</ToolbarButton>
            </div>
          </section>

          <section className="wb-panel">
            <div className="wb-section-head">
              <div>
                <h3>工作区媒体</h3>
                <p>点击条目可快速填入路径。</p>
              </div>
            </div>
            <div className="wb-media-grid">
              <div className="wb-media-list">
                <h4>视频</h4>
                {videos.slice(0, 8).map((row, index) => (
                  <button key={`${row[3]}-${index}`} onClick={() => setVideoPath(row[3])}>
                    <strong>{row[0]}</strong><span>{row[2]} MB</span>
                  </button>
                ))}
              </div>
              <div className="wb-media-list">
                <h4>字幕</h4>
                {subtitles.slice(0, 8).map((row, index) => (
                  <button key={`${row[3]}-${index}`} onClick={() => setSubtitlePath(row[3])}>
                    <strong>{row[0]}</strong><span>{row[2]} MB</span>
                  </button>
                ))}
              </div>
            </div>
          </section>
        </div>

        <section ref={prefillExportRef} className="wb-panel">
          <div className="wb-section-head">
            <div>
              <h3>片段确认</h3>
              <p>分析结果会写入这里，导出前可直接微调 JSON。</p>
            </div>
          </div>
          <textarea className="wb-clips-json" value={clipsJson} onChange={(event) => setClipsJson(event.target.value)} placeholder="等待字幕分析生成片段 JSON" />
          <div className="wb-result-grid">
            <ResultBox value={result} />
            <ResultBox value={exportResult} />
          </div>
        </section>
      </div>
    </AppLayout>
  )
}

/** 从下载器跳转到工作台时预填路径（sessionStorage 键） */
export const WORKBENCH_PREFILL_STORAGE_KEY = 'mediatools.workbench.prefill'

export type WorkbenchPrefillPayload = {
  subtitlePath?: string
  videoPath?: string
  clipCount?: number
  /** 打开后滚动到对应功能区 */
  highlight?: 'analyze' | 'export'
}

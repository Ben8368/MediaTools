import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { DirectoryPickerDialog, FileManagerApp } from '@/apps/FileManagerApp'

const apiMocks = vi.hoisted(() => ({
  createFilebrowserDirectory: vi.fn(),
  deleteFilebrowserPath: vi.fn(),
  emptyFilebrowserTrash: vi.fn(),
  fetchFilebrowserDisks: vi.fn(),
  fetchFilebrowserTrash: vi.fn(),
  getWorkspace: vi.fn(),
  listFilebrowserDirectory: vi.fn(),
  purgeFilebrowserTrash: vi.fn(),
  restoreFilebrowserTrash: vi.fn(),
}))

vi.mock('@/api', () => apiMocks)

const diskD = {
  name: '本地磁盘 (D:)',
  path: 'D:\\',
  total: 1024 * 1024 * 1024 * 1024,
  used: 512 * 1024 * 1024 * 1024,
  free: 512 * 1024 * 1024 * 1024,
}

const diskZ = {
  name: 'SMB 磁盘 (Z:)',
  path: 'Z:\\',
  total: 2 * 1024 * 1024 * 1024 * 1024,
  used: 512 * 1024 * 1024 * 1024,
  free: 1536 * 1024 * 1024 * 1024,
}

const folder = {
  name: 'downloads',
  path: 'D:\\downloads',
  size: 0,
  modified: '2026-04-28T14:49:00',
  type: 'directory' as const,
}

const file = {
  name: 'clip.mp4',
  path: 'D:\\clip.mp4',
  size: 1024,
  modified: '2026-04-28T14:50:00',
  type: 'file' as const,
  extension: '.mp4',
}

function mockDirectory(path: string, directories = [folder], files = [file]) {
  apiMocks.listFilebrowserDirectory.mockResolvedValue({
    ok: true,
    path,
    directories,
    files,
  })
}

describe('FileManagerApp', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    apiMocks.createFilebrowserDirectory.mockReset()
    apiMocks.deleteFilebrowserPath.mockReset()
    apiMocks.emptyFilebrowserTrash.mockReset()
    apiMocks.fetchFilebrowserDisks.mockReset()
    apiMocks.fetchFilebrowserTrash.mockReset()
    apiMocks.getWorkspace.mockReset()
    apiMocks.listFilebrowserDirectory.mockReset()
    apiMocks.purgeFilebrowserTrash.mockReset()
    apiMocks.restoreFilebrowserTrash.mockReset()

    apiMocks.fetchFilebrowserDisks.mockResolvedValue({ disks: [diskD, diskZ] })
    apiMocks.getWorkspace.mockResolvedValue({ workspace: { project_root: 'D:\\' } })
    mockDirectory('D:\\')
    apiMocks.fetchFilebrowserTrash.mockResolvedValue({ ok: true, items: [] })
    apiMocks.createFilebrowserDirectory.mockResolvedValue({ ok: true })
    apiMocks.deleteFilebrowserPath.mockResolvedValue({ ok: true })
    apiMocks.restoreFilebrowserTrash.mockResolvedValue({ ok: true })
    apiMocks.purgeFilebrowserTrash.mockResolvedValue({ ok: true })
    apiMocks.emptyFilebrowserTrash.mockResolvedValue({ ok: true })
  })

  it('renders backend disks and lists the initial directory', async () => {
    render(<FileManagerApp />)

    expect(await screen.findByText('磁盘 (D:)')).toBeInTheDocument()
    expect(await screen.findByText('磁盘 (Z:)')).toBeInTheDocument()
    expect(await screen.findByText('downloads')).toBeInTheDocument()
    expect(await screen.findByText('clip.mp4')).toBeInTheDocument()
    expect(apiMocks.listFilebrowserDirectory).toHaveBeenCalledWith({ directory: 'D:\\' })
  })

  it('filters visible files and folders by keyword', async () => {
    render(<FileManagerApp />)

    expect(await screen.findByText('downloads')).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('搜索'), { target: { value: 'clip' } })

    expect(screen.queryByText('downloads')).not.toBeInTheDocument()
    expect(screen.getByText('clip.mp4')).toBeInTheDocument()
  })

  it('switches to another backend disk from the sidebar', async () => {
    apiMocks.listFilebrowserDirectory
      .mockResolvedValueOnce({ ok: true, path: 'D:\\', directories: [folder], files: [file] })
      .mockResolvedValueOnce({
        ok: true,
        path: 'Z:\\',
        directories: [{ ...folder, name: 'shared', path: 'Z:\\shared' }],
        files: [],
      })

    render(<FileManagerApp />)

    fireEvent.click(await screen.findByText('磁盘 (Z:)'))

    await waitFor(() => {
      expect(apiMocks.listFilebrowserDirectory).toHaveBeenLastCalledWith({ directory: 'Z:\\' })
    })
    expect(await screen.findByText('shared')).toBeInTheDocument()
  })

  it('creates a folder in the current directory and refreshes the listing', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('new-folder')
    render(<FileManagerApp />)

    fireEvent.click(await screen.findByRole('button', { name: '新建文件夹' }))

    await waitFor(() => {
      expect(apiMocks.createFilebrowserDirectory).toHaveBeenCalledWith('D:\\new-folder')
    })
    expect(apiMocks.listFilebrowserDirectory).toHaveBeenLastCalledWith({ directory: 'D:\\' })
  })

  it('moves selected files into the recycle bin instead of deleting directly', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<FileManagerApp />)

    fireEvent.click(await screen.findByText('clip.mp4'))
    fireEvent.click(screen.getByRole('button', { name: '移入回收站' }))

    await waitFor(() => {
      expect(apiMocks.deleteFilebrowserPath).toHaveBeenCalledWith('D:\\clip.mp4', true)
    })
  })

  it('supports restoring and permanently deleting recycle bin items', async () => {
    apiMocks.fetchFilebrowserTrash.mockResolvedValue({
      ok: true,
      items: [
        {
          id: 'trash-1',
          name: 'old.mp4',
          original_path: 'D:\\old.mp4',
          deleted_at: '2026-04-28T15:00:00',
          type: 'file',
          size: 2048,
          stored_path: 'D:\\MediaTools\\runtime\\filebrowser-trash\\trash-1\\old.mp4',
        },
      ],
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    render(<FileManagerApp />)

    fireEvent.click(await screen.findByRole('button', { name: '回收站' }))
    fireEvent.click(await screen.findByText('old.mp4'))
    fireEvent.click(screen.getByRole('button', { name: '恢复' }))

    await waitFor(() => {
      expect(apiMocks.restoreFilebrowserTrash).toHaveBeenCalledWith('trash-1')
    })

    fireEvent.click(await screen.findByText('old.mp4'))
    fireEvent.click(screen.getByRole('button', { name: '彻底删除' }))

    await waitFor(() => {
      expect(apiMocks.purgeFilebrowserTrash).toHaveBeenCalledWith('trash-1')
    })
  })

  it('empties the recycle bin after confirmation', async () => {
    apiMocks.fetchFilebrowserTrash.mockResolvedValue({
      ok: true,
      items: [
        {
          id: 'trash-1',
          name: 'old.mp4',
          original_path: 'D:\\old.mp4',
          deleted_at: '2026-04-28T15:00:00',
          type: 'file',
          size: 2048,
          stored_path: 'D:\\MediaTools\\runtime\\filebrowser-trash\\trash-1\\old.mp4',
        },
      ],
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    render(<FileManagerApp />)

    fireEvent.click(await screen.findByRole('button', { name: '回收站' }))
    fireEvent.click(await screen.findByRole('button', { name: '清空回收站' }))

    await waitFor(() => {
      expect(apiMocks.emptyFilebrowserTrash).toHaveBeenCalled()
    })
  })

  it('lets directory picker confirm the current directory', async () => {
    const onClose = vi.fn()
    const onPick = vi.fn()

    render(<DirectoryPickerDialog open value="" mode="directory" onClose={onClose} onPick={onPick} />)

    expect(await screen.findByRole('textbox', { name: '当前路径' })).toHaveValue('D:\\')
    fireEvent.click(screen.getByRole('button', { name: '确认' }))

    expect(onPick).toHaveBeenCalledWith('D:\\')
    expect(onClose).toHaveBeenCalled()
  })

  it('creates a new folder from directory picker drive bar', async () => {
    vi.spyOn(window, 'prompt').mockReturnValue('picked-subdir')
    mockDirectory('D:\\')
    render(<DirectoryPickerDialog open value="" mode="directory" onClose={vi.fn()} onPick={vi.fn()} />)

    await screen.findByRole('textbox', { name: '当前路径' })
    fireEvent.click(screen.getByRole('button', { name: '新建文件夹' }))

    await waitFor(() => {
      expect(apiMocks.createFilebrowserDirectory).toHaveBeenCalledWith('D:\\picked-subdir')
    })
  })

  it('requires selecting a file when directory picker runs in file mode', async () => {
    const onClose = vi.fn()
    const onPick = vi.fn()

    render(<DirectoryPickerDialog open value="" mode="file" onClose={onClose} onPick={onPick} />)

    const confirmButton = await screen.findByRole('button', { name: '确认' })
    expect(confirmButton).toBeDisabled()

    fireEvent.click(await screen.findByText('downloads'))
    expect(confirmButton).toBeDisabled()

    fireEvent.click(await screen.findByText('clip.mp4'))
    expect(confirmButton).not.toBeDisabled()

    fireEvent.click(confirmButton)
    expect(onPick).toHaveBeenCalledWith('D:\\clip.mp4')
    expect(onClose).toHaveBeenCalled()
  })

  it('opens the parent directory and preselects an existing file path', async () => {
    const onClose = vi.fn()
    const onPick = vi.fn()
    const selectedFile = {
      ...file,
      name: 'song.ncm',
      path: 'D:\\album\\song.ncm',
      extension: '.ncm',
    }
    mockDirectory('D:\\album', [], [selectedFile])

    render(<DirectoryPickerDialog open value={'D:\\album\\song.ncm'} mode="file" onClose={onClose} onPick={onPick} />)

    expect(await screen.findByRole('textbox', { name: '当前路径' })).toHaveValue('D:\\album')
    expect(await screen.findByText('song.ncm')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '确认' }))

    expect(onPick).toHaveBeenCalledWith('D:\\album\\song.ncm')
    expect(onClose).toHaveBeenCalled()
  })

  it('shows selected path in directory picker footer', async () => {
    render(<DirectoryPickerDialog open value="" mode="directory" onClose={vi.fn()} onPick={vi.fn()} />)

    fireEvent.click(await screen.findByText('downloads'))

    const footer = screen.getByText('已选路径').closest('.fm-picker__selection')
    expect(footer).toBeTruthy()
    expect(within(footer as HTMLElement).getByText('D:\\downloads')).toBeInTheDocument()
  })
})

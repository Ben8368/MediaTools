import { CATEGORY_MAP } from '@/apps/downloader/constants'
import { AdminIcon, CategoryIcon, SettingsIcon } from '@/apps/downloader/icons'
import type { CategoryKey, TaskStats } from '@/apps/downloader/types'

type DownloaderSidebarProps = {
  selectedCategory: CategoryKey
  stats: TaskStats
  onSelectCategory: (category: CategoryKey) => void
}

export function DownloaderSidebar({ selectedCategory, stats, onSelectCategory }: DownloaderSidebarProps) {
  return (
    <aside className="dl-sidebar">
      <nav className="dl-nav">
        {Object.entries(CATEGORY_MAP).map(([key, category]) => (
          <button
            key={key}
            className={`dl-nav-item ${selectedCategory === key ? 'dl-nav-item--active' : ''}`}
            onClick={() => onSelectCategory(key as CategoryKey)}
          >
            <CategoryIcon name={category.icon} />
            <span>{category.label}</span>
            <small>({stats[category.key]})</small>
          </button>
        ))}
      </nav>
      <div className="dl-sidebar-bottom">
        <button className="dl-nav-item">
          <AdminIcon />
          <span>管理员视角</span>
        </button>
        <button className="dl-nav-item">
          <SettingsIcon />
          <span>设置</span>
        </button>
      </div>
    </aside>
  )
}

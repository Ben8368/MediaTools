import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from '@/App'
import { PhotoshopApp } from '@/apps/MediaToolsApps'
import { AEApp } from '@/apps/MediaToolsApps'
import '@/i18n'
import './styles/app-window.css'
import './index.css'
import './styles/app-controls.css'
import './styles/mediatools-apps.css'

// 检测 CEP 模式：URL 参数 ?cep=photoshop 或 ?cep=ae
const urlParams = new URLSearchParams(window.location.search)
const cepMode = urlParams.get('cep')

// CEP 模式下只渲染单个应用组件，不渲染完整桌面
let AppComponent = App

if (cepMode === 'photoshop') {
  AppComponent = PhotoshopApp
  document.body.style.background = '#1e1e1e'
} else if (cepMode === 'ae') {
  AppComponent = AEApp
  document.body.style.background = '#1e1e1e'
} else {
  // 完整桌面模式才设置壁纸
  document.documentElement.style.setProperty('--fnos-wp', 'url(/static/bg/wallpaper-3-dark.webp)')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppComponent />
  </StrictMode>
)

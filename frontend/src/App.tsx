import { ConfigProvider, theme, App as AntApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppRouter from './router'

import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

function NProgressBar() {
  const location = useLocation()
  useEffect(() => {
    NProgress.configure({ showSpinner: false, trickleSpeed: 100 })
    NProgress.start()
    const t = setTimeout(() => NProgress.done(), 300)
    return () => { clearTimeout(t); NProgress.done() }
  }, [location.pathname])
  return null
}

import { useThemeStore } from './store/theme'

function App() {
  const dark = useThemeStore((s) => s.dark)

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#6366f1',
          colorSuccess: '#10b981',
          colorWarning: '#f59e0b',
          colorError: '#ef4444',
          colorInfo: '#3b82f6',
          borderRadius: 8,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        },
        algorithm: dark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        components: {
          Layout: {
            headerBg: dark ? '#141414' : '#ffffff',
            siderBg: dark ? '#0a0a0a' : '#0f172a',
            bodyBg: dark ? '#000000' : '#f8fafc',
          },
          Menu: {
            darkItemBg: 'transparent',
            darkItemSelectedBg: 'rgba(99,102,241,0.3)',
          },
          Card: { paddingLG: 24 },
          Table: { headerBg: dark ? '#1a1a1a' : '#f8fafc' },
        },
      }}
    >
      <AntApp>
        <NProgressBar /><AppRouter />
      </AntApp>
    </ConfigProvider>
  )
}

export default App

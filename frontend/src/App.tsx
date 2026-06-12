import { ConfigProvider, theme, App as AntApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppRouter from './router'

function App() {
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
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans SC", sans-serif',
          fontSize: 14,
          colorBgContainer: '#ffffff',
          colorBorder: '#e5e7eb',
          boxShadow:
            '0 1px 3px 0 rgba(0,0,0,0.04), 0 1px 2px -1px rgba(0,0,0,0.03)',
        },
        algorithm: theme.defaultAlgorithm,
        components: {
          Layout: {
            headerBg: '#ffffff',
            siderBg: '#1e1b4b',
            bodyBg: '#f8fafc',
          },
          Menu: {
            darkItemBg: '#1e1b4b',
            darkItemSelectedBg: 'rgba(99,102,241,0.3)',
            darkItemHoverBg: 'rgba(99,102,241,0.15)',
            darkSubMenuItemBg: '#1e1b4b',
          },
          Card: {
            paddingLG: 24,
          },
          Table: {
            headerBg: '#f8fafc',
            rowHoverBg: '#f0f0ff',
          },
          Button: {
            primaryShadow: '0 4px 14px 0 rgba(99,102,241,0.3)',
          },
          Tag: {
            defaultBg: '#f1f5f9',
          },
        },
      }}
    >
      <AntApp>
        <AppRouter />
      </AntApp>
    </ConfigProvider>
  )
}

export default App

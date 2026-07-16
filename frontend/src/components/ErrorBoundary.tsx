import React from 'react'
import { Result, Button } from 'antd'

interface Props { children: React.ReactNode }
interface State { hasError: boolean; error: Error | null }

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="Page Error"
          subTitle={this.state.error?.message || 'An unexpected error occurred'}
          extra={[
            <Button type="primary" key="reload" onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload() }}>
              Reload Page
            </Button>,
            <Button key="home" onClick={() => { window.location.href = '/' }}>
              Go Home
            </Button>,
          ]}
        />
      )
    }
    return this.props.children
  }
}

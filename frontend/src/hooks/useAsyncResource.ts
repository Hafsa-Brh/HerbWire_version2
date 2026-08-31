import { useCallback, useEffect, useState } from "react"

type AsyncResourceState<T> = {
  data: T | null
  isLoading: boolean
  error: Error | null
  reload: () => void
}

const initialState = <T,>(): Omit<AsyncResourceState<T>, "reload"> => ({
  data: null,
  isLoading: true,
  error: null,
})

export function useAsyncResource<T>(load: (signal: AbortSignal) => Promise<T>): AsyncResourceState<T> {
  const [state, setState] = useState<Omit<AsyncResourceState<T>, "reload">>(() => initialState<T>())
  const [reloadToken, setReloadToken] = useState(0)

  const reload = useCallback(() => {
    setReloadToken((value) => value + 1)
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setState(initialState<T>())
      load(controller.signal)
        .then((data) => {
          if (!controller.signal.aborted) {
            setState({ data, isLoading: false, error: null })
          }
        })
        .catch((error: unknown) => {
          if (!controller.signal.aborted) {
            setState({ data: null, isLoading: false, error: error instanceof Error ? error : new Error("Unknown error") })
          }
        })
    }, 0)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [load, reloadToken])

  return { ...state, reload }
}

import { Component, createRef, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

/**
 * Keeps a render-time throw from blanking the window.
 *
 * Without one, React unmounts the whole tree on an uncaught render error and the user is
 * left with an empty window and no way back short of quitting. One boundary wraps the app
 * (`main.tsx`) and one wraps each screen (`App.tsx`), so a screen that throws costs that
 * screen and leaves the shell — header, tabs, notification bell — usable.
 *
 * "Try again" clears the error and re-renders the children, which remount and re-load.
 * `resetKey` does the same automatically when it changes, so a boundary does not stay
 * failed after the user has moved on to something else.
 */
interface Props {
  readonly children: ReactNode;
  /** Names what failed, in the fallback: "The Skills screen" reads better than "Something". */
  readonly label?: string;
  readonly resetKey?: unknown;
}

interface State {
  readonly error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  override state: State = { error: null };
  private readonly fallback = createRef<HTMLDivElement>();
  private focusTimer: ReturnType<typeof setTimeout> | undefined;

  static getDerivedStateFromError(error: unknown): State {
    return { error: error instanceof Error ? error : new Error(String(error)) };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('render error', error, info.componentStack);
  }

  // A boundary can mount already failed (its child throws on the first render), so both
  // lifecycles look for a fallback that has just appeared.
  override componentDidMount() {
    this.focusFallback();
  }

  override componentWillUnmount() {
    if (this.focusTimer !== undefined) clearTimeout(this.focusTimer);
  }

  // Deferred a tick: a click on a tab moves focus to the tab after the render it caused, which
  // would take it straight back from the message.
  private focusFallback() {
    this.focusTimer = setTimeout(() => this.fallback.current?.focus(), 0);
  }

  override componentDidUpdate(previous: Props, previousState: State) {
    // Move focus to the message: the screen the user was on has just been replaced.
    if (this.state.error !== null && previousState.error === null) this.focusFallback();
    if (this.state.error !== null && previous.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  override render() {
    const { error } = this.state;
    if (error === null) return this.props.children;
    return (
      <Alert ref={this.fallback} tabIndex={-1} variant="destructive" className="m-4 w-auto outline-hidden">
        <AlertTriangle />
        <AlertTitle>{this.props.label ?? 'This part of the app'} hit an unexpected error</AlertTitle>
        <AlertDescription>
          <p>{error.message}</p>
          <div className="flex gap-2 pt-1">
            <Button variant="outline" size="sm" onClick={() => this.setState({ error: null })}>
              Try again
            </Button>
            <Button variant="ghost" size="sm" onClick={() => window.location.reload()}>
              Reload the window
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    );
  }
}

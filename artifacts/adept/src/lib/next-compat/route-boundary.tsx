import { Component, type ReactNode } from "react";

import NotFound from "@/pages/not-found";

import { navigate, NotFoundError, RedirectError } from "./router";

type State = { error: unknown };

/** Handles redirect() and notFound() thrown from pages, layouts and async views. */
export class RouteBoundary extends Component<{ children: ReactNode; location: string }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: unknown): State {
    return { error };
  }

  componentDidCatch(error: unknown) {
    if (error instanceof RedirectError) navigate(error.url, { replace: true });
  }

  componentDidUpdate(prev: { location: string }) {
    if (prev.location !== this.props.location && this.state.error) this.setState({ error: null });
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    if (error instanceof RedirectError) return null;
    if (error instanceof NotFoundError) return <NotFound />;
    throw error;
  }
}

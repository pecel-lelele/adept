import { createContext, useContext, useEffect, useMemo, useRef, useState, type Context, type ReactNode } from "react";

import { useGeneration } from "./router";

/** Fallback shown by the outermost pending async view (route loading.tsx equivalent). */
export const FallbackContext = createContext<ReactNode>(null);

function Slot({ ctx }: { ctx: Context<ReactNode> }) {
  return <>{useContext(ctx)}</>;
}

/**
 * Converts an async (server) component into a client component: the async body runs in an
 * effect and its JSX is rendered when ready. Re-runs when props change or the router refreshes;
 * the previous output stays on screen meanwhile. Redirect/notFound errors are rethrown during
 * render so the route boundary handles them.
 */
export function asyncView<P extends object>(fn: (props: P) => Promise<ReactNode>) {
  function AsyncView(props: P) {
    const generation = useGeneration();
    const fallback = useContext(FallbackContext);
    const childrenCtx = useMemo(() => createContext<ReactNode>(null), []);
    const [state, setState] = useState<{ node?: ReactNode; error?: unknown; ready: boolean }>({ ready: false });
    const run = useRef(0);
    const record = props as Record<string, unknown>;
    const hasChildren = "children" in record;
    const keys = Object.keys(record).filter((k) => k !== "children").sort();
    const deps = keys.map((k) => record[k]);

    useEffect(() => {
      const id = ++run.current;
      const input = (hasChildren ? { ...record, children: <Slot ctx={childrenCtx} /> } : record) as P;
      Promise.resolve()
        .then(() => fn(input))
        .then(
          (node) => run.current === id && setState({ node, ready: true }),
          (error) => run.current === id && setState((s) => ({ ...s, error })),
        );
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [generation, keys.join("|"), ...deps]);

    if (state.error) throw state.error;
    if (!state.ready) return <>{fallback}</>;
    return (
      <FallbackContext.Provider value={null}>
        <childrenCtx.Provider value={hasChildren ? (record.children as ReactNode) : null}>{state.node}</childrenCtx.Provider>
      </FallbackContext.Provider>
    );
  }
  AsyncView.displayName = fn.name.replace(/Async$/, "");
  return AsyncView;
}

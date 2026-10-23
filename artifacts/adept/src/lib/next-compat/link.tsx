import { forwardRef, type AnchorHTMLAttributes, type MouseEvent } from "react";

import { navigate, withBase } from "./router";

type Props = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
  href: string;
  replace?: boolean;
  scroll?: boolean;
  prefetch?: boolean | null;
};

/** Drop-in for next/link: a plain anchor with client-side navigation. */
const Link = forwardRef<HTMLAnchorElement, Props>(function Link(
  { href, replace, scroll, prefetch: _prefetch, onClick, target, ...rest },
  ref,
) {
  const internal = href.startsWith("/") && !href.startsWith("//") && !/^\/api(\/|$|\?)/.test(href);
  const handle = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented || !internal || target === "_blank") return;
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    navigate(href, { replace, scroll });
  };
  return <a ref={ref} href={withBase(href)} target={target} onClick={handle} {...rest} />;
});

export default Link;

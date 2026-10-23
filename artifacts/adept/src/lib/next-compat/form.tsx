import type { FormEvent, FormHTMLAttributes } from "react";

import { navigate, withBase } from "./router";

type Props = Omit<FormHTMLAttributes<HTMLFormElement>, "action"> & {
  action: string | ((formData: FormData) => void | Promise<void>);
  replace?: boolean;
  scroll?: boolean;
};

/** Drop-in for next/form: string actions become client-side GET navigations. */
export default function Form({ action, replace, scroll, onSubmit, ...rest }: Props) {
  if (typeof action !== "string") return <form action={action} onSubmit={onSubmit} {...rest} />;
  const handle = (e: FormEvent<HTMLFormElement>) => {
    onSubmit?.(e as Parameters<NonNullable<typeof onSubmit>>[0]);
    if (e.defaultPrevented) return;
    e.preventDefault();
    const params = new URLSearchParams();
    const submitter = (e.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const data = new FormData(e.currentTarget, submitter ?? undefined);
    for (const [key, value] of data.entries()) if (typeof value === "string") params.append(key, value);
    const qs = params.toString();
    navigate(qs ? `${action}?${qs}` : action, { replace, scroll });
  };
  return <form action={withBase(action)} method="get" onSubmit={handle} {...rest} />;
}

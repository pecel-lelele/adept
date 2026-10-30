import type { KeyboardEvent } from "react";

/**
 * Keyboard support for a WAI-ARIA radio group made of buttons: only the checked option is in
 * the tab order (roving tabindex) and the arrow keys, Home and End move focus and select.
 */
export function radioTabIndex(checked: boolean): 0 | -1 {
  return checked ? 0 : -1;
}

export function onRadioKeyDown<T extends string>(
  event: KeyboardEvent<HTMLElement>,
  options: readonly T[],
  current: T,
  select: (next: T) => void,
): void {
  const index = options.indexOf(current);
  let next = index;
  if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % options.length;
  else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index - 1 + options.length) % options.length;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = options.length - 1;
  else return;
  const target = options[next];
  if (target === undefined) return;
  event.preventDefault();
  const radios = event.currentTarget.closest('[role="radiogroup"]')?.querySelectorAll<HTMLElement>('[role="radio"]');
  radios?.[next]?.focus();
  select(target);
}

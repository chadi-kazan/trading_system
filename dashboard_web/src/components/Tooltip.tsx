import {
  Children,
  cloneElement,
  type ReactElement,
  type ReactNode,
  useId,
  useState,
} from "react";

type TooltipProps = {
  children: ReactElement;
  content: ReactNode;
  side?: "top" | "bottom";
};

export function Tooltip({ children, content, side = "top" }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const id = useId();

  const child = Children.only(children) as ReactElement<Record<string, unknown>>;
  const trigger = cloneElement(
    child,
    open ? ({ "aria-describedby": id } as Record<string, unknown>) : undefined,
  );

  const sidePosition =
    side === "top"
      ? "bottom-full mb-3"
      : "top-full mt-3";
  const arrowPosition =
    side === "top"
      ? "top-full"
      : "bottom-full";

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocusCapture={() => setOpen(true)}
      onBlurCapture={() => setOpen(false)}
    >
      {trigger}
      <span
        role="tooltip"
        id={id}
        className={`pointer-events-none absolute ${sidePosition} left-1/2 -translate-x-1/2 transition-all duration-150 ${
          open ? "translate-y-0 opacity-100" : "translate-y-1 opacity-0"
        } z-50`}
      >
        <span className="block max-w-xs rounded-xl border border-slate-700/70 bg-slate-900 px-4 py-3 text-xs leading-relaxed text-slate-200 shadow-2xl ring-1 ring-slate-700/60">
          {content}
        </span>
        <span
          className={`absolute ${arrowPosition} left-1/2 -translate-x-1/2`}
          aria-hidden="true"
        >
          <span className="block h-3 w-3 rotate-45 border border-slate-700/70 bg-slate-900"></span>
        </span>
      </span>
    </span>
  );
}

export function InfoIcon() {
  return (
    <svg
      className="h-3.5 w-3.5"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="8" cy="8" r="6.25" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M7.25 7.25H8.5V11.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="8" cy="4.75" r="0.85" fill="currentColor" />
    </svg>
  );
}

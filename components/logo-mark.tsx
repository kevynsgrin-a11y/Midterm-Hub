// Midterm Watch — sleek eye logo mark, fully transparent SVG.
// Thin red eye outline with a compact American flag motif in the iris.
export function LogoMark({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 36 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={className}
    >
      {/* Eye outline — single continuous almond shape */}
      <path
        d="M4 18C4 18 10 8 18 8C26 8 32 18 32 18C32 18 26 28 18 28C10 28 4 18 4 18Z"
        stroke="#b1222f"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Iris with a compact American flag motif */}
      <circle cx="18" cy="18" r="6.5" fill="#f7f9fc" />
      <clipPath id="iris-flag-clip">
        <circle cx="18" cy="18" r="6.5" />
      </clipPath>
      <g clipPath="url(#iris-flag-clip)">
        <path d="M11.5 13.5H24.5V15.5H11.5ZM11.5 17.5H24.5V19.5H11.5ZM11.5 21.5H24.5V23.5H11.5Z" fill="#b1222f" />
        <path d="M11.5 11.5H18.5V18.5H11.5Z" fill="#0f2f66" />
        <circle cx="14" cy="14" r="0.55" fill="#f7f9fc" />
        <circle cx="16.5" cy="16" r="0.55" fill="#f7f9fc" />
      </g>
      <circle cx="18" cy="18" r="6.5" stroke="#0f2f66" strokeWidth="0.75" />
    </svg>
  );
}

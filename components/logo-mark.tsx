// Midterm Watch — sleek eye/ballot logo mark, fully transparent SVG.
// Thin red eye outline, small navy iris, subtle white checkmark. No background fill.
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
      {/* Iris */}
      <circle cx="18" cy="18" r="6.5" fill="#0f2f66" />
      {/* Checkmark */}
      <path
        d="M14.5 18.5L17 21L21.5 15.5"
        stroke="white"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

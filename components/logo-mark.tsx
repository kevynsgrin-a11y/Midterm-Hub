// Midterm Watch — eye/ballot logo mark, fully transparent SVG
// Red eyelids, navy iris disc, white checkmark. No background fill.
export function LogoMark({ size = 52, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 52 52"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={className}
    >
      {/* Upper eyelid */}
      <path
        d="M6 26C6 26 14 10 26 10C38 10 46 26 46 26"
        stroke="#b1222f"
        strokeWidth="3.5"
        strokeLinecap="round"
        fill="none"
      />
      {/* Lower eyelid */}
      <path
        d="M6 26C6 26 14 42 26 42C38 42 46 26 46 26"
        stroke="#b1222f"
        strokeWidth="3.5"
        strokeLinecap="round"
        fill="none"
      />
      {/* Iris disc */}
      <circle cx="26" cy="26" r="10" fill="#0f2f66" />
      {/* Gloss highlight on iris */}
      <ellipse cx="23" cy="22" rx="3.5" ry="2" fill="white" fillOpacity="0.22" />
      {/* Checkmark */}
      <path
        d="M20.5 26.5L24 30L31.5 22.5"
        stroke="white"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

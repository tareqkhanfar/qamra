/** Design Shop: the activity books' little page drawings (dotted letter, maze, family check). */
export function ActivityArt({ line }: { line: string }) {
  const bg = line === "journey" ? "bg-success-bg" : line === "family" ? "bg-amber-100" : "bg-night-100";
  const tab = line === "journey" ? "#7FA38A" : line === "family" ? "#E9826B" : "#5B6FC0";
  return (
    <div className={`flex h-[124px] w-24 shrink-0 items-center justify-center rounded-xl ${bg}`} aria-hidden="true">
      <svg width="76" height="100" viewBox="0 0 96 124">
        <rect x="1" y="1" width="94" height="122" rx="6" fill="#FFFFFF" stroke="#E4D6BC" />
        {line !== "family" && <rect x="84" y="12" width="11" height="26" fill={tab} />}
        {line === "workbook" && (
          <>
            <text
              x="46"
              y="74"
              textAnchor="middle"
              fontSize="58"
              fontFamily="IBM Plex Sans Arabic, sans-serif"
              fill="none"
              stroke="#16204A"
              strokeWidth="1.8"
              strokeDasharray="2 3"
            >
              ب
            </text>
            <circle cx="64" cy="38" r="3.5" fill="#E9826B" />
            <path d="M14 98 H82 M14 110 H82" stroke="#E4D6BC" strokeWidth="1.5" />
          </>
        )}
        {line === "journey" && (
          <>
            <path
              d="M16 30 H40 V54 H64 V30 M16 54 V82 H40 M64 54 V82 H80 M40 82 V100 H64"
              fill="none"
              stroke="#16204A"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="16" cy="22" r="5" fill="#E9826B" />
            <path d="M76 98 l4 -8 l4 8 z" fill="#F2B33D" />
          </>
        )}
        {line === "family" && (
          <>
            <circle cx="48" cy="54" r="26" fill="none" stroke="#E9826B" strokeWidth="3" strokeDasharray="5 4" />
            <path
              d="M36 54 l8 8 l16 -16"
              fill="none"
              stroke="#E9826B"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path d="M18 98 H78 M18 108 H62" stroke="#E4D6BC" strokeWidth="1.5" />
          </>
        )}
      </svg>
    </div>
  );
}

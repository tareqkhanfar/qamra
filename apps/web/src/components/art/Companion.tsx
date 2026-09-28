/** Illustrated companion: design part `Companion` (blob «نونو», cat «مشمش», robot «قمّور»). */

export type CompanionVariant = "blob" | "cat" | "robot";

export function Companion({
  variant = "blob",
  pose = "front",
  className = "block h-auto w-full",
}: {
  variant?: CompanionVariant;
  pose?: "front" | "wave";
  className?: string;
}) {
  const wave = pose === "wave";
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden="true">
      <g stroke="#1C2140" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        {variant === "blob" && (
          <g>
            <ellipse cx="100" cy="186" rx="44" ry="6" fill="#1C2140" opacity="0.12" stroke="none" />
            <path d="M80 60 C74 44 70 36 66 28 M120 58 C128 44 132 36 136 28" fill="none" />
            <path
              d="M66 14 L69.5 22.5 L78.5 23.5 L71.5 29.5 L74 38 L66 33 L58 38 L60.5 29.5 L53.5 23.5 L62.5 22.5 Z"
              fill="#F2B33D"
            />
            <path
              d="M136 14 L139.5 22.5 L148.5 23.5 L141.5 29.5 L144 38 L136 33 L128 38 L130.5 29.5 L123.5 23.5 L132.5 22.5 Z"
              fill="#F2B33D"
            />
            <path
              d="M78 164 C74 172 72 178 70 182 M100 166 V184 M122 164 C126 172 128 178 130 182"
              fill="none"
              strokeWidth="6"
            />
            <path
              d="M100 58 C150 58 166 104 152 140 C144 162 124 170 100 170 C76 170 56 162 48 140 C34 104 50 58 100 58 Z"
              fill="#A99BD6"
            />
            <ellipse cx="100" cy="138" rx="30" ry="22" fill="#CBC1EA" stroke="none" />
            {wave && (
              <g>
                <path d="M150 120 C166 112 172 98 170 86" fill="none" strokeWidth="9" />
                <path d="M150 120 C166 112 172 98 170 86" fill="none" stroke="#A99BD6" strokeWidth="5" />
              </g>
            )}
            <circle cx="100" cy="100" r="22" fill="#FFFFFF" />
            <circle cx="103" cy="102" r="10" fill="#1C2140" stroke="none" />
            <circle cx="106" cy="98" r="3.5" fill="#FFFFFF" stroke="none" />
            <circle cx="72" cy="120" r="7" fill="#E9826B" opacity="0.5" stroke="none" />
            <circle cx="128" cy="120" r="7" fill="#E9826B" opacity="0.5" stroke="none" />
            <path d="M88 128 Q100 138 112 128" fill="none" stroke="#7A3B2E" strokeWidth="3" />
          </g>
        )}
        {variant === "cat" && (
          <g>
            <ellipse cx="100" cy="188" rx="44" ry="6" fill="#1C2140" opacity="0.12" stroke="none" />
            <path d="M134 168 C170 168 180 132 160 112" fill="none" strokeWidth="12" />
            <path d="M134 168 C170 168 180 132 160 112" fill="none" stroke="#F4A259" strokeWidth="7" />
            <path d="M68 124 C58 150 64 182 100 184 C136 182 142 150 132 124 Z" fill="#F4A259" />
            <ellipse cx="100" cy="156" rx="18" ry="20" fill="#FCEFD2" stroke="none" />
            <path
              d="M58 64 L66 24 L92 48 Q100 46 108 48 L134 24 L142 64 C158 88 150 122 100 124 C50 122 42 88 58 64 Z"
              fill="#F4A259"
            />
            <path d="M68 34 L72 50 L82 44 Z M132 34 L128 50 L118 44 Z" fill="#E9826B" stroke="none" />
            <path d="M90 58 L94 70 M100 56 V70 M110 58 L106 70" fill="none" stroke="#C45A00" strokeWidth="3" />
            <ellipse cx="82" cy="88" rx="9" ry="11" fill="#3E6B4D" />
            <ellipse cx="118" cy="88" rx="9" ry="11" fill="#3E6B4D" />
            <circle cx="85" cy="84" r="3" fill="#FFFFFF" stroke="none" />
            <circle cx="121" cy="84" r="3" fill="#FFFFFF" stroke="none" />
            <path d="M95 102 H105 L100 108 Z" fill="#E9826B" />
            <path d="M92 112 Q100 118 108 112" fill="none" stroke="#7A3B2E" strokeWidth="3" />
            <path d="M56 100 H36 M56 108 L38 116 M144 100 H164 M144 108 L162 116" fill="none" strokeWidth="2" />
            {wave && (
              <g>
                <path d="M130 136 C146 128 152 114 150 102" fill="none" strokeWidth="12" />
                <path d="M130 136 C146 128 152 114 150 102" fill="none" stroke="#F4A259" strokeWidth="7" />
              </g>
            )}
          </g>
        )}
        {variant === "robot" && (
          <g>
            <ellipse cx="100" cy="190" rx="44" ry="6" fill="#1C2140" opacity="0.12" stroke="none" />
            <path d="M78 170 V186 M122 170 V186" fill="none" strokeWidth="8" />
            <path d="M58 116 L40 104" fill="none" strokeWidth="8" />
            {wave ? (
              <path d="M142 116 L162 92" fill="none" strokeWidth="8" />
            ) : (
              <path d="M142 116 L160 130" fill="none" strokeWidth="8" />
            )}
            <rect x="56" y="98" width="88" height="74" rx="18" fill="#7FC4BB" />
            <rect x="74" y="116" width="52" height="30" rx="10" fill="#DDF3EF" />
            <circle cx="88" cy="131" r="5" fill="#E9826B" stroke="none" />
            <circle cx="112" cy="131" r="5" fill="#F2B33D" stroke="none" />
            <path d="M100 44 V24" fill="none" />
            <path d="M96 8 A11 11 0 1 0 110 22 A9 9 0 0 1 96 8 Z" fill="#F2B33D" />
            <rect x="62" y="42" width="76" height="58" rx="20" fill="#7FC4BB" />
            <rect x="74" y="56" width="52" height="32" rx="12" fill="#1C2140" />
            <circle cx="88" cy="72" r="6" fill="#FCEFD2" stroke="none" />
            <circle cx="112" cy="72" r="6" fill="#FCEFD2" stroke="none" />
            <path d="M92 82 Q100 86 108 82" fill="none" stroke="#FCEFD2" strokeWidth="2.5" />
          </g>
        )}
      </g>
    </svg>
  );
}

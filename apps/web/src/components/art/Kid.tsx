/** Child figure: design part `Kid` (design/canvas/Kid.dc.html). Placeholder art until generated characters exist. */

export type KidLook = {
  skin?: string;
  hair?: string;
  outfit?: string;
  hairStyle?: "short" | "long" | "curly";
  hijab?: boolean;
  hijabColor?: string;
  pose?: "front" | "wave" | "tilt";
  cap?: boolean;
};

type Props = KidLook & { look?: "art" | "photo"; className?: string; label?: string };

export function Kid({
  skin = "#E8B98F",
  hair = "#3A2A22",
  outfit = "#5B6FC0",
  hairStyle = "short",
  hijab = false,
  hijabColor = "#A99BD6",
  pose = "front",
  cap = false,
  look = "art",
  className = "block h-auto w-full",
  label,
}: Props) {
  const photo = look === "photo";
  const ink = photo ? "none" : "#1C2140";
  return (
    <svg
      viewBox="0 0 240 280"
      preserveAspectRatio="xMidYMid meet"
      className={className}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      {photo && (
        <>
          <defs>
            <filter id="kp-desat">
              <feColorMatrix type="saturate" values="0.3" />
            </filter>
          </defs>
          <rect width="240" height="280" fill="#D9D3C7" />
          <circle cx="150" cy="90" r="120" fill="#E8E3D8" />
        </>
      )}
      <g filter={photo ? "url(#kp-desat)" : undefined}>
        <path
          d="M36 280 C36 222 78 204 120 204 C162 204 204 222 204 280 Z"
          fill={outfit}
          stroke={ink}
          strokeWidth="2.5"
        />
        <path
          d="M100 206 L120 230 L140 206"
          fill="none"
          stroke="#FFFDF8"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.7"
        />
        {pose === "wave" && (
          <g>
            <path
              d="M170 232 C192 214 202 192 204 170"
              fill="none"
              stroke={outfit}
              strokeWidth="24"
              strokeLinecap="round"
            />
            <circle cx="205" cy="160" r="13" fill={skin} stroke={ink} strokeWidth="2.5" />
          </g>
        )}
        <rect x="106" y="168" width="28" height="42" rx="12" fill={skin} />
        <g transform={pose === "tilt" ? "rotate(-9 120 150)" : undefined}>
          {hijab && (
            <path
              d="M42 124 A78 82 0 0 1 198 124 L206 236 C170 256 70 256 34 236 Z"
              fill={hijabColor}
              stroke={ink}
              strokeWidth="2.5"
            />
          )}
          {!hijab && <path d="M60 126 A60 66 0 0 1 180 126 L184 152 L56 152 Z" fill={hair} />}
          {!hijab && hairStyle === "long" && (
            <path
              d="M58 120 C50 170 54 200 70 214 L92 200 L86 130 Z M182 120 C190 170 186 200 170 214 L148 200 L154 130 Z"
              fill={hair}
              stroke={ink}
              strokeWidth="2.5"
            />
          )}
          {!hijab && (
            <>
              <circle cx="68" cy="132" r="11" fill={skin} stroke={ink} strokeWidth="2.5" />
              <circle cx="172" cy="132" r="11" fill={skin} stroke={ink} strokeWidth="2.5" />
            </>
          )}
          <ellipse cx="120" cy="128" rx="52" ry="58" fill={skin} stroke={ink} strokeWidth="2.5" />
          {hijab && (
            <path
              d="M66 120 C66 64 174 64 174 120 C158 94 82 94 66 120 Z"
              fill={hijabColor}
              stroke={ink}
              strokeWidth="2.5"
            />
          )}
          {!hijab && (
            <path
              d="M64 116 C68 62 172 54 178 116 C162 98 134 90 108 100 C94 106 80 112 64 116 Z"
              fill={hair}
              stroke={ink}
              strokeWidth="2.5"
            />
          )}
          {!hijab && hairStyle === "curly" && (
            <g fill={hair} stroke={ink} strokeWidth="2.5">
              <circle cx="78" cy="88" r="16" />
              <circle cx="100" cy="72" r="17" />
              <circle cx="126" cy="68" r="17" />
              <circle cx="150" cy="76" r="16" />
              <circle cx="166" cy="96" r="14" />
            </g>
          )}
          <path
            d="M92 110 q8 -6 16 0 M132 110 q8 -6 16 0"
            fill="none"
            stroke="#3A2A22"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <ellipse cx="100" cy="128" rx="6.5" ry="8.5" fill="#1C2140" />
          <ellipse cx="140" cy="128" rx="6.5" ry="8.5" fill="#1C2140" />
          <circle cx="102.5" cy="125" r="2.2" fill="#FFFFFF" />
          <circle cx="142.5" cy="125" r="2.2" fill="#FFFFFF" />
          <circle cx="86" cy="150" r="9" fill="#E9826B" opacity="0.4" />
          <circle cx="154" cy="150" r="9" fill="#E9826B" opacity="0.4" />
          <path d="M108 154 Q120 166 132 154" fill="none" stroke="#7A3B2E" strokeWidth="3.5" strokeLinecap="round" />
          {cap && (
            <g>
              <path d="M66 70 L120 48 L174 70 L120 92 Z" fill="#16204A" stroke="#0E1530" strokeWidth="2" />
              <path d="M92 78 L92 94 C108 102 132 102 148 94 L148 78" fill="#22306A" />
              <path d="M120 70 L166 80 L166 104" fill="none" stroke="#F2B33D" strokeWidth="3" strokeLinecap="round" />
              <circle cx="166" cy="108" r="5" fill="#F2B33D" />
            </g>
          )}
        </g>
      </g>
    </svg>
  );
}

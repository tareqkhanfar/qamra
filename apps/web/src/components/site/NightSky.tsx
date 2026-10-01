/** The landing hero's twinkling sky and two shooting stars (decorative; respects the site's motion switch). */
export function NightSky() {
  const stars = [
    "M160 180 C162 194 166 198 180 200 C166 202 162 206 160 220 C158 206 154 202 140 200 C154 198 158 194 160 180 Z",
    "M700 130 C701 137 703 139 710 140 C703 141 701 143 700 150 C699 143 697 141 690 140 C697 139 699 137 700 130 Z",
    "M1210 300 C1211 307 1213 309 1220 310 C1213 311 1211 313 1210 320 C1209 313 1207 311 1200 310 C1207 309 1209 307 1210 300 Z",
    "M330 470 C331 476 333 478 339 479 C333 480 331 482 330 488 C329 482 327 480 321 479 C327 478 329 476 330 470 Z",
  ];
  const dots: [number, number, number, number][] = [
    [420, 120, 3, 0.3],
    [560, 640, 2.5, 1.4],
    [1320, 160, 3, 0.9],
    [1000, 720, 2.5, 2.1],
    [80, 560, 3, 0.5],
    [880, 200, 2, 1.8],
    [1100, 90, 2, 2.6],
    [260, 330, 2, 1.2],
    [1380, 420, 2.5, 0.2],
    [640, 300, 1.8, 2.3],
  ];
  return (
    <>
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        viewBox="0 0 1440 820"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
      >
        <g fill="#F2B33D">
          {stars.map((d, i) => (
            <path
              key={d}
              d={d}
              className="[transform-origin:center] animate-twinkle [transform-box:fill-box]"
              style={{ animationDelay: `${i * 0.55}s` }}
            />
          ))}
          {dots.map(([cx, cy, r, delay]) => (
            <circle
              key={`${cx}-${cy}`}
              cx={cx}
              cy={cy}
              r={r}
              className="[transform-origin:center] animate-twinkle [transform-box:fill-box]"
              style={{ animationDelay: `${delay}s` }}
            />
          ))}
        </g>
        <path d="M0 760 C300 700 600 740 900 760 S1300 730 1440 750 L1440 820 L0 820 Z" fill="#22306A" />
      </svg>
      <span
        aria-hidden="true"
        className="pointer-events-none absolute top-[14%] right-[18%] h-[2px] w-28 -rotate-[28deg] animate-shoot rounded-full bg-gradient-to-l from-transparent via-amber-100 to-transparent"
      />
      <span
        aria-hidden="true"
        className="pointer-events-none absolute top-[38%] left-[8%] h-[2px] w-20 -rotate-[28deg] animate-shoot rounded-full bg-gradient-to-l from-transparent via-amber-300 to-transparent [animation-delay:7.5s]"
      />
    </>
  );
}

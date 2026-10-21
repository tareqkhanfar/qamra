import type { ColoringTitle } from "@/lib/coloring";

const INK = "#16204A";
const AMBER = "#F2B33D";
const CORAL = "#E9826B";
const SAGE = "#7FA38A";
const BLUE = "#5B6FC0";

/** A crayon stroke: a thick, slightly see-through line, as if a child had started colouring. */
function Crayon({ d, color, width = 6 }: { d: string; color: string; width?: number }) {
  return (
    <path
      d={d}
      fill="none"
      stroke={color}
      strokeWidth={width}
      strokeLinecap="round"
      strokeLinejoin="round"
      opacity="0.75"
    />
  );
}

/** A wax crayon lying on the page (the line's motif), its tip at (x, y) pointing along `angle` degrees. */
function CrayonStick({ x, y, angle, color }: { x: number; y: number; angle: number; color: string }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${angle})`}>
      <path d="M0 0 L9 -4.5 H40 V4.5 H9 Z" fill={color} stroke={INK} strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M16 -4.5 V4.5 M33 -4.5 V4.5" stroke={INK} strokeWidth="1.2" />
    </g>
  );
}

function Letters() {
  return (
    <>
      <Crayon d="M34 54 l14 -8 l-8 16 l18 -12 l-8 16 l18 -12 l-6 12" color={AMBER} width={7} />
      <text
        x="60"
        y="96"
        textAnchor="middle"
        fontSize="86"
        fontFamily="IBM Plex Sans Arabic, sans-serif"
        fontWeight="700"
        fill="none"
        stroke={INK}
        strokeWidth="2.2"
        strokeLinejoin="round"
      >
        ب
      </text>
      {/* three small pictures under the letter: a duck, a house, a star */}
      <g fill="#FFFFFF" stroke={INK} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 138 q0 -10 10 -10 q4 -8 10 -4 q-2 4 -6 5 q6 3 6 9 q0 6 -10 6 h-4 q-6 0 -6 -6 z" />
        <path d="M50 146 V132 L60 124 L70 132 V146 Z M57 146 V138 H63 V146" />
        <path d="M92 124 l3.5 7 l7.5 1 l-5.5 5 l1.5 7.5 l-7 -3.5 l-7 3.5 l1.5 -7.5 l-5.5 -5 l7.5 -1 z" />
      </g>
      <Crayon d="M86 132 l10 0" color={AMBER} width={4} />
      <path d="M16 154 H40 M48 154 H72 M80 154 H104" stroke="#E4D6BC" strokeWidth="1.5" />
    </>
  );
}

function Palestine() {
  return (
    <>
      {/* the sun */}
      <circle cx="96" cy="26" r="9" fill="#FFFFFF" stroke={INK} strokeWidth="1.8" />
      <path
        d="M96 11 V7 M96 41 V45 M81 26 H77 M111 26 H115 M85.5 15.5 L83 13 M106.5 36.5 L109 39 M106.5 15.5 L109 13"
        stroke={INK}
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      {/* the Dome of the Rock: the gold dome, the drum, the octagon's arches */}
      <Crayon d="M47 62 q13 -14 26 0 M46 66 h28" color={AMBER} width={7} />
      <g fill="none" stroke={INK} strokeWidth="1.9" strokeLinejoin="round" strokeLinecap="round">
        <path d="M44 68 Q44 46 60 44 Q76 46 76 68 Z" />
        <path d="M60 44 V36 M57 36 a3 3 0 1 0 6 0" />
        <path d="M42 68 H78 V76 H42 Z" />
        <path d="M28 76 H92 V100 H28 Z" />
        <path d="M34 100 V88 a4 4 0 0 1 8 0 V100 M48 100 V88 a4 4 0 0 1 8 0 V100 M64 100 V88 a4 4 0 0 1 8 0 V100 M78 100 V88 a4 4 0 0 1 8 0 V100" />
        <path d="M28 82 H92" strokeDasharray="2 3" />
      </g>
      {/* an olive twig and an orange */}
      <g stroke={INK} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 124 Q38 112 66 120" fill="none" />
        <ellipse cx="26" cy="113" rx="7" ry="3" transform="rotate(-30 26 113)" fill="#FFFFFF" />
        <ellipse cx="34" cy="125" rx="7" ry="3" transform="rotate(25 34 125)" fill="#FFFFFF" />
        <ellipse cx="46" cy="109" rx="7" ry="3" transform="rotate(-20 46 109)" fill="#FFFFFF" />
        <ellipse cx="54" cy="124" rx="7" ry="3" transform="rotate(20 54 124)" fill="#FFFFFF" />
        <circle cx="40" cy="118" r="3" fill={SAGE} />
        <circle cx="60" cy="116" r="3" fill="#FFFFFF" />
        <circle cx="94" cy="122" r="10" fill="#FFFFFF" />
        <path d="M94 112 q5 -6 10 -4 q-3 6 -10 4" fill="#FFFFFF" />
      </g>
      <Crayon d="M88 118 l10 -2 M87 124 l13 -3" color={CORAL} width={4} />
      {/* the sea of Jaffa */}
      <path
        d="M10 146 q7 -6 14 0 t14 0 t14 0 t14 0 t14 0 t14 0 t14 0 M16 156 q7 -6 14 0 t14 0 t14 0 t14 0 t14 0 t14 0"
        fill="none"
        stroke={INK}
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <Crayon d="M20 152 h28" color={BLUE} width={4} />
    </>
  );
}

function Ramadan() {
  return (
    <>
      {/* the crescent and stars */}
      <path
        d="M98 14 a14 14 0 1 0 6 25 a11 11 0 1 1 -6 -25 z"
        fill="#FFFFFF"
        stroke={INK}
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <Crayon d="M90 24 q-3 8 2 14" color={AMBER} width={5} />
      <g fill="#FFFFFF" stroke={INK} strokeWidth="1.5" strokeLinejoin="round">
        <path d="M22 22 l2.5 5 l5.5 .8 l-4 3.8 l1 5.4 l-5 -2.6 l-5 2.6 l1 -5.4 l-4 -3.8 l5.5 -.8 z" />
        <path d="M74 12 l1.6 3.2 l3.5 .5 l-2.5 2.4 l.6 3.5 l-3.2 -1.7 l-3.2 1.7 l.6 -3.5 l-2.5 -2.4 l3.5 -.5 z" />
      </g>
      {/* the lantern */}
      <g fill="#FFFFFF" stroke={INK} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round">
        <circle cx="60" cy="38" r="4" />
        <path d="M46 56 L60 42 L74 56 Z" />
        <path d="M44 56 H76 L82 78 L76 112 H44 L38 78 Z" />
        <path d="M60 56 V112 M41 78 H79" fill="none" />
        <path d="M46 112 H74 V119 H46 Z" />
        <path d="M54 119 L60 126 L66 119" fill="none" />
      </g>
      <path d="M60 70 q7 8 0 16 q-7 -8 0 -16 z" fill={AMBER} stroke={INK} strokeWidth="1.4" />
      <Crayon d="M48 92 l8 -6 l-4 12 l8 -6" color={CORAL} width={4} />
      {/* a mosque on the horizon */}
      <g fill="#FFFFFF" stroke={INK} strokeWidth="1.7" strokeLinejoin="round" strokeLinecap="round">
        <path d="M30 156 V146 Q30 136 40 134 Q50 136 50 146 V156" />
        <path d="M58 156 V128 L61 122 L64 128 V156" />
        <path d="M70 156 V148 Q70 142 76 141 Q82 142 82 148 V156" />
      </g>
      <path d="M12 156 H108" stroke={INK} strokeWidth="1.7" strokeLinecap="round" />
    </>
  );
}

function Sketchbook() {
  return (
    <>
      <rect
        x="14"
        y="22"
        width="92"
        height="132"
        rx="8"
        fill="none"
        stroke={INK}
        strokeWidth="1.4"
        strokeDasharray="4 4"
      />
      {/* a half-finished flower: drawn petals and dotted ones to trace */}
      <g fill="#FFFFFF" stroke={INK} strokeWidth="2" strokeLinecap="round">
        <circle cx="60" cy="72" r="7" />
        <ellipse cx="60" cy="56" rx="7" ry="10" />
        <ellipse cx="76" cy="72" rx="10" ry="7" />
      </g>
      <g fill="none" stroke={INK} strokeWidth="2" strokeLinecap="round" strokeDasharray="0.1 5">
        <ellipse cx="60" cy="88" rx="7" ry="10" />
        <ellipse cx="44" cy="72" rx="10" ry="7" />
      </g>
      <path d="M60 98 V124 M60 112 q10 -10 18 -6" fill="none" stroke={INK} strokeWidth="2" strokeLinecap="round" />
      <Crayon d="M54 54 l6 -4 l-2 8 l6 -4" color={CORAL} width={4} />
      <Crayon d="M26 136 q10 -14 20 0 t20 0 t20 0" color={SAGE} width={4} />
      <CrayonStick x={74} y={40} angle={-20} color={AMBER} />
    </>
  );
}

/** The four books' line drawings, one per title (decorative). */
const ART: Record<ColoringTitle, () => React.ReactElement> = {
  letters: Letters,
  palestine: Palestine,
  ramadan: Ramadan,
  sketchbook: Sketchbook,
};

/**
 * A coloring page drawn as line art (black outlines on white, a few crayon strokes): what a book looks like while
 * its real pages are not exported yet, and the line's little drawing in the shop.
 */
export function ColoringArt({ title, className = "" }: { title: ColoringTitle; className?: string }) {
  const Art = ART[title];
  return (
    <svg viewBox="0 0 120 170" className={className} aria-hidden="true" focusable="false">
      <Art />
    </svg>
  );
}

/** The line's own motif (no title): two crossed crayons over a flower outline. */
export function ColoringMotif({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 96 124" className={className} aria-hidden="true" focusable="false">
      <rect x="1" y="1" width="94" height="122" rx="6" fill="#FFFFFF" stroke="#E4D6BC" />
      <g fill="#FFFFFF" stroke={INK} strokeWidth="2.2" strokeLinecap="round">
        <circle cx="48" cy="48" r="7" />
        <ellipse cx="48" cy="32" rx="7" ry="9" />
        <ellipse cx="64" cy="48" rx="9" ry="7" />
        <ellipse cx="48" cy="64" rx="7" ry="9" />
        <ellipse cx="32" cy="48" rx="9" ry="7" />
      </g>
      <Crayon d="M42 28 l6 -4 l-2 8 l6 -4" color={AMBER} width={4} />
      <CrayonStick x={20} y={96} angle={-18} color={CORAL} />
      <CrayonStick x={24} y={108} angle={-4} color={SAGE} />
    </svg>
  );
}

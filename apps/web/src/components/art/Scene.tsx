/**
 * Book scene: design part `Scene` (backdrop + child + optional companion). Fluid: it fills its
 * container's width at `ratio` (w/h); the child is `kidScale` of the shorter side, as in the design.
 */
import type { CSSProperties } from "react";
import { Companion, type CompanionVariant } from "./Companion";
import { Kid, type KidLook } from "./Kid";

export type SceneTheme = "night" | "garden" | "sea" | "space" | "grad";

/** Shape of the catalog `art` object the API returns (snake_case). */
export type SceneArt = {
  scene: SceneTheme;
  outfit?: string;
  skin?: string;
  hair?: string;
  hair_style?: "short" | "long" | "curly";
  hijab?: boolean;
  hijab_color?: string;
  cap?: boolean;
  pose?: "front" | "wave" | "tilt";
  companion?: "" | CompanionVariant;
  kid_scale?: number;
};

type Props = KidLook & {
  theme: SceneTheme;
  ratio?: number;
  kidScale?: number;
  companion?: "" | CompanionVariant;
  compPose?: "front" | "wave";
  className?: string;
  kidClassName?: string;
  style?: CSSProperties;
};

export function fromArt(art: SceneArt): Omit<Props, "ratio" | "className" | "style"> {
  return {
    theme: art.scene,
    outfit: art.outfit,
    skin: art.skin,
    hair: art.hair,
    hairStyle: art.hair_style,
    hijab: art.hijab,
    hijabColor: art.hijab_color,
    cap: art.cap,
    pose: art.pose,
    companion: art.companion,
    kidScale: art.kid_scale,
  };
}

export function Scene({
  theme,
  ratio = 1,
  kidScale = 0.55,
  companion = "",
  compPose = "wave",
  outfit = "#E9826B",
  className = "",
  kidClassName = "",
  style,
  ...kid
}: Props) {
  const kidPct = kidScale * Math.min(1, 1 / ratio) * 100;
  return (
    <div className={`relative overflow-hidden bg-night-900 ${className}`} style={{ aspectRatio: ratio, ...style }}>
      <svg
        viewBox="0 0 480 480"
        preserveAspectRatio="xMidYMax slice"
        className="absolute inset-0 size-full"
        aria-hidden="true"
      >
        {theme === "night" && (
          <g>
            <rect width="480" height="480" fill="#1F2C63" />
            <rect width="480" height="220" fill="#16204A" />
            <circle cx="360" cy="96" r="44" fill="#FCEFD2" />
            <circle cx="380" cy="84" r="40" fill="#16204A" />
            <g fill="#F2B33D">
              <path d="M90 60 C92 74 96 78 110 80 C96 82 92 86 90 100 C88 86 84 82 70 80 C84 78 88 74 90 60 Z" />
              <path d="M250 120 C251 127 253 129 260 130 C253 131 251 133 250 140 C249 133 247 131 240 130 C247 129 249 127 250 120 Z" />
              <circle cx="170" cy="40" r="3" />
              <circle cx="300" cy="50" r="2.5" />
              <circle cx="40" cy="150" r="2.5" />
              <circle cx="440" cy="190" r="3" />
              <circle cx="200" cy="170" r="2" />
            </g>
            <path d="M0 330 C90 280 170 300 250 320 S400 290 480 310 L480 480 L0 480 Z" fill="#22306A" />
            <path d="M380 300 L380 250 L410 226 L440 250 L440 300 Z" fill="#0E1530" />
            <rect x="402" y="258" width="16" height="18" rx="3" fill="#F2B33D" />
            <path d="M0 380 C120 350 220 370 300 390 S430 370 480 380 L480 480 L0 480 Z" fill="#0E1530" />
          </g>
        )}
        {theme === "garden" && (
          <g>
            <rect width="480" height="480" fill="#FCEFD2" />
            <circle cx="96" cy="100" r="46" fill="#F2B33D" />
            <path d="M0 300 C100 250 200 270 300 280 S420 250 480 260 L480 480 L0 480 Z" fill="#A9C7B1" />
            <rect x="378" y="220" width="12" height="80" rx="5" fill="#6B4E34" />
            <circle cx="366" cy="210" r="30" fill="#7FA38A" />
            <circle cx="400" cy="200" r="32" fill="#6E9579" />
            <circle cx="384" cy="176" r="26" fill="#7FA38A" />
            <g fill="#3E6B4D">
              <circle cx="372" cy="200" r="3.5" />
              <circle cx="398" cy="186" r="3.5" />
              <circle cx="410" cy="214" r="3.5" />
              <circle cx="360" cy="222" r="3.5" />
            </g>
            <rect x="70" y="236" width="10" height="64" rx="4" fill="#6B4E34" />
            <circle cx="62" cy="228" r="24" fill="#6E9579" />
            <circle cx="90" cy="222" r="24" fill="#7FA38A" />
            <circle cx="76" cy="202" r="20" fill="#6E9579" />
            <path d="M0 370 C120 340 240 360 330 372 S440 356 480 362 L480 480 L0 480 Z" fill="#7FA38A" />
            <g fill="#E9826B">
              <circle cx="150" cy="360" r="5" />
              <circle cx="330" cy="380" r="5" />
              <circle cx="420" cy="400" r="5" />
            </g>
          </g>
        )}
        {theme === "sea" && (
          <g>
            <rect width="480" height="480" fill="#E4E8F7" />
            <circle cx="380" cy="100" r="40" fill="#F2B33D" />
            <path
              d="M40 90 q16 -14 32 0 q16 -14 32 0"
              fill="none"
              stroke="#5A4A9C"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <path d="M0 280 L480 280 L480 480 L0 480 Z" fill="#5B6FC0" />
            <path d="M340 250 L420 250 L404 276 L356 276 Z" fill="#E9826B" />
            <path d="M380 250 L380 190 L412 244 Z" fill="#FFFDF8" />
            <path
              d="M0 300 q30 -16 60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0 t60 0"
              fill="none"
              stroke="#E4E8F7"
              strokeWidth="4"
              strokeLinecap="round"
            />
            <path d="M0 360 C120 330 240 350 330 364 S440 350 480 356 L480 480 L0 480 Z" fill="#F3EAD8" />
          </g>
        )}
        {theme === "space" && (
          <g>
            <rect width="480" height="480" fill="#0E1530" />
            <circle cx="110" cy="120" r="54" fill="#E9826B" />
            <ellipse
              cx="110"
              cy="124"
              rx="92"
              ry="18"
              fill="none"
              stroke="#F4B3A2"
              strokeWidth="6"
              transform="rotate(-14 110 124)"
            />
            <circle cx="380" cy="70" r="18" fill="#CBC1EA" />
            <g fill="#F2B33D">
              <path d="M300 150 C302 162 305 165 316 167 C305 169 302 172 300 184 C298 172 295 169 284 167 C295 165 298 162 300 150 Z" />
              <circle cx="220" cy="60" r="3" />
              <circle cx="440" cy="180" r="3" />
              <circle cx="40" cy="240" r="2.5" />
              <circle cx="250" cy="230" r="2" />
              <circle cx="420" cy="290" r="2.5" />
            </g>
            <path d="M0 380 C120 344 360 344 480 380 L480 480 L0 480 Z" fill="#CBC1EA" />
            <g fill="#A99BD6">
              <circle cx="120" cy="400" r="12" />
              <circle cx="360" cy="420" r="16" />
            </g>
          </g>
        )}
        {theme === "grad" && (
          <g>
            <rect width="480" height="480" fill="#FBF6EC" />
            <path d="M0 40 Q240 110 480 40" fill="none" stroke="#9A620A" strokeWidth="2" />
            <path d="M30 46 L50 46 L40 70 Z" fill="#E9826B" />
            <path d="M90 60 L110 62 L98 86 Z" fill="#7FA38A" />
            <path d="M150 70 L172 72 L158 96 Z" fill="#A99BD6" />
            <path d="M212 76 L234 76 L222 100 Z" fill="#F2B33D" />
            <path d="M274 76 L296 74 L286 98 Z" fill="#E9826B" />
            <path d="M336 70 L358 68 L348 92 Z" fill="#7FA38A" />
            <path d="M398 60 L418 56 L412 80 Z" fill="#A99BD6" />
            <path d="M450 46 L470 44 L464 68 Z" fill="#F2B33D" />
            <g fill="#F2B33D">
              <path d="M80 170 C82 182 85 185 96 187 C85 189 82 192 80 204 C78 192 75 189 64 187 C75 185 78 182 80 170 Z" />
              <path d="M400 150 C401 158 403 160 410 161 C403 162 401 164 400 172 C399 164 397 162 390 161 C397 160 399 158 400 150 Z" />
            </g>
            <rect x="0" y="380" width="480" height="100" fill="#16204A" />
            <rect x="0" y="372" width="480" height="12" fill="#22306A" />
          </g>
        )}
      </svg>
      <div className="absolute inset-x-0 bottom-0 flex items-end justify-center gap-1">
        {companion && (
          <div style={{ width: `${kidPct * 0.78}%`, marginBottom: `${kidPct * 0.02}%` }}>
            <Companion variant={companion} pose={compPose} />
          </div>
        )}
        <div style={{ width: `${kidPct}%` }} className={kidClassName}>
          <Kid outfit={outfit} {...kid} />
        </div>
      </div>
    </div>
  );
}

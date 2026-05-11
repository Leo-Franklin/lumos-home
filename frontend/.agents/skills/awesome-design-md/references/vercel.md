# Vercel Design System

**Brand:** Vercel
**Archetype:** Cold monochrome, developer-first
**Atmosphere:** Absolute restraint. Black and white. Every element earns its place. Speed and precision above all.

---

## Color Palette

### Monochrome (Core)
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--color-bg` | `#FFFFFF` | `#000000` | Canvas |
| `--color-surface` | `#FAFAFA` | `#111111` | Cards |
| `--color-surface-raised` | `#F5F5F5` | `#1A1A1A` | Hover states, raised cards |
| `--color-border` | `#EAEAEA` | `#2A2A2A` | Dividers |
| `--color-border-subtle` | `#F5F5F5` | `#1F1F1F` | Very light |
| `--color-text-primary` | `#000000` | `#EDEDED` | Headings, body |
| `--color-text-secondary` | `#444444` | `#888888` | Supporting |
| `--color-text-muted` | `#888888` | `#444444` | Metadata |

### Semantic (Minimal Accent)
| Token | Value | Usage |
|-------|-------|-------|
| `--color-success` | `#0070F3` | Deploys succeeded (uses blue) |
| `--color-success-green` | `#50E3C2` | Build success in terminal |
| `--color-error` | `#FF0000` | Build errors |
| `--color-warning` | `#F5A623` | Warnings |
| `--color-info` | `#0070F3` | Information |

> **Note:** Vercel uses almost no color. Status is communicated through shape and monochrome weight, with blue as the sole accent in light mode.

---

## Typography

**Font:** Geist (preferred), Inter, or system-ui/sans-serif

```
--font-sans: "Geist", "Inter", -apple-system, sans-serif;
--font-mono: "Geist Mono", "Fira Code", monospace;
```

| Token | Size | Weight | Line-height | Letter-spacing |
|-------|------|--------|-------------|----------------|
| `--text-xs` | 12px | 400 | 1.4 | 0 |
| `--text-sm` | 14px | 400 | 1.5 | 0 |
| `--text-base` | 16px | 400 | 1.6 | 0 |
| `--text-lg` | 18px | 500 | 1.5 | -0.01em |
| `--text-xl` | 20px | 600 | 1.4 | -0.02em |
| `--text-2xl` | 24px | 600 | 1.3 | -0.03em |
| `--text-3xl` | 32px | 700 | 1.2 | -0.04em |
| `--text-4xl` | 40px | 700 | 1.1 | -0.04em |

---

## Spacing

Base: **8px**
Scale: `4, 8, 12, 16, 24, 32, 40, 48, 64, 80, 96, 128`

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `4px` | Chips, tiny elements |
| `--radius-md` | `6px` | Buttons, inputs |
| `--radius-lg` | `8px` | Cards |
| `--radius-xl` | `12px` | Modals |
| `--radius-full` | `9999px` | Pills |

---

## Shadows

Minimal. Rely on borders in light mode, near-invisible in dark.

```css
/* Light mode */
--shadow-sm: 0 1px 2px rgba(0,0,0,0.04), 0 1px 6px rgba(0,0,0,0.04);
--shadow-md: 0 4px 12px rgba(0,0,0,0.08);
--shadow-lg: 0 8px 30px rgba(0,0,0,0.12);

/* Dark mode */
--shadow-sm: 0 1px 2px rgba(0,0,0,0.5);
--shadow-md: 0 4px 12px rgba(0,0,0,0.6);
```

---

## Components

### Buttons
```
Primary:    bg black (light) / white (dark), text inverse, radius 6px, height 32px, px 14px
Secondary:  border 1px --color-border, bg transparent, text-primary
Ghost:      no border, text-secondary, hover bg --color-surface-raised
```

Font size for buttons: `14px`, weight `500`

### Cards
```
bg: --color-surface
border: 1px solid --color-border
radius: 8px
padding: 16px or 24px
shadow: none (border only)
hover: bg --color-surface-raised (transition 0.1s)
```

### Code Blocks / Terminal
```
bg: #0A0A0A
border: 1px solid #333
text: #50E3C2 (success output) / #FF6B6B (error) / #EDEDED (neutral)
font: --font-mono
radius: 6px
```

### Navigation
```
Sidebar: bg --color-surface, border-right 1px --color-border
Nav item: text-secondary, hover text-primary + bg --color-surface-raised
Active: text-primary, weight 500
Icon: 16px, text-muted
```

---

## Design Guardrails

**DO:**
- Embrace whitespace — negative space is a design choice, not emptiness
- Default to dark mode as the primary experience
- Use borders over shadows for card separation
- Let content speak — remove every decoration that doesn't add information

**DON'T:**
- Don't add color except for status indicators
- Don't use more than 2 font weights on a single page
- Don't add shadows in dark mode — they're invisible and add noise
- Don't round corners aggressively — Vercel prefers sharp precision (4-8px max)

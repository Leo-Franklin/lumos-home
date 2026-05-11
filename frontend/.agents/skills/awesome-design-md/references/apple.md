# Apple Design System

**Brand:** Apple
**Archetype:** Premium spatial computing, extreme restraint
**Atmosphere:** Invisible sophistication. Hardware and software as one. Every pixel designed as if it costs $1. Calm, clear, effortless.

---

## Color Palette

### System Colors (iOS/macOS Inspired)
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--color-primary` | `#007AFF` | `#0A84FF` | Blue — links, CTAs |
| `--color-secondary` | `#5AC8FA` | `#64D2FF` | Teal |
| `--color-success` | `#34C759` | `#30D158` | Green |
| `--color-warning` | `#FF9500` | `#FF9F0A` | Orange |
| `--color-error` | `#FF3B30` | `#FF453A` | Red |
| `--color-purple` | `#AF52DE` | `#BF5AF2` | Purple |
| `--color-pink` | `#FF2D55` | `#FF375F` | Pink |

### Gray Scale
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--color-bg` | `#F2F2F7` | `#000000` | System background |
| `--color-bg-secondary` | `#FFFFFF` | `#1C1C1E` | Grouped background |
| `--color-bg-tertiary` | `#F2F2F7` | `#2C2C2E` | Tertiary |
| `--color-surface` | `#FFFFFF` | `#1C1C1E` | Cards |
| `--color-separator` | `rgba(60,60,67,0.29)` | `rgba(84,84,88,0.65)` | Dividers |
| `--color-text-primary` | `#000000` | `#FFFFFF` | Labels |
| `--color-text-secondary` | `rgba(60,60,67,0.6)` | `rgba(235,235,245,0.6)` | Secondary |
| `--color-text-tertiary` | `rgba(60,60,67,0.3)` | `rgba(235,235,245,0.3)` | Tertiary |
| `--color-text-placeholder` | `rgba(60,60,67,0.3)` | `rgba(235,235,245,0.3)` | Placeholder |

### Material Effects
```css
/* Vibrancy / Glass */
--material-thin: blur(8px) saturate(1.8) brightness(1.1);
--material-regular: blur(20px) saturate(1.8) brightness(1.05);
--material-thick: blur(40px) saturate(1.8);
--material-bg-thin: rgba(255,255,255,0.5);
--material-bg-regular: rgba(255,255,255,0.72);
/* Dark */
--material-bg-thin-dark: rgba(30,30,30,0.5);
--material-bg-regular-dark: rgba(30,30,30,0.72);
```

---

## Typography

**Font:** SF Pro (system default on Apple, fallback to system-ui)

```css
--font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
--font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif;
--font-mono: "SF Mono", Menlo, monospace;
```

| Style | Size | Weight | Line-height | Letter-spacing |
|-------|------|--------|-------------|----------------|
| Large Title | 34px | 700 | 1.2 | 0.011em |
| Title 1 | 28px | 700 | 1.2 | 0.011em |
| Title 2 | 22px | 700 | 1.3 | 0.016em |
| Title 3 | 20px | 600 | 1.3 | 0.019em |
| Headline | 17px | 600 | 1.3 | -0.024em |
| Body | 17px | 400 | 1.5 | -0.024em |
| Callout | 16px | 400 | 1.5 | -0.02em |
| Subhead | 15px | 400 | 1.5 | -0.016em |
| Footnote | 13px | 400 | 1.5 | -0.006em |
| Caption 1 | 12px | 400 | 1.4 | 0 |

---

## Spacing

Base: **8px** (Apple uses an 8pt grid)
Scale: `4, 8, 12, 16, 20, 24, 32, 44, 48, 64, 80`

Standard cell height: `44px` (Apple minimum touch target)
Navigation bar height: `44px` + safe area
Tab bar height: `49px` + safe area

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-xs` | `6px` | Chips, tags |
| `--radius-sm` | `8px` | Small cards |
| `--radius-md` | `12px` | Buttons, form elements |
| `--radius-lg` | `16px` | Standard cards |
| `--radius-xl` | `20px` | Modals, sheets |
| `--radius-2xl` | `28px` | Large panels |
| `--radius-full` | `9999px` | Pills, toggle switches |

---

## Shadows

```css
/* Light mode */
--shadow-sm:  0 1px 4px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.04);
--shadow-md:  0 4px 16px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.06);
--shadow-lg:  0 8px 32px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.08);

/* Dark mode (very subtle) */
--shadow-sm:  0 1px 4px rgba(0,0,0,0.4);
--shadow-md:  0 4px 16px rgba(0,0,0,0.5);
```

---

## Components

### Cells / List Rows
```
Height: 44px minimum
Bg: --color-surface
Separator: 1px --color-separator (inset 16px left)
Disclosure arrow: 8px, text-tertiary
```

### Buttons
```
Filled:   bg --color-primary, text white, radius 12px, height 50px
Tinted:   bg rgba(0,122,255,0.15), text --color-primary
Gray:     bg --color-bg-tertiary, text-primary
Bordered: border 1.5px --color-primary, text --color-primary
```

### Cards (Grouped Lists)
```
bg: --color-surface
radius: 12px (section) / 16px (feature cards)
padding: 16px
separator between items (not around card)
```

### Glassmorphism (where applicable)
```
bg: --material-bg-regular
backdrop-filter: --material-regular
border: 1px solid rgba(255,255,255,0.2)
```

---

## Design Guardrails

**DO:**
- Use system colors — they adapt to light/dark automatically
- Keep minimum touch targets at 44×44px
- Use rounded corners generously (Apple rounds more than most)
- Prefer glass/vibrancy materials for floating UI (navigation bars, sidebars)
- Animate with `spring` physics — bouncy but controlled

**DON'T:**
- Don't use flat, border-only cards — use material/glass or opaque bg
- Don't crowd elements — generous white space is the luxury item
- Don't use web-like hover states as primary interactions
- Don't mix border-box and glass styles in the same component

# Figma Design System

**Brand:** Figma
**Archetype:** Precision design tooling
**Atmosphere:** Dense with purpose. Every pixel of chrome is a tool. White and black with a signature orange accent. Functional beauty.

---

## Color Palette

### Brand
| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#F24E1E` | Figma Orange — brand accent |
| `--color-primary-hover` | `#DA3C0A` | Hover |
| `--color-primary-subtle` | `#FDF0EC` | Light tint background |
| `--color-secondary` | `#A259FF` | Purple — components |
| `--color-tertiary` | `#1ABCFE` | Blue — prototyping |
| `--color-quaternary` | `#0ACF83` | Green — exports, assets |

### Light Mode (Default)
| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#FFFFFF` | Canvas |
| `--color-surface` | `#FFFFFF` | Panels |
| `--color-surface-hover` | `#F5F5F5` | Hover bg |
| `--color-surface-selected` | `#EAF0FF` | Selected items |
| `--color-border` | `#E5E5E5` | Dividers |
| `--color-text-primary` | `#1E1E1E` | Primary |
| `--color-text-secondary` | `#6E6E6E` | Supporting |
| `--color-text-muted` | `#AFAFAF` | Placeholder |

### Dark Mode (Figma Editor)
| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#2C2C2C` | Canvas bg |
| `--color-surface` | `#383838` | Panels |
| `--color-surface-hover` | `#454545` | Hover |
| `--color-border` | `#1E1E1E` | Dividers |
| `--color-text-primary` | `#E5E5E5` | Primary |
| `--color-text-secondary` | `#B2B2B2` | Supporting |

---

## Typography

**Font:** Inter (Figma's own design uses Inter)

```css
--font-sans: "Inter", -apple-system, sans-serif;
--font-mono: "Roboto Mono", monospace;
```

| Token | Size | Weight | Line-height |
|-------|------|--------|-------------|
| `--text-xs` | 11px | 400 | 1.4 |
| `--text-sm` | 12px | 400 | 1.5 |
| `--text-base` | 14px | 400 | 1.5 |
| `--text-lg` | 16px | 500 | 1.4 |
| `--text-xl` | 18px | 600 | 1.3 |
| `--text-2xl` | 22px | 700 | 1.3 |
| `--text-3xl` | 28px | 700 | 1.2 |

> Figma uses a compact 12–14px base font in its product UI for maximum density.

---

## Spacing

Base: **4px**
Scale: `2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48`

Toolbar height: `40px`
Panel width: `240px`
Property row height: `28px` (compact)
Section header height: `32px`

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-xs` | `2px` | Property inputs |
| `--radius-sm` | `4px` | Buttons, chips |
| `--radius-md` | `6px` | Panels |
| `--radius-lg` | `8px` | Modals, menus |
| `--radius-full` | `9999px` | Avatar, pills |

---

## Shadows

```css
--shadow-sm:  0 1px 3px rgba(0,0,0,0.1);
--shadow-md:  0 4px 12px rgba(0,0,0,0.15);
--shadow-lg:  0 8px 30px rgba(0,0,0,0.2);
--shadow-panel: 2px 0 8px rgba(0,0,0,0.08); /* Right panels */
--shadow-focus: 0 0 0 2px rgba(242,78,30,0.4); /* Orange focus */
```

---

## Components

### Toolbar
```
bg: --color-surface
height: 40px
border-bottom: 1px solid --color-border
items: 28px touch target, 4px gap
active tool: bg --color-surface-hover, text-primary
```

### Property Panel
```
width: 240px
bg: --color-surface
border: 1px solid --color-border
section header: text-xs uppercase, text-muted, 32px height
property row: 28px height, label left, value right
input: bg --color-surface-hover, border none, text-primary
```

### Buttons
```
Primary (orange): bg #F24E1E, text white, radius 6px, height 32px, px 12px
Secondary: bg transparent, border 1px --color-border, text-primary
Ghost: transparent, text-secondary, hover bg --color-surface-hover
Icon button: 28px, radius 4px, hover bg --color-surface-hover
```

### Context Menu
```
bg: --color-surface
border: 1px solid --color-border
radius: 6px
shadow: --shadow-lg
item height: 28px, px 8px
divider: 1px solid --color-border, my 4px
keyboard shortcut: float right, text-muted, text-xs
```

### Color Swatch
```
16x16px, radius 2px
border: 1px solid rgba(0,0,0,0.1)
```

---

## Design Guardrails

**DO:**
- Maximize information density — users are professionals who have learned the interface
- Use orange accent sparingly — it's for brand moments and primary CTAs only
- Keep property panels extremely compact (28px rows)
- Use keyboard shortcuts as first-class citizens (always visible in menus)

**DON'T:**
- Don't add onboarding overlays — Figma users learn by doing
- Don't round corners more than 6–8px — precision tools feel sharp
- Don't use color to decorate — only use color for semantic meaning (components=purple, prototype=blue, etc.)
- Don't add animations longer than 150ms — tool feedback must feel instant

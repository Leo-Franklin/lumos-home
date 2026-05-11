# Design Patterns Reference

Cross-cutting patterns shared across design systems in the awesome-design-md collection.

---

## Canvas Types

### Light Canvas
Clean white/near-white base. High contrast text. Used by: Stripe, Apple, Linear (light), Figma.
```
bg: #FFFFFF or #F8F8F8
surface: #FFFFFF with border
text-primary: #0A0A0A or #111
border: #E5E5E5 or #EBEBEB
```

### Dark Canvas
Near-black base. Reduced contrast for long sessions. Used by: Vercel, Cursor, Spotify.
```
bg: #000000 or #0A0A0A
surface: #111111 or #161616
text-primary: #EDEDED or #FAFAFA
border: #2A2A2A or #333
```

### Warm Canvas
Cream/warm tinted base. Approachable, editorial. Used by: Claude/Anthropic.
```
bg: #FAF8F4 or #FBF9F6
surface: #FFFFFF
text-primary: #1A1A18
border: #E8E4DD
accent: warm coral/orange
```

---

## Typography Archetypes

### Developer Sans (Vercel, Linear, Stripe)
- Font: Inter, Geist, or system-ui
- Weight range: 400–700
- Letter spacing: -0.01em to -0.03em for headings
- Feature: `font-feature-settings: "cv02", "cv03", "cv04"`

### Editorial Serif (Claude/Anthropic)
- Heading font: Tiempos, Georgia, or similar serif
- Body font: Clean sans (Inter or system)
- Weight: 300–600 for headings (lighter feels more premium)
- Warmer tone, larger line heights

### Precision Mono (Cursor, Figma)
- Mix of mono (code/data) and sans (labels)
- JetBrains Mono, Fira Code, or similar for technical content
- Optical size adjustments for small mono text

---

## Spacing Systems

### 4px Grid (most common)
`4, 8, 12, 16, 24, 32, 48, 64, 96, 128`

### 8px Grid (Spotify, Apple)
`8, 16, 24, 32, 40, 48, 64, 80, 96`

### Compact 4px Grid (Linear, Figma)
`2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48`

---

## Shadow Systems

### Flat (Vercel, Linear)
Minimal shadows, rely on borders for definition.
```css
--shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
--shadow-md: 0 2px 8px rgba(0,0,0,0.08);
```

### Classic (Stripe, Apple)
Multi-layer shadows for depth.
```css
--shadow-sm: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
--shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 10px 15px rgba(0,0,0,0.1);
--shadow-lg: 0 10px 25px rgba(0,0,0,0.1), 0 20px 48px rgba(0,0,0,0.12);
```

### Colored Glow (Cursor, dark UIs)
Shadow uses the accent color.
```css
--shadow-primary: 0 0 20px rgba(124, 58, 237, 0.3);
--shadow-sm: 0 2px 8px rgba(0,0,0,0.4);
```

---

## Color Usage Conventions

### Semantic Token Mapping
Always use semantic tokens, not raw colors:
- `--color-primary` — brand/action color (1 or 2 max per product)
- `--color-text-primary` — main readable text
- `--color-text-secondary` — supporting text, metadata
- `--color-text-muted` — placeholders, disabled, timestamps
- `--color-surface` — card/panel backgrounds
- `--color-bg` — page/canvas background
- `--color-border` — lines, outlines, dividers

### Status Colors
| Status | Light Mode | Dark Mode |
|--------|-----------|-----------|
| Success | `#16A34A` bg, `#15803D` text | `#4ADE80` text |
| Warning | `#D97706` bg, `#B45309` text | `#FCD34D` text |
| Error | `#DC2626` bg, `#B91C1C` text | `#F87171` text |
| Info | `#2563EB` bg, `#1D4ED8` text | `#60A5FA` text |

---

## Border Radius Patterns

### Sharp (Stripe, Linear)
`4px` for inputs and buttons, `6–8px` for cards
Professional, precise feeling

### Rounded (Apple, Spotify)
`8–12px` standard, `16px` for prominent cards
Friendly, consumer-grade

### Extreme (Some apps)
`20px+` for panels, `9999px` for pills
Modern, bubbly, or brand-specific

---

## Interactive State Patterns

### Button States
```
default:   bg-primary, text-white
hover:     bg-primary darken 8%
active:    bg-primary darken 15%, scale 0.98
disabled:  opacity 0.4, cursor-not-allowed
focus:     ring 2px offset 2px primary color
loading:   spinner + reduced opacity
```

### Link/Navigation States
```
default:   text-secondary
hover:     text-primary, slight bg tint
active:    text-primary, accent left border OR solid bg
```

### Input States
```
default:   border-border
focus:     border-primary + focus ring
error:     border-error + error message below
disabled:  bg-muted, text-muted, no pointer events
```

# Spotify Design System

**Brand:** Spotify
**Archetype:** Dark content-first, playful energy
**Atmosphere:** The app disappears — only music and visual rhythm remain. Dark canvas makes album art sing. Neon green as pulse.

---

## Color Palette

### Core Brand
| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#1DB954` | Spotify Green — play buttons, CTAs, active |
| `--color-primary-hover` | `#1AA34A` | Hover on green |
| `--color-primary-subtle` | `rgba(29,185,84,0.1)` | Light tint |

### Dark Canvas (Default)
| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#121212` | Base canvas |
| `--color-surface` | `#181818` | Cards, panels |
| `--color-surface-raised` | `#282828` | Hovered cards |
| `--color-surface-overlay` | `#3E3E3E` | Context menus |
| `--color-nav` | `#000000` | Sidebar, player bar |
| `--color-border` | `#333333` | Subtle dividers |

### Text
| Token | Value | Usage |
|-------|-------|-------|
| `--color-text-primary` | `#FFFFFF` | Headings, active |
| `--color-text-secondary` | `#B3B3B3` | Artists, metadata |
| `--color-text-muted` | `#535353` | Timestamps, disabled |

### Semantic
| Token | Value | Usage |
|-------|-------|-------|
| `--color-success` | `#1DB954` | Same as brand (playing) |
| `--color-error` | `#E61E32` | Remove, error |
| `--color-warning` | `#F59B23` | Caution |

---

## Typography

**Font:** Circular (proprietary), fallback to system sans

```css
--font-sans: "Circular Std", "CircularXX", Helvetica, Arial, sans-serif;
```

| Token | Size | Weight | Line-height | Notes |
|-------|------|--------|-------------|-------|
| `--text-xs` | 11px | 400 | 1.4 | Duration, metadata |
| `--text-sm` | 13px | 400 | 1.5 | Caption |
| `--text-base` | 14px | 400 | 1.5 | Body, track names |
| `--text-lg` | 16px | 700 | 1.4 | Section titles |
| `--text-xl` | 20px | 700 | 1.3 | Page headers |
| `--text-2xl` | 24px | 700 | 1.2 | — |
| `--text-3xl` | 32px | 900 | 1.1 | Artist/playlist names |
| `--text-hero` | 48–96px | 900 | 0.95 | Full-bleed hero |

> Spotify uses **900 weight** (Black) for large headers — extreme boldness is on-brand.

---

## Spacing

Base: **8px**
Scale: `4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96`

Grid layout: 8-column for main content
Card gap: `8px` or `16px`
Content padding: `24px`

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `4px` | Bars (progress, volume) |
| `--radius-md` | `8px` | Buttons, rows |
| `--radius-lg` | `12px` | — |
| `--radius-full` | `9999px` | Play button, pills |
| `--radius-cover` | `4px` | Album art (always 4px) |

---

## Shadows

Spotify rarely uses explicit shadows — elevation is communicated via background color.

```css
--shadow-card: 0 8px 24px rgba(0,0,0,0.5);
--shadow-player: 0 -2px 16px rgba(0,0,0,0.8);
--shadow-context-menu: 0 16px 48px rgba(0,0,0,0.7);
```

---

## Components

### Cards (Album / Playlist)
```
bg: --color-surface
radius: 8px
padding: 16px
hover: bg --color-surface-raised, show play button overlay
play button: 48px circle, bg --color-primary, appear on hover
album art: radius 4px (square), fills card width
```

### Navigation Sidebar
```
bg: #000000
width: 232px
item height: 40px
item padding: 0 16px
active: text-primary, weight 700
inactive: text-secondary, weight 400
active indicator: no - weight communicates state
```

### Bottom Player Bar
```
bg: #181818
border-top: 1px solid #282828
height: 90px
three-column layout: track info | controls | volume
```

### Play Button
```
Circle, 56px (normal) / 40px (compact)
bg: --color-primary (#1DB954)
icon: white
hover: scale(1.06) + brightness(1.1)
active: scale(0.96)
```

### Progress Bar
```
Track: bg #535353, radius 9999px, height 4px
Fill: bg --color-primary
Handle: 12px circle, white, appears on hover
```

---

## Design Guardrails

**DO:**
- Let album art drive the visual — use color extraction when possible
- Use 900 (Black) weight for large typographic statements
- Animate the play button at scale — it's the most important affordance
- Use green exclusively for play/active states — don't dilute it

**DON'T:**
- Don't use light mode (Spotify is a dark-mode-only product)
- Don't add borders to cards — bg color change is sufficient separation
- Don't clip album art with anything other than 4px radius
- Don't use Spotify Green (#1DB954) for anything except active/playing states

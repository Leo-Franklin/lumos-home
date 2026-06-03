# Linear Design System

**Brand:** Linear
**Archetype:** Clean dashboard, developer SaaS
**Atmosphere:** Fast, focused, and brutally efficient. Every pixel serves productivity. The gold standard for B2B SaaS dashboard design.

---

## Color Palette

### Primary
| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#5E5CE6` | Linear Purple — active states, links, CTAs |
| `--color-primary-hover` | `#4E4CCF` | Hover |
| `--color-primary-subtle` | `#EDEDFC` | Pill bg, light highlights |

### Dark Mode (Primary)
| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#161618` | Page background |
| `--color-surface` | `#1E1E20` | Cards, sidebar |
| `--color-surface-raised` | `#252528` | Hover, elevated |
| `--color-surface-overlay` | `#2C2C2F` | Modals, dropdowns |
| `--color-border` | `#2F2F33` | Dividers |
| `--color-border-subtle` | `#28282B` | Very subtle |
| `--color-text-primary` | `#E8E8EC` | Primary text |
| `--color-text-secondary` | `#8B8B96` | Supporting |
| `--color-text-muted` | `#56565E` | Metadata |

### Light Mode
| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#FFFFFF` | Page background |
| `--color-surface` | `#F7F7F8` | Cards |
| `--color-surface-raised` | `#EFEFF0` | Hover |
| `--color-border` | `#EBEBED` | Dividers |
| `--color-text-primary` | `#1A1A20` | Primary |
| `--color-text-secondary` | `#6B6B78` | Supporting |

### Issue Status Colors
| Status | Color | Usage |
|--------|-------|-------|
| Backlog | `#95A1B4` | Unstarted |
| Todo | `#E2E4EA` | Planned |
| In Progress | `#F2C94C` | Active (yellow) |
| In Review | `#5E5CE6` | Review (purple) |
| Done | `#26C281` | Completed (green) |
| Cancelled | `#6B6B78` | Cancelled (muted) |
| Blocked | `#F05252` | Blocked (red) |

### Priority Colors
| Priority | Icon Color |
|----------|------------|
| Urgent | `#E45858` |
| High | `#F07D38` |
| Medium | `#F2C94C` |
| Low | `#8B8B96` |

---

## Typography

**Font:** Inter (primary), `-apple-system` fallback

```css
--font-sans: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", monospace;
```

| Token | Size | Weight | Line-height | Letter-spacing |
|-------|------|--------|-------------|----------------|
| `--text-xs` | 11px | 400 | 1.4 | 0.01em |
| `--text-sm` | 12px | 400 | 1.5 | 0 |
| `--text-base` | 14px | 400 | 1.5 | 0 |
| `--text-lg` | 15px | 500 | 1.5 | -0.01em |
| `--text-xl` | 18px | 600 | 1.4 | -0.02em |
| `--text-2xl` | 22px | 700 | 1.3 | -0.02em |
| `--text-3xl` | 28px | 700 | 1.2 | -0.03em |

> **Note:** Linear uses smaller base font sizes than most (14px), which creates information density for power users.

---

## Spacing

Base: **4px**
Scale: `2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80`

Sidebar: `240px` width (collapsible to `52px`)
Content max-width: `1400px`
List item height: `36px` (compact), `44px` (comfortable)

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-xs` | `3px` | Tags, tiny chips |
| `--radius-sm` | `4px` | Buttons, inputs |
| `--radius-md` | `6px` | Cards |
| `--radius-lg` | `8px` | Modals, panels |
| `--radius-full` | `9999px` | Status pills, avatars |

---

## Shadows (Dark Mode)

Linear uses almost no shadows in dark mode — elevation is communicated via background color.

```css
--shadow-sm: 0 1px 4px rgba(0,0,0,0.5);
--shadow-md: 0 4px 12px rgba(0,0,0,0.6);
--shadow-lg: 0 8px 24px rgba(0,0,0,0.7);
--shadow-focus: 0 0 0 2px rgba(94, 92, 230, 0.4);
```

---

## Components

### Sidebar Navigation
```
Width: 240px
Bg: --color-surface
Border-right: 1px solid --color-border
Item height: 28px
Item padding: 0 8px
Active item: bg --color-surface-raised, text-primary, left accent (2px)
Icon: 14px, text-muted
Group header: text-xs, text-muted, uppercase, letter-spacing 0.06em
```

### List Items (Issues, Devices, etc.)
```
Height: 36px
Padding: 0 16px
Hover: bg --color-surface-raised
Text: text-sm text-primary
Subtext: text-xs text-muted
Checkbox/Status: 16px, left-aligned
```

### Buttons
```
Primary:    bg #5E5CE6, text white, radius 4px, height 28px, px 12px, text-sm
Secondary:  bg --color-surface-raised, border 1px --color-border, text-secondary
Ghost:      transparent, text-secondary, hover bg --color-surface-raised
Danger:     text-error on hover, bg transparent normally
```

### Status Badges
```
Pill: bg semi-transparent of status color, text status color
radius: 9999px, padding: 2px 8px, text-xs, weight 500
```

### Keyboard Shortcuts
```
kbd element: bg --color-surface-raised, border --color-border
radius: 3px, padding: 1px 4px, font-mono text-xs
```

---

## Design Guardrails

**DO:**
- Prioritize information density — users are power users who want to see more
- Use keyboard shortcuts everywhere — power users love them
- Animate list transitions with subtle 100ms ease-out
- Use status colors consistently — they're a language, not decoration

**DON'T:**
- Don't use card grids for primary content — lists are faster to scan
- Don't add onboarding modals or tooltips that interrupt work
- Don't round corners more than 6px on interactive list items
- Don't use background colors for emphasis — use weight and color instead

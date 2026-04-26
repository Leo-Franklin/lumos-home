# Cursor Design System

**Brand:** Cursor
**Archetype:** Dark AI-native, technical precision
**Atmosphere:** Dense, powerful, alive. A dark canvas where AI capabilities surface contextually. Every surface is a potential command target.

---

## Color Palette

### Canvas (Dark Only)
| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#0D0D0D` | Base canvas |
| `--color-surface` | `#141414` | Panels, sidebar |
| `--color-surface-raised` | `#1C1C1C` | Hover, secondary panels |
| `--color-surface-overlay` | `#242424` | Floating menus, modals |
| `--color-border` | `#2A2A2A` | Dividers |
| `--color-border-subtle` | `#1F1F1F` | Very subtle |

### Primary (AI Purple)
| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#7C3AED` | Primary CTA, AI accents |
| `--color-primary-bright` | `#8B5CF6` | Hover, glows |
| `--color-primary-subtle` | `rgba(124,58,237,0.15)` | Subtle highlights |
| `--color-primary-glow` | `rgba(124,58,237,0.3)` | Glow effects |

### Text
| Token | Value | Usage |
|-------|-------|-------|
| `--color-text-primary` | `#E8E8E8` | Main readable text |
| `--color-text-secondary` | `#A0A0A0` | Supporting |
| `--color-text-muted` | `#606060` | Metadata, placeholders |
| `--color-text-accent` | `#A78BFA` | AI output, suggestions |

### Semantic
| Token | Value | Usage |
|-------|-------|-------|
| `--color-success` | `#34D399` | Applied changes |
| `--color-error` | `#F87171` | Errors, rejections |
| `--color-warning` | `#FBBF24` | Warnings |
| `--color-diff-add` | `rgba(52,211,153,0.15)` | Added code |
| `--color-diff-remove` | `rgba(248,113,113,0.15)` | Removed code |

---

## Typography

```css
--font-sans: "Inter", system-ui, sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", Consolas, monospace;
```

| Token | Size | Weight | Line-height |
|-------|------|--------|-------------|
| `--text-xs` | 11px | 400 | 1.4 |
| `--text-sm` | 12px | 400 | 1.5 |
| `--text-base` | 13px | 400 | 1.6 |
| `--text-lg` | 14px | 500 | 1.5 |
| `--text-xl` | 16px | 600 | 1.4 |
| `--text-2xl` | 20px | 700 | 1.3 |
| `--text-3xl` | 28px | 700 | 1.2 |

> Cursor uses very small base text (13px) to maximize code density. Mono font appears frequently alongside sans.

---

## Spacing

Base: **4px**
Scale: `2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64`

Editor/panel padding: `12px`
Sidebar width: `220px`

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-xs` | `2px` | Code elements |
| `--radius-sm` | `4px` | Buttons, inputs |
| `--radius-md` | `6px` | Panels, cards |
| `--radius-lg` | `8px` | Floating windows |
| `--radius-xl` | `12px` | Modal corners |

---

## Shadows & Glows

```css
/* Elevation */
--shadow-sm:  0 2px 8px rgba(0,0,0,0.5);
--shadow-md:  0 4px 16px rgba(0,0,0,0.6);
--shadow-lg:  0 8px 32px rgba(0,0,0,0.7);

/* AI/accent glow effects */
--glow-primary: 0 0 20px rgba(124,58,237,0.3), 0 0 60px rgba(124,58,237,0.1);
--glow-success: 0 0 12px rgba(52,211,153,0.25);

/* Focus */
--shadow-focus: 0 0 0 2px rgba(124,58,237,0.5);
```

---

## Components

### Command Palette (Core Pattern)
```
bg: --color-surface-overlay
border: 1px solid --color-border
radius: 10px
shadow: --shadow-lg + --glow-primary (subtle)
input: bg transparent, text-primary, no border
result item height: 36px, hover bg --color-surface-raised
```

### AI Chat Panel
```
bg: --color-surface
border-left: 1px solid --color-border
User message: bg --color-surface-raised, radius 8px, text-primary
AI message: text-accent (soft purple), no bg
Code block: bg #000, border --color-border, mono font
```

### Inline Suggestion
```
text color: --color-text-accent (dimmer than main text)
bg: rgba(124,58,237,0.08)
radius: 2px
```

### Buttons
```
Primary:    bg #7C3AED, text white, hover bg #6D28D9, shadow --glow-primary (subtle)
Secondary:  bg --color-surface-raised, border --color-border, text-secondary
Ghost:      transparent, text-muted, hover text-secondary bg --color-surface-raised
```

### Status Indicators
```
Active process: animated dot, color --color-primary
Success: --color-success, static
Error: --color-error
Loading: spinning ring, --color-primary
```

---

## Design Guardrails

**DO:**
- Embrace deep dark — `#0D0D0D` not `#1E1E1E`, it's an aesthetic statement
- Use purple for AI-generated or AI-assisted content as a visual marker
- Surface contextual commands — hover states reveal actions
- Animate only meaningful state changes, not decorative motion

**DON'T:**
- Don't create light mode — Cursor is dark-only
- Don't use gradients on UI chrome (only subtle glows on key interactive elements)
- Don't make the AI panel feel like a separate app — it should feel integrated
- Don't use opacity-heavy overlays — prefer dark bg-color surfaces

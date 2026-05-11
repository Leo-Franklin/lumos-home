# DESIGN.md Template

Use this blank 9-section template to document any project's design system.

---

# [Project Name] Design System

## 1. Visual Theme & Atmosphere

[Describe the overall feel: modern/classic, light/dark, warm/cold, minimal/rich, professional/playful]

**Keywords:** [e.g., clean, technical, trustworthy, bold, approachable]

---

## 2. Color Palette

### Primary Colors
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-primary` | `#XXXXXX` | CTAs, links, active states |
| `--color-primary-hover` | `#XXXXXX` | Hover states |
| `--color-primary-subtle` | `#XXXXXX` | Backgrounds, chips |

### Semantic Colors
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-success` | `#XXXXXX` | Positive states |
| `--color-warning` | `#XXXXXX` | Caution states |
| `--color-error` | `#XXXXXX` | Error states |
| `--color-info` | `#XXXXXX` | Informational |

### Surface & Background
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-bg` | `#XXXXXX` | Page background |
| `--color-surface` | `#XXXXXX` | Cards, panels |
| `--color-surface-raised` | `#XXXXXX` | Elevated cards |
| `--color-border` | `#XXXXXX` | Dividers, outlines |

### Text
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-text-primary` | `#XXXXXX` | Headings, body |
| `--color-text-secondary` | `#XXXXXX` | Captions, metadata |
| `--color-text-muted` | `#XXXXXX` | Placeholder, disabled |

---

## 3. Typography

**Font Families:**
- Headings: `[font-name], [fallback]`
- Body: `[font-name], [fallback]`
- Mono: `[font-name], monospace`

**Type Scale:**
| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `--text-xs` | 11px | 400 | 1.4 | Labels |
| `--text-sm` | 13px | 400 | 1.5 | Captions |
| `--text-base` | 15px | 400 | 1.6 | Body |
| `--text-lg` | 17px | 500 | 1.5 | Large body |
| `--text-xl` | 20px | 600 | 1.4 | Subheadings |
| `--text-2xl` | 24px | 700 | 1.3 | Section heads |
| `--text-3xl` | 30px | 700 | 1.2 | Page titles |
| `--text-4xl` | 38px | 800 | 1.1 | Hero headings |

---

## 4. Spacing & Layout

**Base unit:** `4px`

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Tight gaps |
| `--space-2` | 8px | Component internal |
| `--space-3` | 12px | Icon gaps |
| `--space-4` | 16px | Standard gap |
| `--space-6` | 24px | Section internal |
| `--space-8` | 32px | Card padding |
| `--space-12` | 48px | Section gap |
| `--space-16` | 64px | Page sections |

**Max content width:** `[px]`
**Column grid:** `[12-col / 8-col / flex]`

---

## 5. Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | Xpx | Inputs, badges |
| `--radius-md` | Xpx | Cards, buttons |
| `--radius-lg` | Xpx | Modals, panels |
| `--radius-xl` | Xpx | Hero sections |
| `--radius-full` | 9999px | Pills, avatars |

---

## 6. Elevation & Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,X)` | Default cards |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,X)` | Raised cards |
| `--shadow-lg` | `0 8px 32px rgba(0,0,0,X)` | Modals, dropdowns |
| `--shadow-focus` | `0 0 0 3px [color]` | Focus rings |

---

## 7. Component Patterns

### Buttons
- **Primary:** Background = `--color-primary`, white text, `--radius-md`
- **Secondary:** Border, transparent bg, primary text
- **Ghost:** No border, primary text on hover
- **Destructive:** Error color, used only for irreversible actions

### Cards
- Background: `--color-surface`
- Border: `1px solid --color-border`
- Shadow: `--shadow-sm`
- Padding: `--space-6`

### Forms
- Input height: `Xpx`
- Border: `1px solid --color-border`
- Focus: `--shadow-focus` ring
- Error state: Error border color + message below

### Navigation
- [Sidebar / Top bar / Tab bar]
- Active state: [describe]

---

## 8. Motion & Animation

- **Duration fast:** 100ms (micro-interactions)
- **Duration base:** 200ms (state changes)
- **Duration slow:** 350ms (page transitions)
- **Easing:** `cubic-bezier(0.16, 1, 0.3, 1)` (snappy)

---

## 9. Design Guardrails

**DO:**
- [Positive rule 1]
- [Positive rule 2]

**DON'T:**
- [Negative rule 1]
- [Negative rule 2]

# Anthropic Claude Design System

**Brand:** Anthropic / Claude
**Archetype:** Warm editorial, conversational AI
**Atmosphere:** Thoughtful, warm, and human. A cream canvas with coral warmth. The most human-feeling AI interface — it reads like a letter, not a terminal.

---

## Color Palette

### Primary (Coral/Warm Orange)
| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#D97559` | Claude Coral — active states, links |
| `--color-primary-hover` | `#C4613E` | Hover |
| `--color-primary-subtle` | `#FAF0EB` | Subtle highlights |

### Warm Canvas
| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#FAF8F4` | Warm cream base |
| `--color-bg-secondary` | `#F5F2EC` | Slightly darker cream |
| `--color-surface` | `#FFFFFF` | Cards, message bubbles |
| `--color-surface-warm` | `#FBF9F5` | Warm white |
| `--color-border` | `#E8E4DD` | Warm dividers |
| `--color-border-subtle` | `#F0EDE7` | Very subtle |

### Text
| Token | Value | Usage |
|-------|-------|-------|
| `--color-text-primary` | `#1A1A18` | Near-black warm |
| `--color-text-secondary` | `#5C5952` | Warm gray |
| `--color-text-muted` | `#9E9B95` | Timestamps, metadata |
| `--color-text-placeholder` | `#C5C2BB` | Input placeholder |

### Semantic
| Token | Value | Usage |
|-------|-------|-------|
| `--color-success` | `#26874B` | Positive |
| `--color-error` | `#C0392B` | Error |
| `--color-warning` | `#D4741B` | Warning (warm orange) |
| `--color-info` | `#2670B5` | Info |

### Message Colors
| Type | Background | Text | Border |
|------|-----------|------|--------|
| Human message | `#FFFFFF` | text-primary | border |
| AI message | `#FAF8F4` | text-primary | none |
| Code block | `#F5F2EC` | text-primary | border |
| Artifact | `#FDFCFA` | text-primary | `--color-border` |

---

## Typography

**Heading font:** Tiempos Text, Georgia, or a high-quality serif
**Body font:** Inter, system-ui
**Mono:** JetBrains Mono, Menlo

```css
--font-sans: "Inter", -apple-system, sans-serif;
--font-serif: "Tiempos Text", "Georgia", serif;
--font-mono: "JetBrains Mono", Menlo, monospace;
```

| Token | Size | Weight | Font | Line-height | Notes |
|-------|------|--------|------|-------------|-------|
| `--text-xs` | 12px | 400 | sans | 1.5 | Labels |
| `--text-sm` | 14px | 400 | sans | 1.5 | Caption |
| `--text-base` | 16px | 400 | sans | 1.7 | Body copy — generous line-height |
| `--text-lg` | 18px | 500 | sans | 1.6 | — |
| `--text-xl` | 20px | 600 | sans/serif | 1.4 | Subheadings |
| `--text-2xl` | 24px | 600 | serif | 1.3 | Section heads |
| `--text-3xl` | 30px | 700 | serif | 1.2 | Page titles |
| `--text-4xl` | 38px | 300 | serif | 1.1 | Hero (lighter weight feels premium) |

> Claude uses **light-weight serif for large headings** (300 or 400 weight) — counterintuitively, this makes them feel more premium, not weaker.
> Body copy uses **1.7 line-height** — slightly more airy than typical, because this is reading-focused.

---

## Spacing

Base: **4px**
Scale: `4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96`

Message padding: `24px`
Content max-width: `728px` (reading column)
Side margins: at least `24px`

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `6px` | Inputs, small elements |
| `--radius-md` | `10px` | Buttons, chips |
| `--radius-lg` | `14px` | Cards, message bubbles |
| `--radius-xl` | `20px` | Panels, modals |
| `--radius-full` | `9999px` | Avatars, pills |

---

## Shadows

Very soft, warm-toned.

```css
--shadow-xs:  0 1px 2px rgba(74,55,40,0.04);
--shadow-sm:  0 2px 6px rgba(74,55,40,0.06), 0 1px 2px rgba(74,55,40,0.04);
--shadow-md:  0 4px 16px rgba(74,55,40,0.08), 0 2px 4px rgba(74,55,40,0.04);
--shadow-lg:  0 8px 32px rgba(74,55,40,0.10);
--shadow-focus: 0 0 0 3px rgba(217,117,89,0.25);
```

---

## Components

### Chat Input
```
bg: white
border: 1px solid --color-border
radius: 14px (pill-like, large)
shadow: --shadow-sm
focus: --shadow-focus (coral glow)
min-height: 52px
padding: 14px 16px
```

### Message Bubble (AI)
```
bg: transparent (or --color-surface-warm)
padding: 0 (inline with flow)
max-width: 728px
prose: text-base, 1.7 line-height, serif for headings, sans for body
```

### Artifact / Code Output
```
bg: #F5F2EC
border: 1px solid --color-border
radius: 10px
header: text-xs text-muted, px 16px, py 10px, border-bottom
body: padding 16px, mono font
```

### Buttons
```
Primary:    bg #D97559, text white, radius 8px, height 36px, px 16px
Secondary:  border 1px #E8E4DD, bg transparent, text-secondary
Ghost:      transparent, text-secondary, hover text-primary
```

### Thinking / Reasoning Block
```
bg: #F5F2EC
border-left: 3px solid #D97559
radius: 0 8px 8px 0
padding: 12px 16px
text: text-sm text-secondary, italic
```

---

## Design Guardrails

**DO:**
- Prioritize reading comfort — generous line heights, warm backgrounds, max-width columns
- Use serif fonts for headings to signal editorial care
- Keep the interaction surface warm (coral) not cold (blue)
- Let long-form content breathe — this is a writing/reading product

**DON'T:**
- Don't use pure white (#FFF) backgrounds — always warm cream (#FAF8F4)
- Don't use cold blues as the primary accent — this is a warm product
- Don't compress vertical rhythm — Claude's UX is calm, not dense
- Don't use light weight serif for body text — only for display/hero headings

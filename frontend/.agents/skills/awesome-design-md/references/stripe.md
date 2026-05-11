# Stripe Design System

**Brand:** Stripe
**Archetype:** Premium fintech, trust-inspiring
**Atmosphere:** Professional, clean, precise. Builds trust through visual restraint and exceptional detail. Used by millions of businesses worldwide.

---

## Color Palette

### Primary
| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#635BFF` | Stripe Violet — CTAs, links, focus |
| `--color-primary-hover` | `#5147E8` | Hover on primary |
| `--color-primary-subtle` | `#F0EFFE` | Chip backgrounds, badges |

### Brand Accents
| Token | Value | Usage |
|-------|-------|-------|
| `--color-navy` | `#0A2540` | Dark headings, sidebar |
| `--color-cyan` | `#00D4FF` | Secondary accent, highlights |
| `--color-slate` | `#425466` | Secondary text |

### Semantic
| Token | Value | Usage |
|-------|-------|-------|
| `--color-success` | `#30B130` | Payment success, positive |
| `--color-warning` | `#E39A10` | Pending, review |
| `--color-error` | `#DF1B41` | Failed, destructive |
| `--color-info` | `#006AFF` | Informational |

### Surface & Text
| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#F6F9FC` | Page background |
| `--color-surface` | `#FFFFFF` | Cards, panels |
| `--color-surface-raised` | `#FFFFFF` | Elevated elements |
| `--color-border` | `#E3EBF6` | Dividers, card borders |
| `--color-border-subtle` | `#F0F4F9` | Very light dividers |
| `--color-text-primary` | `#0A2540` | Headings, body |
| `--color-text-secondary` | `#425466` | Supporting text |
| `--color-text-muted` | `#697386` | Metadata, timestamps |
| `--color-text-placeholder` | `#8898AA` | Input placeholders |

---

## Typography

**Font:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`

| Token | Size | Weight | Line-height | Letter-spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| `--text-xs` | 11px | 400 | 1.4 | 0 | Labels, badges |
| `--text-sm` | 13px | 400 | 1.5 | 0 | Captions |
| `--text-base` | 15px | 400 | 1.6 | 0 | Body copy |
| `--text-lg` | 17px | 500 | 1.5 | -0.01em | Large body |
| `--text-xl` | 20px | 600 | 1.4 | -0.02em | Subheadings |
| `--text-2xl` | 24px | 700 | 1.3 | -0.02em | Section titles |
| `--text-3xl` | 32px | 700 | 1.2 | -0.03em | Page titles |
| `--text-4xl` | 42px | 800 | 1.1 | -0.04em | Hero |

---

## Spacing

Base: **4px**
Scale: `4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128`

---

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `4px` | Inputs, small badges |
| `--radius-md` | `6px` | Buttons, form elements |
| `--radius-lg` | `8px` | Cards, dropdowns |
| `--radius-xl` | `12px` | Modals, featured cards |
| `--radius-full` | `9999px` | Pills, avatars |

---

## Shadows

```css
--shadow-xs:  0 1px 1px rgba(0,0,0,0.03), 0 2px 4px rgba(0,0,0,0.04);
--shadow-sm:  0 2px 5px rgba(0,0,0,0.05), 0 1px 1px rgba(0,0,0,0.03);
--shadow-md:  0 7px 14px rgba(50,50,93,0.10), 0 3px 6px rgba(0,0,0,0.08);
--shadow-lg:  0 13px 27px rgba(50,50,93,0.12), 0 8px 16px rgba(0,0,0,0.08);
--shadow-focus: 0 0 0 3px rgba(99,91,255,0.25);
```

---

## Components

### Buttons
```
Primary:    bg #635BFF, text white, radius 6px, height 36px, px 16px
Secondary:  border 1px #E3EBF6, bg white, text #0A2540, same sizing
Ghost:      no border/bg, text #635BFF, hover bg #F0EFFE
Danger:     bg #DF1B41, text white
```

### Cards
```
bg: white
border: 1px solid #E3EBF6
border-radius: 8px
padding: 24px
shadow: --shadow-sm
```

### Badges / Status Pills
```
Default:    bg #F0F4F9, text #425466, radius 99px
Paid:       bg #ECFDF5, text #15803D
Failed:     bg #FEF2F2, text #B91C1C
Pending:    bg #FFFBEB, text #B45309
```

### Forms
```
Input height: 40px
Border: 1px solid #E3EBF6
Radius: 6px
Focus: border #635BFF + shadow-focus
Placeholder: #8898AA
```

### Data Tables
```
Header: bg #F6F9FC, text-sm font-medium text-secondary
Row: border-b #E3EBF6, hover bg #FAFBFC
Cell padding: 12px 16px
```

---

## Design Guardrails

**DO:**
- Use `--color-navy` (#0A2540) as the primary text color for authority
- Prefer subtle borders over heavy shadows for card separation
- Use violet (#635BFF) sparingly — only for primary actions
- Keep forms clean: one visual treatment (border, no fill background)

**DON'T:**
- Don't use gradients on UI chrome (only acceptable on hero marketing sections)
- Don't stack more than 2 font weights in a single component
- Don't use pure black (#000) for text — use `--color-navy` or `--color-text-primary`
- Don't make buttons taller than 40px for standard actions

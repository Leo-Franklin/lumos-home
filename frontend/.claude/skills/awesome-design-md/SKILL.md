---
name: awesome-design-md
description: Generate or apply DESIGN.md design systems from 55+ popular brands (Stripe, Vercel, Linear, Apple, Figma, Spotify, Cursor, etc.) to create pixel-accurate UI components matching any brand's visual language.
triggers:
  - design system
  - DESIGN.md
  - brand style
  - build like
  - UI style
  - apply design
---

# Awesome Design MD

A collection of DESIGN.md files reverse-engineered from popular developer-focused websites.
Drop a brand's design spec into your project and let AI coding agents generate matching UI.

Source: https://github.com/VoltAgent/awesome-design-md

---

## Workflows

### Workflow 1: Apply an Existing Design System

**Trigger:** "Build [component] like [brand]" / "Apply [brand] design" / "Style this like [brand]"

1. Read the brand spec from `references/[brand].md`
2. Extract: color tokens, typography scale, spacing, component patterns, elevation
3. Apply the design language to generate or restyle components
4. Ensure semantic color usage (primary, surface, text, border, error, success)

### Workflow 2: List Available Designs

**Trigger:** "What design systems are available?" / "Show me the catalog"

1. Read `references/catalog.md`
2. Present brands grouped by archetype
3. Suggest the best fit based on project context

### Workflow 3: Create a DESIGN.md for This Project

**Trigger:** "Create a DESIGN.md for my app" / "Document my design system" / "Generate design spec"

1. Inspect existing CSS, components, and color variables in the project
2. Use `references/template.md` as the 9-section structure
3. Use `references/design-patterns.md` for standard cross-cutting patterns
4. Output a complete `DESIGN.md` file at the project root

---

## Bundled Design Systems

| Slug | Brand | Archetype |
|------|-------|-----------|
| `apple` | Apple | Premium spatial, extreme restraint |
| `claude` | Anthropic Claude | Warm editorial, conversational AI |
| `cursor` | Cursor | Dark AI-native, technical |
| `figma` | Figma | Precision design tooling |
| `linear` | Linear | Clean dashboard, developer SaaS |
| `spotify` | Spotify | Dark content-first, playful |
| `stripe` | Stripe | Premium fintech, trust-inspiring |
| `vercel` | Vercel | Cold monochrome, developer-first |

For 47+ additional brands, see `references/catalog.md`.

---

## Design Principles

- **DESIGN.md is the design equivalent of AGENTS.md** — it tells design agents *how the project should look*
- Markdown is the format LLMs read best — no Figma exports, no JSON schemas required
- Keep token, rule, and rationale in the same file
- One file covers: visual theme, color palette, typography, component styles, spacing, elevation, guardrails

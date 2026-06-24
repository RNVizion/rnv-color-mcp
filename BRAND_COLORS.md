# RNVizion Brand Colors

The single source of truth for RNV brand color. Machine source: `engine/brand.py`
(import from there; never hardcode). This doc is the human-readable explanation.

Last locked: 2026-06-24

---

## Canonical brand colors

The answer when someone asks for "the brand color" with no other context.

| Role | Hex | RGB |
|---|---|---|
| Brand gold (primary) | `#d2bc93` | 210, 188, 147 |
| Dark gold | `#b19145` | 177, 145, 69 |
| Brand black (charcoal) | `#1a1a1a` | 26, 26, 26 |

Gold is one value everywhere. Black is charcoal `#1a1a1a` by default.

---

## The two-dark rule

The brand deliberately runs **two** darks, by context. This is intentional, not drift.

- **App / desktop UI** uses a neutral dark: true-black window with charcoal panels.
- **Website (rnvizion.dev)** uses a blue-tinted near-black *ramp* for depth. Flattening it to charcoal would kill the layering, so the site keeps its own base. Do not "fix" it to `#1a1a1a`.

What stays constant across both: the gold.

---

## Desktop / app palette

| Role | Hex |
|---|---|
| Window background | `#000000` |
| Panel (raised surface) | `#1a1a1a` |
| Card | `#2a2a2a` |
| Border | `#333333` |
| Text | `#e0e0e0` |
| Text dim | `#aaaaaa` |
| Accent | `#d2bc93` |
| Accent (light mode) | `#b19145` |
| Text on gold | `#000000` |

## Website palette (rnvizion.dev)

| Role | Hex |
|---|---|
| Base background | `#0a0a0f` |
| Background 2 | `#11111a` |
| Background 3 | `#1a1a26` |
| Border | `#25253a` |
| Border soft | `#1e1e2e` |
| Text | `#e8e8f0` |
| Text dim | `#9a9ab0` |
| Text faint | `#5a5a72` |
| Accent | `#d2bc93` |
| Accent violet (secondary, sparing) | `#b794ff` |
| Accent warm (secondary, sparing) | `#ffd166` |

## Status colors (app)

| Role | Hex |
|---|---|
| Success | `#4caf50` |
| Warning | `#ffc107` |
| Error | `#f44336` |

---

## Resolver vocabulary (MCP)

What the color server resolves brand names to in chat. Defined once in `brand.py`
as `RNV_BRAND`; the resolver imports it. RNV names win over CSS names on collision
(so `gold` = brand gold, not CSS gold); use `css:gold` to force the universal one.

| You say | Resolves to |
|---|---|
| near-black, brand black, rnv black | `#1a1a1a` |
| gold, brand gold, rnv gold | `#d2bc93` |
| dark gold, gold dark, light-mode gold | `#b19145` |

To teach the server a new brand color: add it to `RNV_BRAND` in `engine/brand.py`,
push, done. Every consumer updates from the one edit.

---

## Typography (reference)

Verified from rnvizion.dev:

- Display: Bricolage Grotesque
- Serif (emphasis / italics): Instrument Serif
- Mono (wordmark, labels, footer): JetBrains Mono
- Body: Inter / system stack

Social / OG-card typography is tracked separately; add it here when you want this doc
to cover those surfaces too.

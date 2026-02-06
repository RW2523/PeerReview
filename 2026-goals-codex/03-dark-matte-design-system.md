# Dark Matte Design System (Carry Forward)

## Objective
Preserve the existing Arinar visual identity (dark, matte, minimal glow) while rebuilding the product architecture.

## 1) Visual Direction
- Base canvas: matte black and charcoal layers.
- Surfaces: translucent dark cards with subtle borders.
- Accent: restrained white/neutral glow, not neon-heavy.
- Motion: soft and intentional (state clarity over decoration).

## 2) Core Tokens
```css
:root {
  --bg-0: #070707;
  --bg-1: #0d0d0f;
  --bg-2: #141418;
  --surface-0: rgba(255,255,255,0.04);
  --surface-1: rgba(255,255,255,0.07);
  --border-soft: rgba(255,255,255,0.10);
  --text-0: #f4f4f5;
  --text-1: #c8c8cf;
  --text-2: #9a9aa4;
  --accent: #f2f2f2;
  --success: #4ade80;
  --warning: #fbbf24;
  --danger: #f87171;
}
```

## 3) Typography and Spacing
- Keep type lightweight and spacious (existing dashboard style).
- Heading weight: 300-500, body weight: 400.
- Letter spacing slightly expanded for navigation labels.
- 8px spacing grid.

## 4) Layout Rules
- Persistent left rail for workspace/debate navigation.
- Sticky top context bar for room state and controls.
- Content in layered cards, no flat white panels.
- Max content width to avoid over-wide chat/decision views.

## 5) Interaction and Motion
- Hover: slight lift (`translateY(-2px to -4px)`) and soft glow.
- Active states: brighter border and tighter shadow.
- Transitions: 150-250ms for most interactions.
- Loading indicators should match matte theme (monochrome pulse/spinner).

## 6) Component Guidance
- Debate message bubbles: role-colored border accents with dark fills.
- Participant cards: status chip + model/provider chip + role label.
- Document evidence panel: citation chips and confidence tags.
- Decision summary panel: high contrast section headers, clear action-item rows.

## 7) Accessibility Requirements
- Minimum contrast WCAG AA for all text on dark surfaces.
- Keyboard-visible focus rings on all interactive controls.
- Motion-reduced mode support.
- Color never as sole meaning (icons + labels required).

## 8) Guardrails for Rebuild
- Do not reintroduce bright white auth/marketing pages in core app shell.
- Keep a single token system used by landing, auth, and dashboard.
- Avoid style divergence across teams by enforcing Storybook token checks.

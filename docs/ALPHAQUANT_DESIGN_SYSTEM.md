# AlphaQuant Design System

AlphaQuant OS uses a dark institutional interface with clear execution hierarchy, consistent metric cards, rounded controls, and a single primary action pattern.

## Principles

1. **Mission-first execution**: Mission Control is the default workspace and `RUN ALPHAQUANT` is the only primary execution action.
2. **Institutional clarity**: dashboards emphasize portfolio state, risk visibility, confidence, and explainable intelligence over debug controls.
3. **Future-ready authentication**: the login screen is prepared for identity providers, role permissions, broker authorization, and audit workflows.
4. **Developer containment**: diagnostic and legacy controls are labelled as developer actions and separated from the primary platform navigation.
5. **Brain preservation**: strategy engines, AI Consensus, Historical Analog, Risk Manager, portfolio decisions, and memory logic remain unchanged.

## Core tokens

The Streamlit shell centralizes tokens in `DESIGN_TOKENS` inside `app.py`:

- Ink: `#E6EDF7`
- Muted text: `#8EA4C2`
- Panel: `#111A2E`
- Alternate panel: `#17233A`
- Accent: `#55D6BE`
- Warning: `#F6C85F`
- Danger: `#FF6B6B`
- Success: `#66E08A`

## Navigation standard

All product pages must use the AlphaQuant OS sidebar order:

1. Dashboard
2. Mission Control
3. Portfolio
4. Performance
5. Reports
6. Learning
7. Broker Manager
8. Settings
9. Developer Mode

## Interaction standard

- Only one primary action should be visible for execution: `RUN ALPHAQUANT`.
- Secondary or diagnostic controls must be labelled with `Developer:` and belong in Developer Mode.
- Reports must retain Daily, Weekly, Monthly, and Yearly timeframes.
- Learning surfaces must expose Reviewer, Experience Memory, Confidence, and Historical Analog metrics.

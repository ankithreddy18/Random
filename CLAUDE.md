# Project Instructions

## Installed Skills

| Skill | Source | Purpose |
|-------|--------|---------|
| `ui-ux-pro-max` | nextlevelbuilder/ui-ux-pro-max-skill | UI/UX design: styles, palettes, fonts, 13 stacks |
| `caveman` | JuliusBrussee/caveman | Terse mode — cuts token usage ~75% |
| `caveman-commit` | JuliusBrussee/caveman | Ultra-concise Conventional Commits messages |
| `caveman-review` | JuliusBrussee/caveman | One-line PR review: `L42: 🔴 bug: problem. Fix.` |
| `caveman-help` | JuliusBrussee/caveman | Quick reference for all caveman modes/commands |
| `compress` | JuliusBrussee/caveman | Compress .md files to save input tokens (~46%) |

## Before Every Task

For any UI/UX work, activate **ui-ux-pro-max** first to apply design intelligence (palettes, typography, stack-specific components).

## Skill Usage

### ui-ux-pro-max
- Use for any task involving UI structure, visual design, interaction patterns, or UX review
- Covers: React, Next.js, Vue, Svelte, SwiftUI, React Native, Flutter, Tailwind, shadcn/ui
- 67 styles, 96 palettes, 57 font pairings, 25 chart types

### caveman
- Activate: `/caveman` (default: full), `/caveman lite`, `/caveman ultra`
- Deactivate: "stop caveman" or "normal mode"
- Auto-suspends for security warnings and destructive operations

### caveman-commit
- Triggers on "write a commit", "commit message", `/commit`
- Format: `<type>(<scope>): <summary>` ≤50 chars, no AI attribution

### caveman-review
- Triggers on "review this PR", "code review", `/review`
- Format: `L<line>: 🔴/🟡/🔵 <problem>. <fix>.`

### compress
- Use `/caveman:compress <filepath>` to compress CLAUDE.md or other .md files
- Creates `FILE.original.md` backup — never modifies code files

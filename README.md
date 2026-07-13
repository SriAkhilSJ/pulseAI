# PulseAI - AI-Native IDE

VS Code OSS Fork + Autonomous Agent Runtime.

## Structure
- `pulse_agent/` - Core agent (18K lines, multi-provider routing, safety hard-block, backups+undo, 6 permission modes)
- `D:\vscodesfresh\` - VS Code fork (80% done, agent wired as chat participant) - NOT in this repo, separate local repo
- `documents/` - Hiring, roadmap

## Quick Start
- Agent: `python pulse_agent/main.py --permission-mode plan`
- IDE Fork: See D:\vscodesfresh\ README

## Discipline
TDD RED->GREEN->REFACTOR, 3-tier testing (unit/wiring/live), no fabrication.

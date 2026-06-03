# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## 5. TDD 驱动开发（项目强制要求）

本项目强制要求 TDD（测试驱动开发）流程，所有代码变更必须遵循以下顺序：

1. **先写测试**：在修改或新增任何业务代码之前，先在 `tests/` 中编写能覆盖目标场景的测试用例
2. **确认测试失败**：运行新测试，确保测试因缺少功能/Bug 未修复而失败（红色阶段）
3. **实现代码**：编写最小量的代码使测试通过（绿色阶段）
4. **重构**：在测试保护下优化代码结构
5. **全量回归**：运行 `uv run pytest tests/ -v` 确保所有现有测试全部通过

### 适用场景

- Bug 修复：先写能复现 Bug 的测试，再修 Bug
- 新功能：先写 API/服务层的集成测试，再写实现
- 重构：确保已有测试覆盖足够后再动手

### 测试文件约定

- `tests/conftest.py`：全局 fixture，包含数据库建表、环境变量等
- `tests/integration/`：API 端点集成测试，按功能模块划分
- `tests/unit/`：纯单元测试，按模块划分，优先编写，必要时补充集成测试

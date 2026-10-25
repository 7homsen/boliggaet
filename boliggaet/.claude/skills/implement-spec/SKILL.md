---
name: implement-spec
description: Runs the multi-agent pipeline that takes a spec sheet from plan to verified Flutter code - spec analyst, UX designer, architect, parallel implementers and test writer, adversarial and spec reviewers, triage, verifier - pausing for the user's answers and approvals. Use when the user asks to implement a spec, spec sheet or set of features with the agent pipeline, or runs /implement-spec. Also resumes a run from its docs/specs/<slug>/ folder.
argument-hint: <spec file | docs/specs/<slug> to resume>
---

# Implement a spec with the agent pipeline

Arguments: $ARGUMENTS

You are the orchestrator. You run in the main session, spawn the persona subagents in `.claude/agents/` with the Agent tool, relay between them, pause for the user, and keep the run's status file current. Subagents can't talk to each other or to the user: everything goes through you.

`CLAUDE.md` overrides everything here. In particular: no new packages without asking and no pushes. The only commits allowed are implementers' commits on their own worktree branches, per the exception in `CLAUDE.md`. Never commit in the main checkout.

## Is the pipeline worth it?

The pipeline spawns 8+ agents and costs many times a normal request. If the request is a small change (one screen tweak, a bug fix, a single simple feature with no open UX questions), say so and offer to do it directly instead. Run the pipeline when the user confirms or the spec clearly warrants it.

## The run folder

Everything for a run lives in `docs/specs/<slug>/` (slug: short kebab-case name from the spec title). Always pass agents absolute paths into this folder.

```
docs/specs/<slug>/
  spec.md            # the input spec (copied or saved from pasted text)
  status.md          # owned by you: phase, rounds, branches, pending user input
  plan.md            # spec-analyst
  design.md          # ux-designer
  contracts.md       # architect
  reviews/round-<n>/ # adversarial-<feature>.md, spec-<feature>.md, triage.md
  verification.md    # verifier
```

`status.md` format (update it at every phase change and before every pause):

```markdown
phase: plan | answers | design | design-approval | contracts | build | review | fix | verify | done | escalated
review_round: 0
arch_ux_rounds: 0
base_commit: <git rev-parse HEAD when the build phase started>
features:
  - F1 <name>: <pending | building | merged | blockers | verified>, branch: <worktree branch or main-checkout>
waiting_for_user: <what you asked, or none>
log:
  - <date> <phase>: <one line>
```

**Resuming:** if the argument is an existing run folder, or the user is replying to a pause, read `status.md` and continue from its phase. Record the user's answers/approvals in the right file (answers in `plan.md` under Answers, design approvals and changes in `design.md`) before continuing.

## Phase 1: Plan

1. Create the run folder and `spec.md`. Write `status.md` with `phase: plan`.
2. Spawn `spec-analyst` with the spec path and run folder.
3. If `plan.md` has open questions: set `phase: answers`, show the user the questions (with the suggested defaults) and the feature list, and **end your turn**. When they answer, record the answers and re-run `spec-analyst` to fold them in. Repeat until no open questions remain.

## Phase 2: UX design

1. Spawn `ux-designer` with the run folder.
2. Set `phase: design-approval`. Show the user the screen flows per feature (short), the shared components, and every "UX decision not covered by the spec". **End your turn** and wait for approval or changes. If they ask for changes, re-run `ux-designer` with their feedback.

## Phase 3: Contracts

1. Spawn `architect` with the run folder.
2. If `contracts.md` has pushback:
   - Pushback that needs a new package or changes user-visible behaviour: ask the user (end your turn).
   - Other pushback: re-run `ux-designer` with the pushback, then `architect` again. Count each loop in `arch_ux_rounds`. After 2 loops without agreement, set `phase: escalated`, show the user the disagreement, and end your turn.
3. Continue when the contracts have no open pushback.

## Phase 4: Build (implementers and test writer in parallel)

1. Check `git status`. Worktrees branch from the last commit, so uncommitted changes under `lib/` or `test/` won't be visible to worktree implementers. If there are any, tell the user and ask whether to continue anyway (end your turn). Record `base_commit`.
2. In **one message**, spawn in parallel:
   - one `feature-implementer` per feature (F-id, absolute run folder path). If there are two or more implementers, give each `isolation: "worktree"`. A single implementer runs in the main checkout without a worktree.
   - one `test-writer` for all features, in the main checkout. Give it only the plan, design and contracts paths, never implementer output.
3. Merge each worktree branch into the main checkout **without committing**, one at a time:
   ```
   git merge --squash <branch>
   git reset -q
   ```
   Features live in separate folders, so merges shouldn't conflict. If one does, or git refuses because of local changes, stop and ask the user. Keep the branches; list them in the final report instead of deleting them.
4. Apply the "Shared changes" from `contracts.md` yourself (routes in `main.dart`, `core/` widgets, etc.). If platform changes (`android/`, `ios/` or `web/`) are listed, spawn `platform-engineer` for them.
5. Run `flutter analyze` and `flutter test`. Fix failures caused by your merge or shared changes (imports, routes, `main.dart`, `core/`) now, and re-run until those are clean. Failures inside a feature's own code or tests are left for the reviewers and triage.

## Phase 5: Review (fresh context, in parallel)

1. Increment `review_round` (n). In **one message**, spawn per feature an `adversarial-reviewer` and a `spec-reviewer`, with the run folder, feature id and round number. Don't pass them implementer reports or earlier triage results.
2. Spawn `triage` with the round's report folder.
3. No blockers: go to Phase 7. Blockers: Phase 6.

## Phase 6: Fix

1. Spawn one `feature-implementer` per feature with blockers, in the main checkout (the code is merged now, so no worktrees), passing only that feature's blockers from `triage.md`. Features are in separate folders, so they can run in parallel. If a blocker is in a shared change, fix it yourself.
2. Go back to Phase 5 for a fresh round.
3. Cap: 3 review rounds. If round 3 still has blockers, set `phase: escalated`, show the user the remaining blockers with evidence, and end your turn.

## Phase 7: Verify

1. Spawn `verifier` with the run folder.
2. FAIL: treat the failing items as blockers and go to Phase 6 (they count toward the round cap).
3. PASS: update `docs/implementation-spec.md` yourself to reflect the verified pages, their purpose, the navigation and any styling changes, following the rules in `CLAUDE.md` (high-level, built features only). Then set `phase: done`. If the user asked for docs, spawn `docs-writer`.

## Final report

Tell the user:
- PASS/FAIL per feature, with the path to `verification.md`.
- What changed in `docs/implementation-spec.md`.
- Should-fix items from the triage files that were not fixed.
- UX decisions made and how they were resolved.
- The worktree branches that were merged (they can be deleted once the work is committed).
- That nothing is committed: the changes are in the working tree for them to review. Offer to commit.

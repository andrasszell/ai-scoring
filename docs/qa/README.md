# QA notes (historical)

Manual validation artifacts from Phase 1 and Block F. Not living documentation —
see [`../data-sources.md`](../data-sources.md) and [`../implementation-plan.md`](../implementation-plan.md) for current status.

| File | Contents |
|---|---|
| [`phase-1-validation-run.md`](phase-1-validation-run.md) | Block D validation collect run metrics |
| [`phase-1-spot-check.md`](phase-1-spot-check.md) | Manual evidence accuracy spot-check |
| [`phase-1-pilot-notes.md`](phase-1-pilot-notes.md) | Early pilot run notes |
| [`outcome-semantics-validation.md`](outcome-semantics-validation.md) | Block F re-run outcome breakdown (run #12) |

Re-validate after major collector changes:

```bash
ai-collect collect --validation-set
ai-collect validate
ai-collect status
```

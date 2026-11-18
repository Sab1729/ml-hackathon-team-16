# HMM and Viterbi route reconstruction

The challenge brief schedules Review 1 before lunch and describes a final evaluation. The Review 1 checklists below are proposed team milestones. The brief gives no separate checklist for that checkpoint.

## Review 1 requirements

- [x] Use the Workstream 01 candidate-score fixture and demonstrate decoding with fixed synthetic scores.
- [x] Show a toy directed graph where the highest pointwise scores yield a disconnected route and Viterbi finds a feasible sequence.
- [x] Define how empty candidates, timestamp gaps and impossible transitions are surfaced to callers.

The decoder returns `[0, 1]` on the synthetic fixture, whose independent top scores yield `[0, 2]`. It combines log candidate scores with the difference between directed network distance and observed GPS displacement. Empty candidate lists return unmatched assignments. Non-positive time steps, gaps over 30 seconds, and observations with no feasible transition start a separate section. Warnings report counts by reason, and geometry preserves the section boundaries.

## Final evaluation requirements

- [ ] Decode the chosen model's scores into per-observation assignments and a directed route with any gaps clearly marked.
- [ ] Compare classifier-only and classifier-plus-HMM on identical development trips. Report pointwise accuracy, continuity, sequence performance and cases where decoding helps or hurts.
- [ ] Export decoder configuration and document the hidden states, emissions, transitions, recurrence and fallback behavior.

## Detailed tasks

1. Consume one ordered candidate list per observation, keyed by observation index. Validate each candidate's trip-local arc ID, projected position and probability. Use a directed arc and its projected position as the candidate state.
2. Convert scores into log emissions with a documented probability floor. Define deterministic tie-breaking. Test that observation and arc IDs survive decoding.
3. Compute legal network distance between projected positions, including same-arc movement and intermediate arcs. Use distance and elapsed time to score transitions and mark unreachable pairs impossible. Bound and cache repeated shortest-path lookups where useful.
4. Implement log-space Viterbi with backpointers and recover intermediate directed arcs for the output geometry. Preserve observation assignments separately from the expanded route. Avoid joining disconnected sections with straight lines.
5. Define when long gaps restart decoding, and return an explicit unmatched assignment for empty observations. Record discontinuities and verify behavior on one-way roads, duplicate timestamps, repeated arcs and disconnected graphs.
6. Tune decoder settings using permitted training and student-testing data. Compare both variants using the same aligned references and denominators. Record pointwise accuracy, directed continuity and a defined sequence metric, such as arc edit distance. Save representative failure maps and timings.

## Handoff

Return assignments aligned to GPS indices, ordered route sections and gap warnings to [FastAPI](03-fastapi-backend.md). Use the fixture and score semantics from [data and model training](01-data-and-model-training.md).

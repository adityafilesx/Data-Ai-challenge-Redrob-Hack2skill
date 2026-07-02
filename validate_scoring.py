#!/usr/bin/env python3
"""
Validation script: measures how well rank.py's system ranking aligns with an
independent proxy "recruiter judgment" ranking, using standard IR metrics
(NDCG@20, Precision@10, MRR).

LIMITATION: The "manual" ranking here is a proxy heuristic - a second,
independently-coded scoring function using different weights/logic than
scorer/*.py - NOT labels from an actual human recruiter. Treat results as
an internal-consistency sanity check, not ground-truth validation. For
real validation, replace manual_score() with actual recruiter labels.
"""
import math
import random
import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent))
from rank import score_candidate, load_candidates

RANDOM_SEED = 42
SAMPLE_SIZE = 100
TOP_K = 20

CORE_ML_TITLES = [
    'ml engineer', 'machine learning engineer', 'ai engineer',
    'nlp engineer', 'data scientist', 'applied scientist',
    'research scientist', 'computer vision engineer',
    'recommendation systems engineer', 'search engineer',
]

CORE_ML_SKILLS = {
    'PyTorch', 'TensorFlow', 'Deep Learning', 'NLP', 'LLM',
    'Recommendation Systems', 'Computer Vision', 'MLOps',
    'Reinforcement Learning', 'FAISS', 'Pinecone', 'Weaviate',
    'Embeddings', 'Vector Search', 'Fine-tuning LLMs', 'LoRA', 'PEFT',
}


def manual_score(candidate):
    """Independent proxy for 'how a recruiter would judge this candidate'.
    Deliberately uses different weighting logic than scorer/*.py so this
    is not circular validation."""
    profile = candidate.get('profile', {}) or {}
    skills = candidate.get('skills', []) or []
    signals = candidate.get('redrob_signals', {}) or {}
    career = candidate.get('career_history', []) or []

    score = 0.0
    reasons = []

    # 1. Title relevance (0-25)
    title = (profile.get('current_title') or '').lower()
    if any(t in title for t in CORE_ML_TITLES):
        score += 25
        reasons.append('core ML title')
    elif 'engineer' in title or 'scientist' in title:
        score += 8

    # 2. Core skill depth (0-40)
    depth_points = 0
    core_hits = 0
    for sk in skills:
        name = sk.get('name', '')
        if name in CORE_ML_SKILLS:
            dur = sk.get('duration_months', 0) or 0
            prof = sk.get('proficiency', 'beginner')
            if dur >= 12 and prof in ('advanced', 'expert'):
                depth_points += 4
                core_hits += 1
            elif dur >= 6:
                depth_points += 2
                core_hits += 1
    score += min(40, depth_points)
    if core_hits >= 3:
        reasons.append(f'{core_hits} well-evidenced core ML skills')

    # 3. Verified assessment scores (0-15)
    assess = signals.get('skill_assessment_scores', {}) or {}
    if assess:
        avg = sum(assess.values()) / len(assess)
        score += (avg / 100.0) * 15
        if avg >= 75:
            reasons.append(f'verified avg {avg:.0f}/100')

    # 4. Years of experience sanity (0-10)
    yoe = profile.get('years_of_experience', 0) or 0
    if 3 <= yoe <= 12:
        score += 10
    elif 1 <= yoe < 3 or 12 < yoe <= 16:
        score += 5

    # 5. Career trajectory coherence (0-10)
    prior_ml = sum(1 for j in career if any(t in (j.get('title') or '').lower() for t in CORE_ML_TITLES))
    score += min(10, prior_ml * 5)

    # 6. Engagement sanity check (0-10)
    if signals.get('open_to_work_flag'):
        score += 3
    last_active = signals.get('last_active_date')
    if last_active:
        try:
            days = (date.today() - datetime.strptime(last_active, '%Y-%m-%d').date()).days
            if days <= 30:
                score += 4
            elif days <= 90:
                score += 2
        except (ValueError, TypeError):
            pass
    rr = signals.get('recruiter_response_rate', 0.5) or 0.5
    score += rr * 3

    # 7. Hard penalty: zero core skill evidence + non-ML title = not a fit
    if core_hits == 0 and not any(t in title for t in CORE_ML_TITLES):
        score *= 0.15
        reasons.append('no ML evidence - heavy penalty')

    return round(score, 2), reasons


def ndcg_at_k(ordered_relevances, k):
    dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ordered_relevances[:k]))
    ideal = sorted(ordered_relevances, reverse=True)
    idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal[:k]))
    return dcg / idcg if idcg > 0 else 0.0


def main():
    random.seed(RANDOM_SEED)
    print("Loading candidates.jsonl...", file=sys.stderr)
    all_candidates = load_candidates('candidates.jsonl')
    sample = random.sample(all_candidates, SAMPLE_SIZE)

    rows = []
    for c in sample:
        sys_raw, bd = score_candidate(c)
        m_score, m_reasons = manual_score(c)
        rows.append({
            'candidate_id': c.get('candidate_id', ''),
            'title': c.get('profile', {}).get('current_title', ''),
            'system_score': sys_raw,
            'manual_score': m_score,
            'manual_reasons': '; '.join(m_reasons),
            'bd': bd,
        })

    sys_order = sorted(rows, key=lambda r: -r['system_score'])
    man_order = sorted(rows, key=lambda r: -r['manual_score'])

    for rank, r in enumerate(sys_order, 1):
        r['system_rank'] = rank
    for rank, r in enumerate(man_order, 1):
        r['manual_rank'] = rank

    sys_order_relevances = [r['manual_score'] for r in sys_order]
    ndcg20 = ndcg_at_k(sys_order_relevances, TOP_K)

    sys_top10 = {r['candidate_id'] for r in sys_order[:10]}
    man_top10 = {r['candidate_id'] for r in man_order[:10]}
    precision10 = len(sys_top10 & man_top10) / 10.0

    reciprocals = [1.0 / r['system_rank'] for r in man_order[:10]]
    mrr = sum(reciprocals) / len(reciprocals)

    for r in rows:
        r['rank_diff'] = r['system_rank'] - r['manual_rank']

    ranked_too_low = sorted(rows, key=lambda r: -r['rank_diff'])[:5]
    ranked_too_high = sorted(rows, key=lambda r: r['rank_diff'])[:5]

    lines = []
    lines.append("=" * 70)
    lines.append("VALIDATION RESULTS - rank.py vs proxy recruiter judgment")
    lines.append("=" * 70)
    lines.append("")
    lines.append("LIMITATION: 'Manual' ranking is a proxy heuristic (independently coded")
    lines.append("in validate_scoring.py, different weights than scorer/*.py), NOT actual")
    lines.append("human recruiter labels. Use as an internal-consistency sanity check.")
    lines.append("")
    lines.append(f"Sample size: {SAMPLE_SIZE} (seed={RANDOM_SEED})")
    lines.append("")
    lines.append("METRICS")
    lines.append("-" * 70)
    lines.append(f"NDCG@{TOP_K}:      {ndcg20:.4f}")
    lines.append(f"Precision@10:    {precision10:.4f}  ({len(sys_top10 & man_top10)}/10 overlap)")
    lines.append(f"MRR (top-10):    {mrr:.4f}")
    lines.append("")

    lines.append("TOP 10 - SYSTEM RANKING")
    lines.append("-" * 70)
    for r in sys_order[:10]:
        lines.append(f"  #{r['system_rank']:>2} {r['candidate_id']}  sys={r['system_score']:.1f}  "
                      f"manual={r['manual_score']:.1f} (manual_rank={r['manual_rank']})  {r['title']}")
    lines.append("")

    lines.append("TOP 10 - PROXY MANUAL RANKING")
    lines.append("-" * 70)
    for r in man_order[:10]:
        lines.append(f"  #{r['manual_rank']:>2} {r['candidate_id']}  manual={r['manual_score']:.1f}  "
                      f"sys={r['system_score']:.1f} (system_rank={r['system_rank']})  {r['title']}")
    lines.append("")

    lines.append("TOP 5 MISMATCHES - SYSTEM RANKED TOO LOW (underrated vs manual)")
    lines.append("-" * 70)
    for r in ranked_too_low:
        lines.append(f"  {r['candidate_id']}  system_rank={r['system_rank']} manual_rank={r['manual_rank']} "
                      f"(diff={r['rank_diff']})  title={r['title']}")
        lines.append(f"      manual reasons: {r['manual_reasons']}")
        lines.append(f"      system breakdown: {r['bd']}")
    lines.append("")

    lines.append("TOP 5 MISMATCHES - SYSTEM RANKED TOO HIGH (overrated vs manual)")
    lines.append("-" * 70)
    for r in ranked_too_high:
        lines.append(f"  {r['candidate_id']}  system_rank={r['system_rank']} manual_rank={r['manual_rank']} "
                      f"(diff={r['rank_diff']})  title={r['title']}")
        lines.append(f"      manual reasons: {r['manual_reasons']}")
        lines.append(f"      system breakdown: {r['bd']}")
    lines.append("")

    lines.append("RECOMMENDATIONS")
    lines.append("-" * 70)
    if ndcg20 < 0.7:
        lines.append("- NDCG@20 < 0.70: ranking order diverges meaningfully from proxy judgment.")
        lines.append("  Re-run hyperparameter_tuning.py against this same sample to search for")
        lines.append("  a better tier_a_multiplier / title_weight / relevance_exponent combo.")
    else:
        lines.append("- NDCG@20 >= 0.70: reasonable alignment; fine-tune rather than redesign.")
    if precision10 < 0.5:
        lines.append("- Precision@10 < 0.50: top-10 sets barely overlap. Inspect mismatches above")
        lines.append("  for a systematic pattern (e.g. system over-weighting title vs skill depth).")
    lines.append("- Replace manual_score() with real recruiter labels before treating these")
    lines.append("  numbers as final validation evidence for the submission deck.")
    lines.append("")

    report = '\n'.join(lines)
    Path('validation_results.txt').write_text(report, encoding='utf-8')
    print(report)
    print("\nWritten to validation_results.txt", file=sys.stderr)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
import argparse, csv, gzip, json, sys, time, math
from pathlib import Path
from scorer.honeypot_detector import is_honeypot
from scorer.title_scorer import title_score, apply_career_title_modifier
from scorer.skills_scorer import skills_score
from scorer.yoe_scorer import yoe_score
from scorer.career_scorer import career_pattern_score
from scorer.location_scorer import location_score
from scorer.education_scorer import education_score
from scorer.behavioral_multiplier import behavioral_multiplier
from scorer.reasoning import generate_reasoning

def load_candidates(path):
    p = Path(path)
    if p.suffix == '.json':
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return [data]
    opener = gzip.open(p, 'rt') if p.suffix == '.gz' else open(p, 'r', encoding='utf-8')
    with opener as f:
        return [json.loads(line) for line in f if line.strip()]

def evaluate_knockout(candidate, t_score, s_data):
    # Gate 1 & 4: Strict Recruiter Logic
    # Returns (is_knockout, reason, rule)
    
    tier_a_count = s_data['tier_a_count']
    tier_b_count = s_data['tier_b_count']
    score = s_data['score']
    
    # Condition 1: Title is irrelevant AND no Tier A/B skills
    if t_score == 0 and tier_a_count == 0 and tier_b_count == 0:
        return True, "Irrelevant title and no Tier A/B skills", "Condition 1"
        
    # Condition 2: No technical skills at all
    if score == 0:
        return True, "No recognized technical skills", "Condition 2"
        
    # Condition 3: Handled mostly by title_score=0 (which filters out Accountant etc if no other tech skills are present)
    # If they have a title score of 0, but SOME tier_b skills, they might slip through, but they will have a very low score anyway.
    # To be extremely strict on unrelated professions without evidence:
    if t_score == 0 and tier_a_count == 0 and score < 5:
        return True, "Unrelated profession with weak technical evidence", "Condition 3"
        
    return False, "", ""

def score_candidate(candidate):
    hp, hp_reason = is_honeypot(candidate)
    if hp:
        return 0.0, {'honeypot': hp_reason, 'knockout_triggered': True, 'behavior_score': 0}
    
    bd = {}
    base_title = title_score(candidate.get('profile', {}).get('current_title', ''))
    t_score = apply_career_title_modifier(base_title, candidate.get('career_history', []))
    
    s_data = skills_score(candidate)
    
    is_ko, ko_reason, ko_rule = evaluate_knockout(candidate, t_score, s_data)
    if is_ko:
        return 0.0, {'knockout_triggered': True, 'knockout_reason': ko_reason, 'knockout_rule': ko_rule}
        
    bd['knockout_triggered'] = False
    bd['title_score'] = t_score
    bd['skills_score'] = s_data['score']
    bd['assessment_score'] = s_data['assessment_score']
    
    # Technical relevance dominates (70-80% weighting logic achieved by making tech raw score large)
    # Title (max ~115), Skills (max ~150+) -> Technical Score ~ 200+
    tech_score = t_score * 1.5 + s_data['score']
    bd['technical_score'] = tech_score
    
    # Metadata bonuses (minor additions)
    bd['experience_bonus'] = yoe_score(candidate.get('profile', {}).get('years_of_experience', 0)) * 0.5
    bd['education_bonus'] = education_score(candidate) * 0.5
    bd['location_bonus'] = location_score(candidate) * 0.5
    
    raw_base = tech_score + bd['experience_bonus'] + bd['education_bonus'] + bd['location_bonus']
    
    # Behavioral Tie-breaker
    bm = behavioral_multiplier(candidate.get('redrob_signals', {}))
    bd['behavior_score'] = bm
    
    final_raw = raw_base * bm
    return final_raw, bd

def calibrate_scores(scored_list):
    # Returns the list with calibrated scores (Min-Max to 0-100 range based on top candidate)
    if not scored_list:
        return scored_list
        
    scores = [x[1] for x in scored_list]
    max_s = max(scores) if max(scores) > 0 else 1.0
    min_s = min(scores)
    
    calibrated = []
    for (cand, s, bd) in scored_list:
        # Min-Max Scaling bounded [0, 100]
        if max_s == min_s:
            c_score = 100.0 if s > 0 else 0.0
        else:
            c_score = ((s - min_s) / (max_s - min_s)) * 100.0
        
        bd['final_score'] = round(c_score, 4)
        calibrated.append((cand, c_score, bd))
        
    return calibrated

def main():
    t0 = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidates', required=True)
    parser.add_argument('--team-id', default='lyle', help='Team ID for the output filename')
    args = parser.parse_args()
    
    out_filename = f'team_{args.team_id}.csv'
    
    print(f"[{time.time()-t0:.1f}s] Loading candidates...", file=sys.stderr)
    candidates = load_candidates(args.candidates)
    
    print(f"[{time.time()-t0:.1f}s] Scoring...", file=sys.stderr)
    scored = []
    knockouts = []
    
    for c in candidates:
        final_raw, bd = score_candidate(c)
        if bd.get('knockout_triggered'):
            knockouts.append({
                'candidate_id': c.get('candidate_id', ''),
                'name': c.get('profile', {}).get('name', 'Unknown'),
                'reason': bd.get('knockout_reason', 'Honeypot/Other'),
                'triggered_rule': bd.get('knockout_rule', 'N/A')
            })
        else:
            scored.append((c, final_raw, bd))
            
    print(f"[{time.time()-t0:.1f}s] Writing Knockout Report...", file=sys.stderr)
    with open('knockout_report.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['candidate_id', 'name', 'reason', 'triggered_rule'])
        writer.writeheader()
        writer.writerows(knockouts)
    
    print(f"[{time.time()-t0:.1f}s] Calibrating and Sorting...", file=sys.stderr)
    scored = calibrate_scores(scored)
    scored.sort(key=lambda x: (-x[1], x[0].get('candidate_id', '')))
    
    top100 = scored[:100]
    
    # Pad to exactly 100 rows if necessary
    if len(top100) < 100:
        needed = 100 - len(top100)
        for ko in knockouts[:needed]:
            mock_cand = {'candidate_id': ko['candidate_id'], 'profile': {'name': ko['name']}}
            mock_bd = {'knockout_triggered': True, 'padding_row': True}
            top100.append((mock_cand, 0.0, mock_bd))
    
    # Write Out CSV
    with open(out_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['candidate_id', 'rank', 'score', 'reasoning'])
        prev_score = None
        for rank_idx, (candidate, score, bd) in enumerate(top100, 1):
            out_score = round(score, 6)
            if prev_score is not None and out_score > prev_score:
                out_score = prev_score
            prev_score = out_score
            
            if bd.get('padding_row'):
                reasoning = "Candidate does not meet baseline criteria but is included to fulfill system row requirements."
            else:
                reasoning = generate_reasoning(candidate, bd, rank_idx, score)
                
            writer.writerow([candidate.get('candidate_id', ''), rank_idx, out_score, reasoning])
            
    # Write Explanation JSON
    explanations = {}
    for rank_idx, (candidate, score, bd) in enumerate(top100, 1):
        cid = candidate.get('candidate_id', f'unknown_{rank_idx}')
        explanations[cid] = bd
        
    with open('ranking_explanation.json', 'w', encoding='utf-8') as f:
        json.dump(explanations, f, indent=2)
    
    print(f"[{time.time()-t0:.1f}s] Done. Written {out_filename}, knockout_report.csv, and ranking_explanation.json.", file=sys.stderr)

if __name__ == '__main__':
    main()

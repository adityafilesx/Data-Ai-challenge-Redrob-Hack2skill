from datetime import date, datetime

def is_honeypot(candidate):
    """
    Returns (bool, reason_string).
    If True: set final_score = 0.0 regardless of other scores.
    """
    p = candidate.get('profile', {})
    s = candidate.get('redrob_signals', {})
    skills = candidate.get('skills', [])
    career = candidate.get('career_history', [])
    today = date.today()
    
    # CHECK 1: Salary range inverted (catches ~100% of honeypots in sample)
    sr = s.get('expected_salary_range_inr_lpa', {})
    if sr.get('min', 0) > sr.get('max', 0):
        return True, f"salary_inverted:{sr['min']}>{sr['max']}"
    
    # CHECK 2: Multiple expert skills with 0 months (literal impossibility)
    expert_zero = [sk['name'] for sk in skills
                   if sk.get('proficiency') == 'expert'
                   and sk.get('duration_months', 1) == 0]
    if len(expert_zero) >= 2:   # 2+ expert skills with 0 months = honeypot
        return True, f"expert_zero_months:{expert_zero[:3]}"
    
    # CHECK 3: Duration_months wildly exceeds calendar span
    for job in career:
        try:
            start = datetime.strptime(job['start_date'], '%Y-%m-%d').date()
            end_str = job.get('end_date')
            end = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else today
            actual_months = max(0, (end.year - start.year)*12 + (end.month - start.month))
            stated = job.get('duration_months', 0)
            # If stated duration is >80% more than actual calendar → impossible
            if stated > 0 and actual_months > 0 and stated > actual_months * 1.8:
                return True, f"impossible_duration:{stated}m_stated,{actual_months}m_actual"
        except (ValueError, TypeError):
            pass
    
    # CHECK 4: YoE claim exceeds career history span
    try:
        if career:
            earliest = min(
                datetime.strptime(j['start_date'], '%Y-%m-%d').date()
                for j in career
            )
            max_possible_yoe = (today - earliest).days / 365.25
            claimed_yoe = p.get('years_of_experience', 0)
            if claimed_yoe > max_possible_yoe + 3:   # 3yr grace for pre-career experience
                return True, f"yoe_impossible:{claimed_yoe}claimed,{max_possible_yoe:.1f}max"
    except (ValueError, TypeError):
        pass
    
    return False, None

from scorer.skills_scorer import SKILLS_TIER_A
from scorer.career_scorer import PRODUCT_INDUSTRIES, PURE_SERVICES

def generate_reasoning(candidate, score_breakdown, rank, final_score):
    p = candidate.get('profile', {})
    s = candidate.get('redrob_signals', {})
    skills = candidate.get('skills', [])
    career = candidate.get('career_history', [])
    
    facts = {}
    facts['title'] = p.get('current_title', '')
    facts['yoe'] = p.get('years_of_experience', 0)
    facts['company'] = p.get('current_company', '')
    
    loc = p.get('location', '')
    facts['location'] = loc.split(',')[0].strip() if loc else ''
    
    facts['notice'] = s.get('notice_period_days', 60)
    facts['open'] = s.get('open_to_work_flag', True)
    facts['rr'] = s.get('recruiter_response_rate', 0.5)
    
    tier_a_found = [sk['name'] for sk in skills
                    if sk.get('name') in SKILLS_TIER_A
                    and sk.get('duration_months', 0) >= 12]
    facts['top_skills'] = tier_a_found[:3]
    
    recent_product_roles = [
        f"{j.get('title', '')} at {j.get('company', '')}"
        for j in career[:3]
        if j.get('industry', '').lower() in PRODUCT_INDUSTRIES
    ]
    facts['career_highlight'] = recent_product_roles[0] if recent_product_roles else None
    
    relevant_scores = {k: round(v) for k, v in s.get('skill_assessment_scores', {}).items()
                       if k in SKILLS_TIER_A | {'NLP', 'Feature Engineering', 'MLflow'}}
    facts['assessments'] = relevant_scores if relevant_scores else None
    
    concerns = []
    if facts['notice'] > 90:
        concerns.append(f"{facts['notice']}-day notice")
    if facts['rr'] < 0.3:
        concerns.append(f"low response rate ({facts['rr']:.0%})")
    if not facts['open']:
        concerns.append("not marked open to work")
        
    days_inactive = 0
    last_active = s.get('last_active_date')
    if last_active:
        try:
            from datetime import date, datetime
            last = datetime.strptime(last_active, '%Y-%m-%d').date()
            days_inactive = (date.today() - last).days
        except (ValueError, TypeError):
            pass
            
    if days_inactive > 90:
        concerns.append(f"inactive for {days_inactive}d")
        
    if rank <= 20:
        skill_str = ', '.join(facts['top_skills']) if facts['top_skills'] else 'relevant ML background'
        base = f"{facts['yoe']:.0f}-yr {facts['title']} at {facts['company']}"
        if facts['assessments']:
            assess_str = ', '.join(f"{k}:{v}" for k, v in list(facts['assessments'].items())[:2])
            base += f"; platform-verified scores ({assess_str})"
        elif facts['career_highlight']:
            base += f"; {facts['career_highlight']}"
        if facts['top_skills']:
            base += f"; strong on {skill_str}"
        if concerns:
            base += f"; concern: {', '.join(concerns)}"
        return base + "."
        
    elif rank <= 70:
        base = f"{facts['yoe']:.0f}-yr {facts['title']}"
        if facts['top_skills']:
            base += f" with {', '.join(facts['top_skills'][:2])}"
        if concerns:
            base += f"; flagged for {', '.join(concerns)}"
        else:
            base += f"; {facts['location']}-based, {facts['notice']}d notice"
        return base + "."
        
    else:
        if facts['top_skills']:
            base = f"Adjacent skills ({', '.join(facts['top_skills'][:2])}) but"
        else:
            base = f"{facts['title']} background —"
        if concerns:
            base += f" concerns on {', '.join(concerns)}"
        base += "; included given engagement signals, below primary fit threshold"
        return base + "."

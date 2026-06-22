from datetime import date, datetime

def behavioral_multiplier(signals):
    m = 1.0
    today = date.today()
    
    # 1. Open to work flag (Slight penalty if passive)
    if not signals.get('open_to_work_flag', True):
        m -= 0.05
    
    # 2. Last active date (Minor penalty if inactive)
    last_active = signals.get('last_active_date')
    if last_active:
        try:
            last = datetime.strptime(last_active, '%Y-%m-%d').date()
            days = (today - last).days
            if days > 180:
                m -= 0.10
            elif days > 90:
                m -= 0.05
        except (ValueError, TypeError):
            pass
            
    # 3. Recruiter Response Rate
    rr = signals.get('recruiter_response_rate', 0.5)
    if rr > 0.8:
        m += 0.05
    elif rr < 0.2:
        m -= 0.05
        
    # 4. Notice Period
    notice = signals.get('notice_period_days', 60)
    if notice > 90:
        m -= 0.05
    elif notice <= 30:
        m += 0.05
        
    # 5. Saved by recruiters
    saved = signals.get('saved_by_recruiters_30d', 0)
    if saved >= 5:
        m += 0.05
        
    # 6. Github activity
    github = signals.get('github_activity_score', -1)
    if github >= 70:
        m += 0.05
        
    # Clamp the final multiplier between 0.80 and 1.20
    return max(0.80, min(1.20, m))

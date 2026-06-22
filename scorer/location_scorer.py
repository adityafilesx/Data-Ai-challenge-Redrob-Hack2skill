TIER_1_CITIES = {
    'noida', 'pune',
}
TIER_2_CITIES = {
    'delhi', 'new delhi', 'gurgaon', 'gurugram',
    'hyderabad', 'bangalore', 'bengaluru',
    'mumbai', 'chennai',
}

def location_score(candidate):
    p = candidate.get('profile', {})
    s = candidate.get('redrob_signals', {})
    
    loc = p.get('location', '').lower()
    country = p.get('country', '').lower()
    relocate = s.get('willing_to_relocate', False)
    work_mode = s.get('preferred_work_mode', '').lower()
    
    city = loc.split(',')[0].strip() if loc else ''
    
    if city in TIER_1_CITIES:
        return 10
    
    if city in TIER_2_CITIES:
        return 8
    
    if country in ('india', 'in'):
        if relocate:
            return 7
        elif work_mode in ('remote', 'flexible'):
            return 5
        else:
            return 4
            
    if relocate:
        return 3
    return 0

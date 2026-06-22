def education_score(candidate):
    education = candidate.get('education', [])
    if not education:
        return 2
    
    tier_map = {'tier_1': 5, 'tier_2': 4, 'tier_3': 3, 'tier_4': 2, 'unknown': 2}
    best_tier = max(tier_map.get(e.get('tier', 'unknown'), 2) for e in education)
    
    relevant_fields = {
        'computer science', 'computer engineering', 'information technology',
        'artificial intelligence', 'machine learning', 'data science',
        'mathematics', 'statistics', 'electrical engineering', 'electronics',
    }
    
    has_relevant_field = any(
        any(rf in e.get('field_of_study', '').lower() for rf in relevant_fields)
        for e in education
    )
    
    field_bonus = 1 if has_relevant_field else 0
    return min(5, best_tier + field_bonus - 1)

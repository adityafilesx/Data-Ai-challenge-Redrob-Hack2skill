TITLE_SCORE_MAP = {
    100: [
        'ml engineer', 'machine learning engineer',
        'ai engineer', 'artificial intelligence engineer',
        'applied ai engineer', 'applied scientist',
        'nlp engineer', 'natural language',
        'recommendation systems engineer', 'recommendation engineer',
        'ranking engineer', 'retrieval engineer',
        'search engineer', 'search ranking engineer'
    ],
    90: [
        'data scientist', 'deep learning engineer',
        'ml research engineer', 'research scientist',
        'computer vision engineer'
    ],
    85: [
        'backend engineer', 'platform engineer',
        'data engineer', 'systems engineer'
    ],
    70: [
        'software engineer', 'full stack developer',
        'software developer', 'senior software engineer',
        'staff software engineer', 'principal engineer'
    ],
    20: [
        'devops engineer', 'cloud engineer',
        'mobile developer', 'frontend engineer',
        'qa engineer', 'java developer',
        '.net developer', 'android developer',
        'general engineer', 'systems administrator'
    ]
}

# Semantic mapping for fast synonym matching without transformer overhead
SEMANTIC_TITLE_ALIASES = {
    'applied ai scientist': 'applied scientist',
    'llm engineer': 'nlp engineer',
    'genai engineer': 'ai engineer',
    'generative ai engineer': 'ai engineer',
    'mlops engineer': 'ml engineer',
    'machine learning researcher': 'ml research engineer'
}

def semantic_normalize_title(title: str) -> str:
    title = title.lower().strip()
    for alias, target in SEMANTIC_TITLE_ALIASES.items():
        if alias in title:
            title = title.replace(alias, target)
    return title

def title_score(current_title: str) -> float:
    if not current_title:
        return 0.0
    
    lower_title = semantic_normalize_title(current_title)
    
    # Check top tier down to lowest
    for score in sorted(TITLE_SCORE_MAP.keys(), reverse=True):
        keywords = TITLE_SCORE_MAP[score]
        if any(kw in lower_title for kw in keywords):
            return float(score)
            
    # Implicitly return 0 for unrelated (Civil Engineer, Accountant, etc.)
    return 0.0

def apply_career_title_modifier(base_score: float, career_history: list) -> float:
    if not career_history:
        return base_score
        
    ml_keywords = TITLE_SCORE_MAP[100] + TITLE_SCORE_MAP[90]
    
    ml_titles_in_career = 0
    for job in career_history:
        if job.get('title'):
            norm_title = semantic_normalize_title(job['title'])
            if any(t in norm_title for t in ml_keywords):
                ml_titles_in_career += 1
                
    if ml_titles_in_career >= 2:
        return min(100.0, base_score + 15.0) # Boost slightly
    if ml_titles_in_career == 0 and base_score >= 85.0:
        return base_score * 0.9 # Minor penalty if no history
    return base_score

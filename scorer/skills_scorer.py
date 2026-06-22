SKILLS_TIER_A = {
    'PyTorch', 'TensorFlow', 'Deep Learning', 'NLP', 'LLM',
    'Recommendation Systems', 'Computer Vision', 'MLOps',
    'Reinforcement Learning', 'FAISS', 'Pinecone', 'Weaviate',
    'Embeddings', 'Sentence Transformers', 'Information Retrieval',
    'Vector Search', 'Fine-tuning LLMs', 'LoRA', 'PEFT'
}

SKILLS_TIER_B = {
    'Python', 'SQL', 'Spark', 'scikit-learn', 'AWS',
    'Docker', 'Kubernetes', 'Hugging Face Transformers',
    'LangChain', 'Prompt Engineering', 'Machine Learning',
    'Feature Engineering', 'MLflow', 'BentoML', 'Kubeflow',
    'GCP', 'Azure', 'Data Science', 'Statistical Modeling'
}

SKILLS_TIER_C = {
    'Git', 'Linux', 'APIs', 'CI/CD', 'Redis', 'MongoDB',
    'PostgreSQL', 'FastAPI', 'Data Pipelines', 'ETL',
    'Databricks', 'BigQuery'
}

SEMANTIC_SKILL_ALIASES = {
    'llmops': 'MLOps',
    'pytorch lightning': 'PyTorch',
    'huggingface': 'NLP',
    'genai': 'LLM',
    'generative ai': 'LLM',
    'keras': 'Deep Learning',
    'elasticsearch': 'Vector Search',
    'opensearch': 'Vector Search',
    'bm25': 'Information Retrieval'
}

def semantic_normalize_skill(skill_name: str) -> str:
    lower_name = skill_name.lower().strip()
    for alias, target in SEMANTIC_SKILL_ALIASES.items():
        if alias in lower_name:
            return target
    # Capitalize matched items properly if they exist in tiers
    for t_set in [SKILLS_TIER_A, SKILLS_TIER_B, SKILLS_TIER_C]:
        for t_skill in t_set:
            if t_skill.lower() == lower_name:
                return t_skill
    return skill_name

def compute_trust_weight(skill):
    prof_map = {'expert': 1.4, 'advanced': 1.1, 'intermediate': 0.9, 'beginner': 0.5}
    prof_w = prof_map.get(skill.get('proficiency', 'intermediate'), 0.9)
    
    duration = skill.get('duration_months', 0)
    endorsements = skill.get('endorsements', 0)
    
    if duration == 0: dur_w = 0.1
    elif duration < 6: dur_w = 0.4
    elif duration < 12: dur_w = 0.65
    elif duration < 24: dur_w = 0.85
    elif duration < 48: dur_w = 1.0
    else: dur_w = 1.25
    
    if endorsements >= 30: end_bonus = 1.2
    elif endorsements >= 10: end_bonus = 1.1
    else: end_bonus = 1.0
    
    return prof_w * dur_w * end_bonus

def compute_assessment_boost(assessment_scores):
    if not assessment_scores:
        return 1.0
    
    # Simple average of all assessment scores
    avg_score = sum(assessment_scores.values()) / len(assessment_scores)
    
    if avg_score >= 80: return 1.5
    elif avg_score >= 60: return 1.3
    elif avg_score >= 40: return 1.1
    else: return 0.9

def skills_score(candidate):
    skills = candidate.get('skills', [])
    if not skills:
        return {'score': 0.0, 'tier_a_count': 0, 'tier_b_count': 0, 'relevance_ratio': 0.0, 'assessment_score': 0.0}
        
    tier_a_total = 0
    tier_b_total = 0
    tier_c_total = 0
    
    tier_a_count = 0
    tier_b_count = 0
    relevant_skills_count = 0
    total_skills = len(skills)
    
    for sk in skills:
        orig_name = sk.get('name', '')
        if not orig_name:
            continue
        
        name = semantic_normalize_skill(orig_name)
        tw = compute_trust_weight(sk)
        
        if name in SKILLS_TIER_A:
            tier_a_total += 3.0 * tw
            tier_a_count += 1
            relevant_skills_count += 1
        elif name in SKILLS_TIER_B:
            tier_b_total += 1.8 * tw
            tier_b_count += 1
            relevant_skills_count += 1
        elif name in SKILLS_TIER_C:
            tier_c_total += 0.8 * tw
            relevant_skills_count += 1

    # Dynamic relevance penalty
    relevance_ratio = relevant_skills_count / total_skills if total_skills > 0 else 0
    alpha = 2.0
    relevance_penalty = relevance_ratio ** alpha
    
    # Weight Tiers A >> B >> C
    raw = (tier_a_total * 5.0) + (tier_b_total * 2.0) + (tier_c_total * 0.5)
    score_with_relevance = raw * relevance_penalty
    
    assessment_scores = candidate.get('redrob_signals', {}).get('skill_assessment_scores', {})
    assessment_boost = compute_assessment_boost(assessment_scores)
    
    final_skill_score = score_with_relevance * assessment_boost
    
    return {
        'score': final_skill_score,
        'tier_a_count': tier_a_count,
        'tier_b_count': tier_b_count,
        'relevance_ratio': relevance_ratio,
        'assessment_score': assessment_boost
    }

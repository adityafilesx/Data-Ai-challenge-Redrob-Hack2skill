PURE_SERVICES = {
    'tcs', 'tata consultancy services', 'tata consultancy',
    'infosys', 'wipro', 'accenture',
    'cognizant', 'cognizant technology solutions',
    'capgemini', 'tech mahindra', 'mphasis',
    'hexaware', 'mindtree', 'hcl technologies',
    'hcl tech', 'l&t infotech', 'ltimindtree',
    'ntt data', 'cts', 'virtusa',
}

PRODUCT_INDUSTRIES = {
    'software', 'ai/ml', 'fintech', 'e-commerce',
    'food delivery', 'saas', 'technology',
    'transportation', 'edtech', 'healthtech',
    'gaming', 'internet', 'consumer tech',
}

def career_pattern_score(candidate: dict) -> float:
    career = candidate.get('career_history', [])
    if not career:
        return 5.0
        
    companies = [job.get('company', '').lower() for job in career]
    
    is_pure_services = all(
        any(sc in co for sc in PURE_SERVICES)
        for co in companies if co
    )
    if is_pure_services and companies:
        return 0.0
        
    product_months = 0
    services_months = 0
    total_months = 0
    
    for job in career:
        months = job.get('duration_months', 0)
        total_months += months
        
        co = job.get('company', '').lower()
        if any(sc in co for sc in PURE_SERVICES):
            services_months += months
        elif job.get('industry', '').lower() in PRODUCT_INDUSTRIES:
            product_months += months
            
    if total_months == 0:
        return 5.0
        
    product_ratio = product_months / total_months
    
    base = min(15.0, 15.0 * product_ratio * 1.5)
    
    current_size = candidate.get('profile', {}).get('current_company_size', '')
    size_bonus = {
        '11-50': 1.2,
        '51-200': 1.15,
        '201-500': 1.1,
        '501-1000': 1.05,
        '1001-5000': 1.0,
        '5001-10000': 0.95,
        '10001+': 0.80,
    }.get(current_size, 1.0)
    
    adjusted = base * size_bonus
    
    most_recent_title = career[0].get('title', '').lower() if career else ''
    still_technical = any(t in most_recent_title for t in
        ['engineer', 'developer', 'scientist', 'architect',
         'analyst', 'researcher'])
         
    if not still_technical and most_recent_title:
        adjusted *= 0.6
        
    return min(15.0, adjusted)

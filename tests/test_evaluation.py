import sys
import os

# Add parent dir to path so we can import scorer modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rank import score_candidate

def make_candidate(cid, title, skills=None, last_active="2026-06-20"):
    if skills is None:
        skills = []
    
    skill_dicts = [{'name': s, 'proficiency': 'advanced', 'duration_months': 36} for s in skills]
    
    return {
        'candidate_id': cid,
        'profile': {
            'name': f"Test_{cid}",
            'current_title': title,
            'years_of_experience': 5
        },
        'skills': skill_dicts,
        'redrob_signals': {
            'last_active_date': last_active,
            'open_to_work_flag': True
        }
    }

def test_civil_engineer_knockout():
    c = make_candidate('C01', 'Civil Engineer', ['AutoCAD', 'Excel'])
    score, bd = score_candidate(c)
    assert bd['knockout_triggered'] is True
    assert score == 0.0

def test_accountant_with_python():
    c = make_candidate('C02', 'Accountant', ['Accounting', 'Python'])
    score, bd = score_candidate(c)
    # They have 1 tier B skill, so they might not hit condition 1, but they have 0 title score.
    # Score should be very low due to relevance ratio penalty.
    assert score < 20.0 # Just to ensure it's heavily penalized

def test_ml_engineer_top_percentile():
    c = make_candidate('C03', 'Machine Learning Engineer', ['TensorFlow', 'PyTorch', 'NLP'])
    score, bd = score_candidate(c)
    assert bd['knockout_triggered'] is False
    assert bd['title_score'] == 100.0
    assert bd['technical_score'] > 150.0 # 100 * 1.5 + skills

def test_ai_engineer_inactive():
    # Active
    c_active = make_candidate('C04A', 'AI Engineer', ['Deep Learning', 'PyTorch'], last_active='2026-06-20')
    score_active, bd_active = score_candidate(c_active)
    
    # Inactive
    c_inactive = make_candidate('C04B', 'AI Engineer', ['Deep Learning', 'PyTorch'], last_active='2020-01-01')
    score_inactive, bd_inactive = score_candidate(c_inactive)
    
    # The inactive candidate should only suffer a tie-breaker penalty (e.g. 0.8x to 0.9x), not a 0.25x penalty.
    ratio = score_inactive / score_active
    assert 0.70 < ratio < 1.0

def test_backend_engineer_strong_skills():
    c = make_candidate('C05', 'Backend Engineer', ['Python', 'Docker', 'Kubernetes', 'AWS', 'Redis'])
    score, bd = score_candidate(c)
    assert bd['knockout_triggered'] is False
    assert bd['title_score'] == 85.0
    assert bd['technical_score'] > 100.0

import streamlit as st
import json
import pandas as pd
import sys
from pathlib import Path
import plotly.express as px

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from rank import score_candidate
    from scorer.reasoning import generate_reasoning
except ImportError:
    st.error("Could not import scorer modules. Please ensure this app is run from the sandbox directory within the redrob-lyle project.")
    st.stop()

st.set_page_config(page_title="Redrob Candidate Ranker", layout="wide")

st.title("Redrob Candidate Ranker — Team Lyle")
st.markdown("A hosted sandbox demo featuring the **Interactive XAI Recruiter Tuner**.")

with st.sidebar:
    st.header("Scoring Component Weights")
    w_title = st.slider("Title Weight", 0.0, 2.0, 1.0, 0.1)
    w_skills = st.slider("Skills Weight", 0.0, 2.0, 1.0, 0.1)
    w_yoe = st.slider("Experience Weight", 0.0, 2.0, 1.0, 0.1)
    w_edu = st.slider("Education Weight", 0.0, 2.0, 1.0, 0.1)
    w_loc = st.slider("Location Weight", 0.0, 2.0, 1.0, 0.1)
    
    st.markdown("---")
    st.markdown("""
    *Behavioral Multiplier (0.0 - 1.0) is applied to the final score automatically to down-rank unengaged candidates.*
    """)

uploaded_file = st.file_uploader("Upload candidates JSON file (≤100 candidates)", type=['json'])

@st.cache_data
def load_and_parse_file(uploaded_content):
    try:
        data = json.loads(uploaded_content)
        if not isinstance(data, list):
            return None, "File must contain a JSON array of candidates."
        if len(data) > 100:
            return None, f"File contains {len(data)} candidates. Please upload ≤ 100."
        return data, None
    except Exception as e:
        return None, f"Failed to parse JSON: {e}"

def get_badges(candidate, bd):
    badges = []
    if bd.get('knockout_triggered'):
        return "🔴 Knockout"
    if bd.get('behavior_score', 0) < 0.8:
        badges.append("⚠️ Low Engagement")
    if bd.get('skills_score', 0) > 100:
        badges.append("🟢 Top Tier Skills")
    if bd.get('experience_bonus', 0) > 5:
        badges.append("🔵 Senior")
    return " ".join(badges)

if uploaded_file is not None:
    content = uploaded_file.getvalue().decode("utf-8")
    data, error = load_and_parse_file(content)
    
    if error:
        st.error(error)
    else:
        st.success(f"Successfully loaded {len(data)} candidates.")
        
        # We always run the base ranker, then apply the sliders
        scored = []
        for c in data:
            _, bd = score_candidate(c)
            
            # Recalculate based on XAI Tuner sliders
            if bd.get('knockout_triggered'):
                final = 0.0
            else:
                recalc_raw = (
                    bd.get('title_score', 0) * w_title +
                    bd.get('skills_score', 0) * w_skills +
                    bd.get('experience_bonus', 0) * w_yoe +
                    bd.get('education_bonus', 0) * w_edu +
                    bd.get('location_bonus', 0) * w_loc
                )
                final = recalc_raw * bd.get('behavior_score', 1.0)
                
            scored.append((c, final, bd))
            
        # Re-rank dynamically
        scored.sort(key=lambda x: (-x[1], x[0].get('candidate_id', '')))
        
        results = []
        prev_score = None
        for rank_idx, (candidate, score, bd) in enumerate(scored, 1):
            out_score = round(score, 6)
            if prev_score is not None and out_score > prev_score:
                out_score = prev_score
            prev_score = out_score
            
            if bd.get('padding_row'):
                reasoning = "Candidate does not meet baseline criteria but is included to fulfill system row requirements."
            else:
                reasoning = generate_reasoning(candidate, bd, rank_idx, out_score)
            
            results.append({
                "Rank": rank_idx,
                "Candidate ID": candidate.get('candidate_id', 'Unknown'),
                "Name": candidate.get('profile', {}).get('name', 'Unknown'),
                "Title": candidate.get('profile', {}).get('current_title', 'Unknown'),
                "Badges": get_badges(candidate, bd),
                "Score": out_score,
                "Reasoning": reasoning
            })
            
        df = pd.DataFrame(results)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Top Ranked Candidates")
            st.dataframe(df.head(15), use_container_width=True)
        
        with col2:
            st.subheader("Candidate Trust Radar")
            candidate_options = [f"{r['Candidate ID']} - {r['Name']}" for r in results[:15]]
            if candidate_options:
                selected = st.selectbox("Select Candidate to Inspect", candidate_options)
                selected_id = selected.split(" - ")[0]
                
                # Find bd
                cand_tuple = next((x for x in scored if x[0].get('candidate_id') == selected_id), None)
                if cand_tuple:
                    cand_bd = cand_tuple[2]
                    radar_df = pd.DataFrame(dict(
                        r=[
                            cand_bd.get('title_score', 0) * w_title, 
                            cand_bd.get('skills_score', 0) * w_skills, 
                            cand_bd.get('experience_bonus', 0) * w_yoe * 10, # normalized visually
                            cand_bd.get('education_bonus', 0) * w_edu * 10,
                            cand_bd.get('location_bonus', 0) * w_loc * 10
                        ],
                        theta=['Title', 'Skills', 'Experience', 'Education', 'Location']
                    ))
                    fig = px.line_polar(radar_df, r='r', theta='theta', line_close=True)
                    st.plotly_chart(fig, use_container_width=True)
                    
        st.subheader("Score Distribution")
        st.bar_chart(df['Score'])
        
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Full Ranking CSV",
            data=csv,
            file_name="team_lyle_sandbox_results.csv",
            mime="text/csv",
        )

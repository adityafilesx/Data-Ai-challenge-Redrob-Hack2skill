import streamlit as st
import json
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from rank import score_candidate
    from scorer.reasoning import generate_reasoning
except ImportError:
    st.error("Could not import scorer modules. Please ensure this app is run from the sandbox directory within the redrob-lyle project.")
    st.stop()

st.set_page_config(page_title="Redrob Candidate Ranker", layout="wide")

st.title("Redrob Candidate Ranker — Team Lyle")
st.markdown("A hosted sandbox demo that lets hackathon organizers verify the ranking system works.")

with st.sidebar:
    st.header("Scoring Components")
    st.markdown("""
    - **Title Gate (0-30)**: Most decisive signal
    - **Skills Score (0-30)**: Trust-weighted by duration & endorsements
    - **YoE Score (0-15)**: Sweet spot 5-9 years
    - **Career Pattern (0-15)**: Penalizes pure IT-services
    - **Location (0-10)**: Noida/Pune preferred
    - **Education (0-5)**: Tier 1/2 bonus
    
    *Behavioral Multiplier (0.0 - 1.0) applied to final score.*
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

if uploaded_file is not None:
    content = uploaded_file.getvalue().decode("utf-8")
    data, error = load_and_parse_file(content)
    
    if error:
        st.error(error)
    else:
        st.success(f"Successfully loaded {len(data)} candidates.")
        
        unique_titles = list(set(c.get('profile', {}).get('current_title', 'Unknown') for c in data))
        st.write("Unique titles found in sample:", ", ".join(unique_titles[:10]) + ("..." if len(unique_titles) > 10 else ""))
        
        if st.button("Run Ranker", type="primary"):
            with st.spinner("Running ranking system..."):
                scored = []
                for idx, c in enumerate(data):
                    final, bd = score_candidate(c)
                    scored.append((c, final, bd))
                
                scored.sort(key=lambda x: (-x[1], x[0].get('candidate_id', '')))
                
                results = []
                prev_score = None
                for rank_idx, (candidate, score, bd) in enumerate(scored, 1):
                    out_score = round(score, 6)
                    if prev_score is not None and out_score > prev_score:
                        out_score = prev_score
                    prev_score = out_score
                    
                    reasoning = generate_reasoning(candidate, bd, rank_idx, out_score)
                    
                    results.append({
                        "Rank": rank_idx,
                        "Candidate ID": candidate.get('candidate_id', 'Unknown'),
                        "Current Title": candidate.get('profile', {}).get('current_title', 'Unknown'),
                        "Score": out_score,
                        "Reasoning": reasoning
                    })
                
                df = pd.DataFrame(results)
                
                st.subheader("Top Ranked Candidates")
                st.dataframe(df.head(10), use_container_width=True)
                
                st.subheader("Score Distribution")
                st.bar_chart(df['Score'])
                
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download Full Ranking CSV",
                    data=csv,
                    file_name="team_lyle_sandbox_results.csv",
                    mime="text/csv",
                )

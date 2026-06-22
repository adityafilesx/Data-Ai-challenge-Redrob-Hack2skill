# Redrob Hackathon — Team One Wish Willow

## Overview
This repository contains a rule-based multi-component candidate ranking system developed for the **Intelligent Candidate Discovery & Ranking Challenge** hosted by Hack2skill and Redrob. 

The core objective of the system is to take a large dataset of unstructured candidate profiles and produce a ranked list of the top 100 most technically fit and behaviorally engaged candidates. 

It uses deep data insights to prioritize candidates based on a robust Title Gate rather than relying on keyword matching. We apply trust weighting to skill durations to separate real engineers from keyword stuffers, penalize unrelated career backgrounds, and heavily reward verified platform assessments.

## Quick Start
Clone the repository and install the required dependencies:
```bash
git clone https://github.com/adityafilesx/Data-Ai-challenge-Redrob-Hack2skill.git
cd Data-Ai-challenge-Redrob-Hack2skill
pip install -r requirements.txt
```

## Reproduce Submission
To run the candidate ranking pipeline, execute the main entry point script:
```bash
python rank.py --candidates ./candidates.jsonl --out ./team_lyle.csv
python validate_submission.py team_lyle.csv
```
**Expected runtime:** ~10 seconds for 100K candidates on a modern CPU. 
**Dependencies:** No network connection, GPU, or pre-computed artifacts are needed.

### Generated Artifacts
When you run `rank.py`, it generates three important output files:
1. `team_lyle.csv`: The final submission file containing the top 100 ranked candidates with their scores and a generated reasoning summary.
2. `knockout_report.csv`: A report listing all candidates who were instantly disqualified (knocked out) due to irrelevant backgrounds, honeypot detection, or zero technical evidence, along with the reason.
3. `ranking_explanation.json`: A detailed breakdown of the score components for each of the top 100 candidates, providing explainability for why a candidate received their specific score.

## Architecture
The system consists of a 5-component technical fit score modulated by a behavioral multiplier. Our key competitive insights from data analysis include: 
- **Duration Trust Weighting**: Verifies skill depth instead of trusting self-reported proficiency.
- **Assessment Multiplier**: Provides an assessment score boost for candidates with platform-verified tests.
- **Honeypot Detector**: Detects fake profiles based on salary inversions or logically impossible career progressions. 
- **Industry Penalties**: Heavily penalizes IT services backgrounds to favor product company experience.
- **Title Verification**: Verifies ML and software engineering history using previous titles.

## Sandbox (Interactive UI)
We have built an interactive Streamlit application to visualize the scoring logic and sandbox candidate profiles. You can run the Streamlit sandbox locally:
```bash
streamlit run sandbox/app.py
```

## Scoring Components
| Component | Range | Key Signal Used | Description |
|---|---|---|---|
| **Title Score** | 0-30 | Matches current/past titles to ML taxonomy | Ensures the candidate has a strong history of relevant titles (e.g., MLE, Data Scientist). |
| **Skills Score** | 0-30 | Trust-weighted by duration & endorsements | Evaluates both Tier A (core ML/DL) and Tier B (Data/Cloud) skills based on time usage. |
| **YoE Score** | 0-15 | 5-9 years sweet spot | Normalizes years of experience to target mid-to-senior level talent without bias against extremely senior or junior roles. |
| **Career Pattern** | 0-15 | IT Services penalty, Product Company reward | Gives priority to candidates whose background is more aligned with product development. |
| **Location Score** | 0-10 | Proximity and willingness to relocate | Provides a minor bump for candidates geographically close to target tech hubs. |
| **Behavioral** | 0.0 - 1.0 | Ghost candidate detection via recent activity | A multiplier that scales down scores for candidates who have been inactive or show red flags. |

## File Structure
```text
Data-Ai-challenge-Redrob-Hack2skill/
├── rank.py                  # Main entry point for the ranker
├── validate_submission.py   # Validation script checking CSV format
├── requirements.txt         # Project dependencies
├── README.md                # Project documentation
├── candidates.jsonl         # Input dataset (ignored in git if large)
├── sandbox/                 # Streamlit interactive UI
│   └── app.py               # Sandbox launch script
└── scorer/                  # Scoring modules
    ├── __init__.py
    ├── honeypot_detector.py # Flags impossible candidates (0 score)
    ├── title_scorer.py      # Title matching and taxonomy
    ├── skills_scorer.py     # Trust-weighted skill valuation
    ├── career_scorer.py     # Product vs Services evaluation
    ├── yoe_scorer.py        # Years of experience scoring
    ├── location_scorer.py   # Geographic proximity bonus
    ├── education_scorer.py  # Tiered education bonus
    ├── behavioral_multiplier.py # Engagement and behavioral multipliers
    └── reasoning.py         # Factual summary generation
```

## Declarations
- **Privacy & Connectivity**: No external API calls are made during the ranking process.
- **Hardware Agnostic**: No GPU is required. The system is heavily optimized for CPU execution.
- **Performance**: Tested runtime is ~10 seconds.

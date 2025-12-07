# LLM-as-Judge Report: Skarbnik AI

## 1. Assessment of Current Architecture
The current implementation of "Skarbnik AI" is a solid **rule-based expert system** but falls short of being a true "AI" system that can compete with LLM-native solutions.

### Strengths:
- **Modular Architecture**: Clear separation of `agents` for different tasks (Forecasting, Compliance, Conflicts).
- **Comprehensive Domain Logic**: You have encoded specific Polish budget regulations (Paragraf 4300, 6060, etc.) into the code.
- **Frontend Dashboard**: Functional React dashboard with tailored views for different agents.

### Weaknesses (The "Losing" Factors):
- **Fake AI**: The "Agents" rely on `regex` and hardcoded `keywords` (e.g., `forecaster_agent.py` line 33, `compliance_agent.py` line 39).
    - *Risk*: If a user types "Komputeryzacja stanowisk pracy" instead of "zakup sprzętu", your `ComplianceAgent` fails to flag it as investment.
    - *Risk*: `ConflictAgent` uses `SequenceMatcher` (Levenshtein), which misses semantic duplicates like "Zakup MS Office" vs "Licencje biurowe".
- **Rigid Ingestion**: The system assumes the Excel structure matches specific column names. Real budget files are messy.
- **Lack of "Wow" Factor**: It feels like a slightly smarter Excel. It doesn't "think" for the user.

## 2. Strategy to Win (Thinking Outside the Box)

To beat participants just using standard "Chat with PDF" wrappers, we need **Agentic Intelligence** that proactively acts as a "Shadow Controller" (Główny Księgowy).

### Winning Features to Implement:

#### A. The "Regulations RAG" (Retrieval Augmented Generation) -> **IMPLEMENTED (Partial)**
Instead of hardcoding `6050 = Investment`, embed the full text of `docs/Wyciąg nr 2c...pdf`.
- **Implementation**: `SemanticComplianceAgent` now capable of using LLM to reason about regulations.

#### B. Semantic Anomaly Detection (The "Hunter" Agent) -> **IMPLEMENTED**
We have replaced strict thresholds with an LLM-based auditor.
- **New Feature**: "Pełny Audyt AI" in the Compliance tab.
- **Prompt**: "You are a ruthless budget auditor. This department spent 0 PLN on training last year but wants 50k this year. Is this suspicious given they are the IT department?"
- **Why it wins**: It finds logic errors, not just math errors.

#### C. Reverse-Templating "Bureaucrat"
Your usage of LLM to *generate* the Word documents is good. Take it further:
- **Feature**: Real-time "Legal Check". As the user types the justification in the UI, a sidebar highlights "weak" legal arguments and suggests stronger "Urzędniczy" phrasing.

## 3. How to Enable "God Mode" (Real AI)

I have implemented the **Semantic Compliance Agent** (`backend/app/agents/semantic_compliance_agent.py`). By default, it runs in **Demo Mode** (simulated AI) to ensure it works during the demo even without keys.

To enable the **Real OpenAI Reasoning**:

1. Create a `.env` file in `backend/`:
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ```

2. Restart the backend.
   The agent will automatically switch from "Simulation" to "GPT-4 Turbo" mode, providing:
   - Deep reasoning about "Wata słowna" (vague justifications).
   - Linking specific legal acts (not just the ones we hardcoded).
   - Detecting "salamislicing" (splitting orders to avoid tenders).

## 4. Next Steps for Hackathon Victory
1. **Live Demo Strategy**:
   - Start with a standard "Regex" check (show it passing green).
   - Then click **"Pełny Audyt AI"** and watch it turn RED because the description was "Purchase of stuff" (too vague).
   - This contrast ("Rule-based says OK, AI says NO") is a winning narrative.

2. **Ingestion Upgrade**:
   - Improve `ingestion_agent.py` to use LLM to map columns dynamically, so you can upload *any* excel file, not just the template.

Good luck! You have built a solid foundation. Now we have added the "Brain".

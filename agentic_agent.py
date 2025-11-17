# ============================
# FILE: agentic_agent.py
# ============================

import re
from datetime import datetime
from typing import Dict, List, Any


class VoiceAgent:
    """
    Core agentic brain: perceive -> reason -> act.
    Works on text, can be wrapped with voice I/O later.
    """

    def __init__(self):
        self.memory: List[Dict[str, Any]] = []

    # ---------- PERCEIVE ----------
    def perceive(self, text: str) -> Dict[str, Any]:
        intent = self._extract_intent(text)
        entities = self._extract_entities(text)
        sentiment = self._analyze_sentiment(text)

        perception = {
            "text": text,
            "intent": intent,
            "entities": entities,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat(),
        }

        self.memory.append(perception)
        return perception

    def _extract_intent(self, text: str) -> str:
        text_lower = text.lower()
        intent_patterns = {
            "create": ["create", "make", "generate", "write"],
            "search": ["search", "find", "look for", "show me"],
            "analyze": ["analyze", "explain", "understand", "what is"],
            "calculate": ["calculate", "compute", "how much", "sum"],
            "schedule": ["schedule", "plan", "set reminder", "meeting"],
            "translate": ["translate", "say in", "convert to"],
            "summarize": ["summarize", "brief", "tldr", "overview"],
        }
        for intent, keywords in intent_patterns.items():
            if any(kw in text_lower for kw in keywords):
                return intent
        return "conversation"

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        entities = {
            "numbers": re.findall(r"\d+", text),
            "dates": re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", text),
            "times": re.findall(r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b", text.lower()),
            "emails": re.findall(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text
            ),
        }
        return {k: v for k, v in entities.items() if v}

    def _analyze_sentiment(self, text: str) -> str:
        positive = ["good", "great", "excellent", "happy", "love", "thank"]
        negative = ["bad", "terrible", "sad", "hate", "angry", "problem"]
        text_lower = text.lower()

        pos_count = sum(1 for word in positive if word in text_lower)
        neg_count = sum(1 for word in negative if word in text_lower)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"

    # ---------- REASON ----------
    def reason(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        intent = perception["intent"]
        reasoning = {
            "goal": self._identify_goal(intent),
            "prerequisites": self._check_prerequisites(intent),
            "plan": self._create_plan(intent, perception["entities"]),
            "confidence": self._calculate_confidence(perception),
        }
        return reasoning

    def _identify_goal(self, intent: str) -> str:
        mapping = {
            "create": "Generate new content",
            "search": "Retrieve information",
            "analyze": "Understand and explain",
            "calculate": "Perform computation",
            "schedule": "Organize time-based tasks",
            "translate": "Convert between languages",
            "summarize": "Condense information",
        }
        return mapping.get(intent, "Assist user")

    def _check_prerequisites(self, intent: str) -> List[str]:
        prereqs = {
            "search": ["internet access", "search tool"],
            "calculate": ["math processor"],
            "translate": ["translation model"],
            "schedule": ["calendar access"],
        }
        return prereqs.get(intent, ["language understanding"])

    def _create_plan(self, intent: str, entities: Dict[str, List[str]]) -> Dict[str, Any]:
        plans = {
            "create": {
                "steps": [
                    "understand_requirements",
                    "generate_content",
                    "validate_output",
                ],
                "estimated_time": "10s",
            },
            "analyze": {
                "steps": ["parse_input", "analyze_components", "synthesize_explanation"],
                "estimated_time": "5s",
            },
            "calculate": {
                "steps": ["extract_numbers", "determine_operation", "compute_result"],
                "estimated_time": "2s",
            },
        }
        default_plan = {
            "steps": ["understand_query", "process_information", "formulate_response"],
            "estimated_time": "3s",
        }
        return plans.get(intent, default_plan)

    def _calculate_confidence(self, perception: Dict[str, Any]) -> float:
        base = 0.7
        if perception["entities"]:
            base += 0.15
        if perception["sentiment"] != "neutral":
            base += 0.1
        if len(perception["text"].split()) > 5:
            base += 0.05
        return min(base, 1.0)

    # ---------- ACT ----------
    def act(self, reasoning: Dict[str, Any]) -> str:
        plan = reasoning["plan"]
        results = []
        for step in plan["steps"]:
            results.append(self._execute_step(step))
        response = self._generate_response(results, reasoning)
        return response

    def _execute_step(self, step: str) -> Dict[str, Any]:
        # Placeholder – this is where you'd plug in tools (calculator, search, etc.)
        return {"step": step, "status": "completed", "output": f"Executed {step}"}

    def _generate_response(self, results: List[Dict[str, Any]], reasoning: Dict[str, Any]) -> str:
        goal = reasoning["goal"]
        conf = reasoning["confidence"]

        prefix = (
            "I understand you want to"
            if conf > 0.8
            else "I think you're asking me to"
        )
        response = f"{prefix} {goal.lower()}. "

        if len(self.memory) > 1:
            response += "Based on our conversation so far, "

        response += f"I've analyzed your request and completed {len(results)} reasoning steps."
        return response


class AgenticTextAssistant:
    """
    Thin wrapper to keep it simple for Streamlit:
    you call `process(text)` and get back the full reasoning bundle.
    """

    def __init__(self):
        self.agent = VoiceAgent()
        self.interaction_count = 0

    def process(self, text: str) -> Dict[str, Any]:
        perception = self.agent.perceive(text)
        reasoning = self.agent.reason(perception)
        response_text = self.agent.act(reasoning)
        self.interaction_count += 1

        return {
            "input_text": text,
            "perception": perception,
            "reasoning": reasoning,
            "response_text": response_text,
        }


def render_reasoning_block(st, result: Dict[str, Any]):
    """
    Streamlit-friendly visualization of the agent's chain:
    INPUT -> PERCEPTION -> REASONING -> RESPONSE
    """
    perc = result["perception"]
    rsn = result["reasoning"]

    st.markdown("### 🤖 Agentic Reasoning Breakdown")

    st.markdown(f"**📝 Input:** {result['input_text']}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Intent:** `{perc['intent']}`")
    with col2:
        st.markdown(f"**Sentiment:** `{perc['sentiment']}`")
    with col3:
        st.markdown(f"**Confidence:** `{rsn['confidence']:.0%}`")

    if perc["entities"]:
        st.markdown("**🔍 Entities detected:**")
        for k, v in perc["entities"].items():
            st.markdown(f"- **{k}**: {', '.join(v)}")

    st.markdown("**🧠 Plan:**")
    st.markdown(
        f"- **Goal:** {rsn['goal']}\n"
        f"- **Prerequisites:** {', '.join(rsn['prerequisites'])}\n"
        f"- **Steps:** " + " → ".join(rsn["plan"]["steps"])
    )

    st.markdown("**💬 Response:**")
    st.write(result["response_text"])

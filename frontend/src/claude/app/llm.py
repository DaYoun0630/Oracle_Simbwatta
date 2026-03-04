"""
LLM Chat Service for MCI Platform.

Provides Korean-optimized conversational AI for cognitive training.
Uses OpenAI GPT-4o-mini with carefully crafted prompts for elderly patients.
"""

from typing import List, Dict, Optional
import yaml
from pathlib import Path

from openai import AsyncOpenAI

from .config import settings


class LLMService:
    """Service for LLM-based chat interactions."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, str]:
        """Load prompts from YAML configuration."""
        prompts_file = Path(__file__).parent / "prompts.yaml"

        if not prompts_file.exists():
            # Return default prompts if file doesn't exist
            return {
                "system": "당신은 노인 환자를 위한 친절하고 따뜻한 AI 상담사입니다. 간단하고 명확한 한국어로 대화하세요.",
                "cognitive_training": "환자의 인지 능력을 향상시키기 위한 대화를 진행하세요. 기억력, 주의력, 언어 능력을 자연스럽게 테스트하세요."
            }

        with open(prompts_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("prompts", {})

    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        prompt_type: str = "cognitive_training",
        patient_stage: str = "unknown"
    ) -> str:
        """
        Send a chat message and get LLM response.

        Args:
            message: User's message
            conversation_history: Previous conversation (list of {"role": "user/assistant", "content": "..."})
            prompt_type: Type of prompt to use (cognitive_training, memory_exercise, etc.)
            patient_stage: Patient's MCI stage for tailored responses

        Returns:
            LLM response text
        """
        # Build system prompt
        system_prompt = self.prompts.get("system", "")
        task_prompt = self.prompts.get(prompt_type, "")

        # Add patient stage context
        stage_context = f"\n\n환자의 현재 상태: {patient_stage}"
        full_system_prompt = f"{system_prompt}\n\n{task_prompt}{stage_context}"

        # Build messages
        messages = [{"role": "system", "content": full_system_prompt}]

        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Keep last 10 messages for context

        # Add current message
        messages.append({"role": "user", "content": message})

        try:
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7,  # Slightly creative but consistent
                top_p=0.9,
                frequency_penalty=0.5,  # Reduce repetition
                presence_penalty=0.3
            )

            return response.choices[0].message.content

        except Exception as e:
            # Log error and return fallback response
            print(f"LLM API error: {str(e)}")
            return "죄송합니다. 잠시 후 다시 시도해 주세요."

    async def generate_exercise_prompt(self, exercise_type: str, difficulty: str = "medium") -> str:
        """
        Generate a cognitive exercise prompt.

        Args:
            exercise_type: Type of exercise (memory, attention, language)
            difficulty: Difficulty level (easy, medium, hard)

        Returns:
            Exercise prompt text
        """
        prompt_key = f"exercise_{exercise_type}_{difficulty}"
        exercise_prompt = self.prompts.get(prompt_key, self.prompts.get(f"exercise_{exercise_type}", ""))

        if not exercise_prompt:
            # Fallback
            return f"{exercise_type} 훈련을 시작합니다. 준비되셨나요?"

        return exercise_prompt

    async def evaluate_response(
        self,
        question: str,
        user_response: str,
        expected_answer: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Evaluate user's response to a cognitive exercise.

        Args:
            question: The exercise question
            user_response: User's answer
            expected_answer: Optional expected answer for comparison

        Returns:
            Evaluation result with score and feedback
        """
        evaluation_prompt = f"""
다음 인지 훈련 질문과 환자의 답변을 평가해주세요.

질문: {question}
환자 답변: {user_response}
{'기대 답변: ' + expected_answer if expected_answer else ''}

평가 기준:
1. 적절성 (관련성)
2. 정확성 (정답 여부)
3. 언어 능력 (유창성, 문법)
4. 인지 능력 수준

JSON 형식으로 응답:
{{
    "score": 0-100,
    "feedback": "피드백 내용",
    "aspects": {{
        "relevance": 0-100,
        "accuracy": 0-100,
        "fluency": 0-100
    }}
}}
"""

        messages = [
            {"role": "system", "content": "당신은 인지 평가 전문가입니다."},
            {"role": "user", "content": evaluation_prompt}
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.3  # More consistent for evaluation
            )

            # Parse JSON response
            import json
            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"Evaluation error: {str(e)}")
            return {
                "score": 50,
                "feedback": "평가를 완료하지 못했습니다.",
                "aspects": {"relevance": 50, "accuracy": 50, "fluency": 50}
            }


# Singleton instance
llm_service = LLMService()

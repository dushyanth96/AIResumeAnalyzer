import os
import re
from textwrap import shorten

from app.core.config import get_settings
from app.schemas.ai import AICoachOutput
from app.services.skill_extractor import SkillComparison


class AICoachConfigurationError(RuntimeError):
    """Raised when the OpenAI integration is not configured."""


class AICoachGenerationError(RuntimeError):
    """Raised when the OpenAI API call fails."""


class AICoachService:
    """Generate all coaching content through prioritized AI providers.

    Phase 6 intentionally does not use static interview questions or local
    suggestion templates. The deterministic services still compute facts
    such as matched skills and score breakdown, then OpenAI generates the
    human-facing guidance from that data.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    def generate(
        self,
        resume_text: str,
        job_description: str,
        skills: SkillComparison,
        score_breakdown: dict[str, float],
        gemini_key: str | None = None,
        openai_key: str | None = None,
        hf_token: str | None = None,
    ) -> AICoachOutput:
        openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        hf_token = hf_token or self.settings.hf_token
        gemini_key = gemini_key or self.settings.gemini_api_key

        if not openai_key and not hf_token and not gemini_key:
            raise AICoachConfigurationError("Neither OPENAI_API_KEY, HF_TOKEN, nor GEMINI_API_KEY is configured.")

        provider_attempts: list[tuple[str, str | None]] = [
            ("gemini", gemini_key),
            ("huggingface", hf_token),
            ("openai", openai_key if self.settings.enable_openai else None),
        ]

        last_error: Exception | None = None
        for provider, api_key in provider_attempts:
            if not api_key:
                continue
            try:
                return self._try_generate_with_quality_checks(
                    provider, resume_text, job_description, skills, score_breakdown, api_key
                )
            except Exception as exc:
                last_error = exc
                print(f"{provider.title()} generation failed, trying the next provider. Error: {exc}")

        if last_error is not None:
            raise self._format_error(last_error) from last_error

        raise AICoachGenerationError("All AI providers failed or were not configured.")

    def _format_error(self, exc: Exception) -> Exception:
        if isinstance(exc, AICoachGenerationError):
            return exc
        error_message = str(exc)
        if "insufficient_quota" in error_message or "exceeded your current quota" in error_message:
            return AICoachGenerationError(
                "API quota is unavailable for this key. Check billing/quota or use another key."
            )
        if "Incorrect API key" in error_message or "invalid_api_key" in error_message or "401" in error_message:
            return AICoachGenerationError("AI authentication failed. Check your API key or HF_TOKEN.")
        return AICoachGenerationError("AI coaching generation failed.")

    def _try_generate_with_quality_checks(
        self,
        provider: str,
        resume_text: str,
        job_description: str,
        skills: SkillComparison,
        score_breakdown: dict[str, float],
        api_key: str,
    ) -> AICoachOutput:
        coach_output = self._generate_with_ai(
            provider=provider,
            resume_text=resume_text,
            job_description=job_description,
            skills=skills,
            score_breakdown=score_breakdown,
            api_key=api_key,
        )
        quality_issues = self._quality_issues(coach_output)
        if quality_issues:
            coach_output = self._generate_with_ai(
                provider=provider,
                resume_text=resume_text,
                job_description=job_description,
                skills=skills,
                score_breakdown=score_breakdown,
                api_key=api_key,
                quality_feedback=quality_issues,
            )
            quality_issues = self._quality_issues(coach_output)
            if quality_issues:
                raise AICoachGenerationError(
                    f"{provider} returned malformed or insufficiently grounded coaching content."
                )
        return coach_output

    def _generate_with_ai(
        self,
        provider: str,
        resume_text: str,
        job_description: str,
        skills: SkillComparison,
        score_breakdown: dict[str, float],
        api_key: str,
        quality_feedback: list[str] | None = None,
    ) -> AICoachOutput:
        from openai import OpenAI
        import json

        system_prompt = (
            "You are an expert career coach for college students. "
            "Generate every recommendation, suggestion, interview "
            "question, answer strategy, study plan, summary, and "
            "pitch from the provided resume and job description. "
            "Do not use generic boilerplate. Do not invent experience "
            "the candidate has not shown. Every recommendation must "
            "be grounded in the resume text, the job description, the "
            "matched skills, the missing skills, or the score breakdown. "
            "If a skill is missing, frame it as a learning/preparation "
            "gap instead of pretending the candidate has it. Do not say "
            "the candidate is currently learning something unless the "
            "resume explicitly says so. Use conditional language such as "
            "'if you have used it' or 'prepare a small project' for skills "
            "that are missing. Do not recommend listing certifications, "
            "coursework, projects, or skills unless the candidate has completed "
            "them. Instead recommend completing a small proof project first. "
            "Every sentence must be clean natural language, with no debug text, "
            "schema field names, random numbers, or metadata. Be specific, "
            "practical, and interview-focused."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": self._build_prompt(
                    resume_text=resume_text,
                    job_description=job_description,
                    skills=skills,
                    score_breakdown=score_breakdown,
                    quality_feedback=quality_feedback,
                ),
            },
        ]

        if provider == "openai":
            client = OpenAI(api_key=api_key)
            response = client.beta.chat.completions.parse(
                model=self.settings.openai_model,
                messages=messages,
                response_format=AICoachOutput,
            )
            coach_output = response.choices[0].message.parsed
            coach_output.ai_provider = f"openai:{self.settings.openai_model}"
            coach_output.ai_generated = True
            return coach_output

        elif provider == "gemini":
            client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=api_key,
            )
            response = client.beta.chat.completions.parse(
                model="gemini-flash-latest",
                messages=messages,
                response_format=AICoachOutput,
            )
            coach_output = response.choices[0].message.parsed
            coach_output.ai_provider = "gemini:gemini-flash-latest"
            coach_output.ai_generated = True
            return coach_output

        elif provider == "huggingface":
            client = OpenAI(
                base_url="https://router.huggingface.co/hf-inference/v1/",
                api_key=api_key,
            )
            model = "meta-llama/Meta-Llama-3-8B-Instruct"
            
            schema_json = AICoachOutput.model_json_schema()
            messages[0]["content"] += f"\n\nYou MUST return ONLY valid JSON matching this schema: {json.dumps(schema_json)}"
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            content = response.choices[0].message.content
            
            try:
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                
                parsed_json = json.loads(content)
                coach_output = AICoachOutput.model_validate(parsed_json)
            except Exception as e:
                raise AICoachGenerationError(f"Hugging Face returned invalid JSON: {e}\nContent: {content}")
                
            coach_output.ai_provider = f"huggingface:{model}"
            coach_output.ai_generated = True
            return coach_output

    def _build_prompt(
        self,
        resume_text: str,
        job_description: str,
        skills: SkillComparison,
        score_breakdown: dict[str, float],
        quality_feedback: list[str] | None = None,
    ) -> str:
        feedback_text = ""
        if quality_feedback:
            feedback_text = (
                "\nPrevious output quality issues to fix completely:\n- "
                + "\n- ".join(quality_feedback)
                + "\n"
            )

        return f"""
Resume text:
{shorten(resume_text, width=5000, placeholder=" ...")}

Job description:
{shorten(job_description, width=3500, placeholder=" ...")}

Matched skills from deterministic extractor: {skills.matched_skills}
Missing skills from deterministic extractor: {skills.missing_skills}
Score breakdown from deterministic scoring engine: {score_breakdown}
{feedback_text}

Generate all fields in the output schema:
1. A tailored fit summary that separates demonstrated strengths from gaps.
2. At least 4 resume recommendations based on this resume and job description. Refer to
   sections such as Skills, Projects, Education, Internship, or Summary when useful.
   Do not recommend adding a missing skill as a skill claim unless the candidate has used it.
3. At least 3 job alignment advice items that connect the candidate's shown experience to the JD.
4. At least 5 likely interview questions tailored to the JD and resume, including questions
   about missing skills where the candidate should explain a learning plan.
5. Why each question matters.
6. Strong answer points grounded in the candidate's shown experience. Do not
   claim AWS, CI/CD, or other missing skills as experience unless the resume shows them.
7. At least 4 interview answer strategy items.
8. A 7-day study plan based on missing skills and weak score areas.
9. A recruiter pitch the student can say out loud.
"""

    def _quality_issues(self, output: AICoachOutput) -> list[str]:
        issues: list[str] = []
        text_items = [
            output.ai_summary,
            output.recruiter_pitch,
            *output.resume_recommendations,
            *output.job_alignment_advice,
            *output.answer_strategy,
            *output.study_plan,
        ]
        for question in output.interview_questions:
            text_items.extend(
                [
                    question.question,
                    question.why_it_matters,
                    *question.strong_answer_points,
                ]
            )

        bad_patterns = [
            r"\bstrong_answer_points\b",
            r"\binterview_questions\b",
            r"\bIndeterminate\b",
            r"\bN/A\b",
            r"\b\d{4}\s+\d{4}\b",
            r"\b0\.\d{3}\s+0\.\d{3}\b",
        ]

        for item in text_items:
            if len(item.strip()) < 12:
                issues.append("One or more generated fields are too short to be useful.")
                break
            if any(re.search(pattern, item) for pattern in bad_patterns):
                issues.append("Generated text contains schema names, debug artifacts, or numeric junk.")
                break

        missing_skill_claims = [
            "currently learning",
            "have experience with aws",
            "have experience with ci/cd",
            "have experience with nlp",
            "my experience with aws",
            "my experience with ci/cd",
            "my experience with nlp",
        ]
        combined_text = " ".join(text_items).lower()
        if any(claim in combined_text for claim in missing_skill_claims):
            issues.append("Generated text overclaims missing skills instead of framing them as gaps.")

        return issues

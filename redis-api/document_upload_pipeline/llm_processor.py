from openai import OpenAI, OpenAIError

from document import SearchResult

SYSTEM_PROMPT = """You answer questions using only the documents provided.
If the documents don't contain the answer, say you don't know.
Mention which document(s) the answer came from."""


class LlmError(Exception):
    """Raised when the LLM call fails."""


class LlmProcessor:
    """
    A class to answer a question with an LLM, using documents found by vector
    search as context (the "generation" step of RAG).
    """

    def __init__(
        self,
        openai_client: OpenAI,
        llm_model_name: str,
        max_tokens: int = 150,
        temperature: float = 0.2,
        top_p: float = 0.9,
    ):
        """
        Initialize the LlmProcessor.

        Args:
            openai_client: Authenticated OpenAI client instance
            llm_model_name: Name of the LLM deployment to use
            max_tokens: Maximum tokens in the answer
            temperature: Randomness of the answer; lower is more factual
            top_p: Nucleus sampling cut-off
        """
        self.openai_client = openai_client
        self.llm_model_name = llm_model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p

    def answer_question(self, question: str, results: list[SearchResult]) -> str:
        """
        Answer a question using the search results as context.

        Args:
            question: The user's question
            results: Documents returned by vector search

        Returns:
            The LLM's answer
        """
        # Label each document with its filename so the LLM can cite it
        context = "\n\n".join(
            f"### Document: {result.filename}\n{result.content}" for result in results
        )

        try:
            response = self.openai_client.chat.completions.create(
                model=self.llm_model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Documents:\n\n{context}\n\nQuestion: {question}",
                    },
                ],
                max_completion_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
            )
            return response.choices[0].message.content or ""
        except OpenAIError as e:
            raise LlmError(f"Failed to generate answer: {e!s}") from e

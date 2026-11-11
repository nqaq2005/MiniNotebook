import json
import re
import time
from typing import Dict, Iterator, List, Optional, Tuple
import httpx

from src.agent.state import ResearchAgentState
from src.config import settings
from src.models.schemas import RetrievedPassage
from src.retrieval.hybrid_retriever import HybridGraphRetriever


StreamEvent = Tuple[str, str]  # ("thinking" | "token", text)


class _ThinkTagRouter:
    """
    Routes streamed text between <think>...</think> tags to the 'thinking' channel.
    Handles tags split across chunk boundaries (e.g. '<thi' + 'nk>').
    Used for reasoning models (Qwen3, DeepSeek-R1, ...) served via Ollama / llama.cpp,
    which put their reasoning inside the normal `content` field.
    """

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self.in_think = False
        self.buf = ""

    def _channel(self) -> str:
        return "thinking" if self.in_think else "token"

    def feed(self, text: str) -> List[StreamEvent]:
        self.buf += text
        out: List[StreamEvent] = []
        while self.buf:
            tag = self.CLOSE if self.in_think else self.OPEN
            idx = self.buf.find(tag)
            if idx >= 0:
                if idx > 0:
                    out.append((self._channel(), self.buf[:idx]))
                self.buf = self.buf[idx + len(tag):]
                self.in_think = not self.in_think
                continue
            # Hold back a suffix that could be the beginning of a split tag
            keep = 0
            for k in range(min(len(tag) - 1, len(self.buf)), 0, -1):
                if tag.startswith(self.buf[-k:]):
                    keep = k
                    break
            emit = self.buf[: len(self.buf) - keep]
            if emit:
                out.append((self._channel(), emit))
            self.buf = self.buf[len(self.buf) - keep:]
            break
        return out

    def flush(self) -> List[StreamEvent]:
        if not self.buf:
            return []
        out = [(self._channel(), self.buf)]
        self.buf = ""
        return out


class LLMClient:
    """
    Unified LLM client supporting:
    1. Google Gemini API (official endpoint or custom Gemini reverse proxy URL)
    2. Custom OpenAI-compatible endpoints (/v1/chat/completions: Ollama, vLLM, LM Studio, LiteLLM, OpenRouter)
    3. Graceful offline fallback when neither API key nor custom URL is configured.

    Both providers are called in streaming mode, so tokens are available from the very first one
    (and proxies such as Cloudflare Tunnel never hit their idle timeout).
    """

    DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.provider = (provider or settings.llm_provider or "gemini").strip().lower()
        self.model_name = (model_name or settings.llm_model or "gemini-2.5-flash").strip()
        self.base_url = (base_url if base_url is not None else settings.llm_base_url).strip()
        self.timeout = timeout or settings.llm_timeout_seconds
        self.max_tokens = settings.llm_max_tokens if max_tokens is None else max_tokens
        raw_effort = (
            reasoning_effort
            if reasoning_effort is not None
            else getattr(settings, "llm_reasoning_effort", "medium")
        )
        self.reasoning_effort: Optional[str] = raw_effort.strip() if raw_effort else None
        self.transport = transport
        self.last_error: Optional[str] = None

        if api_key is not None:
            self.api_key = api_key.strip()
        elif self.provider in self.OPENAI_COMPATIBLE_PROVIDERS:
            self.api_key = (
                settings.custom_api_key
                or settings.openai_api_key
                or settings.gemini_api_key
            ).strip()
        else:
            self.api_key = settings.gemini_api_key.strip()

    OPENAI_COMPATIBLE_PROVIDERS = {
        "custom",
        "openai",
        "openai_compatible",
        "deepseek",
        "groq",
        "openrouter",
        "ollama",
        "together",
        "mistral",
        "anthropic",
    }

    PROVIDER_DEFAULT_BASE_URLS = {
        "openai": "https://api.openai.com/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "groq": "https://api.groq.com/openai/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "ollama": "http://localhost:11434/v1",
        "together": "https://api.together.xyz/v1",
        "mistral": "https://api.mistral.ai/v1",
    }

    @staticmethod
    def _is_valid_key(key: str) -> bool:
        placeholders = {
            "",
            "your_gemini_api_key_here",
            "your_openai_api_key_here",
            "your_custom_api_key_here",
        }
        return key not in placeholders

    @property
    def is_openai_compatible(self) -> bool:
        if self.provider in self.OPENAI_COMPATIBLE_PROVIDERS:
            return True
        if self.base_url and (
            self.base_url.rstrip("/").endswith("/v1")
            or self.base_url.rstrip("/").endswith("/chat/completions")
        ):
            return True
        return False

    @property
    def is_configured(self) -> bool:
        if self.is_openai_compatible:
            # Local endpoints (Ollama/vLLM) don't require an API key
            if self.provider == "ollama" or (self.base_url and ("localhost" in self.base_url or "127.0.0.1" in self.base_url)):
                return True
            return bool(self._is_valid_key(self.api_key) or self.base_url)
        return self._is_valid_key(self.api_key)

    def resolve_endpoint_url(self, stream: bool = False) -> str:
        """Build the target request URL based on provider and custom base_url."""
        if self.is_openai_compatible:
            default_base = self.PROVIDER_DEFAULT_BASE_URLS.get(self.provider, "https://api.openai.com/v1")
            raw_base = (self.base_url or default_base).rstrip("/")
            if raw_base.endswith("/chat/completions"):
                return raw_base
            return f"{raw_base}/chat/completions"

        # Gemini native or custom Gemini proxy
        method = "streamGenerateContent" if stream else "generateContent"
        raw_base = (self.base_url or self.DEFAULT_GEMINI_BASE_URL).rstrip("/")
        if raw_base.endswith(":generateContent") or raw_base.endswith(":streamGenerateContent"):
            base_endpoint = raw_base.rsplit(":", 1)[0] + f":{method}"
        elif "/models" in raw_base:
            base_endpoint = f"{raw_base}/{self.model_name}:{method}"
        else:
            base_endpoint = f"{raw_base}/v1beta/models/{self.model_name}:{method}"

        params = []
        if stream:
            params.append("alt=sse")
        if self._is_valid_key(self.api_key):
            params.append(f"key={self.api_key}")
        if params:
            sep = "&" if "?" in base_endpoint else "?"
            return f"{base_endpoint}{sep}{'&'.join(params)}"
        return base_endpoint

    def _http_client(self) -> httpx.Client:
        # `read` is the max silence BETWEEN two chunks (not the total duration) in streaming mode.
        timeout_cfg = httpx.Timeout(self.timeout, connect=20.0, write=30.0, pool=30.0)
        return httpx.Client(timeout=timeout_cfg, transport=self.transport)

    @staticmethod
    def _iter_sse_data(resp: httpx.Response) -> Iterator[str]:
        for line in resp.iter_lines():
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str:
                    yield data_str

    def _stream_openai(self, client: httpx.Client, messages: List[Dict], temperature: float) -> Iterator[StreamEvent]:
        url = self.resolve_endpoint_url(stream=True)
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if self._is_valid_key(self.api_key):
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: Dict = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if self.max_tokens and self.max_tokens > 0:
            payload["max_tokens"] = self.max_tokens
        if self.reasoning_effort and self.reasoning_effort.lower() not in ("none", "off"):
            payload["reasoning_effort"] = self.reasoning_effort

        router = _ThinkTagRouter()
        with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code >= 400:
                body = resp.read().decode("utf-8", errors="replace")[:300]
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code} from {url}: {body}", request=resp.request, response=resp
                )

            if "text/event-stream" not in resp.headers.get("content-type", ""):
                # Server ignored "stream": true and returned a single JSON body
                data = json.loads(resp.read().decode("utf-8"))
                choice = (data.get("choices") or [{}])[0]
                msg = choice.get("message", {}) or {}
                reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
                if reasoning:
                    yield ("thinking", reasoning)
                for ev in router.feed(msg.get("content") or choice.get("text") or ""):
                    yield ev
                yield from router.flush()
                return

            for data_str in self._iter_sse_data(resp):
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if chunk.get("error"):
                    raise RuntimeError(f"Upstream stream error: {chunk['error']}")
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                # vLLM / DeepSeek use `reasoning_content`, OpenRouter uses `reasoning`
                reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
                if reasoning:
                    yield ("thinking", reasoning)
                content = delta.get("content") or ""
                if content:
                    yield from router.feed(content)
            yield from router.flush()

    def _stream_gemini(self, client: httpx.Client, system: Optional[str], prompt: str, temperature: float) -> Iterator[StreamEvent]:
        url = self.resolve_endpoint_url(stream=True)
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if self._is_valid_key(self.api_key):
            headers["x-goog-api-key"] = self.api_key
        gen_cfg: Dict = {"temperature": temperature}
        if self.max_tokens and self.max_tokens > 0:
            gen_cfg["maxOutputTokens"] = self.max_tokens
        if self.reasoning_effort:
            effort = self.reasoning_effort.lower()
            budget_map = {"low": 1024, "medium": 2048, "high": 4096, "off": 0, "none": 0}
            if effort in budget_map and budget_map[effort] > 0:
                gen_cfg["thinkingConfig"] = {"thinkingBudget": budget_map[effort]}
        payload: Dict = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": gen_cfg,
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code >= 400:
                body = resp.read().decode("utf-8", errors="replace")[:300]
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code} from Gemini: {body}", request=resp.request, response=resp
                )
            for data_str in self._iter_sse_data(resp):
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                for cand in chunk.get("candidates") or []:
                    for part in (cand.get("content") or {}).get("parts") or []:
                        text = part.get("text") or ""
                        if text:
                            yield ("thinking" if part.get("thought") else "token", text)

    def stream(
        self,
        prompt: str,
        temperature: float = 0.2,
        system: Optional[str] = None,
    ) -> Iterator[StreamEvent]:
        """
        Yield ("thinking", text) / ("token", text) events as soon as the model produces them.
        Raises on connection / HTTP errors so callers can decide how to fall back.
        """
        if not self.is_configured:
            raise RuntimeError("LLM is not configured (missing API key or base URL).")
        self.last_error = None
        try:
            with self._http_client() as client:
                if self.is_openai_compatible:
                    messages: List[Dict] = []
                    if system:
                        messages.append({"role": "system", "content": system})
                    messages.append({"role": "user", "content": prompt})
                    yield from self._stream_openai(client, messages, temperature)
                else:
                    yield from self._stream_gemini(client, system, prompt, temperature)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            print(f"[LLMClient Warning] {self.provider} request failed: {self.last_error}")
            raise

    def generate(self, prompt: str, temperature: float = 0.2, system: Optional[str] = None) -> Optional[str]:
        """Non-streaming convenience wrapper (still streams under the hood). Returns None on failure."""
        if not self.is_configured:
            return None
        try:
            text = "".join(t for kind, t in self.stream(prompt, temperature, system) if kind == "token").strip()
            return text or None
        except Exception:
            return None


# Backward-compatible alias
GeminiClient = LLMClient


def get_synthesis_system_prompt(language: str = "vi") -> str:
    lang = (language or "vi").lower().strip()
    if lang in ("vi", "vietnamese", "tieng_viet", "tiếng việt"):
        lang_rule = (
            "4. IMPORTANT: You MUST write your ENTIRE synthesis in VIETNAMESE (Tiếng Việt) "
            "with a rigorous, fluent, and scholarly academic style. Translate complex scientific concepts clearly "
            "while preserving standard international technical terms and KEEPING EXACT inline citation tags "
            "[paper_id: Section, p.X] intact."
        )
    elif lang in ("en", "english"):
        lang_rule = (
            "4. IMPORTANT: You MUST write your ENTIRE synthesis in ENGLISH in a formal, scholarly, academic tone. "
            "Preserve exact inline citation tags [paper_id: Section, p.X] for every claim."
        )
    else:
        lang_rule = "4. Answer in the same language as the user's question. Be concise and well-structured."

    return (
        "You are an expert AI Research Assistant performing a rigorous literature review.\n"
        "Answer the user's question using ONLY the provided academic paper passages.\n"
        "Rules:\n"
        "1. Every claim MUST include the exact inline citation tag from the source, "
        "such as [2305.14314: 3 Methodology, p.4].\n"
        "2. If comparing multiple papers or methods, structure key differences clearly (a Markdown table is welcome).\n"
        "3. Do NOT invent facts or cite papers not present in the sources.\n"
        f"{lang_rule}"
    )


SYNTHESIS_SYSTEM_PROMPT = get_synthesis_system_prompt("vi")


class AgentNodes:
    """Core nodes for the Agentic Literature Review workflow."""

    COMPARISON_SPLIT_PATTERN = re.compile(
        r"\b(?:vs\.?|versus|compare|comparing|difference between|so sánh|khác nhau giữa)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        retriever: HybridGraphRetriever,
        llm_client: Optional[LLMClient] = None,
        per_query_top_k: int = settings.rerank_top_k,
    ):
        self.retriever = retriever
        self.llm = llm_client or LLMClient()
        self.per_query_top_k = per_query_top_k

    def decompose_query(self, state: ResearchAgentState) -> ResearchAgentState:
        """
        Node 1: Fast deterministic query decomposition (<1ms) so we don't waste an extra
        LLM round-trip before the main synthesis call.
        """
        question = state["question"].strip()

        sub_queries = [question]
        if self.COMPARISON_SPLIT_PATTERN.search(question):
            entities = re.findall(r"\b[A-Z][A-Za-z0-9\-]{2,}\b", question)
            unique_entities = list(dict.fromkeys(entities))
            if len(unique_entities) >= 2:
                for ent in unique_entities[:3]:
                    sub_queries.append(f"{ent} methodology architecture experiments and performance")

        state["sub_queries"] = sub_queries
        return state

    def retrieve_evidence(self, state: ResearchAgentState) -> ResearchAgentState:
        """
        Node 2: Execute Hybrid + Rerank + Citation Graph retrieval across all sub-queries
        and deduplicate retrieved chunks.
        """
        sub_queries = state.get("sub_queries") or [state["question"]]
        merged_passages: Dict[str, RetrievedPassage] = {}
        related_graph_set: Dict[str, None] = {}

        for sq in sub_queries:
            passages, graph_links = self.retriever.retrieve(
                query=sq,
                rerank_top_k=self.per_query_top_k,
            )
            for p in passages:
                cid = p.chunk.chunk_id
                if cid not in merged_passages or p.rerank_score > merged_passages[cid].rerank_score:
                    merged_passages[cid] = p
            for gl in graph_links:
                related_graph_set[gl] = None

        sorted_passages = sorted(
            merged_passages.values(),
            key=lambda p: p.rerank_score,
            reverse=True,
        )[: max(1, settings.llm_max_context_passages)]

        state["retrieved_passages"] = sorted_passages
        state["related_papers_from_graph"] = list(related_graph_set.keys())
        return state

    @staticmethod
    def _compact(text: str, limit: int) -> str:
        """Collapse whitespace / OCR picture-text noise and cap passage length to keep prefill fast."""
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
        text = re.sub(r"<br\s*/?>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

    def build_synthesis_prompt(self, question: str, passages: List[RetrievedPassage]) -> str:
        limit = settings.llm_context_chars_per_passage
        context_blocks = [
            f"Source {idx} {p.citation_tag} (Title: {p.chunk.paper_title}):\n{self._compact(p.chunk.content, limit)}"
            for idx, p in enumerate(passages, start=1)
        ]
        context_str = "\n\n---\n\n".join(context_blocks)
        return (
            f"Context Passages:\n{context_str}\n\n"
            f"User Question: {question}\n\n"
            "Synthesized Literature Review Answer:"
        )

    @staticmethod
    def build_extractive_answer(
        question: str,
        passages: List[RetrievedPassage],
        related: List[str],
        language: str = "vi",
    ) -> str:
        """Structured extractive synthesis used when the LLM is not configured or fails."""
        is_vi = (language or "vi").lower().startswith("vi")
        header = f"### Tổng hợp tài liệu nghiên cứu: *{question}*\n" if is_vi else f"### Literature Review Synthesis: *{question}*\n"
        lines = [header]
        for p in passages:
            snippet = p.chunk.content.strip().replace("\n", " ")
            if len(snippet) > 360:
                snippet = snippet[:357] + "..."
            lines.append(f"- **{p.chunk.paper_title}** ({p.citation_tag}): {snippet}")
        if related:
            net_hdr = "\n#### Mạng lưới liên kết trích dẫn" if is_vi else "\n#### Citation Network Connections"
            lines.append(net_hdr)
            for rel in related[:5]:
                lines.append(f"- {rel}")
        return "\n".join(lines)

    def synthesize_answer(self, state: ResearchAgentState) -> ResearchAgentState:
        """
        Node 3: Synthesize a grounded scientific response with inline section & page citations.
        """
        question = state["question"]
        passages = state.get("retrieved_passages", [])
        lang = state.get("language") or getattr(settings, "llm_language", "vi")

        if not passages:
            state["draft_answer"] = (
                "Không tìm thấy đoạn trích phù hợp trong thư viện tài liệu đã đánh chỉ mục. "
                "Vui lòng nạp thêm bài báo ArXiv hoặc tải PDF lên."
                if (lang or "").lower().startswith("vi")
                else "No relevant passages were found in the indexed research papers. Please ingest relevant ArXiv papers first."
            )
            return state

        system_prompt = get_synthesis_system_prompt(lang)
        if self.llm.is_configured:
            generated = self.llm.generate(
                self.build_synthesis_prompt(question, passages),
                temperature=0.1,
                system=system_prompt,
            )
            if generated:
                state["draft_answer"] = generated
                return state

        state["draft_answer"] = self.build_extractive_answer(
            question, passages, state.get("related_papers_from_graph", []), language=lang
        )
        return state

    def synthesize_answer_stream(self, state: ResearchAgentState) -> Iterator[Dict]:
        """
        Streaming variant of Node 3. Yields UI events:
          {"type": "thinking", "text"} / {"type": "token", "text"} / {"type": "fallback", "message", "text"}
        and finally stores the complete answer in state["draft_answer"].
        """
        question = state["question"]
        passages = state.get("retrieved_passages", [])
        lang = state.get("language") or getattr(settings, "llm_language", "vi")

        if not passages:
            msg = (
                "Không tìm thấy đoạn trích phù hợp trong thư viện tài liệu đã đánh chỉ mục. "
                "Vui lòng nạp thêm bài báo ArXiv hoặc tải PDF lên."
                if (lang or "").lower().startswith("vi")
                else "No relevant passages were found in the indexed research papers. Please ingest relevant ArXiv papers first."
            )
            state["draft_answer"] = msg
            yield {"type": "token", "text": msg}
            return

        system_prompt = get_synthesis_system_prompt(lang)
        answer_parts: List[str] = []
        if self.llm.is_configured:
            t0 = time.perf_counter()
            first_token_at: Optional[float] = None
            try:
                for kind, text in self.llm.stream(
                    self.build_synthesis_prompt(question, passages),
                    temperature=0.1,
                    system=system_prompt,
                ):
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                        state["ttft_ms"] = round((first_token_at - t0) * 1000)
                    if kind == "token":
                        answer_parts.append(text)
                    yield {"type": kind, "text": text}
            except Exception:
                pass
            state["llm_ms"] = round((time.perf_counter() - t0) * 1000)

            answer = "".join(answer_parts).strip()
            if answer:
                state["draft_answer"] = answer
                return
            reason = self.llm.last_error or "the model returned an empty answer"
        else:
            reason = "no LLM is configured"

        fallback = self.build_extractive_answer(
            question, passages, state.get("related_papers_from_graph", []), language=lang
        )
        state["draft_answer"] = fallback
        yield {
            "type": "fallback",
            "message": f"LLM unavailable ({reason}). Showing extractive synthesis instead.",
            "text": fallback,
        }

    def verify_grounding(self, state: ResearchAgentState) -> ResearchAgentState:
        """
        Node 4 (Hallucination & Citation Guard): Verify that cited paper IDs in the answer
        exist in the retrieved context and compute a grounding confidence score.
        """
        answer = state.get("draft_answer", "")
        passages = state.get("retrieved_passages", [])
        if not passages:
            state["is_grounded"] = False
            state["grounding_score"] = 0.0
            state["verification_notes"] = "No retrieved context available."
            return state

        valid_paper_ids = {p.chunk.paper_id for p in passages}
        cited_brackets = re.findall(r"\[([0-9]{4}\.[0-9]{4,5}|[A-Za-z0-9_.\-]+):", answer)

        if not cited_brackets:
            state["is_grounded"] = False
            state["grounding_score"] = 0.0
            state["verification_notes"] = "Answer did not include explicit inline citation tags."
            return state

        verified_citations = [cid for cid in cited_brackets if cid in valid_paper_ids]
        score = len(verified_citations) / len(cited_brackets)
        state["grounding_score"] = round(score, 2)
        state["is_grounded"] = score >= 0.8
        state["verification_notes"] = (
            f"Verified {len(verified_citations)}/{len(cited_brackets)} inline citations against retrieved papers."
        )
        return state

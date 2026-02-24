import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel


class AzureDevOpsConfig(BaseModel):
    organization: str
    project: str
    repository_id: str
    pat_token: str


class OpenAIConfig(BaseModel):
    api_key: str
    rule_model: str
    expert_model: str
    critic_model: str
    embedding_model: str


class RulesConfig(BaseModel):
    rules_path: str
    faiss_index_path: str
    faiss_meta_path: str


class AppConfig(BaseModel):
    azure: AzureDevOpsConfig
    openai: OpenAIConfig
    rules: RulesConfig
    log_level: str = "INFO"
    max_diff_chars: int = 16000
    max_rule_chunks: int = 20
    request_timeout_seconds: int = 60
    openai_max_retries: int = 3


@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)

    azure = AzureDevOpsConfig(
        organization=os.getenv("AZURE_DEVOPS_ORG", ""),
        project=os.getenv("AZURE_DEVOPS_PROJECT", ""),
        repository_id=os.getenv("AZURE_DEVOPS_REPO_ID", ""),
        pat_token=os.getenv("AZURE_DEVOPS_PAT_TOKEN", ""),
    )

    openai_cfg = OpenAIConfig(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        rule_model=os.getenv("OPENAI_RULE_MODEL", "gpt-4.1-mini"),
        expert_model=os.getenv("OPENAI_EXPERT_MODEL", "gpt-4.1-mini"),
        critic_model=os.getenv("OPENAI_CRITIC_MODEL", "gpt-4.1-mini"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
    )

    rules_cfg = RulesConfig(
        rules_path=os.getenv("RULES_DIR", os.path.join(os.getcwd(), "rules")),
        faiss_index_path=os.getenv("RULES_FAISS_INDEX_PATH", os.path.join(os.getcwd(), "rules", "faiss_index.bin")),
        faiss_meta_path=os.getenv("RULES_FAISS_META_PATH", os.path.join(os.getcwd(), "rules", "faiss_meta.json")),
    )

    log_level = os.getenv("LOG_LEVEL", "INFO")
    max_diff_chars = int(os.getenv("MAX_DIFF_CHARS", "16000"))
    max_rule_chunks = int(os.getenv("MAX_RULE_CHUNKS", "20"))
    request_timeout_seconds = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))
    openai_max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))

    return AppConfig(
        azure=azure,
        openai=openai_cfg,
        rules=rules_cfg,
        log_level=log_level,
        max_diff_chars=max_diff_chars,
        max_rule_chunks=max_rule_chunks,
        request_timeout_seconds=request_timeout_seconds,
        openai_max_retries=openai_max_retries,
    )


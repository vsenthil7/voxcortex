from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    # GCP / PubSub
    gcp_project: str = os.getenv("GCP_PROJECT", "")
    pubsub_topic_ingest: str = os.getenv("PUBSUB_TOPIC_INGEST", "voxcortex-ingest")
    pubsub_subscription_phase0: str = os.getenv("PUBSUB_SUB_PHASE0", "voxcortex-phase0-sub")

    # Database
    database_url: str = "postgresql+psycopg://postgres:Future2026@localhost:5432/voxcortex"


    # AI providers (keys injected via Secret Manager -> env)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3")
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "")

    # Security / signing
    evidence_signing_key_b64: str = os.getenv("EVIDENCE_SIGNING_KEY_B64", "")

settings = Settings()

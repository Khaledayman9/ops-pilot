from pydantic import BaseModel, Field


class IncidentState(BaseModel):
    query: str
    session_id: str

    # Classifier output
    service: str | None = None
    severity: str | None = None
    incident_type: str | None = None
    affected_components: list[str] = Field(default_factory=list)
    trigger_event: str | None = None
    classification: dict = Field(default_factory=dict)

    # Document processor output
    document_context: str = ""
    document_context_chars: int = 0
    document_filenames: list = Field(default_factory=list)

    # Entity extractor output
    entities: dict = Field(default_factory=dict)

    # Graph analyzer output
    graph_context: dict = Field(default_factory=dict)

    # Root cause finder output
    root_cause: str | None = None
    causal_chain: list[dict] = Field(default_factory=list)
    deployment_correlation: bool = False
    deployment_version: str | None = None
    timeline: list[str] = Field(default_factory=list)

    # Remediator output
    remediation_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    escalation_paths: list[dict] = Field(default_factory=list)
    runbook_references: list[str] = Field(default_factory=list)

    # RepoScoutAgent output
    repo_scout_summary: str | None = None
    repo_scout_tools_used: list[str] = Field(default_factory=list)

    # TerraformScoutAgent output
    terraform_scout_summary: str | None = None
    terraform_scout_tools_used: list[str] = Field(default_factory=list)

    # OpsAnalystAgent output
    ops_analyst_result: str | None = None
    ops_analyst_tools_used: list[str] = Field(default_factory=list)

    # Web search citations
    web_citations: list[dict] = Field(default_factory=list)

    # ConversationalistAgent output
    natural_response: str = ""
    is_incident_relevant: bool = True
    conversation_summary: str = ""

    # Pipeline bookkeeping
    current_step: str = "start"
    errors: list[str] = Field(default_factory=list)
    completed_steps: list[str] = Field(default_factory=list)

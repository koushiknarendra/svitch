# Project Plan: Svitch (Autonomous Compliance Engine)

## 1. Executive Summary
**Svitch** is a "Compliance-First" AI Gateway and Orchestration layer. Unlike general-purpose AI routers or agent frameworks, Svitch focuses on **Governance, Compliance (DPDP/POSH), and Auditability** for enterprise AI agents operating in regulated markets (primarily India).

## 2. Core Value Proposition
* **Compliance-as-Code:** Automatically validate agent outputs against DPDP (Digital Personal Data Protection) and POSH regulations.
* **Governance Gateway:** Acts as the mandatory communication layer between agent frameworks (like LangGraph/CrewAI) and LLM providers.
* **Auditability:** Generates immutable logs of all agent-to-model interactions for regulatory audits.

## 3. Architecture Roadmap

### Phase 1: The Gateway (MVP)
* **Objective:** Build a secure API proxy that enforces compliance rules.
* **Technical Stack:**
    * **Backend:** Fast-API / Go for high-throughput proxying.
    * **Compliance Engine:** Custom regex/LLM-based PII (Personally Identifiable Information) scanners.
    * **Logging:** Supabase for real-time audit trails.
* **Key Deliverable:** A functioning endpoint that routes model requests while flagging non-compliant prompts or outputs.

### Phase 2: The Orchestration Bridge
* **Objective:** Integrate with existing agent frameworks (e.g., LangGraph).
* **Features:**
    * **State Serialization:** Save/load agent states to ensure compliance across long-running workflows.
    * **Model Router:** Toggle between high-tier/low-tier models based on data sensitivity (e.g., routing sensitive data only to local/private endpoints).

### Phase 3: The Enterprise Dashboard
* **Objective:** Compliance/Legal visualization.
* **Features:**
    * **Audit Dashboard:** Visualize agent activity for non-technical stakeholders (Legal/HR).
    * **Policy Editor:** No-code interface for companies to set their own "compliance rules" for AI agents.

## 4. Development Timeline (Aggressive)

| Phase | Duration | Focus |
| :--- | :--- | :--- |
| **Week 1-2** | MVP Construction | API Proxy + Basic PII Masking |
| **Week 3-4** | Compliance Layer | DPDP Policy Engine Integration |
| **Week 5-6** | Orchestration API | LangGraph middleware integration |
| **Week 7+** | Enterprise Beta | Dashboard + Legal/HR UI |

## 5. Strategic Differentiation
| Competitor | Focus | Svitch Focus |
| :--- | :--- | :--- |
| **OpenRouter** | General API Access | **Compliance/Regulatory** |
| **Supergent** | Knowledge Layers | **Policy/Audit Layers** |
| **LangGraph/CrewAI**| Agent Workflows | **Agent Governance** |

## 6. Success Metrics
* **Latency:** < 200ms overhead on API calls.
* **Compliance Catch Rate:** 99.9% detection of PII exposure.
* **Enterprise Adoption:** Onboarding one pilot customer in the legal-tech sector.

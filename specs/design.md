# Design
```
Browser (Amplify Hosting, React/Vite, VITE_API_BASE_URL)
  -> API Gateway HTTP API (/{proxy+}, throttled 5 rps)
  -> Lambda: FastAPI via Mangum (app.main.handler)
       /api/decide -> proposal (supplied, or Strands Agent + BedrockModel) -> policy.validate() -> final reply
       /api/evaluate -> fixtures in data/cases.json -> metrics
```
- `backend/app/policy.py` rules E1-E5 (see README), fail closed on missing facts.
- `backend/app/agent.py` mock mode (default locally) or Bedrock mode; any model/parse error -> escalate holding message.
- `infra/template.yaml` Lambda (python3.12, 512 MB, 29 s), IAM bedrock:InvokeModel*, params BedrockModelId/AgentMode/AllowedOrigin.
- CORS handled only by FastAPI middleware (single source), locked to the Amplify origin after first deploy.
- Deploy without SAM/Docker: pip Linux wheels + `aws cloudformation package/deploy` + Amplify manual zip deployment.

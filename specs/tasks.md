# Tasks
✅ done and verified · ⬜ not done

- ✅ T1 Adopt reference implementation (`ai-scheduling-reliability`), 10 fixtures / 5 categories
- ✅ T2 Fix frontend build (`vite-env.d.ts`); add live-agent button
- ✅ T3 Strands `BedrockModel` mapped from `BEDROCK_MODEL_ID`; failure → escalate
- ✅ T4 Generalise policy rules E1–E5; 28 backend tests pass
- ✅ T5 Lambda adapter (Mangum), CloudFormation (cfn-lint clean), `deploy.sh`, deploy workflow
- ✅ T6 Deployed to AWS `staging` (stack `scheduling-reliability-staging`, Amplify app `scheduling-reliability-ui-staging`); `/api/evaluate` 10/10, 10 live Bedrock decisions validated, CORS locked
- ✅ T7a Detailed design implemented: agents/, tools/, services/, policies/, evidence pack, one-rewrite guard, confidence gate (163 tests)
- ⬜ T7b Deploy this refactor (not deployed yet)
- ⬜ T7 Map the final model ID (pending from owner) and re-run the live cases
- ⬜ T8 Auth, explicit-date parsing, paraphrase eval set (30–50 per case), CloudWatch metrics on blocks

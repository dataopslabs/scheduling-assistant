#!/usr/bin/env bash
# End-to-end deploy: FastAPI on Lambda (Strands + Bedrock) + React UI on Amplify Hosting.
# Needs: AWS CLI, python3, node/npm, credentials, Bedrock access to $MODEL_ID in $AWS_REGION. No SAM/Docker.
# Env: AWS_REGION (us-east-1) STACK AMPLIFY_APP BRANCH MODEL_ID
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"; STACK="${STACK:-scheduling-reliability-staging}"
APP="${AMPLIFY_APP:-scheduling-reliability-ui-staging}"; BRANCH="${BRANCH:-staging}"
MODEL="${MODEL_ID:-amazon.nova-pro-v1:0}"

(cd backend && python3 -m pytest -q && python3 -m app.evaluation >/dev/null)   # never deploy a red build

# --- backend package: Linux wheels for the Lambda runtime
rm -rf .build && mkdir -p .build/backend
pip install -q -r backend/requirements-lambda.txt -t .build/backend --platform manylinux2014_x86_64 --python-version 3.12 --implementation cp --only-binary=:all:
cp -r backend/app backend/fixtures .build/backend/
cp infra/template.yaml .build/template.yaml
ACCT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="$STACK-artifacts-$ACCT-$REGION"
aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null || aws s3 mb "s3://$BUCKET" --region "$REGION"
aws cloudformation package --template-file .build/template.yaml --s3-bucket "$BUCKET" --output-template-file .build/packaged.yaml --region "$REGION" >/dev/null
deploy() { aws cloudformation deploy --template-file .build/packaged.yaml --stack-name "$STACK" --region "$REGION" \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --no-fail-on-empty-changeset \
  --parameter-overrides "BedrockModelId=$MODEL" "AllowedOrigin=$1"; }
deploy '*'
API=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
echo "API: $API"; curl -fsS "$API/health"; echo

# --- frontend: build with the API URL baked in, zip-deploy to Amplify
(cd frontend && npm ci --no-audit --no-fund && VITE_API_BASE_URL="$API" npm run build)
APP_ID=$(aws amplify list-apps --region "$REGION" --max-results 100 --no-paginate --query "apps[?name=='$APP'].appId | [0]" --output text)
if [ "$APP_ID" = "None" ]; then
  APP_ID=$(aws amplify create-app --name "$APP" --region "$REGION" --query app.appId --output text)
  aws amplify create-branch --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION" >/dev/null
elif ! aws amplify get-branch --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION" >/dev/null 2>&1; then
  aws amplify create-branch --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION" >/dev/null
fi
DOMAIN=$(aws amplify get-app --app-id "$APP_ID" --region "$REGION" --query app.defaultDomain --output text)
rm -f .build/ui.zip; (cd frontend/dist && zip -qr ../../.build/ui.zip .)
read -r URL JOB < <(aws amplify create-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION" --query '[zipUploadUrl,jobId]' --output text)
curl -fsS -T .build/ui.zip "$URL"
aws amplify start-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB" --region "$REGION" >/dev/null

# --- lock CORS to the Amplify origin
deploy "https://$BRANCH.$DOMAIN"
echo "UI: https://$BRANCH.$DOMAIN"

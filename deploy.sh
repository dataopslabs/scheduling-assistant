#!/usr/bin/env bash
# End-to-end deploy: Lambda + HTTP API (SAM) -> Amplify static hosting (manual zip deploy).
# Prereqs: AWS CLI (no SAM/Docker needed), credentials, Bedrock model access enabled in $AWS_REGION.
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"; STACK="${STACK:-scheduling-safeguard}"; APP="${AMPLIFY_APP:-scheduling-safeguard-ui}"; BRANCH=main; MODEL="${MODEL_ID:-us.amazon.nova-lite-v1:0}"

PYTHONPATH=backend:tests python3 -m unittest discover -s tests          # never deploy a red build

# Package without Docker/SAM: Linux wheels for the Lambda runtime (strands deps include compiled pydantic-core)
rm -rf .build && mkdir -p .build/backend
pip install -q -r backend/requirements.txt -t .build/backend --platform manylinux2014_x86_64 --python-version 3.12 --implementation cp --only-binary=:all:
cp -r backend/*.py backend/prompts .build/backend/
sed 's#CodeUri: ../backend/#CodeUri: backend/#' infra/template.yaml > .build/template.yaml
ACCT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="$STACK-artifacts-$ACCT-$REGION"
aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null || aws s3 mb "s3://$BUCKET" --region "$REGION"
aws cloudformation package --template-file .build/template.yaml --s3-bucket "$BUCKET" --output-template-file .build/packaged.yaml --region "$REGION"
DEPLOY=(aws cloudformation deploy --template-file .build/packaged.yaml --stack-name "$STACK" --region "$REGION" --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND --no-fail-on-empty-changeset)
"${DEPLOY[@]}" --parameter-overrides "BedrockModelId=$MODEL"
API=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
echo "API: $API"; curl -fsS "$API/health"; echo

APP_ID=$(aws amplify list-apps --region "$REGION" --query "apps[?name=='$APP'].appId | [0]" --output text)
if [ "$APP_ID" = "None" ]; then
  APP_ID=$(aws amplify create-app --name "$APP" --region "$REGION" --query app.appId --output text)
  aws amplify create-branch --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION" >/dev/null
fi
DOMAIN=$(aws amplify get-app --app-id "$APP_ID" --region "$REGION" --query app.defaultDomain --output text)

TMP=$(mktemp -d); cp frontend/index.html "$TMP/"; echo "window.API_URL='$API';" > "$TMP/config.js"
(cd "$TMP" && zip -q ../ui.zip index.html config.js)
read -r URL JOB < <(aws amplify create-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION" --query '[zipUploadUrl,jobId]' --output text)
curl -fsS -T "$TMP/../ui.zip" "$URL"
aws amplify start-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB" --region "$REGION" >/dev/null

# tighten CORS to the Amplify origin
"${DEPLOY[@]}" --parameter-overrides "BedrockModelId=$MODEL" "AllowedOrigin=https://$BRANCH.$DOMAIN"
echo "UI: https://$BRANCH.$DOMAIN"

#!/usr/bin/env bash
# End-to-end deploy: Lambda + HTTP API (SAM) -> Amplify static hosting (manual zip deploy).
# Prereqs: AWS CLI + SAM CLI, credentials, Bedrock model access enabled in $AWS_REGION.
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"; STACK="${STACK:-scheduling-safeguard}"; APP="${AMPLIFY_APP:-scheduling-safeguard-ui}"; BRANCH=main

PYTHONPATH=backend:tests python3 -m unittest discover -s tests          # never deploy a red build

sam build -t infra/template.yaml
sam deploy --stack-name "$STACK" --region "$REGION" --resolve-s3 --capabilities CAPABILITY_IAM --no-confirm-changeset --no-fail-on-empty-changeset
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
sam deploy --stack-name "$STACK" --region "$REGION" --resolve-s3 --capabilities CAPABILITY_IAM --no-confirm-changeset --no-fail-on-empty-changeset \
  --parameter-overrides "AllowedOrigin=https://$BRANCH.$DOMAIN"
echo "UI: https://$BRANCH.$DOMAIN"

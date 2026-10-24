#!/usr/bin/env bash
# From local computer: AWS_PROFILE=b3-1 bash scripts/verify.sh ~/.ssh/b3-1.pem
set -euo pipefail
[[ $# -eq 1 && -f "$1" ]] || { echo 'Usage: bash scripts/verify.sh PRIVATE_KEY.pem' >&2; exit 2; }
REGION=ap-northeast-2
output() {
  aws cloudformation describe-stacks --region "$REGION" --stack-name b3-1 \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" --output text
}
PUBLIC_IP=$(output PublicIp)
INSTANCE_ID=$(output InstanceId)
SG_ID=$(output SecurityGroupId)
[[ "$PUBLIC_IP" != None && -n "$PUBLIC_IP" ]] || exit 1
STATE=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' --output text)
[[ "$STATE" == running ]] || { echo "EC2 not running: $STATE" >&2; exit 1; }
echo "[EC2] $INSTANCE_ID $PUBLIC_IP $STATE"
ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i "$1" "ec2-user@$PUBLIC_IP" 'bash -se' <<'REMOTE'
sudo cloud-init status --wait
systemctl is-active --quiet nginx
CODE=$(curl -sS -o /dev/null -w '%{http_code}' http://localhost)
[[ "$CODE" == 200 ]]
curl -fsS https://example.com > /dev/null
printf 'Nginx active; localhost HTTP %s; outbound HTTPS OK\n' "$CODE"
REMOTE
CODE=$(curl -sS --connect-timeout 10 --max-time 20 -o /dev/null -w '%{http_code}' "http://$PUBLIC_IP/health")
BODY=$(curl -fsS --connect-timeout 10 --max-time 20 "http://$PUBLIC_IP/health")
[[ "$CODE" == 200 && "$BODY" == OK ]] || { echo "Health failed: $CODE $BODY" >&2; exit 1; }
echo "[External] GET http://$PUBLIC_IP/health => HTTP $CODE, $BODY"
echo "[Security group] $SG_ID: verify inbound rules separately"

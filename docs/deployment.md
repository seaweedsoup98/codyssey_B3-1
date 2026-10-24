# 배포 · 검증 · 삭제

**현재는 실행 절차만 준비된 상태로, AWS 배포나 과금 리소스 삭제가 확인되지 않았습니다.** AWS 계정의 프리 티어/크레딧과 퍼블릭 IPv4 비용을 먼저 확인합니다. 모든 리소스는 서울 리전(`ap-northeast-2`)에 만듭니다.

## 1. 실습 IAM 사용자 준비

기존 **관리자 IAM 사용자(루트 아님)**로 IAM 콘솔에서 `b3-1-lab` 사용자 하나를 생성합니다. [제한 정책](../iam/least-privilege-policy.json)을 **인라인 정책**으로 적용합니다. 해당 정책은 특정 CloudFormation 스택(`b3-1`), EC2/VPC 관련 작업, 공개 AMI 파라미터 조회만 허용합니다. AdministratorAccess 및 무관한 S3/RDS 권한을 부여하지 않습니다. 콘솔 사용 시 MFA를 활성화합니다. 자격 증명을 Git에 올리지 않습니다.

```bash
aws configure --profile b3-1
# Default region: ap-northeast-2
export AWS_PROFILE=b3-1
aws sts get-caller-identity
```

ARN이 `arn:aws:iam::...:user/b3-1-lab`인지 확인합니다. 루트 계정이면 진행하지 않습니다.

## 2. SSH 키 및 접속 IP

기존 서울 리전 키페어가 없다면 생성합니다. 개인 키는 Git에 절대 저장하지 않습니다.

```bash
mkdir -p ~/.ssh
umask 077
aws ec2 create-key-pair --region ap-northeast-2 --key-name b3-1 \
  --key-type rsa --query KeyMaterial --output text > ~/.ssh/b3-1.pem
chmod 400 ~/.ssh/b3-1.pem
MY_IP=$(curl -fsS https://checkip.amazonaws.com | tr -d '\r\n')
echo "$MY_IP/32"
```

## 3. 인프라 생성

```bash
aws cloudformation validate-template --region ap-northeast-2 \
  --template-body file://template.yaml
aws cloudformation create-stack --region ap-northeast-2 \
  --stack-name b3-1 --template-body file://template.yaml \
  --parameters ParameterKey=KeyName,ParameterValue=b3-1 \
               ParameterKey=SshCidr,ParameterValue="$MY_IP/32"
aws cloudformation wait stack-create-complete --region ap-northeast-2 --stack-name b3-1
aws cloudformation describe-stacks --region ap-northeast-2 \
  --stack-name b3-1 --query 'Stacks[0].Outputs'
```

실패한 경우 `aws cloudformation describe-stack-events --region ap-northeast-2 --stack-name b3-1 --max-items 25`로 확인합니다. **CREATE_COMPLETE는 Nginx 설치 성공을 보장하지 않으므로** 아래 검증이 별도로 필요합니다.

## 4. 검증과 실제 증거

```bash
bash scripts/verify.sh ~/.ssh/b3-1.pem
```

스크립트는 EC2 running → SSH → cloud-init 완료 → Nginx 활성 → 내부 `localhost` HTTP 200 → `curl https://example.com` 외부 전송 → EC2 밖에서 `GET /health`의 200/OK를 확인합니다.

보안 그룹 확인:
```bash
SG_ID=$(aws cloudformation describe-stacks --region ap-northeast-2 --stack-name b3-1 \
  --query "Stacks[0].Outputs[?OutputKey=='SecurityGroupId'].OutputValue | [0]" --output text)
aws ec2 describe-security-groups --region ap-northeast-2 --group-ids "$SG_ID" \
  --query 'SecurityGroups[0].IpPermissions'
```

**필수:** 외부 PC에서 `curl -i http://<PUBLIC_IP>/health`를 실행하고 실제 **HTTP 200, OK, URL/접속 정보**를 README에 작성하며 실제 화면을 `docs/screenshots/external-health.png`에 저장합니다. 실제 문제가 발생한 경우 최소 1건의 문제 → 가설 → 검증 → 조치 → 결과 → 재발 방지를 `docs/troubleshooting.md`에 기록합니다.

## 5. 자원 정리

스크린샷 증빙을 **먼저** 확보하고:

```bash
aws cloudformation delete-stack --region ap-northeast-2 --stack-name b3-1
aws cloudformation wait stack-delete-complete --region ap-northeast-2 --stack-name b3-1
```

스택 삭제 후 [체크리스트](cleanup-checklist.md)를 기반으로 EC2/EBS/EIP/IGW/VPC/Route Table/SG를 실제 조회하세요. IAM 사용자와 외부에서 생성한 키페어는 스택이 삭제하지 않습니다. 해당 실습만을 위해 생성한 경우에만 별도로 제거합니다. Billing 반영에는 지연이 생길 수 있습니다.

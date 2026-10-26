# 트러블슈팅 — IAM 보안 그룹 조회 권한 누락

**환경:** AWS 서울 리전, IAM 사용자 `b3-1-lab`, EC2 생성 콘솔.  
**발생 및 해결:** 2026-10-26 KST.

## 1. 증상

EC2 생성 화면의 네트워크 설정에서 기존 보안 그룹 `b3-1-web-sg`를 선택했지만, 다음 API 작업에 대한 **권한이 없다는 경고**가 표시됐다.

```text
ec2:GetSecurityGroupsForVpc
```

EC2가 실행된 뒤 통신이 막힌 문제가 아니라, **콘솔에서 VPC의 Security Group을 조회하는 단계**에서 발생한 오류였다.

## 2. 가설과 검증

실습 사용자에게 연결된 정책 `b3-1-lab-policy`의 조회 권한은 처음에 다음과 같았다.

```json
"Action": "ec2:Describe*"
```

IAM의 `Action`은 API 작업 이름과 일치해야 한다. `Describe*` 패턴은 `Describe`로 시작하는 API만 허용하므로 `GetSecurityGroupsForVpc`는 여기에 포함되지 않는다. 실제 콘솔 경고와 정책 내용을 대조해 누락된 권한을 확인했다.

## 3. 조치

정책의 `ReadEc2` 항목에 필요한 조회 권한만 추가했다.

```json
"Action": [
  "ec2:Describe*",
  "ec2:GetSecurityGroupsForVpc"
]
```

리전 조건 `aws:RequestedRegion = ap-northeast-2`는 유지하고, AWS IAM 정책 **버전 2**를 기본 버전으로 지정했다. `AdministratorAccess`는 부여하지 않았다.

## 4. 결과

기존 보안 그룹을 선택한 EC2 생성 화면에서 이전 권한 경고가 보이지 않았고, EC2 `i-0fe03d78532fbbe17` 생성에 성공했다. 이후 SSH 로그인, Nginx 상태 `active`, 내부 및 외부 HTTP 200 응답도 확인했다.

- 변경 정책: [`iam/least-privilege-policy.json`](../iam/least-privilege-policy.json)의 `ReadEc2`
- 검증 기록: [SSH·내부 서버](evidence/internal-checks.txt), [외부 HTTP](evidence/external-health.txt)
- **검증 범위:** 콘솔 경고, 정책 변경과 재시도 결과를 근거로 했다. CloudTrail 원문이나 IAM 정책 시뮬레이터 결과는 확보하지 않았다.

## 5. 재발 방지

권한 오류 시 관리자 권한을 추가하기보다 **거부된 Action 확인 → 정책의 허용 작업과 비교 → 필요한 권한만 추가 → 같은 작업 재검증** 순서로 대응한다. AWS 콘솔에서 사용하는 조회 API가 모두 `Describe*` 형태인 것은 아니다.

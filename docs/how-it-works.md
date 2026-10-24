# 구현 해설 — 생성부터 종료까지

## 요청과 리소스 생성

1. 실습 IAM 사용자의 AWS CLI 호출을 **IAM 정책**이 허용하는지 평가합니다. 이 정책은 콘솔/API를 제어하며 서버의 TCP 포트 제어와 구별됩니다. 사용자 생성에는 IAM 관리 권한이 필요하므로 템플릿 밖에서 기존 관리자 IAM이 최초 1회 준비합니다.
2. `template.yaml`의 **LabVPC**로 `10.0.0.0/16` 주소 공간을 만들고, **PublicSubnet**에 `10.0.1.0/24`를 할당합니다.
3. **InternetGateway**, **GatewayAttachment**로 VPC와 인터넷 경계를 연결합니다.
4. **PublicRouteTable**, **PublicRoute**가 `0.0.0.0/0 -> IGW` 경로를 정의하고 **PublicRouteAssociation**이 해당 라우트 테이블을 서브넷에 연결합니다. VPC 내부 `local` 경로는 AWS가 기본 생성합니다.
5. **WebSecurityGroup**이 인바운드 HTTP 80 전체 공개와 SSH 22 개인 IPv4/32 제한만 허용합니다. 기본 아웃바운드는 패키지 설치와 외부 통신 테스트를 위해 열려 있습니다.
6. **WebInstance**는 AMI(Ssm 공개 파라미터), t3.micro, 암호화된 gp3 8GiB 루트 EBS, EC2 SSH 키, 공인 IPv4를 포함합니다. `DependsOn`을 통해 라우트가 준비된 뒤 EC2를 만듭니다.

CloudFormation은 상호 의존 리소스를 `!Ref`, `!GetAtt`, `DependsOn`으로 연결하며 일부 독립 작업은 병렬 진행합니다. `!Ref`는 참조 값, `!GetAtt`는 생성 리소스의 속성을 반환합니다.

## EC2 부팅 중 웹 서버 설치

`WebInstance.UserData`는 cloud-init이 첫 부팅 시 실행하는 Bash 스크립트입니다.

```bash
set -euo pipefail
dnf install -y nginx
printf 'OK\n' > /usr/share/nginx/html/health
systemctl enable --now nginx
```

`set -euo pipefail`은 오류를 조기에 드러내고, `dnf`는 Nginx 패키지를 설치하며, `printf`는 정적 헬스체크 파일을 만들고, `systemctl`은 서버를 지금 및 다음 부팅에도 실행합니다. `index.html`도 만들기 때문에 `/`에 접속하면 기본 페이지가 뜹니다.

**CREATE_COMPLETE와 Nginx 성공은 다릅니다.** 인스턴스 생성이 끝나도 UserData 오류가 날 수 있어 `scripts/verify.sh`가 cloud-init, Nginx, HTTP를 검사합니다.

## 웹 요청과 응답

외부 사용자 → 퍼블릭 IP:80 → Internet Gateway → EC2 네트워크 인터페이스의 Security Group 허용 → Nginx → `/health` 정적 파일 → HTTP 200 / 본문 OK. SG는 **stateful**이므로 허용된 요청에 대한 응답을 추적합니다. `0.0.0.0/0 → IGW`는 VPC에서 인터넷으로 나가는 기본 라우트 선택이며 포트를 열어주는 규칙이 아닙니다.

`curl http://localhost`는 **서버 자체**의 200만 검증합니다. `curl https://example.com`은 아웃바운드를 확인합니다. 외부 PC의 `curl http://PUBLIC_IP/health`는 인바운드와 외부 웹 접근을 검사합니다. 각각 별개입니다.

## 종료와 설계 이유

CloudFormation 스택 삭제로 템플릿 내 리소스의 제거를 시도합니다. 루트 EBS는 `DeleteOnTermination: true`입니다. 별도로 만든 IAM 사용자/키페어는 별도 삭제가 필요합니다.

| 선택 | 이유 |
|---|---|
| CloudFormation 단일 템플릿 | 구성 누락을 줄이고 재현/삭제에 유리 |
| Nginx 정적 사이트 | 필수 웹 서비스를 최소 코드로 충족 |
| 공인 IPv4 자동 할당 | Elastic IP 관리 불필요(재시작 시 변경 가능) |
| SSH /32 · IAM 제한 | 네트워크 권한과 AWS API 권한을 각각 최소화 |
| IMDSv2 필수, T3 크레딧 standard | 메타데이터 보호 및 과금 위험 완화 |

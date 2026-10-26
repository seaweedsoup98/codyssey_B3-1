# 구현과 핵심 개념

## 1. 웹 서버가 인터넷에서 보이기까지

로컬 PC의 `localhost`는 **그 컴퓨터 자신**을 가리킨다. 따라서 EC2 안에서 웹페이지가 열린다는 사실만으로 다른 PC에서도 접속되는 것은 아니다. 외부 접속에는 **주소, 인터넷 경로, 포트 허용, 실제 웹 서버**가 모두 필요하다.

```text
WSL/브라우저 ── HTTP 요청: 퍼블릭 IP:80 ──> Internet Gateway
                                                │
VPC 10.0.0.0/16 ── Public Subnet 10.0.1.0/24 ──┤
                        │                       │
                        └─ EC2 네트워크 인터페이스 ← Security Group 검사
                                  │
                            Nginx :80
                                  │
                      /health 파일 → 200 OK
```

- **EC2:** 운영체제를 실행하는 가상 컴퓨터. 자체로 웹 서버는 아니므로 Nginx를 설치해야 한다.
- **퍼블릭 IPv4:** 인터넷에서 EC2를 호출할 주소. 사설 IP(이번 EC2 내부 주소는 `10.0.1.32`)만으로는 외부에서 직접 IPv4 접속할 수 없다.
- **포트:** 한 컴퓨터에서 어떤 서비스에 연결하는지 구분한다. TCP 80은 HTTP, TCP 22는 SSH 관리 접속에 사용했다.

## 2. 네트워크를 구성한 순서와 이유

| 순서 | 구성 | 필요한 이유 · 실제 설정 |
|---|---|---|
| 1 | **VPC** | 다른 네트워크와 구분할 IP 공간. `10.0.0.0/16`을 지정했다. |
| 2 | **Public Subnet** | EC2가 속할 더 작은 주소 구역. `10.0.1.0/24`, 퍼블릭 IPv4 자동 할당 활성화. |
| 3 | **Internet Gateway(IGW)** | VPC와 인터넷의 연결 지점. IGW를 생성하여 해당 VPC에 연결했다. |
| 4 | **Route Table** | 인터넷 목적지 패킷을 IGW로 보내도록 `0.0.0.0/0 → IGW` 경로를 추가하고 **서브넷에 연결**했다. |
| 5 | **Security Group** | 서버에 도달할 수 있는 새 연결을 제한했다. HTTP 80은 전체, SSH 22는 실습자 IPv4 한 개(`/32`)만 허용했다. |
| 6 | **EC2** | Public Subnet에 Amazon Linux 2023/`t3.micro` 1대와 8GiB EBS를 배치하고, Nginx를 첫 부팅에 설치했다. |

### CIDR와 Public Subnet

IPv4 주소는 32비트다. **CIDR**의 `/16`·`/24`·`/32`는 앞에서 고정한 네트워크 비트 수이며, 숫자가 클수록 주소 범위가 작다. VPC의 `10.0.0.0/16` 안에 `10.0.1.0/24` 서브넷을 넣은 이유가 이것이다. `/32`는 IPv4 **한 주소**, `0.0.0.0/0`은 IPv4 **전체 범위**를 의미한다.

하지만 `0.0.0.0/0`의 뜻은 **어디에 사용하느냐**에 따라 다르다.

- **Route Table의 목적지:** 더 구체적인 경로가 없을 때 인터넷 목적지로 나가는 **기본 경로**. VPC 내부 주소에는 자동 생성된 `local` 경로가 적용된다.
- **Security Group의 출발지:** 이 출발지에서 해당 **포트로 들어오는 연결**을 허용. HTTP 80에는 적합하지만 SSH 22를 전체 공개해서는 안 된다.

서브넷에 IGW를 향하는 경로가 연결되면 Public Subnet으로 볼 수 있다. 다만 인스턴스가 외부 IPv4 통신을 하려면 퍼블릭 IP와 보안 규칙도 맞아야 한다. **서브넷의 이름이 Public이라고 해서 인터넷이 열리는 것은 아니다.**

### Security Group과 IAM을 구분하는 방법

**Security Group**은 EC2의 네트워크 연결을 제어하는 *상태 저장(stateful)* 방화벽이다. 허용된 연결의 응답은 별도 반대 방향 규칙 없이 추적된다. 실습에서 HTTP 80은 `0.0.0.0/0`, SSH 22는 실습 당시 공인 IP `/32`로 제한했다. 외부 패키지 설치를 위해 아웃바운드는 기본 허용을 사용했다.

**IAM**은 AWS API를 호출하는 사용자의 권한을 제어한다. `ec2:RunInstances`는 EC2 생성 작업이고, `ec2:GetSecurityGroupsForVpc`는 VPC에 연결할 보안 그룹을 조회하는 작업이다. SSH 로그인을 허용하는 SG 규칙과 AWS 자원을 생성하는 IAM 권한은 서로 대체하지 못한다. `iam/least-privilege-policy.json`의 `Effect`(허용/거부), `Action`(API), `Resource`(대상), `Condition`(조건)을 보면 제한 방식이 드러난다.

## 3. EC2 부팅부터 HTTP 응답까지

이번 인스턴스는 **AMI**(Amazon Linux 2023 운영체제 이미지)로 부팅했고, **EBS**(파일을 보관하는 블록 스토리지) gp3 8GiB를 루트 디스크로 사용했다. EC2 키 페어는 SSH 공개 키 인증에 사용했으며, 실제 개인 키 `.pem`은 GitHub에 올리지 않았다.

EC2 생성 화면의 **User Data**에 다음 스크립트를 입력했다. User Data는 처음 부팅할 때 `cloud-init`이 실행하는 초기 설정이다.

```bash
#!/bin/bash
set -euo pipefail
dnf install -y nginx
printf '%s\n' '<!doctype html><html lang="en"><meta charset="utf-8"><title>B3-1</title><h1>Hello Cloud - B3-1</h1></html>' > /usr/share/nginx/html/index.html
printf 'OK\n' > /usr/share/nginx/html/health
systemctl enable --now nginx
```

- `dnf`: Amazon Linux에서 소프트웨어를 설치하는 패키지 관리자.
- `printf ... > 경로`: 문자열을 Nginx 문서 루트의 파일로 저장. `index.html`은 기본 화면, `health`는 고정 응답 `OK`다.
- `systemctl enable --now`: Nginx를 **지금 실행**하고 이후 부팅 시에도 시작하도록 등록.
- `set -euo pipefail`: 실패·정의되지 않은 변수 등의 문제를 조기에 드러내는 Bash 설정.

Nginx는 웹 요청 `GET /health`가 도착하면 정적 파일 `/usr/share/nginx/html/health`를 반환한다. 이 응답은 서버의 HTTP 처리가 정상임을 보여주지만, 애플리케이션 전체 상태를 보증하는 종합 건강 검사는 아니다.

AWS의 EC2 `Running` 또는 상태 검사 통과만으로 Nginx 설치 성공을 알 수는 없다. 그래서 Linux 내부 확인이 별도로 필요하다.

## 4. 검증은 세 방향으로 나눈다

Windows **WSL Ubuntu**에서 SSH를 사용하여 원격 EC2의 Amazon Linux에 접속했다. 서로 다른 컴퓨터이므로 WSL의 `localhost`와 EC2의 `localhost`는 다르다.

| 실행 위치 | 명령 | 확인하는 것 |
|---|---|---|
| WSL → EC2 | `ssh -i ~/.ssh/b3-1.pem ec2-user@<퍼블릭IP>` | 키 인증·SSH 22·네트워크 경로 |
| EC2 내부 | `sudo cloud-init status --wait` / `systemctl is-active nginx` | 첫 부팅 설치 완료 및 Nginx 실행 |
| EC2 내부 | `curl -i http://localhost/health` | **서버 자체의** HTTP 200·`OK` |
| EC2 내부 | `curl -I https://example.com` | **EC2 → 인터넷** 아웃바운드 통신 |
| WSL | `curl -i http://<퍼블릭IP>/health` | **인터넷 → EC2** 인바운드 및 웹 응답 |

실제 테스트는 모두 성공했다. [내부 검증 기록](evidence/internal-checks.txt)과 [외부 HTTP 기록](evidence/external-health.txt)을 비교하면 확인 대상이 다르다는 점을 알 수 있다.

- 내부 `localhost`는 성공하는데 외부 접속이 실패한다면 **퍼블릭 IP·IGW 경로·SG의 HTTP 80**을 먼저 점검한다.
- 외부에서 HTTP `404`를 받았다면 **요청이 웹 서버까지 도달한 것**이므로 Nginx의 URL 경로와 파일을 확인한다.
- 콘솔에서 `AccessDenied`가 보이면 네트워크보다 **어떤 IAM API 작업이 거부됐는지**를 확인한다. 실제 해결 사례는 [트러블슈팅 기록](troubleshooting.md)에 있다.

## 5. 코드 위치와 재현 흐름

실제 AWS 리소스는 **콘솔에서 수동 생성**했다. 같은 구성을 코드로 살펴볼 수 있도록 다음 파일을 보관했다.

| 파일/부분 | 역할 |
|---|---|
| `template.yaml` → `Parameters` | SSH 키 이름, SSH 허용 주소, AMI 선택 |
| `template.yaml` → `LabVPC`, `PublicSubnet`, `PublicRoute`, `PublicRouteAssociation` | IP 공간, 인터넷 경로, 서브넷 연결 |
| `template.yaml` → `WebSecurityGroup`, `WebInstance.UserData` | 접근 제어 및 Nginx 설치 |
| `template.yaml` → `Outputs` | 배포 후 인스턴스 ID·퍼블릭 IP 등 출력 |
| `iam/least-privilege-policy.json` | EC2/VPC 작업과 리전 권한 제한 |
| `scripts/verify.sh` | CloudFormation으로 생성한 스택에서 Outputs를 조회해 SSH·HTTP 확인 |

CloudFormation은 **인프라를 코드로 선언하는 도구(IaC)**다. `!Ref`는 생성된 자원의 참조 값, `!GetAtt`는 자원의 속성, `DependsOn`은 선행 생성 조건을 뜻한다. 하지만 이 실습에서는 **템플릿을 실제로 배포하지 않았으므로** 템플릿의 동작 결과와 콘솔 실습 결과를 구분해야 한다. `scripts/verify.sh`도 수동 생성한 EC2에서는 스택 Outputs가 없어 그대로 실행할 수 없다.

직접 같은 환경을 재현하려면 **서울 리전 선택 → 제한된 IAM 사용자 → VPC → Public Subnet → IGW → Route Table·Subnet 연결 → SG → EC2·User Data → SSH/HTTP 검증 → 증빙 보관 → 리소스 삭제** 순서로 진행한다. 실제 화면 및 API 사용 권한은 계정에 따라 달라질 수 있다. 키와 자격 증명은 저장소에 올리지 않고, 삭제 과정은 [체크리스트](cleanup-checklist.md)에 기록한다.

## 6. 설계 선택

- **Nginx 정적 파일:** 필수 HTTP 응답을 위해 애플리케이션 프레임워크·DB가 필요하지 않다.
- **EC2 직접 퍼블릭 IPv4:** 로드 밸런서나 NAT Gateway 없이 하나의 웹 서버를 노출할 수 있다. 대신 서버 하나에 의존하며 중지 후 IP가 달라질 수 있다.
- **SSH /32 및 전용 IAM:** 인터넷 방문자와 운영 관리자의 권한을 분리한다.
- **종료 시 EBS 삭제:** EC2만 종료하고 디스크 요금이 남는 상황을 방지한다. 실제 삭제 결과까지 별도로 확인했다.

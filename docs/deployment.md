# B3-1 따라 하는 실습 — AWS 콘솔에서 직접 만들어 보기

> **추천 경로 A: AWS 콘솔에서 손으로 한 번씩 만드는 방식.** 네트워크와 보안 설정을 직접 확인하므로 첫 학습에 적합합니다. 이미 작성된 CloudFormation 코드를 실행하는 **경로 B**도 아래에 있지만, **A와 B를 동시에 진행하면 중복 EC2·VPC를 만들어 과금될 수 있습니다. 한 경로만 선택하세요.**
>
> **현재 상태:** 2026-10-26 KST 수동 실습 경로 A에서 EC2/Nginx 배포 및 외부 접속에 성공했습니다. 실제 결과는 [README](../README.md)에 기록했으며, **리소스 삭제는 미확인**입니다. 아래는 재현을 위한 실습 안내입니다. AWS UI 명칭은 변경될 수 있으므로 영문 명칭을 병기했습니다. 결과가 다르면 무리해서 넘기지 말고 관찰값을 기록하세요.

## 시작하기 전: 오늘 무슨 일을 할 것인가?

내 컴퓨터에서 `http://localhost`로 열리는 페이지를 **다른 네트워크의 사람도 열 수 있게** 만드는 게 목표입니다.

```text
[AWS에서 내 네트워크 구성]
 VPC → Subnet → Internet Gateway → Route Table
                        ↓
              [Security Group 허용 규칙]
                        ↓
                [EC2 컴퓨터 생성]
                        ↓
                [Nginx 설치/실행]
                        ↓
[내 PC] GET http://퍼블릭IP/health → 200 OK
                        ↓
            실제 증빙 저장 → AWS 자원 삭제
```

**반드시 기록할 최소 4가지:** 사용한 리전, EC2 퍼블릭 IP(실습 당시), SG TCP 80/22 규칙, 외부 `/health` HTTP 200+OK 화면. 결과는 [README](../README.md)와 [트러블슈팅 보고서](troubleshooting.md)에 적습니다.

## 0. 준비·비용·계정

### 0-1. 비용부터 확인하는 이유

EC2는 켜져 있으면 사용하지 않아도 과금될 수 있고, EBS와 퍼블릭 IPv4는 별도 비용 대상이 될 수 있습니다. **'t3.micro는 항상 무료'가 아닙니다.** 프리 티어/크레딧은 계정 생성 시기와 사용량에 따라 다릅니다.

AWS Billing → Free Tier / Credits / Cost Explorer에서 본인 계정의 혜택을 확인하고 시작하세요. 오늘 실습이 끝나면 **웹 서비스가 사라져도 괜찮다는 사실을 이해한 뒤 모든 리소스를 삭제**합니다. 'Stop' 대신 'Terminate'가 필요한 상황을 [개념 교재](concepts.md#9-삭제도-인프라의-일부-컴퓨터를-껐는데-왜-돈이-나갈까)에서 설명합니다.

### 0-2. IAM 사용자 1명

미션에서는 **루트 계정 실습 및 AdministratorAccess 부여를 금지**합니다.

- 이미 조직/개인 AWS 계정에 관리용 **IAM 사용자**가 있다면, 그 사용자가 먼저 실습 전용 IAM 사용자 `b3-1-lab`을 만들고 [제한 정책](../iam/least-privilege-policy.json)을 부여합니다.
- 실습 계정으로 로그인하고 **서울 리전(ap-northeast-2)**으로 전환합니다.
- MFA를 활성화하고 AWS 비밀번호, 액세스 키, SSH 개인 키(`.pem`)를 GitHub에 올리지 않습니다.

**원리:** IAM이 허용하는 것은 **AWS 콘솔/API에서 네트워크·서버를 만들 권한**입니다. 아래에서 만들 Security Group의 **TCP 22/80 접근 허용**과는 별개입니다.

> 저장소의 IAM 정책은 **실제 AWS 환경에서 검증되지 않은 학습용 초안**입니다. 기존 계정의 다른 AWS 서비스가 아닌 실습 전용 환경에서 진행하고, IAM 권한 오류가 뜨면 오류의 Action/Resource를 확인한 뒤 필요한 권한만 검토하세요. 관리자 권한으로 우회하지 않습니다.

### 0-3. 내가 사용할 값 메모

다음 표는 기록용입니다. **ID와 IP는 실제 생성 후 채우세요.**

| 리소스 | 이번에 사용할 이름 | 값/ID 기록 |
|---|---|---|
| Region | Seoul | `ap-northeast-2` |
| VPC | `b3-1-vpc` | `vpc-...` |
| Public Subnet | `b3-1-public-subnet` | `subnet-...` |
| Internet Gateway | `b3-1-igw` | `igw-...` |
| Route Table | `b3-1-public-route` | `rtb-...` |
| Security Group | `b3-1-web-sg` | `sg-...` |
| EC2 | `b3-1-web` | `i-...`, Public IPv4 |
| Key pair | `b3-1` | 개인 키 다운로드 보관(내용 공개 금지) |

---

# 경로 A. AWS 콘솔에서 직접 만드는 실습

## 1. VPC 생성 — 서버를 놓을 네트워크 공간 확보

**먼저 던질 질문:** EC2를 어느 네트워크에 놓을지 정하지 않으면, 인터넷 접근을 어떻게 통제할까요?

1. [VPC 콘솔](https://console.aws.amazon.com/vpc/)에 접속합니다.
2. 리전이 **Asia Pacific (Seoul) / ap-northeast-2**인지 확인합니다.
3. **Your VPCs → Create VPC**로 이동합니다.
4. 선택지가 있다면 **VPC only**를 고릅니다. (VPC and more는 NAT Gateway 등 불필요한 자원을 함께 만들 수 있으므로 사용하지 않습니다.)
5. Name tag = `b3-1-vpc`, IPv4 CIDR = `10.0.0.0/16`, IPv6 = 없음, Tenancy = Default로 생성합니다.
6. 생성된 **VPC ID**를 위 표에 기록합니다. DNS resolution/hostnames 설정을 확인해 필요하면 활성화합니다.

**눈으로 확인:** VPC가 하나 생겼지만 아직 웹 서버도 없고 인터넷 경로도 없습니다. VPC가 네트워크 주소 범위를 정의하는 **첫 번째 그릇**이라는 점을 확인합니다.

**코드 비교:** [`template.yaml`의 `LabVPC`](../template.yaml).

## 2. Subnet 생성 — 그 네트워크의 어느 구역에 놓을까?

1. VPC 콘솔 → **Subnets → Create subnet**.
2. **VPC ID = 방금 만든 b3-1-vpc** 선택.
3. Subnet name = `b3-1-public-subnet`.
4. Availability Zone = 서울 리전 내 임의의 한 가용 영역(예: ap-northeast-2a; 실제 계정에서 선택 가능한 AZ).
5. IPv4 subnet CIDR block = `10.0.1.0/24`.
6. 생성한 서브넷을 선택한 뒤 **Actions → Edit subnet settings**에서 **Enable auto-assign public IPv4 address**를 활성화합니다.

**왜 /24일까?** VPC의 `10.0.0.0/16` 안에서 웹 서버용 작은 주소 영역을 따로 떼어내기 위해서입니다. **왜 public IP 자동 할당을 켤까?** 앞으로 만들 EC2가 외부에서 접근할 주소를 갖게 하기 위해서입니다. *단, 아직 라우트를 만들지 않았으므로 이것만으로 퍼블릭 서브넷이 된 것은 아닙니다.*

**눈으로 확인:** Subnet ID, VPC ID, CIDR, Public IPv4 자동 할당 설정이 맞는지 검사합니다.

**코드 비교:** `PublicSubnet`의 `VpcId: !Ref LabVPC`, `MapPublicIpOnLaunch: true`.

## 3. Internet Gateway와 Route Table — 이제 외부로 길을 낸다

**여기가 B3-1의 핵심입니다.** 단순히 IGW를 '만드는 것'과 이 서브넷이 '그것을 경로로 사용하는 것'은 다른 단계입니다.

### 3-1. IGW 만들고 VPC에 붙이기

1. VPC 콘솔 → **Internet gateways → Create internet gateway**.
2. Name = `b3-1-igw`로 생성.
3. 만든 IGW 선택 → **Actions → Attach to VPC** → `b3-1-vpc` 선택 후 Attach.

**확인:** IGW 상태가 VPC에 **Attached**이고, 연결된 VPC ID가 내 VPC인지 봅니다.

### 3-2. Route Table 만들고 기본 경로 지정

1. VPC 콘솔 → **Route tables → Create route table**.
2. Name = `b3-1-public-route`, VPC = `b3-1-vpc`로 생성.
3. 라우트 테이블 선택 → **Routes → Edit routes → Add route**.
4. Destination = `0.0.0.0/0`, Target = **Internet Gateway** → `b3-1-igw`.
5. **Subnet associations → Edit subnet associations**에서 `b3-1-public-subnet`를 선택해 연결합니다.

**눈으로 확인해야 할 표:**

| Destination | Target |
|---|---|
| `10.0.0.0/16` | `local` |
| `0.0.0.0/0` | `igw-...` |

**핵심:** 새 라우트 테이블에 경로를 추가했더라도 **그것을 서브넷에 연결하지 않았다면** 해당 서브넷의 트래픽이 이를 사용하지 않을 수 있습니다.

**코드 비교:** `InternetGateway` → `GatewayAttachment` → `PublicRouteTable` → `PublicRoute` → `PublicRouteAssociation`.

## 4. Security Group — 길은 열렸지만 어떤 문을 열까?

1. [EC2 콘솔](https://console.aws.amazon.com/ec2/) → **Security Groups → Create security group**.
2. Name = `b3-1-web-sg`, Description = `B3-1 HTTP and personal SSH`, VPC = `b3-1-vpc`.
3. **Inbound rules**:
   - HTTP, TCP, Port **80**, Source **Anywhere-IPv4 (0.0.0.0/0)**.
   - SSH, TCP, Port **22**, Source **My IP**를 선택해 **현재 내 퍼블릭 IPv4/32**만 허용.
4. **Outbound rules**는 패키지 설치와 `example.com` 접속 실험을 위해 기본 허용 상태인지 확인합니다.
5. 전체 TCP 포트를 `0.0.0.0/0`로 허용하는 인바운드 규칙이 **없는지** 확인하고 생성합니다.

**왜 SSH는 /32일까?** 80번 포트로 오는 브라우저는 누구나 허용해야 하지만, 22번 포트로 오는 원격 OS 관리 요청은 내 PC에서만 받아야 하기 때문입니다. **HTTP 허용과 관리자 로그인 허용은 서로 다른 권한**입니다.

**확인:** SG 상세 페이지에서 인바운드 규칙 **정확히 두 개(80 전체, 22 내 IP)**를 눈으로 확인합니다. VPN이나 네트워크가 바뀌면 My IP도 바뀌므로 SSH가 끊길 수 있습니다.

**코드 비교:** `WebSecurityGroup.SecurityGroupIngress`.

## 5. EC2 생성 — 실제 컴퓨터와 웹 서버를 준비한다

1. EC2 콘솔 → **Instances → Launch instances**.
2. Name = `b3-1-web`.
3. AMI = **Amazon Linux 2023**, Architecture = x86_64.
4. Instance type = **t3.micro** (실제 본인 계정의 비용 혜택을 먼저 확인).
5. **Key pair** = `b3-1`을 새로 만들고 `.pem`을 **안전하게 다운로드**합니다. 개인 키는 재다운로드가 불가능한 경우가 있으므로 잘 보관하세요.
6. **Network settings → Edit**:
   - VPC = `b3-1-vpc`
   - Subnet = `b3-1-public-subnet`
   - Auto-assign public IP = **Enable**
   - Firewall = **Select existing security group** → `b3-1-web-sg`
7. **Storage** = 루트 EBS **gp3 8GiB**. 가능한 설정에서 Encryption 활성화, **Delete on termination** 확인. (UI에 보이지 않는 옵션은 인스턴스 생성 후 볼륨/블록 디바이스 설정에서 검증.)
8. **Advanced details → User data**에 아래 내용을 그대로 넣습니다. 이 스크립트는 첫 부팅에 OS가 실행합니다.

```bash
#!/bin/bash
set -euo pipefail
dnf install -y nginx
printf '%s\n' '<!doctype html><html lang="en"><meta charset="utf-8"><title>B3-1</title><h1>Hello Cloud - B3-1</h1></html>' > /usr/share/nginx/html/index.html
printf 'OK\n' > /usr/share/nginx/html/health
systemctl enable --now nginx
```

9. 인스턴스를 시작합니다. **Running**과 **2/2 status checks passed**를 확인합니다. UserData 실행은 이보다 늦게 끝날 수 있습니다.
10. 인스턴스 상세 화면에서 **Public IPv4 address**와 **Instance ID**를 기록합니다.

**아하 포인트:** 이전 단계는 AWS 네트워크와 가상 컴퓨터의 설정이었습니다. UserData부터는 **Linux 내부에서 앱을 설치하는 단계**입니다. AWS 리소스 생성 성공과 Nginx 설치 성공은 같은 것이 아닙니다.

**코드 비교:** `WebInstance`의 `ImageId`, `InstanceType`, `NetworkInterfaces`, `BlockDeviceMappings`, `UserData`.

## 6. SSH로 들어가 서버 내부 검증

### 6-1. 내 PC에서 로그인

Linux/macOS/WSL의 터미널을 기준으로 다음을 실행합니다(파일 경로는 다운로드한 키의 실제 위치로 바꿉니다).

```bash
chmod 400 ~/Downloads/b3-1.pem
ssh -i ~/Downloads/b3-1.pem ec2-user@<PUBLIC_IP>
```

**명령의 뜻:** `ssh`는 원격 OS 접속, `-i`는 서버와 맞는 개인 키 지정, `ec2-user`는 Amazon Linux의 기본 로그인 사용자, `PUBLIC_IP`는 실제 EC2의 퍼블릭 주소입니다.

- `Permission denied (publickey)`: 사용자 이름·키페어·키 파일이 맞는지 먼저 확인.
- `Connection timed out`: 퍼블릭 IP·SG 22/My IP·경로·인스턴스 상태를 확인.
- 첫 SSH 접속에서 호스트 키 지문을 확인하라는 메시지가 뜨면, 가능한 경우 EC2 인스턴스의 실제 지문과 대조 후 수락합니다.

### 6-2. EC2 내부에서 세 가지 검사

SSH 세션 **안에서** 다음을 실행합니다.

```bash
sudo cloud-init status --wait
systemctl is-active nginx
curl -i http://localhost/
curl -i http://localhost/health
curl -I https://example.com
```

관찰해야 할 것은:

- cloud-init: 최초 설치 과정이 끝났는지. 완료/실패 상태를 구분합니다.
- `systemctl`: 기대 출력 `active`.
- `curl http://localhost/`: HTTP 200과 `Hello Cloud - B3-1` HTML.
- `curl http://localhost/health`: HTTP 200과 `OK`.
- `curl https://example.com`: DNS 해석 및 아웃바운드 연결 성공. 예시 사이트의 상태 코드는 서비스 상황에 따라 달라질 수 있으므로, HTTP 응답이 왔는지와 명령 종료 코드도 확인합니다.

**아하 포인트:** `localhost`는 EC2 **자기 자신**입니다. 여기서 200이 나와도 밖에서 접속된다는 뜻은 아닙니다. 마지막 명령은 EC2가 **밖으로 나갈 수 있는지**를 검사하지, 밖에서 **들어올 수 있는지**를 검사하지 않습니다.

## 7. 내 PC에서 외부 접속 검증과 스크린샷 확보

SSH 세션은 `exit`로 닫고 **내 PC의 터미널에서** 다음을 실행합니다.

```bash
curl -i --connect-timeout 10 http://<PUBLIC_IP>/health
```

예상 출력 예시(실제 실행 결과가 아님):

```http
HTTP/1.1 200 OK
...

OK
```

성공을 판단할 때는 **퍼블릭 IP로 접속했는지**, **HTTP 200이 실제 반환됐는지**, **본문이 OK인지** 확인합니다. 이 세 가지가 충족되면 미션의 방식 **B** 외부 접속 검증에 해당합니다.

**제출할 스크린샷은 직접 실제 화면에서 찍어야 합니다.** 터미널에 `curl -i http://실제IP/health` 명령과 HTTP 200/OK 출력이 함께 보이도록 캡처하여 `docs/screenshots/external-health.png`로 저장하고 GitHub에 추가하세요. README의 **실제 URL·검증 시간·응답**도 작성합니다. 예시 스크린샷이나 이론상 출력으로 대체하면 안 됩니다.

기본 HTML 페이지도 확인하려면 브라우저에서 `http://<PUBLIC_IP>/`를 열어 보세요. 미션은 A/B 중 하나만 필수이므로 본 경로에서는 B 증빙을 주로 사용합니다.

## 8. 장애가 왜 생기는지 '안전하게' 한 번 확인하고 기록한다

미션은 실제 **증상 → 가설 → 검증 → 조치 → 결과 → 재발방지** 한 건 이상을 요구합니다.

추천 실습은 **웹서버가 존재하지 않는 파일을 요청해 HTTP 404를 재현**하는 것입니다. 인프라 보안 규칙을 위험하게 풀지 않고도 오류와 서버 로그를 연결해 볼 수 있습니다.

내 PC:
```bash
curl -i http://<PUBLIC_IP>/no-such-page
```

기대: `404 Not Found` (직접 실행해서 실제 출력을 기록해야 합니다).

EC2 내부 SSH:
```bash
sudo tail -n 30 /var/log/nginx/access.log
sudo ls -l /usr/share/nginx/html/health
```

**가설과 검증:** 네트워크가 끊긴 게 아니라 Nginx는 요청을 받았으나 `/no-such-page` 파일이 없으므로 404가 발생했다. access.log의 요청 경로·응답 코드와 파일 목록을 확인하고, 실제 있는 `/health` 경로로 다시 요청해 HTTP 200/OK를 확인합니다.

이 사례는 **HTTP 경로 오류**입니다. 보안그룹·라우팅 오류를 직접 다루고 싶다면 [트러블슈팅 가이드](troubleshooting.md)의 SG 점검 시나리오를 보세요. **실제 수행·기록하지 않았다면 보고서에 해결 완료라고 쓰지 않습니다.**

## 9. 스크린샷 확보 후 리소스 삭제 — 제일 중요한 마지막 단계

**중요:** 경로 A로 만든 리소스는 CloudFormation이 관리하지 않습니다. **`delete-stack` 명령으로 삭제되지 않습니다.**

본 실습에서 직접 생성한 **b3-1 자원만** 삭제합니다.

1. EC2 콘솔 → `b3-1-web` → **Instance state → Terminate (delete) instance**. 상태가 **Terminated**가 될 때까지 확인합니다.
2. EC2 → **Volumes**에서 연결된 8GiB EBS가 삭제됐는지 확인합니다. 남아 있으면 **해당 실습 전용 볼륨인지 식별한 다음** 삭제합니다.
3. VPC → Subnets → `b3-1-public-subnet` 삭제.
4. VPC → Route tables → `b3-1-public-route` 삭제. 서브넷 연결이 남아 있으면 먼저 해제합니다.
5. VPC → Internet gateways → `b3-1-igw` → **Detach from VPC → Delete**.
6. EC2 → Security Groups → `b3-1-web-sg` 삭제(인스턴스 ENI 연결이 완전히 제거된 후). 기본 SG는 삭제하지 않습니다.
7. VPC → Your VPCs → `b3-1-vpc` 삭제.
8. EC2 → **Key pairs**에서 실습 전용 `b3-1` 키페어 삭제. 로컬 개인 키도 더 사용하지 않는 경우 안전하게 제거합니다.
9. (해당 계정에서 실습 전용 IAM 사용자도 준비했다면) 관리용 IAM 사용자로 로그인해 실습 정책/사용자의 필요 여부를 확인하고 정리합니다. 본인의 다른 프로젝트 권한·자원은 건드리지 않습니다.
10. **Elastic IP, NAT Gateway, Load Balancer, RDS**를 생성하지 않았는지 확인하고, **Billing Dashboard**를 다시 확인합니다.

삭제한 사실을 [정리 체크리스트](cleanup-checklist.md)에 실제 ID/시각과 함께 기록합니다. Billing 데이터는 실시간으로 정확히 반영되지 않을 수 있습니다.

---

# 경로 B. 이미 작성된 CloudFormation 템플릿으로 배포 (선택 경로)

**콘솔 직접 실습을 원하면 경로 A만 수행하세요.** 경로 B는 IaC를 재현하고 코드 구조를 읽기 위한 대안입니다.

사전조건: 로컬 AWS CLI 프로필 `b3-1`(실습 IAM 사용자), 서울 리전 키페어 `b3-1`, `template.yaml`이 있는 저장소 루트에서 실행, 적절한 권한. **두 경로는 혼용하지 않습니다.**

```bash
export AWS_PROFILE=b3-1
aws sts get-caller-identity
MY_IP=$(curl -fsS https://checkip.amazonaws.com | tr -d '\r\n')
aws cloudformation validate-template --region ap-northeast-2 --template-body file://template.yaml
aws cloudformation create-stack --region ap-northeast-2 --stack-name b3-1 \
  --template-body file://template.yaml \
  --parameters ParameterKey=KeyName,ParameterValue=b3-1 \
               ParameterKey=SshCidr,ParameterValue="$MY_IP/32"
aws cloudformation wait stack-create-complete --region ap-northeast-2 --stack-name b3-1
bash scripts/verify.sh ~/.ssh/b3-1.pem
```

실행 오류는 `aws cloudformation describe-stack-events --region ap-northeast-2 --stack-name b3-1`로 확인하고, `CREATE_COMPLETE` 후에도 웹 서버가 실제 응답하는지 테스트합니다. 이 `verify.sh`는 **CloudFormation Outputs**를 사용하기 때문에 **경로 B에만 적용**됩니다.

경로 B 정리:
```bash
aws cloudformation delete-stack --region ap-northeast-2 --stack-name b3-1
aws cloudformation wait stack-delete-complete --region ap-northeast-2 --stack-name b3-1
```

별도로 만든 키페어, IAM 사용자와 남아 있는 EBS/EIP/네트워크 자원은 [체크리스트](cleanup-checklist.md)대로 확인해야 합니다.

---

## 공식 AWS 도움말

- [VPC 생성](https://docs.aws.amazon.com/ko_kr/vpc/latest/userguide/create-vpc.html)
- [인터넷 게이트웨이 생성·라우팅 연결](https://docs.aws.amazon.com/vpc/latest/userguide/working-with-igw.html)
- [EC2 인스턴스 생성](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/LaunchingAndUsingInstances.html)
- [EC2 SSH 연결](https://docs.aws.amazon.com/ko_kr/AWSEC2/latest/UserGuide/connect-to-linux-instance.html)
- [AWS 계정별 Free Tier 조건](https://docs.aws.amazon.com/ko_kr/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html)

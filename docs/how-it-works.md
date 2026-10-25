# B3-1 구현 해설 — AWS 명령 한 번이 실제로 만드는 것들

> [개념 교재](concepts.md)를 읽었다면 이제 **그 개념들이 코드의 어떤 부분에서 연결되는지** 확인할 차례입니다. 출발점은 `template.yaml`입니다. 이 파일은 실행 코드처럼 위에서 아래로 차례로 수행되는 Bash가 아니라, **만들 자원과 자원 사이의 관계를 선언**한 CloudFormation 문서입니다.

## 0. 가장 먼저 전체 그림을 읽는다

이번 프로젝트에 실행 역할이 서로 다른 파일은 네 종류입니다.

| 파일 | 누구에게 주는 지시인가? | 언제 사용하나? |
|---|---|---|
| `template.yaml` | **AWS CloudFormation**에게 "어떤 인프라를 만들지" | 인프라 배포 시 |
| `iam/least-privilege-policy.json` | **AWS IAM**에게 "누가 무엇을 조작해도 되는지" | 실습 IAM 사용자를 준비할 때 |
| `WebInstance.UserData` (`template.yaml` 내부) | **EC2 안의 Linux**에게 "첫 부팅 때 어떤 명령을 실행할지" | EC2 첫 부팅 시 |
| `scripts/verify.sh` | **내 PC의 Bash/AWS CLI/SSH**에게 "완성됐는지 어떻게 검사할지" | 배포 후 검사 시 |

**눈여겨볼 구분:** IAM 정책은 HTTP 요청이 들어올 때마다 평가되는 규칙이 아닙니다. AWS API로 자원을 만들거나 고칠 때 평가합니다. Security Group은 서버로 향하는 네트워크 통신을 제어합니다.

## 1. 배포 요청의 시작: `Parameters`는 왜 필요한가?

처음 보는 사람이 같은 템플릿을 쓰더라도 **자기 SSH 키 이름**과 **현재 접속 IP**는 다릅니다. 그래서 값을 코드에 박아 두지 않고 `Parameters`로 받습니다.

```yaml
Parameters:
  KeyName:
    Type: AWS::EC2::KeyPair::KeyName
  SshCidr:
    Type: String
    Description: Learner public IPv4 with /32
```

- `KeyName`: EC2 생성 시 사용할 **AWS에 등록된 키페어 이름**입니다. 개인 키 `.pem`의 본문을 전달하는 곳이 아닙니다.
- `SshCidr`: SSH를 허용할 출발지 범위입니다. 예를 들어 **내 IP가** `198.51.100.8`이라면 `198.51.100.8/32`를 입력합니다. 예시는 문서용 IP이며 자신의 실제 IP로 바꿔야 합니다.
- `AllowedPattern`: 다른 형식이나 `0.0.0.0/0`을 입력해 SSH를 실수로 전체 공개하지 못하도록 제한합니다. 입력 형식을 검사하는 것이지 네트워크 방화벽 자체는 아닙니다.
- `AmazonLinuxAmi`: AWS Systems Manager의 공개 파라미터에서 **Amazon Linux 2023 AMI ID**를 찾아옵니다. AMI ID는 리전별·업데이트별로 달라지므로 고정 ID를 외울 필요가 없습니다.

**한 문장 설명 연습:** "Parameters는 사람·환경마다 달라지는 설정만 입력받아 **동일한 인프라 설계를 재사용**하도록 만든다."

## 2. 네트워크가 만들어지는 실제 의존 관계

코드에 등장하는 중요한 자원 이름을 그래프로 보면 다음과 같습니다.

```text
LabVPC ────────────────┬─ PublicSubnet ───────────┐
                       ├─ InternetGateway         │
                       │     └─ GatewayAttachment │
                       ├─ PublicRouteTable        │
                       │     ├─ PublicRoute ──────┤
                       │     └─ PublicRouteAssociation
                       └─ WebSecurityGroup ───────┤
                                                  ▼
                                            WebInstance
```

이 그림은 **개념상 의존성을 읽기 위한 도식**입니다. 실제 실행 순서는 CloudFormation이 `!Ref` 등 참조를 보고 정하며, 가능한 독립 작업은 병렬 처리합니다. 예를 들어 `PublicRoute`는 `GatewayAttachment`가 끝나야 정상 생성되므로 `DependsOn`이 있습니다.

### 2-1. `LabVPC`: 가장 바깥 주소 공간

```yaml
LabVPC:
  Type: AWS::EC2::VPC
  Properties:
    CidrBlock: 10.0.0.0/16
    EnableDnsSupport: true
    EnableDnsHostnames: true
```

"우리가 `10.0.x.x` 주소를 쓰는 독립 네트워크를 하나 만들어 달라"는 뜻입니다. `EnableDnsSupport`는 VPC 내부 DNS 조회를 지원하게 하고, `EnableDnsHostnames`는 조건이 충족되면 DNS 호스트 이름을 제공하는 설정입니다.

여기까지만 실행했다면 EC2도 없고, 외부 인터넷 길도 없습니다.

### 2-2. `PublicSubnet`: VPC 안에 서버를 둘 구역

```yaml
PublicSubnet:
  Type: AWS::EC2::Subnet
  Properties:
    VpcId: !Ref LabVPC
    CidrBlock: 10.0.1.0/24
    MapPublicIpOnLaunch: true
```

`!Ref LabVPC`는 생성 후 반환되는 **VPC ID**를 이 필드에 넣으라는 CloudFormation의 참조 표기입니다. 아직 VPC ID를 몰라도 관계를 정의할 수 있는 이유입니다. `MapPublicIpOnLaunch: true`는 서브넷에서 새 네트워크 인터페이스에 퍼블릭 IPv4를 자동 배정할 수 있게 하는 설정이지만 **이것만으로 퍼블릭 서브넷이 되지는 않습니다**.

이 프로젝트의 EC2는 `NetworkInterfaces.AssociatePublicIpAddress: true`로 실제 퍼블릭 IP 할당도 명시합니다.

### 2-3. `InternetGateway`, `GatewayAttachment`: 밖으로 연결할 출입구

`InternetGateway`를 생성한 뒤 `GatewayAttachment`에서 `VpcId`와 `InternetGatewayId`를 연결합니다.

**의미:** IGW라는 부품이 존재하는 것과, 이 IGW가 **우리 VPC에 연결된 것**은 다릅니다. 그래서 두 자원이 별도로 존재합니다.

### 2-4. `PublicRouteTable` + `PublicRoute`: 바깥으로 보내는 규칙

```yaml
PublicRoute:
  Type: AWS::EC2::Route
  DependsOn: GatewayAttachment
  Properties:
    RouteTableId: !Ref PublicRouteTable
    DestinationCidrBlock: 0.0.0.0/0
    GatewayId: !Ref InternetGateway
```

라우트 테이블에 "**다른 구체적 경로와 일치하지 않는 IPv4는 인터넷 게이트웨이를 통과**"라는 규칙을 추가합니다. `DependsOn`은 먼저 IGW를 VPC에 연결하도록 지정합니다. VPC 내부의 `local` 경로는 AWS가 기본 생성합니다.

### 2-5. `PublicRouteAssociation`: 만든 규칙을 어디에 적용하나?

```yaml
PublicRouteAssociation:
  Type: AWS::EC2::SubnetRouteTableAssociation
  Properties:
    RouteTableId: !Ref PublicRouteTable
    SubnetId: !Ref PublicSubnet
```

라우트 테이블만 생성하고 **서브넷에 연결하지 않으면**, 그 서브넷은 기본 Main Route Table을 사용할 수 있습니다. 이 차이 때문에 "라우트는 있는데 접속이 안 돼요"라는 장애가 생길 수 있습니다.

> **여기까지의 핵심:** 퍼블릭 IP, IGW, 기본 경로, 서브넷-라우트 테이블 연결은 **서로 대신할 수 없는 별도 설정**입니다.

## 3. `WebSecurityGroup`: 네트워크 길은 열었지만 포트는 제한한다

```yaml
SecurityGroupIngress:
  - {IpProtocol: tcp, FromPort: 80, ToPort: 80, CidrIp: 0.0.0.0/0}
  - IpProtocol: tcp
    FromPort: 22
    ToPort: 22
    CidrIp: !Ref SshCidr
```

네트워크에서 도달할 수 있다는 사실만으로 서버가 새 연결을 허용하는 것은 아닙니다. SG는 **포트별 허용 규칙**을 둡니다.

- HTTP 80: 외부 방문자는 누구나 웹페이지를 확인해야 하므로 `0.0.0.0/0`.
- SSH 22: 개발자 한 사람만 OS에 로그인하므로 `내 퍼블릭 IP/32`.
- 이 SG에 인바운드 전체 포트 허용 규칙은 없습니다.
- 명시적 아웃바운드 규칙이 없으므로 생성 시 적용되는 기본 아웃바운드 허용 설정을 사용합니다. 실제 생성 후 AWS 콘솔에서 확인해야 합니다.

**강력한 반례:** `!Ref SshCidr` 대신 `0.0.0.0/0`을 넣으면 SSH가 전 세계 IP에서 접근 가능한 상태가 됩니다. 구현을 빠르게 하려고 범위를 넓히는 것은 **미션 요구와 최소권한 원칙 모두를 위반**합니다.

## 4. `WebInstance`: 하드웨어 역할, OS 준비, 앱 설치를 한곳에서 읽는다

```yaml
ImageId: !Ref AmazonLinuxAmi
InstanceType: t3.micro
CreditSpecification: {CPUCredits: standard}
KeyName: !Ref KeyName
MetadataOptions: {HttpTokens: required}
```

- `ImageId`: OS 이미지(AMI)를 선택.
- `InstanceType`: CPU/메모리 사양을 선택. `t3.micro`가 반드시 무료인 것은 아닙니다.
- `CPUCredits: standard`: T3 버스트 크레딧의 무제한 모드로 인한 초과 요금을 피하려는 선택(성능 특성은 다름).
- `KeyName`: 나중에 SSH로 접속할 키.
- `HttpTokens: required`: 인스턴스 메타데이터 접근에 IMDSv2 사용을 요구.

### 네트워크 인터페이스(ENI)

```yaml
NetworkInterfaces:
  - DeviceIndex: '0'
    AssociatePublicIpAddress: true
    DeleteOnTermination: true
    SubnetId: !Ref PublicSubnet
    GroupSet: [!Ref WebSecurityGroup]
```

이 설정으로 EC2가 **어떤 서브넷에 속하는지**, **어떤 SG를 쓰는지**, **외부에서 부를 퍼블릭 IPv4가 있는지**를 한 번에 확인할 수 있습니다. ENI(Elastic Network Interface)는 EC2의 가상 네트워크 카드입니다.

### EBS 디스크

```yaml
BlockDeviceMappings:
  - DeviceName: /dev/xvda
    Ebs:
      VolumeSize: 8
      VolumeType: gp3
      Encrypted: true
      DeleteOnTermination: true
```

Linux 운영체제와 Nginx 파일을 올릴 **8GiB 저장장치**입니다. `Encrypted: true`는 저장 데이터를 암호화하고, `DeleteOnTermination: true`는 인스턴스 **종료(terminate)** 시 연결된 루트 볼륨을 삭제하도록 하는 설정입니다. 단순 **중지(stop)**와 종료는 다릅니다.

## 5. EC2가 실제로 켜진 다음: `UserData`의 순서를 따라가자

AWS가 EC2를 만들었다고 Nginx가 자동으로 존재하지는 않습니다. OS 안의 **cloud-init**이 첫 부팅 작업으로 `UserData`에 들어 있는 Bash를 실행합니다.

```bash
#!/bin/bash
set -euo pipefail
dnf install -y nginx
printf '%s\n' '<!doctype html>...Hello Cloud - B3-1...</html>' > /usr/share/nginx/html/index.html
printf 'OK\n' > /usr/share/nginx/html/health
systemctl enable --now nginx
```

구문마다 이유가 있습니다.

1. `#!/bin/bash`: Bash로 해석할 스크립트임을 선언.
2. `set -euo pipefail`: 명령 실패/정의하지 않은 변수/파이프라인 오류를 조기에 확인하기 위한 설정.
3. `dnf install -y nginx`: Nginx 설치. **아웃바운드 인터넷이 먼저 필요**하므로 IGW와 라우트가 없으면 여기부터 실패할 수 있습니다.
4. `printf ... > ...`: Nginx가 응답할 정적 파일을 생성. `>`는 파일로 출력 결과를 보냅니다.
5. `systemctl enable --now nginx`: Nginx를 지금 시작하고 다음 부팅에도 자동 시작 설정.

따라서 **네트워크 경로가 어긋나면 애플리케이션 설치까지 실패할 수 있습니다.** "외부로 나가는 인터넷"과 "외부에서 들어오는 HTTP"가 서로 다른 검사인 이유입니다.

`/health`는 이 예제에서 **프로그램 코드가 아니라 파일 하나**입니다. `GET /health`는 Nginx가 `health` 파일을 반환하므로 HTTP 200과 문자열 `OK`가 기대됩니다.

**왜 `CREATE_COMPLETE`만으로 부족한가?** 이 템플릿은 `cfn-signal`이나 `CreationPolicy`를 사용하지 않습니다. AWS 인프라 생성 완료와 Linux 내부 Nginx 설치 성공을 동기화하지 않으므로 `curl`로 확인해야 합니다.

## 6. 완성된 뒤 인터넷에서 요청 하나가 지나가는 경로

```text
[내 PC] curl http://PUBLIC_IP/health
   → 인터넷에서 PUBLIC_IP:80으로 연결 시도
   → IGW에서 인스턴스의 퍼블릭↔프라이빗 IPv4 주소 변환
   → EC2 네트워크 인터페이스의 SG: TCP 80 허용?
   → Linux에서 TCP 80을 듣는 Nginx가 GET /health 처리
   → /usr/share/nginx/html/health 파일의 OK 응답
   → 상태 추적된 연결을 통해 PC로 HTTP 200 + OK 반환
```

여기서 **SG는 포트를 허용할 뿐 파일을 찾아 응답하지 않습니다**. **Nginx는 응답할 뿐 EC2 퍼블릭 IP나 VPC 라우트를 생성하지 않습니다**. 각 부품이 정확히 한 층씩 책임지는 구조입니다.

## 7. `scripts/verify.sh`를 코드로 읽는 순서

이 스크립트는 **EC2 내부가 아닌 내 PC에서** 실행합니다. 계층별로 실패 지점을 좁히도록 구성되어 있습니다.

```bash
set -euo pipefail
PUBLIC_IP=$(output PublicIp)
INSTANCE_ID=$(output InstanceId)
```

- `set -euo pipefail`: 실패를 무시하고 다음 검사를 통과 처리하지 않도록 합니다.
- `output()`: CloudFormation Outputs에 기록된 실제 인스턴스 ID/퍼블릭 IP를 가져옵니다. 생성 시마다 ID가 달라서 코딩하지 않습니다.
- `aws ec2 describe-instances`: **가상 컴퓨터**가 `running`인지 확인.
- `ssh -i ... ec2-user@PUBLIC_IP`: 내 컴퓨터에서 인스턴스 안으로 원격 로그인.
- `cloud-init status --wait`: 처음 부팅 작업 완료를 대기.
- `systemctl is-active --quiet nginx`: Nginx 프로세스 상태 확인.
- `curl http://localhost`: 서버 내부 HTTP 동작 확인.
- `curl https://example.com`: EC2의 인터넷 아웃바운드 확인.
- `curl http://PUBLIC_IP/health`: **서버 밖**에서 HTTP 200과 `OK` 확인.

`$( ... )`는 **명령 실행 결과를 변수에 담는 Bash 문법**이고 `[[ ... ]]`는 조건 검사입니다. 실패하면 스크립트가 중단되어 **어느 단계까지 성공했는지**가 단서가 됩니다.

주의: 이 자동 검사에는 SSH와 AWS CLI 준비가 필요합니다. 콘솔에서 수동으로 EC2를 만든 **경로 A**에서는 CloudFormation Outputs가 없으므로 이 스크립트를 그대로 실행하지 않습니다. [수동 점검 명령](deployment.md)을 사용하세요.

## 8. 종료도 실행 흐름이다

인프라는 `create-stack`만큼 `delete-stack`도 중요합니다. 템플릿에서 만든 EC2/서브넷/VPC 등은 스택 삭제로 정리를 시도하고, 생성 상태를 확인해야 합니다.

하지만 **스택 밖에서 별도로 만든 IAM 사용자 및 SSH 키페어는 자동 삭제되지 않습니다.** 사용하지 않는 퍼블릭 IP·EBS 잔여 여부도 콘솔에서 재확인해야 합니다. **수동 생성과 CloudFormation 생성은 삭제 경로가 다릅니다.** [정리 체크리스트](cleanup-checklist.md)를 따르세요.

## 9. 설계 의사결정과 대안

| 선택 | 왜 택했나 | 다른 방법과의 비교 |
|---|---|---|
| AWS 콘솔 수동 경로 지원 | 개념과 실제 화면을 연결하며 한 번씩 직접 만져보기 위해 | CloudFormation은 반복 배포가 편하지만 내부 설정을 체감하기 어렵기 쉬움 |
| CloudFormation 템플릿 유지 | 같은 구성을 재현·검토하고 생성 누락을 줄임 | 콘솔만 사용하면 수동 누락 가능 |
| Nginx 정적 파일 | HTTP 200과 `/health` 필수 요건을 최소 코드로 충족 | Python 웹 프레임워크는 이번 요구에 과함 |
| EC2에 직접 퍼블릭 IP | 외부 접속을 간단하게 확인 | NAT, 로드 밸런서, 도메인은 이번 필수 범위에 없음 |
| SSH 22 소스 제한 | 웹 사용자와 서버 관리자 권한 분리 | 전 세계 SSH 오픈은 금지 |
| 같은 파일의 상태를 세 곳에서 검증 | OS/아웃바운드/인바운드 실패 원인 구분 | "브라우저 안 열림"만으로는 원인 특정 불가 |

**마지막 연습:** `template.yaml`에서 `WebInstance` 하나를 찾고, **VPC부터 그 인스턴스가 인터넷에 연결되고 Nginx를 실행할 때까지** 각 설정을 실제 자원 이름으로 짚어서 설명해 보세요. 이해했는지 검증하는 가장 좋은 방법입니다.

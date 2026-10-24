# 학습 개념 — 정의 → 원리 → 코드 연결

## 1. CIDR와 IPv4

**정의:** IPv4는 32비트 주소이고 CIDR `주소/n`은 처음 n비트가 같은 주소 범위입니다. **원리:** `10.0.0.0/16`은 `10.0.0.0~10.0.255.255`, `10.0.1.0/24`는 더 좁은 주소 영역입니다. `/32`는 IP 한 개, `0.0.0.0/0`는 IPv4 전체를 나타냅니다. **코드:** `LabVPC.CidrBlock`, `PublicSubnet.CidrBlock`, `Parameters.SshCidr`.

## 2. VPC와 Subnet

**VPC:** AWS에서 격리된 가상 네트워크와 주소 범위. **Subnet:** 그 VPC를 나눈 네트워크 구역이며 한 가용 영역에 속합니다. **원리:** VPC만 생성하면 인터넷에 자동 연결되지 않습니다. 외부로 나갈 수 있는 서브넷은 인터넷 게이트웨이 경로를 가진 Route Table과 연결되어야 합니다. **코드:** `LabVPC`, `PublicSubnet`.

## 3. 라우팅과 IGW

**Route Table:** 목적지 IP에 따라 다음 경로를 정하는 규칙 집합입니다. **원리:** `10.0.0.0/16 → local`은 VPC 내부 경로이고, `0.0.0.0/0 → IGW`는 외부 IPv4 기본 경로입니다. 가장 긴(구체적인) 목적지 접두사의 경로가 우선됩니다. **IGW(Internet Gateway)**는 VPC 인터넷 연결 요소로 VPC에 붙어야 합니다. **코드:** `GatewayAttachment`, `PublicRoute`, `PublicRouteAssociation`. 서브넷 연결이 빠지면 의도한 경로가 적용되지 않습니다.

## 4. EC2 · AMI · EBS

**EC2:** 가상 서버. **AMI:** 운영체제가 설치된 시작 이미지. **EBS:** 서버의 블록 저장장치(가상 디스크). **원리:** EC2를 중지해도 EBS가 남아 과금될 수 있으며, 인스턴스 종료 시 `DeleteOnTermination`이 켜진 볼륨은 제거 대상입니다. 공인 IPv4가 있으면 인터넷 목적지 주소로 사용할 수 있지만, 통신을 위해 경로/SG/실제 서버가 필요합니다. **코드:** `WebInstance`, `AmazonLinuxAmi`, `BlockDeviceMappings`, `NetworkInterfaces`.

## 5. SG와 IAM은 완전히 다르다

**Security Group:** 인스턴스 네트워크 트래픽에 대한 포트/프로토콜/출발지 규칙. **원리:** stateful이므로 허용 요청에 대한 응답을 추적합니다. HTTP 80은 모두에게, 원격 셸 접근용 SSH 22는 한 IP(/32)에만 허용합니다. **코드:** `WebSecurityGroup.SecurityGroupIngress`.

**IAM:** 사용자/Role의 AWS API 실행 가능 작업(Action), 대상 리소스(Resource), 조건(Condition)을 정하는 정책. **원리:** EC2를 생성할 권한과 EC2 서버로 들어오는 패킷 허용은 별개입니다. **코드:** `iam/least-privilege-policy.json`. 실습 작업과 리전을 제한하고 관리자·S3·RDS 권한을 부여하지 않지만, 일부 EC2 작업은 AWS API 특성상 `Resource: "*"`라 운영 계정의 모든 자원 격리 수준은 아닙니다.

## 6. Nginx와 HTTP

**HTTP:** 클라이언트 요청에 서버가 상태 코드·본문을 반환하는 프로토콜. **Nginx:** 정적 파일을 응답하는 웹 서버. **코드:** `WebInstance.UserData`가 `index.html`, `health` 파일을 작성하고 Nginx를 실행합니다. `GET /health`의 기대 결과는 HTTP 200과 `OK`. `localhost` 검사만으로 외부 접속 성공을 증명할 수 없으므로 로컬·아웃바운드·외부 인바운드를 따로 검증합니다.

## 7. CloudFormation, UserData, 오류 원인

**CloudFormation:** 템플릿으로 AWS 인프라를 선언하고 스택 단위로 관리하는 IaC. **원리:** `!Ref`로 리소스/파라미터 값을, `!GetAtt`로 리소스 속성을 읽고 `DependsOn`으로 생성 선행 조건을 지정합니다. **UserData:** EC2 최초 부팅 시 cloud-init이 실행하는 초기화 스크립트. **코드:** `WebInstance.UserData`.

**트러블슈팅:** 타임아웃은 SG/라우팅/IP를, Connection refused는 서버 포트/Nginx 실행 상태를, HTTP 404는 파일 경로를 우선 점검하되 로그 없이 원인을 단정하지 않습니다. 조회·가설·검증·수정·재검증 과정을 기록합니다.

## 8. 비용 정리

**원리:** 프리 티어 혜택, EC2 사용 시간, 공인 IPv4·EBS·데이터 전송 비용은 별도입니다. **코드:** Elastic IP, NAT, ALB, RDS 없이 최소 구성. 실습 후 `delete-stack`하고 인스턴스/디스크/네트워크/키페어/IAM과 Billing을 점검합니다. Billing 정보는 지연될 수 있습니다.

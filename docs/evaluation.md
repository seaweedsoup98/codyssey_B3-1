# B3-1 이해도 점검 — 질문을 받았을 때 흐름으로 설명하기

> 이 문서는 정답 문장을 암기하기보다, **원인 → 설계 판단 → 실제 설정 → 어떻게 확인했는가**를 자신의 말로 설명하도록 돕습니다. AWS에서 실행하지 않은 결과는 **예상 동작**이라고 분명히 말하세요. 개념이 막히면 [개념 교재](concepts.md), 구현을 증명할 근거가 필요하면 [템플릿 해설](how-it-works.md)을 보세요.

## 1. 우선 90초로 프로젝트 전체를 설명해 보기

> "목표는 제 PC 밖에서도 접속 가능한 웹 서버를 AWS 서울 리전에 만드는 것입니다. EC2는 서버 컴퓨터이고 Nginx가 실제 HTTP 요청을 처리합니다. 이 EC2를 자체 VPC의 Public Subnet에 넣고, IGW를 VPC에 연결한 다음 해당 서브넷의 Route Table에 `0.0.0.0/0 → IGW` 경로를 둡니다. 인스턴스에 퍼블릭 IPv4를 부여하며, Security Group은 HTTP 80을 전체 허용하고 SSH 22는 제 IP 한 개로 제한합니다. IAM은 AWS 인프라 생성 권한을 따로 제한합니다. 내부 localhost, 외부로 나가는 통신, 외부에서 들어오는 HTTP를 구분해 검증하고 스크린샷을 남긴 뒤 실습 자원을 삭제합니다."

**이 말이 단순 암기인지 판별하는 방법:** 이 문장에서 **라우트 연결 하나를 지우면** 왜 서비스가 실패하는지 설명할 수 있나요? 각각의 설정이 막는 실패를 설명하면 이해한 것입니다.

## 2. 처음 배우는 사람에게 설명하는 질문

### Q1. "EC2가 서버라면 VPC는 왜 필요해요?"

**핵심 이유:** EC2는 컴퓨터지만 그 컴퓨터가 어떤 IP 범위를 사용하고 어떤 네트워크로 통신할지는 별도로 정해야 합니다. VPC는 이 경계를 정의합니다. 우리 `LabVPC`는 `10.0.0.0/16`, `PublicSubnet`은 그 안의 `10.0.1.0/24`를 사용합니다.

**코드 위치:** `template.yaml → LabVPC / PublicSubnet`.

**되물어보면 좋은 질문:** VPC를 만들면 자동으로 인터넷이 되나요? → 아니요. IGW 연결과 라우팅이 필요합니다.

### Q2. "Public Subnet이랑 Public IP는 같은 뜻인가요?"

**전혀 다릅니다.** Public Subnet은 **서브넷에 적용된 경로가 IGW를 향하는 상태**, Public IP는 **EC2를 인터넷 IPv4에서 부를 수 있는 주소**입니다. 하나만 있다고 다른 것이 생기는 것은 아닙니다.

**코드 위치:** `PublicRoute + PublicRouteAssociation`과 `WebInstance.NetworkInterfaces.AssociatePublicIpAddress`.

**예시:** IGW 경로는 있는데 퍼블릭 IPv4가 없으면 인터넷 밖에서 그 EC2로 직접 IPv4 연결하기 어렵습니다.

### Q3. "왜 Route Table에서 0.0.0.0/0은 보안상 위험한 SSH 전체 허용이 아니죠?"

`0.0.0.0/0` 자체는 IPv4 전체 **범위**입니다. 하지만 **Route Table**에서는 기본적으로 목적지가 그 범위인 패킷을 *어디로 보낼지* 결정합니다. **SG 인바운드**에서는 *어디서 오는 어떤 포트 연결을 허용할지* 결정합니다. 같은 CIDR라도 **어느 정책의 필드에 들어갔는지**가 다릅니다.

**코드 위치:** `PublicRoute.DestinationCidrBlock` vs `WebSecurityGroup.SecurityGroupIngress`.

### Q4. "Internet Gateway가 있어도 왜 외부 접속이 안 될 수 있나요?"

IGW는 VPC와 인터넷의 연결 요소일 뿐, 해당 서브넷의 Route Table에 IGW 경로가 없거나 라우트 테이블이 서브넷과 연결되지 않았다면 인터넷 트래픽이 올바르게 흐르지 못합니다. 퍼블릭 IP, SG 80, OS/Nginx도 필요합니다.

**코드 위치:** `GatewayAttachment`, `PublicRoute`, `PublicRouteAssociation`, `WebInstance`.

## 3. 보안·권한을 이해하는 질문

### Q5. "왜 HTTP 80은 모두에게 열고 SSH 22는 내 IP 하나만 열죠?"

HTTP는 일반 사용자가 웹페이지를 읽는 통로, SSH는 관리자가 서버 OS 명령을 실행하는 통로입니다. 목적과 위험도가 달라서 권한 범위도 다릅니다. 이번 미션은 HTTP 공개가 목적이므로 80은 `0.0.0.0/0`, SSH는 `내IP/32`입니다.

**코드 위치:** `WebSecurityGroup`, 입력 `SshCidr`.

**추가 질문:** 내 IP가 바뀌어 SSH가 안 되면 어떻게 할까? → 보안 그룹 22의 소스를 **새 개인 IP/32로 수정**합니다. 전 세계에 열어서 해결하지 않습니다.

### Q6. "IAM과 Security Group의 결정적 차이를 한 문장으로 설명해 보세요."

IAM은 **AWS API로 EC2·VPC 등의 리소스를 만들거나 수정할 수 있는 권한**을 판단하고, SG는 **EC2로 향하는 네트워크 연결을 포트·프로토콜·출발지 기준으로 허용하는지** 판단합니다.

**코드 위치:** `iam/least-privilege-policy.json` vs `template.yaml → WebSecurityGroup`.

**함정 질문:** "웹페이지가 안 열린다. IAM에 AdministratorAccess를 붙일까?" → HTTP 경로 장애에 대한 부적절하고 위험한 조치입니다.

### Q7. "IAM 최소권한은 정확히 어떻게 보였나요?"

관리자 정책을 사용하지 않고 EC2/VPC/특정 CloudFormation 스택 조작에 필요한 Action을 중심으로 허용하고 서울 리전 조건을 뒀습니다. S3/RDS 같은 무관한 서비스의 Allow는 없습니다. **다만 일부 `ec2:*` 관련 작업에 `Resource: "*"`가 있으므로 완전한 자원 수준 격리 정책이라고 과장해서는 안 됩니다.** 실제 IAM 적용·접근거부 결과는 배포 후 검증해야 합니다.

**코드 위치:** `iam/least-privilege-policy.json`의 `Effect`, `Action`, `Resource`, `Condition`.

## 4. 서버 배포·동작을 이해하는 질문

### Q8. "EC2를 만들었는데 왜 UserData도 작성했나요?"

EC2는 가상 컴퓨터이고, HTTP 요청을 받아줄 웹 서버 프로그램은 별도로 설치해야 합니다. UserData는 처음 부팅할 때 cloud-init이 Nginx 설치, 정적 파일 작성, 서비스 실행을 자동 수행합니다.

**코드 위치:** `WebInstance.UserData`의 `dnf install`, `printf`, `systemctl`.

**꼬리 질문:** EC2 `running` = Nginx 성공? → 아닙니다.

### Q9. "왜 /health를 만들었나요? API 서버가 필요한가요?"

이번에는 **정적 파일** `/usr/share/nginx/html/health`에 `OK`를 기록했습니다. Nginx가 `GET /health`에 HTTP 200과 `OK`로 응답하는지 확인해 웹 서버의 기본 동작을 판단합니다. 복잡한 API나 DB가 없어도 됩니다.

**코드 위치:** UserData의 `printf 'OK\n' > /usr/share/nginx/html/health`.

**한계:** 200/OK는 이 정적 페이지가 응답함을 증명할 뿐 전체 시스템의 모든 기능이 정상이라는 보증은 아닙니다.

### Q10. "CloudFormation의 !Ref, !GetAtt, DependsOn은 왜 있죠?"

AWS 리소스 ID는 생성 전에는 모르기 때문입니다. `!Ref`는 생성된 VPC 등 리소스를 값으로 연결하고, `!GetAtt`는 EC2 퍼블릭 IP처럼 속성을 읽습니다. `DependsOn`은 IGW 연결처럼 선행 완료가 필요한 작업 순서를 명시합니다. 이를 통해 사람이 ID를 복사해 넣는 실수를 줄입니다.

**코드 위치:** `PublicSubnet.VpcId`, `PublicRoute.DependsOn`, `Outputs.PublicIp`.

### Q11. "AWS 콘솔에서 만든 자원과 CloudFormation으로 만든 자원은 똑같이 삭제하나요?"

결과가 비슷해 보이더라도 **관리 주체가 다릅니다**. 수동 생성한 자원은 콘솔에서 의존 관계를 풀고 직접 삭제해야 하며, CloudFormation으로 만든 자원은 해당 스택을 삭제하고 실제 제거 여부를 확인합니다. 두 방법을 섞어 중복 생성하지 않습니다.

**코드/문서 위치:** `docs/deployment.md` 경로 A/B, `docs/cleanup-checklist.md`.

## 5. 문제를 주고 원인을 추론하게 하는 질문

### Q12. "EC2에서 localhost 200인데 외부 접속이 타임아웃입니다. 어디부터 보나요?"

내부 Nginx가 응답한다는 단서는 확보됐습니다. 따라서 외부 퍼블릭 IP가 맞는지, SG TCP 80이 허용됐는지, IGW가 VPC에 붙었는지, 라우트가 서브넷에 적용되는지 확인합니다. **가설마다 검증할 설정**을 하나씩 지정합니다.

**코드/검증:** `PublicRouteAssociation`, `WebSecurityGroup`, 외부 `curl -i http://PUBLIC_IP/health`.

### Q13. "외부에서 HTTP 404를 받으면 라우팅 문제인가요?"

보통은 아닙니다. HTTP 404를 받았다는 것은 이미 HTTP 요청에 대해 **웹 서버의 응답을 받았다는 뜻**이므로, URL 경로나 Nginx 문서 루트를 먼저 확인합니다. 예를 들어 `/no-such-page`는 존재하지 않고 `/health`는 파일이 있습니다. access.log를 보고 확인합니다.

**위치:** `docs/troubleshooting.md`, `WebInstance.UserData`.

### Q14. "왜 내부/아웃바운드/외부 인바운드를 따로 테스트하나요?"

`localhost`는 **Nginx 내부 동작**, `curl https://example.com`은 **EC2에서 바깥으로 나가는 통신**, `curl http://PUBLIC_IP/health`는 **바깥에서 들어오는 통신**을 확인합니다. 서로 다른 장애 지점을 구분하기 때문에 세 검사를 나눕니다.

**코드 위치:** `scripts/verify.sh` (CloudFormation 경로), 실습서 6~7단계(콘솔 경로).

### Q15. "프리 티어라는데 왜 리소스 삭제까지 해야 하나요?"

혜택은 계정의 생성 시기·플랜·사용량에 따라 달라지고, 퍼블릭 IPv4, EBS, EC2 실행 등이 비용 대상일 수 있습니다. **인스턴스 중지(stop)는 볼륨 정리를 의미하지 않습니다.** 실습 증빙 확보 뒤 인스턴스를 종료(terminate)하고 관련 볼륨·네트워크 자원을 점검합니다.

**문서 위치:** `docs/cleanup-checklist.md`.

## 6. 2분 시연 시나리오(실제로 실행한 후)

1. [아키텍처](architecture.png)를 보여주며 VPC → Subnet → IGW/Route → SG → EC2/Nginx 흐름을 설명.
2. 실제 AWS 화면에서 **서브넷에 연결된 Route Table**과 **SG 80/22 규칙**을 보여주기.
3. EC2 안에서 `curl http://localhost/health`를 실행하고 목적을 설명.
4. **내 PC에서** `curl -i http://퍼블릭IP/health`의 200/OK 결과를 보여주기.
5. 실제 트러블슈팅의 가설/로그/수정 전후를 간단히 설명.
6. 실습 리소스 삭제와 정리 기록을 보여주기.

**실제로 수행하지 않았다면 "이 명령으로 검증할 예정"이라고 말해야 합니다.** 예시 결과를 자신이 실행한 기록처럼 발표하지 않습니다.

## 7. 책을 덮고 답해 볼 마지막 질문

- 웹페이지가 안 뜨면 왜 먼저 HTTP 80 포트를 **모두 열면 안 되는가**?
- AWS VPC의 IGW, Route Table, SG, Nginx는 각각 **어떤 실패를 막는가**?
- Nginx 로그에 요청 자체가 없으면 무엇을 먼저 의심하고 어떤 추가 증거를 찾을까?
- 내 IP가 바뀐 상태에서 SSH가 끊기면 **최소권한을 유지한 채** 어떻게 복구할까?
- 코드가 하는 일을 설명할 때 "AWS가 처리한다"에서 멈추지 않고 **어떤 AWS 리소스와 설정**을 지목할 수 있을까?

이 질문들에 **자기 말로**, 그리고 **실제 코드 위치를 가리키며** 대답할 수 있다면 암기보다 한 단계 깊이 이해한 것입니다.

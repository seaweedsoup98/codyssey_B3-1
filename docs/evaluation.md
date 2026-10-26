# 주요 기능·개념 설명

실제 구성과 [구현 가이드](guide.md)를 기준으로, 질문을 받았을 때 **설정의 목적 → 동작 원리 → 확인 방법** 순서로 설명할 수 있도록 정리했다.

| 질문 | 답변의 핵심 | 관련 위치 |
|---|---|---|
| **1. VPC와 Subnet은 왜 나누는가?** | VPC는 독립된 IP 주소 공간이고, Subnet은 그 일부를 서비스 목적에 맞게 구분한 구역이다. 이 실습에서는 `10.0.0.0/16` 안에 `10.0.1.0/24`를 두고 EC2를 배치했다. | `template.yaml`: `LabVPC`, `PublicSubnet` |
| **2. Public Subnet은 무엇으로 결정되는가?** | 이름이나 퍼블릭 IP 자동 할당만으로 결정되지 않는다. 서브넷에 연결된 Route Table에 `0.0.0.0/0 → IGW`가 있어야 인터넷으로 가는 IPv4 경로가 성립한다. | `PublicRoute`, `PublicRouteAssociation` |
| **3. Route Table과 IGW의 역할은?** | Route Table은 목적지 IP에 따른 다음 경로를 선택하고, IGW는 VPC와 인터넷 사이 연결 지점이다. IGW를 붙여도 경로와 서브넷 연결이 없으면 충분하지 않다. | `GatewayAttachment`, `PublicRoute` |
| **4. `0.0.0.0/0`의 의미는?** | 모든 IPv4 주소 범위다. Route Table에서는 기본 목적지 경로이며, SG에서는 지정한 포트의 출발지 허용 범위다. 같은 문자열도 설정의 역할이 다르다. | `PublicRoute`, `WebSecurityGroup` |
| **5. Security Group과 IAM은 어떻게 다른가?** | SG는 패킷의 프로토콜·포트·주소를 검사한다. IAM은 AWS API 실행 주체가 어떤 작업을 허용받는지 판단한다. IAM에 EC2 조회 권한을 줘도 SSH 22가 열리는 것은 아니다. | `WebSecurityGroup`, `iam/least-privilege-policy.json` |
| **6. HTTP 80은 전체 허용, SSH 22는 /32인 이유는?** | 웹 방문자는 누구나 HTTP 페이지를 조회해야 하지만 SSH는 OS 관리 통로다. 한 IP만 허용하여 외부 공격 면적을 줄인다. | `SecurityGroupIngress`, 실제 SG 구성 |
| **7. EC2만 켜면 웹페이지가 보이는가?** | 아니다. EC2는 가상 컴퓨터다. AMI로 OS를 시작한 뒤 Nginx를 설치·실행해야 HTTP 80에서 응답한다. EC2 상태 검사와 Nginx 상태 확인은 별개다. | `WebInstance`, `UserData` |
| **8. User Data의 역할은?** | 첫 부팅의 `cloud-init`이 실행하는 초기화 스크립트다. `dnf`로 Nginx를 설치하고 `index.html`/`health` 파일을 만들며 `systemctl enable --now nginx`로 서비스를 실행한다. | `WebInstance.UserData` |
| **9. HTTP 200을 왜 세 위치에서 검증했는가?** | `localhost`는 Nginx 자체, EC2→외부 HTTPS는 아웃바운드 라우팅, WSL→퍼블릭 IP는 외부 인바운드 전체 경로를 확인한다. 내부 성공만으로 외부 성공을 주장할 수 없다. | [내부 기록](evidence/internal-checks.txt), [외부 기록](evidence/external-health.txt) |
| **10. 실제로 발생한 IAM 오류를 어떻게 해결했는가?** | `ec2:Describe*`로는 `ec2:GetSecurityGroupsForVpc`가 허용되지 않았다. 거부된 API 이름을 확인해 권한 하나를 추가하고 기본 정책 버전을 갱신하여 다시 확인했다. | [트러블슈팅](troubleshooting.md), `ReadEc2` |
| **11. `!Ref`·`!GetAtt`·`DependsOn`은 무엇인가?** | CloudFormation에서 자원 간 값을 연결하고 생성 순서를 제어한다. 실제 실습은 수동이었으며 `template.yaml`은 동일 설계를 재현하는 코드다. | `template.yaml`: `Resources`, `Outputs` |
| **12. EC2를 중지하지 않고 종료한 이유는?** | 중지는 EBS 같은 자원을 남길 수 있다. 종료 시 루트 볼륨 삭제를 설정하고 실제 `Terminated` 및 볼륨 목록 0건을 확인했다. 다른 네트워크 자원도 별도 삭제했다. | [정리 기록](cleanup-checklist.md) |

## 전체 실행 흐름

```text
IAM 권한 → VPC/서브넷 → IGW/라우팅 → SG → EC2 부팅
 → User Data(Nginx 설치) → SSH·내부·외부 HTTP 검증
 → 실제 권한 오류 해결 기록 → 증빙 보관 → 리소스 삭제
```

외부 페이지는 삭제 전 `http://3.35.220.184/`에서 표시됐으며 [스크린샷](screenshots/external-page.png)이 남아 있다. 서버를 종료했으므로 현재 URL을 열 수 없다는 점과 **실습 당시 성공**을 구분해 설명한다.

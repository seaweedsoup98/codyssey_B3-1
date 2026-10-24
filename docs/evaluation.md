# 설명 대비 Q&A

| 질문 | 핵심 논리 | 코드 위치 |
|---|---|---|
| VPC가 무엇인가? | 논리적으로 격리된 AWS 가상 네트워크와 IP 범위 | `LabVPC` |
| Subnet이 무엇인가? | VPC의 일부 네트워크, 특정 AZ에 속함 | `PublicSubnet` |
| Public Subnet의 조건은? | IGW로의 기본 경로가 연결된 Route Table을 사용 | `PublicRouteAssociation` |
| Route Table의 `0.0.0.0/0` 의미는? | 다른 구체적 경로가 없는 모든 IPv4 목적지의 기본 경로 | `PublicRoute` |
| 인터넷 요청의 실제 경로는? | 공인 IP → IGW → 인스턴스 ENI/SG → Nginx → 응답 | `architecture.png`, `WebInstance` |
| 공인 IP는 왜 필요한가? | 외부에서 EC2로 접속할 주소 | `AssociatePublicIpAddress` |
| SG와 IAM의 차이는? | SG는 패킷/포트, IAM은 AWS API 실행 권한 | `WebSecurityGroup`, `iam/least-privilege-policy.json` |
| SSH 22를 /32로 제한한 이유는? | 원격 셸 접근 공격 표면을 줄이기 위해 | `SshCidr` |
| 최소권한의 구현 근거는? | EC2/VPC/스택 작업 제한, 서울 리전, 관리자 정책 배제 | IAM JSON |
| Nginx는 어떻게 설치되나? | EC2 첫 부팅 시 cloud-init/UserData에서 dnf 설치, systemctl 시작 | `WebInstance.UserData` |
| localhost 200이면 외부 성공인가? | 아님. Nginx 자체 검증과 외부 네트워크 통신은 분리 | `scripts/verify.sh` |
| 접속 오류를 어떻게 분석하나? | IP·경로·SG → 서비스/cloud-init 로그 → 수정 후 재검증 | `docs/troubleshooting.md` |
| `!Ref`와 `DependsOn`의 차이는? | 리소스 값 참조와 명시적 선행 생성 제약 | `template.yaml` |
| 프리 티어인데도 과금되는 이유는? | 계정 혜택·크레딧·IP/EBS/전송량 등과 사용량에 따라 다름 | `README.md` |
| 종료 시 무엇을 지우나? | 스택의 EC2/EBS/VPC/IGW 등, 별도 키페어·IAM과 Billing 확인 | `docs/cleanup-checklist.md` |

**시연 순서:** 아키텍처 → 템플릿 VPC/라우팅/EC2 → SG/IAM → 실제 내부/외부 curl → 실제 트러블슈팅 → 삭제 증거. 아직 실행하지 않았다면 예상 동작과 실제 결과를 엄격히 구분합니다.

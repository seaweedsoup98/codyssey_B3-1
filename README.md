# B3-1 — 내가 만든 웹사이트를 인터넷에 올려 누구나 쓰게 하기

AWS 서울 리전(`ap-northeast-2`)에 **VPC → Public Subnet → Internet Gateway/Route Table → Security Group → EC2/Nginx**를 연결하고 외부에서 HTTP로 접속하는 미션입니다. 보너스 과제(HTTPS/Docker)는 제외했습니다.

> **현재 상태:** 인프라 정의, 아키텍처 및 **학습·실습 가이드 작성**. **AWS 실배포, 외부 접속 스크린샷, 실제 트러블슈팅 수행, 리소스 삭제는 아직 검증하지 않았습니다.** 예시 출력을 실습 성공으로 오인하지 마세요.

## 먼저 이것부터: 서버가 켜졌는데 밖에서 접속이 안 되는 이유

웹서비스가 실제로 열리려면 **서로 다른 네 가지 문제**가 해결되어야 합니다.

1. **서버 자체:** EC2가 실행되고 Nginx가 HTTP에 응답해야 합니다.
2. **찾아갈 주소:** EC2에 퍼블릭 IPv4가 있어야 합니다.
3. **인터넷 경로:** Public Subnet에 IGW를 향하는 Route Table 경로가 적용되어야 합니다.
4. **접근 허용:** Security Group에서 웹 접속용 TCP 80을 열어야 합니다. SSH 22는 내 IP/32만 허용합니다.

IAM은 이 네트워크 흐름과는 별도로 **누가 AWS 자원을 생성/수정할 수 있는가**를 결정합니다. 이 관계를 이해하는 것이 B3-1의 핵심입니다.

![B3-1 AWS 아키텍처](docs/architecture.png)

## 공부를 어떻게 하면 좋을까?

**처음에는 내용을 통째로 암기하지 말고, 아래 순서대로 질문에 답하면서 읽으세요.**

| 읽는 순서 | 문서 | 무엇을 이해하게 되나? |
|---|---|---|
| 1 | **[개념 교재](docs/concepts.md)** | "EC2만으로 왜 안 되지?"에서 시작해 IP, VPC, 라우트, SG, IAM이 등장한 이유를 **하나의 이야기**로 학습 |
| 2 | **[AWS 콘솔 따라 하기](docs/deployment.md)** | 화면에서 직접 생성할 때 각 단계의 **이유 → 설정 → 관찰 결과** 확인 |
| 3 | **[구현 흐름 해설](docs/how-it-works.md)** | 손으로 만든 설정이 `template.yaml`의 어느 코드와 대응하는지, 실행부터 HTTP 응답까지 추적 |
| 4 | **[문제 해결 실습](docs/troubleshooting.md)** | 404, 타임아웃, SSH 실패를 구분하고 실제 로그로 가설을 검증 |
| 5 | **[설명 연습 Q&A](docs/evaluation.md)** | 다른 사람 앞에서 코드를 가리키며 **왜 그렇게 구성했는지** 자신의 말로 설명 |
| 마지막 | **[리소스 정리](docs/cleanup-checklist.md)** | 인스턴스 종료와 실제 비용 자원 삭제의 차이 이해 및 정리 기록 |

**추천 학습법:** 개념 한 장을 읽고 → 콘솔에서 해당 설정을 만든 다음 → `template.yaml`의 같은 설정을 찾아보세요. 예를 들어 Public Subnet의 라우트 연결을 화면에서 확인한 직후 `PublicRouteAssociation` 코드를 읽으면 역할이 분명해집니다.

## 실제 실습 경로: 둘 중 하나만 선택

- **경로 A — AWS 콘솔 수동 실습(첫 학습 추천):** [docs/deployment.md](docs/deployment.md)의 경로 A를 따라 VPC, 라우팅, SG, EC2를 각각 만듭니다. **CloudFormation 스택이 없으므로 수동으로 삭제**해야 합니다.
- **경로 B — CloudFormation 배포:** 기존 [template.yaml](template.yaml)과 [검증 스크립트](scripts/verify.sh)로 일괄 생성합니다. 연결을 이해한 뒤 재현할 때 유용합니다. `verify.sh`는 스택 `b3-1`의 Outputs를 읽으므로 **경로 A에서는 사용할 수 없습니다.**

**두 경로를 동시에 실행하면 EC2와 VPC가 중복 생성될 수 있으니 피하세요.** 계정의 프리 티어/크레딧 조건과 퍼블릭 IPv4 비용을 시작 전에 확인해야 합니다.

## 실제 구현 요소와 파일

| 파일 | 역할 |
|---|---|
| [template.yaml](template.yaml) | AWS VPC `10.0.0.0/16`, Subnet `10.0.1.0/24`, IGW/기본 경로, SG, `t3.micro`+Nginx, gp3 8GiB 정의 |
| [iam/least-privilege-policy.json](iam/least-privilege-policy.json) | 실습 IAM 사용자용 제한 정책 **초안** (AWS 실권한 검증 필요) |
| [scripts/verify.sh](scripts/verify.sh) | CloudFormation 경로 전용: 인스턴스/SSH/Nginx/localhost/아웃바운드/외부 접속 검사 |
| [docs/architecture.png](docs/architecture.png) | 미션 제출용 아키텍처 그림 ([편집 가능한 SVG](docs/architecture.svg)) |
| [tests/test_template.py](tests/test_template.py) | 템플릿 구조 정적 검사. AWS 실배포 검증과는 다름 |

정적 검사(로컬에 Python, PyYAML이 있는 경우):

```bash
python -m pip install PyYAML
python -m unittest discover -s tests -v
```

## 미션 제출 4종과 남은 실제 증빙

| 필수 결과물 | 파일 | 상태 |
|---|---|---|
| 아키텍처 그림 | `docs/architecture.png` | 작성됨 |
| **외부 접속 증명 (B: GET /health)** | 이 README의 실제 URL + `docs/screenshots/external-health.png` | **AWS 배포 후 실제 촬영 필요** |
| 트러블슈팅 보고서 | `docs/troubleshooting.md` | 가이드 작성, **실제 문제 재현 기록 필요** |
| 리소스 정리 체크리스트 | `docs/cleanup-checklist.md` | 작성됨, **실제 삭제 검증 필요** |

### 외부 접속 확인 기록 — 실제 실습 후 직접 채우기

| 항목 | 실습 결과 |
|---|---|
| 방식 | **B — `GET http://<PUBLIC_IP>/health`** |
| 실제 퍼블릭 IP / URL | **미배포 / 미기록** |
| HTTP 상태와 본문 | **미검증** (기대: `200`, `OK`) |
| 테스트 일시 | 미실행 |
| 스크린샷 | 미첨부 — `docs/screenshots/external-health.png` |

**증빙 방법:** EC2 밖의 **내 PC**에서 `curl -i http://실제퍼블릭IP/health`를 실행합니다. **명령·퍼블릭 IP·HTTP 200·OK**가 함께 보이도록 실제 화면을 캡처하고 위 표를 갱신합니다. **실제 실행 전에 이 표를 완료로 바꾸지 않습니다.** 실습 후에는 모든 자원을 종료/삭제합니다.

## 안전과 비용

루트 계정과 `AdministratorAccess`를 실습에 사용하지 않습니다. SSH 22는 현재 본인의 퍼블릭 IP 한 개만 허용하고, 비밀번호·AWS 액세스 키·SSH 개인 키는 절대 저장소에 올리지 않습니다.

AWS의 Free Tier 혜택은 계정 생성 시기와 계정 플랜에 따라 다릅니다. EC2뿐 아니라 EBS, 퍼블릭 IPv4, 네트워크 전송도 살펴봐야 합니다. 자세한 확인 절차는 실습서에 있습니다.

공식 근거: [AWS VPC 인터넷 연결](https://docs.aws.amazon.com/ko_kr/vpc/latest/userguide/VPC_Internet_Gateway.html), [AWS EC2 Free Tier 조건](https://docs.aws.amazon.com/ko_kr/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html).

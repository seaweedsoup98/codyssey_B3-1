# 트러블슈팅

> **현재 AWS에서 오류 재현/원인 분석/해결을 실행하지 않았습니다.** 실제 미션 제출 시 실제 오류 **1건 이상**의 로그와 재현·조치·결과를 기입해야 합니다.

## 안전한 오류 재현: SSH CIDR 제약

`template.yaml`의 `Parameters.SshCidr.AllowedPattern`은 IP 하나만 허용하는 `/32`를 요구합니다. `0.0.0.0/0`를 입력하는 **실패하는** 명령을 시도하면 보안 그룹이 인터넷 전체에 SSH를 열기 전에 입력이 거부되는지 확인할 수 있습니다. 기존 `b3-1` 스택이 **없는 상태**에서만 재현하고, 실제 오류 응답을 적습니다.

```bash
aws cloudformation create-stack --region ap-northeast-2 --stack-name b3-1 \
  --template-body file://template.yaml \
  --parameters ParameterKey=KeyName,ParameterValue=b3-1 \
               ParameterKey=SshCidr,ParameterValue=0.0.0.0/0

# 수정: 현재 실습 PC의 공인 IP 하나만 허용
MY_IP=$(curl -fsS https://checkip.amazonaws.com | tr -d '\r\n')
# 이후 docs/deployment.md의 정상 create-stack 명령 실행
```

| 항목 | 실제 검증 결과 |
|---|---|
| 증상 | **미재현** — 실제 명령/시각/stderr 기록 필요 |
| 가설 | `/0`은 `SshCidr`의 `/32` 제약에 위배 |
| 검증 | **미실행** — 오류 응답과 AllowedPattern 비교, 실패 스택 상태 확인 |
| 조치 | **미실행** — 실습 PC의 `<IP>/32`로 변경 |
| 결과 | **미검증** — SG의 TCP 22 허용 IP와 SSH 성공 확인 |
| 재발방지 | 파라미터 제약 유지, 생성 전 CIDR 확인 |

실제 AWS 오류가 다르게 나타나면 그 문제에 맞춰 **증상 → 가설 → 로그·검증 → 조치 → 결과 → 재발방지**를 기록합니다. 가설을 실제 관측값으로 오인하지 않습니다.

### 증상별 출발점

| 증상 | 확인할 것 |
|---|---|
| 외부 접속 타임아웃 | 공인 IP, IGW 경로, SG TCP 80 |
| SSH 타임아웃 | 현재 사용자 IP, SG TCP 22, 인스턴스 상태, 키 |
| localhost 200이 아닌 경우 | `systemctl status nginx`, `/var/log/cloud-init-output.log` |
| HTTP 404 | Nginx 문서 루트와 `/health` 파일 |
| AccessDenied | `aws sts get-caller-identity`, 실패한 IAM Action/Resource |

원인을 추측으로 결정하지 말고 실제 명령 출력과 로그를 증거로 남겨야 합니다.

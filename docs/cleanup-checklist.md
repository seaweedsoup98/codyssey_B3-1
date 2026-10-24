# AWS 리소스 정리 체크리스트

> **현재 삭제 미실행/미확인.** AWS에서 점검해 확인한 후에만 체크박스를 완료 처리합니다. **다른 프로젝트의 리소스는 삭제하지 마세요.**

| 항목 | 완료 | 실제 확인 시간·리소스 ID·근거 |
|---|---|---|
| 외부 접속 스크린샷 확보 | [ ] | 미확인 |
| CloudFormation `b3-1` 스택 삭제 | [ ] | 미확인 |
| EC2 terminated | [ ] | 미확인 |
| EBS 루트 볼륨 및 미사용 볼륨 삭제 | [ ] | 미확인 |
| Elastic IP 잔여 없음 (템플릿 미사용) | [ ] | 미확인 |
| IGW detach·삭제 | [ ] | 미확인 |
| VPC·Subnet·Route Table·SG 삭제 | [ ] | 미확인 |
| NAT/ALB/RDS 별도 생성 없음 | [ ] | 미확인 |
| 실습 전용 키페어 `b3-1` 및 로컬 키 정리 | [ ] | 미확인 |
| 실습 IAM 사용자/정책 필요 없는 경우 제거 | [ ] | 미확인 |
| AWS Billing Dashboard 확인 | [ ] | 미확인 |

## 삭제 명령

```bash
aws cloudformation delete-stack --region ap-northeast-2 --stack-name b3-1
aws cloudformation wait stack-delete-complete --region ap-northeast-2 --stack-name b3-1
# 실습 전용 키페어이고 더 이상 필요 없는 경우만
aws ec2 delete-key-pair --region ap-northeast-2 --key-name b3-1
```

스택 삭제 후 EC2, EBS, EIP, Internet Gateway, VPC를 AWS 콘솔이나 `aws ec2 describe-instances`, `describe-volumes`, `describe-addresses`, `describe-internet-gateways`, `describe-vpcs`로 재확인합니다. 해당 AWS 계정의 기존 리소스와 구분해야 합니다. 스택 밖에 만든 IAM 사용자는 관리자 IAM이 정리합니다. **스택 삭제만으로 모든 비용이 0이라는 뜻은 아니며 Billing 반영이 지연될 수 있습니다.**

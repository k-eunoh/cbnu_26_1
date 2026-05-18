# Terraform

> Infrastructure as Code — 인프라를 코드로 선언적 관리

## 기본 구조

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  name     = "rg-portfolio"
  location = "Korea Central"
}
```

## 워크플로우

```bash
terraform init      # 초기화 / 플러그인 설치
terraform plan      # 변경사항 미리보기
terraform apply     # 인프라 배포
terraform destroy   # 인프라 삭제
```

> 🔗 [Notion 원본](https://www.notion.so/fff5e60c6bd381cdbfcadd07cd628666)

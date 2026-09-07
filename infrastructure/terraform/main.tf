# Terraform Root Infrastructure Module for AI Data Analyst OS
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
  }
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Target deployment tier (dev, staging, production)"
}

variable "primary_region" {
  type        = string
  default     = "us-east-1"
}

variable "replica_regions" {
  type        = list(string)
  default     = ["eu-central-1", "ap-south-1"]
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"
}

# Kubernetes Cluster (EKS)
module "k8s_cluster" {
  source = "./modules/eks"
}

# Relational Database (Aurora Multi-Region PostgreSQL)
module "rds_postgres" {
  source = "./modules/rds"
}

# Distributed Cache (ElastiCache Redis Cluster)
module "elasticache_redis" {
  source = "./modules/redis"
}

#!/bin/bash
# AWS Infrastructure Setup Script — AgroSaaS Minimal Configuration
# Usage: bash aws-setup.sh --region us-east-1 --environment prod

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

REGION="${REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
PROJECT_NAME="agrosaas"
CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}-cluster"
RDS_INSTANCE="${PROJECT_NAME}-${ENVIRONMENT}-db"
REDIS_INSTANCE="${PROJECT_NAME}-${ENVIRONMENT}-redis"
S3_BUCKET="${PROJECT_NAME}-uploads-${ENVIRONMENT}"
VPC_CIDR="10.0.0.0/16"
PUBLIC_SUBNET_1="10.0.1.0/24"
PUBLIC_SUBNET_2="10.0.2.0/24"
PRIVATE_SUBNET_1="10.0.10.0/24"
PRIVATE_SUBNET_2="10.0.11.0/24"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed. Please install it first."
    fi
    log "AWS CLI found: $(aws --version)"
}

check_aws_credentials() {
    if ! aws sts get-caller-identity --region "$REGION" > /dev/null 2>&1; then
        error "AWS credentials not configured or invalid."
    fi
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log "AWS Account ID: $ACCOUNT_ID"
}

# ============================================================================
# VPC & NETWORKING
# ============================================================================

create_vpc() {
    log "Creating VPC..."

    VPC_ID=$(aws ec2 create-vpc \
        --cidr-block "$VPC_CIDR" \
        --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=${PROJECT_NAME}-${ENVIRONMENT}-vpc}]" \
        --region "$REGION" \
        --query 'Vpc.VpcId' \
        --output text)

    log "VPC created: $VPC_ID"

    # Enable DNS hostnames
    aws ec2 modify-vpc-attribute \
        --vpc-id "$VPC_ID" \
        --enable-dns-hostnames \
        --region "$REGION"

    echo "$VPC_ID"
}

create_subnets() {
    local VPC_ID=$1
    log "Creating subnets..."

    # Public Subnet AZ-a
    PUB_SUBNET_1=$(aws ec2 create-subnet \
        --vpc-id "$VPC_ID" \
        --cidr-block "$PUBLIC_SUBNET_1" \
        --availability-zone "${REGION}a" \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT_NAME}-public-1a}]" \
        --region "$REGION" \
        --query 'Subnet.SubnetId' \
        --output text)

    # Public Subnet AZ-b
    PUB_SUBNET_2=$(aws ec2 create-subnet \
        --vpc-id "$VPC_ID" \
        --cidr-block "$PUBLIC_SUBNET_2" \
        --availability-zone "${REGION}b" \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT_NAME}-public-1b}]" \
        --region "$REGION" \
        --query 'Subnet.SubnetId' \
        --output text)

    # Private Subnet AZ-a
    PRIV_SUBNET_1=$(aws ec2 create-subnet \
        --vpc-id "$VPC_ID" \
        --cidr-block "$PRIVATE_SUBNET_1" \
        --availability-zone "${REGION}a" \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT_NAME}-private-1a}]" \
        --region "$REGION" \
        --query 'Subnet.SubnetId' \
        --output text)

    # Private Subnet AZ-b
    PRIV_SUBNET_2=$(aws ec2 create-subnet \
        --vpc-id "$VPC_ID" \
        --cidr-block "$PRIVATE_SUBNET_2" \
        --availability-zone "${REGION}b" \
        --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT_NAME}-private-1b}]" \
        --region "$REGION" \
        --query 'Subnet.SubnetId' \
        --output text)

    log "Subnets created: Public [$PUB_SUBNET_1, $PUB_SUBNET_2] Private [$PRIV_SUBNET_1, $PRIV_SUBNET_2]"

    echo "$VPC_ID,$PUB_SUBNET_1,$PUB_SUBNET_2,$PRIV_SUBNET_1,$PRIV_SUBNET_2"
}

create_security_groups() {
    local VPC_ID=$1
    log "Creating security groups..."

    # ALB Security Group
    SG_ALB=$(aws ec2 create-security-group \
        --group-name "${PROJECT_NAME}-alb-sg" \
        --description "ALB Security Group" \
        --vpc-id "$VPC_ID" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)

    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ALB" \
        --protocol tcp --port 80 --cidr 0.0.0.0/0 \
        --region "$REGION"

    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ALB" \
        --protocol tcp --port 443 --cidr 0.0.0.0/0 \
        --region "$REGION"

    # ECS Security Group
    SG_ECS=$(aws ec2 create-security-group \
        --group-name "${PROJECT_NAME}-ecs-sg" \
        --description "ECS Tasks Security Group" \
        --vpc-id "$VPC_ID" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)

    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ECS" \
        --protocol tcp --port 3000 --source-group "$SG_ALB" \
        --region "$REGION"

    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ECS" \
        --protocol tcp --port 3001 --source-group "$SG_ALB" \
        --region "$REGION"

    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ECS" \
        --protocol tcp --port 8000 --source-group "$SG_ALB" \
        --region "$REGION"

    # RDS Security Group
    SG_RDS=$(aws ec2 create-security-group \
        --group-name "${PROJECT_NAME}-rds-sg" \
        --description "RDS Database Security Group" \
        --vpc-id "$VPC_ID" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)

    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_RDS" \
        --protocol tcp --port 5432 --source-group "$SG_ECS" \
        --region "$REGION"

    # Redis Security Group
    SG_REDIS=$(aws ec2 create-security-group \
        --group-name "${PROJECT_NAME}-redis-sg" \
        --description "Redis ElastiCache Security Group" \
        --vpc-id "$VPC_ID" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)

    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_REDIS" \
        --protocol tcp --port 6379 --source-group "$SG_ECS" \
        --region "$REGION"

    log "Security Groups created: ALB [$SG_ALB] ECS [$SG_ECS] RDS [$SG_RDS] Redis [$SG_REDIS]"

    echo "$SG_ALB,$SG_ECS,$SG_RDS,$SG_REDIS"
}

# ============================================================================
# RDS POSTGRESQL
# ============================================================================

create_rds_instance() {
    log "Creating RDS PostgreSQL instance..."

    aws rds create-db-instance \
        --db-instance-identifier "$RDS_INSTANCE" \
        --db-instance-class db.t4g.small \
        --engine postgres \
        --engine-version 14.9 \
        --master-username postgres \
        --master-user-password "$(openssl rand -base64 20)" \
        --allocated-storage 100 \
        --storage-type gp3 \
        --vpc-security-group-ids "$1" \
        --db-subnet-group-name "${PROJECT_NAME}-subnet-group" \
        --multi-az \
        --backup-retention-period 30 \
        --enable-cloudwatch-logs-exports postgresql \
        --enable-iam-database-authentication \
        --storage-encrypted \
        --region "$REGION" \
        2>/dev/null || warn "RDS instance already exists or creation failed"

    log "RDS instance creation initiated: $RDS_INSTANCE (may take 5-10 minutes)"
}

# ============================================================================
# ELASTICACHE REDIS
# ============================================================================

create_elasticache_redis() {
    log "Creating ElastiCache Redis cluster..."

    aws elasticache create-cache-cluster \
        --cache-cluster-id "$REDIS_INSTANCE" \
        --engine redis \
        --cache-node-type cache.t4g.micro \
        --engine-version 6.x \
        --num-cache-nodes 1 \
        --vpc-security-group-ids "$1" \
        --cache-subnet-group-name "${PROJECT_NAME}-redis-subnet-group" \
        --at-rest-encryption-enabled \
        --transit-encryption-enabled \
        --auto-failover-enabled \
        --region "$REGION" \
        2>/dev/null || warn "Redis cluster already exists or creation failed"

    log "Redis cluster creation initiated: $REDIS_INSTANCE"
}

# ============================================================================
# S3 BUCKET
# ============================================================================

create_s3_bucket() {
    log "Creating S3 bucket..."

    if [ "$REGION" = "us-east-1" ]; then
        aws s3api create-bucket \
            --bucket "$S3_BUCKET" \
            --region "$REGION" \
            2>/dev/null || warn "S3 bucket already exists"
    else
        aws s3api create-bucket \
            --bucket "$S3_BUCKET" \
            --region "$REGION" \
            --create-bucket-configuration LocationConstraint="$REGION" \
            2>/dev/null || warn "S3 bucket already exists"
    fi

    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "$S3_BUCKET" \
        --versioning-configuration Status=Enabled \
        --region "$REGION"

    # Enable server-side encryption
    aws s3api put-bucket-encryption \
        --bucket "$S3_BUCKET" \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }' \
        --region "$REGION"

    # Block public access
    aws s3api put-public-access-block \
        --bucket "$S3_BUCKET" \
        --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
        --region "$REGION"

    log "S3 bucket created: $S3_BUCKET"
}

# ============================================================================
# ECR REPOSITORIES
# ============================================================================

create_ecr_repositories() {
    log "Creating ECR repositories..."

    for repo in api web backoffice workers; do
        repo_name="${PROJECT_NAME}-${repo}"
        aws ecr create-repository \
            --repository-name "$repo_name" \
            --image-scanning-configuration scanOnPush=true \
            --region "$REGION" \
            --tag-specifications "ResourceType=repository,Tags=[{Key=Environment,Value=${ENVIRONMENT}}]" \
            2>/dev/null || warn "ECR repository $repo_name already exists"

        log "ECR repository: $repo_name"
    done
}

# ============================================================================
# ECS CLUSTER
# ============================================================================

create_ecs_cluster() {
    log "Creating ECS Cluster..."

    aws ecs create-cluster \
        --cluster-name "$CLUSTER_NAME" \
        --capacity-providers FARGATE FARGATE_SPOT \
        --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1,base=1 \
        --region "$REGION" \
        2>/dev/null || warn "ECS cluster already exists"

    log "ECS cluster created: $CLUSTER_NAME"
}

# ============================================================================
# CLOUDWATCH LOG GROUPS
# ============================================================================

create_log_groups() {
    log "Creating CloudWatch Log Groups..."

    for service in api web backoffice workers; do
        log_group="/aws/ecs/${PROJECT_NAME}-${service}"
        aws logs create-log-group \
            --log-group-name "$log_group" \
            --region "$REGION" \
            2>/dev/null || true

        aws logs put-retention-policy \
            --log-group-name "$log_group" \
            --retention-in-days 30 \
            --region "$REGION"

        log "Log group: $log_group (30 days retention)"
    done
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    log "=== AgroSaaS AWS Infrastructure Setup ==="
    log "Region: $REGION | Environment: $ENVIRONMENT"

    check_aws_cli
    check_aws_credentials

    # Create VPC
    VPC_ID=$(create_vpc)

    # Create Subnets
    SUBNET_DATA=$(create_subnets "$VPC_ID")
    IFS=',' read -r VPC_ID PUB_SUBNET_1 PUB_SUBNET_2 PRIV_SUBNET_1 PRIV_SUBNET_2 <<< "$SUBNET_DATA"

    # Create Security Groups
    SG_DATA=$(create_security_groups "$VPC_ID")
    IFS=',' read -r SG_ALB SG_ECS SG_RDS SG_REDIS <<< "$SG_DATA"

    # Create RDS
    create_rds_instance "$SG_RDS"

    # Create ElastiCache Redis
    create_elasticache_redis "$SG_REDIS"

    # Create S3 Bucket
    create_s3_bucket

    # Create ECR Repositories
    create_ecr_repositories

    # Create ECS Cluster
    create_ecs_cluster

    # Create Log Groups
    create_log_groups

    # Summary
    cat << EOF

${GREEN}=== Setup Complete ===${NC}

Infrastructure Components Created:
├── VPC:             $VPC_ID
├── Public Subnets:  $PUB_SUBNET_1, $PUB_SUBNET_2
├── Private Subnets: $PRIV_SUBNET_1, $PRIV_SUBNET_2
├── Security Groups: ALB=$SG_ALB, ECS=$SG_ECS, RDS=$SG_RDS, Redis=$SG_REDIS
├── RDS Instance:    $RDS_INSTANCE (t4g.small, 100GB)
├── Redis Cluster:   $REDIS_INSTANCE (cache.t4g.micro)
├── S3 Bucket:       $S3_BUCKET
├── ECR Repos:       agrosaas-{api,web,backoffice,workers}
└── ECS Cluster:     $CLUSTER_NAME

${YELLOW}Next Steps:${NC}

1. Build and push Docker images to ECR:
   docker build -t agrosaas-api ./services/api
   aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
   docker tag agrosaas-api:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/agrosaas-api:latest
   docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/agrosaas-api:latest

2. Get RDS endpoint and create database:
   aws rds describe-db-instances --db-instance-identifier $RDS_INSTANCE --region $REGION

3. Create ALB and target groups (see: AWS_MINIMAL_SETUP.md for detailed steps)

4. Deploy ECS task definitions and services

Documentation: See docs/AWS_MINIMAL_SETUP.md for complete configuration guide.

EOF
}

# ============================================================================
# RUN
# ============================================================================

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi

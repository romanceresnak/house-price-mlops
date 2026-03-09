#!/bin/bash
# ============================================================================
# Build and Push Docker Image to AWS ECR
# ============================================================================
#
# Tento script:
#   1. Buildne Docker image
#   2. Loguje sa do AWS ECR
#   3. Taguje image
#   4. Pushne do ECR
#
# Použitie:
#   ./scripts/build_and_push.sh [region] [image-name]
#
# Príklad:
#   ./scripts/build_and_push.sh eu-west-1 house-price-mlops
#
# Predpoklady:
#   - AWS CLI nakonfigurované
#   - Docker daemon beží
#   - ECR repository už existuje (vytvorené cez Terraform)
#
# ============================================================================

set -e  # Exit on error

# Colors pre output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# Configuration
# ============================================================================

# Default values
AWS_REGION="${1:-eu-west-1}"
IMAGE_NAME="${2:-house-price-mlops}"
IMAGE_TAG="${3:-latest}"

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Build and Push Docker Image to ECR${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Configuration:"
echo "  Region: $AWS_REGION"
echo "  Image: $IMAGE_NAME"
echo "  Tag: $IMAGE_TAG"
echo ""

# ============================================================================
# Get AWS Account ID
# ============================================================================

echo -e "${YELLOW}→ Getting AWS Account ID...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}✗ Failed to get AWS Account ID${NC}"
    echo "  Make sure AWS CLI is configured: aws configure"
    exit 1
fi

echo -e "${GREEN}✓ AWS Account ID: $AWS_ACCOUNT_ID${NC}"

# ============================================================================
# ECR Repository URI
# ============================================================================

ECR_REPOSITORY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME"

echo ""
echo "ECR Repository: $ECR_REPOSITORY"
echo ""

# ============================================================================
# Check if ECR repository exists
# ============================================================================

echo -e "${YELLOW}→ Checking if ECR repository exists...${NC}"

if aws ecr describe-repositories --repository-names "$IMAGE_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ECR repository exists${NC}"
else
    echo -e "${YELLOW}⚠ ECR repository does not exist${NC}"
    echo "  Create it with:"
    echo "  aws ecr create-repository --repository-name $IMAGE_NAME --region $AWS_REGION"
    echo ""
    read -p "Create repository now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        aws ecr create-repository --repository-name "$IMAGE_NAME" --region "$AWS_REGION"
        echo -e "${GREEN}✓ ECR repository created${NC}"
    else
        echo -e "${RED}✗ Aborted${NC}"
        exit 1
    fi
fi

# ============================================================================
# Build Docker Image
# ============================================================================

echo ""
echo -e "${YELLOW}→ Building Docker image...${NC}"

# Get git commit hash for tagging
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

docker build \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg GIT_HASH="$GIT_HASH" \
    --tag "$IMAGE_NAME:$IMAGE_TAG" \
    --tag "$IMAGE_NAME:$GIT_HASH" \
    --file Dockerfile \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
    echo -e "${RED}✗ Docker build failed${NC}"
    exit 1
fi

# ============================================================================
# Login to ECR
# ============================================================================

echo ""
echo -e "${YELLOW}→ Logging in to ECR...${NC}"

aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Logged in to ECR${NC}"
else
    echo -e "${RED}✗ ECR login failed${NC}"
    exit 1
fi

# ============================================================================
# Tag Image for ECR
# ============================================================================

echo ""
echo -e "${YELLOW}→ Tagging image for ECR...${NC}"

docker tag "$IMAGE_NAME:$IMAGE_TAG" "$ECR_REPOSITORY:$IMAGE_TAG"
docker tag "$IMAGE_NAME:$IMAGE_TAG" "$ECR_REPOSITORY:$GIT_HASH"

echo -e "${GREEN}✓ Image tagged${NC}"
echo "  - $ECR_REPOSITORY:$IMAGE_TAG"
echo "  - $ECR_REPOSITORY:$GIT_HASH"

# ============================================================================
# Push to ECR
# ============================================================================

echo ""
echo -e "${YELLOW}→ Pushing image to ECR...${NC}"

docker push "$ECR_REPOSITORY:$IMAGE_TAG"
docker push "$ECR_REPOSITORY:$GIT_HASH"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Image pushed successfully${NC}"
else
    echo -e "${RED}✗ Push to ECR failed${NC}"
    exit 1
fi

# ============================================================================
# Summary
# ============================================================================

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✓ Build and Push Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Image URI:"
echo "  $ECR_REPOSITORY:$IMAGE_TAG"
echo "  $ECR_REPOSITORY:$GIT_HASH"
echo ""
echo "Local image size:"
docker images "$IMAGE_NAME:$IMAGE_TAG" --format "  {{.Size}}"
echo ""
echo "Next steps:"
echo "  1. Use this image URI in SageMaker Training Job"
echo "  2. Update scripts/run_training_job.py with --ecr-image"
echo "  3. Run training: python scripts/run_training_job.py \\"
echo "       --ecr-image $ECR_REPOSITORY:$IMAGE_TAG"
echo ""

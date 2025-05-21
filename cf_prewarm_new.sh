#!/bin/bash
# CloudFront预热脚本
# 用途：读取文件列表并调用Lambda函数对CloudFront资源进行预热
# 作者：Lambda + CloudFront预热工具

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置参数（请根据实际情况修改）
CLOUDFRONT_URL="d2qupf6sbg9i95.cloudfront.net"  # 您的CloudFront分配域名
LAMBDA_FUNCTION_NAME="cloudfront_prewarm"        # Lambda函数名称
FILE_LIST="file.txt"                             # 预热文件列表
MAX_CONCURRENT=10                                # 最大并发数

# 检查AWS CLI是否安装
if ! command -v aws &> /dev/null; then
    echo -e "${RED}错误: AWS CLI 未安装，请先安装AWS CLI工具。${NC}"
    echo "安装指南: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# 检查是否已配置AWS凭证
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}错误: AWS凭证未配置或已过期。${NC}"
    echo "请运行 'aws configure' 配置您的AWS凭证。"
    exit 1
fi

# 检查文件列表是否存在
if [ ! -f "$FILE_LIST" ]; then
    echo -e "${RED}错误: 文件列表 '$FILE_LIST' 不存在。${NC}"
    exit 1
fi

# 检查Lambda函数是否存在
if ! aws lambda get-function --function-name "$LAMBDA_FUNCTION_NAME" &> /dev/null; then
    echo -e "${RED}错误: Lambda函数 '$LAMBDA_FUNCTION_NAME' 不存在。${NC}"
    echo "请确认函数名称是否正确，或者按照README.md中的说明创建Lambda函数。"
    exit 1
fi

# 显示配置信息
echo -e "${BLUE}===== CloudFront预热任务开始 =====${NC}"
echo -e "${BLUE}CloudFront URL:${NC} $CLOUDFRONT_URL"
echo -e "${BLUE}Lambda函数:${NC} $LAMBDA_FUNCTION_NAME"
echo -e "${BLUE}预热文件列表:${NC} $FILE_LIST"
echo -e "${BLUE}最大并发数:${NC} $MAX_CONCURRENT"

# 计算文件总数
total_files=$(wc -l < "$FILE_LIST")
echo -e "${BLUE}预热文件总数:${NC} $total_files"

# 开始预热
echo -e "${YELLOW}开始提交预热任务...${NC}"

count=0
success=0
failed=0

# 使用信号量控制最大并发数
sem_init() {
    mkfifo /tmp/sem.$$
    exec 3<> /tmp/sem.$$
    rm /tmp/sem.$$
    
    for ((i=0; i<$1; i++)); do
        echo >&3
    done
}

sem_acquire() {
    read -u 3
}

sem_release() {
    echo >&3
}

# 初始化信号量
sem_init $MAX_CONCURRENT

# 读取文件列表并提交Lambda预热任务
while IFS= read -r file || [ -n "$file" ]; do
    # 跳过空行
    if [ -z "$file" ]; then
        continue
    fi
    
    # 增加计数器
    ((count++))
    
    # 获取信号量（控制并发）
    sem_acquire
    
    # 构建Lambda调用的Payload
    payload="{\"filename\":\"$file\",\"cloudfront_url\":\"$CLOUDFRONT_URL\"}"
    
    # 提交Lambda任务
    (
        echo -e "${GREEN}[$count/$total_files] 正在预热:${NC} $file"
        if aws lambda invoke \
            --function-name "$LAMBDA_FUNCTION_NAME" \
            --invocation-type Event \
            --cli-binary-format raw-in-base64-out \
            --payload "$payload" \
            /dev/null > /dev/null 2>&1; then
            echo -e "${GREEN}[$count/$total_files] 成功提交:${NC} $file"
            ((success++))
        else
            echo -e "${RED}[$count/$total_files] 提交失败:${NC} $file"
            ((failed++))
        fi
        
        # 释放信号量
        sem_release
    ) &
    
done < "$FILE_LIST"

# 等待所有后台任务完成
wait

echo -e "${BLUE}===== CloudFront预热任务统计 =====${NC}"
echo -e "${BLUE}总任务数:${NC} $count"
echo -e "${GREEN}成功提交:${NC} $success"
echo -e "${RED}提交失败:${NC} $failed"

echo -e "${YELLOW}注意: 预热任务已提交到Lambda，实际预热结果请查看CloudWatch日志。${NC}"
echo -e "${YELLOW}日志组路径: /aws/lambda/$LAMBDA_FUNCTION_NAME${NC}"

echo -e "${BLUE}===== CloudFront预热任务结束 =====${NC}"

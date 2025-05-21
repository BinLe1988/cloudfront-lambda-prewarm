import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def warm(pop, cf_id, cf_url, file_name):
    """
    对特定的PoP节点进行预热
    
    Args:
        pop (str): CloudFront的PoP节点标识
        cf_id (str): CloudFront分配ID
        cf_url (str): CloudFront分配的域名
        file_name (str): 需要预热的文件路径
    """
    try:
        file_url = f'http://{cf_id}.{pop}.cloudfront.net{file_name}'
        header = {'Host': cf_url}
        req = urllib.request.Request(url=file_url, headers=header)
        response = urllib.request.urlopen(req)
        logger.info(f'SUCCESS: POP:{pop} FILE:{file_url}')
    except urllib.error.HTTPError as e:
        logger.error(f'FAILED: POP:{pop} FILE:{file_url} REASON:HTTPError: {e.code}')
    except urllib.error.URLError as e:
        logger.error(f'FAILED: POP:{pop} FILE:{file_url} REASON:URLError: {e.reason}')
    except Exception as e:
        logger.error(f'FAILED: POP:{pop} FILE:{file_url} REASON:{str(e)}')

def lambda_handler(event, context):
    """
    Lambda函数的入口点
    
    Args:
        event (dict): 包含预热文件信息的事件数据
        context: Lambda上下文对象
    
    Returns:
        dict: 执行结果
    """
    # CloudFront全球PoP节点列表
    cloudfront_pops = [
        "EZE51-C1", "MEL50-C1", "PER50-C1", "SYD1-C1", "SYD1-C2", "SYD4-C1", "SYD4-C2", 
        "VIE50-C1", "BAH53-C1", "BRU50-C1", "GIG51-C2", "GRU1-C1", "GRU3-C1", "GRU50-C1", 
        "SOF50-C1", "YUL62-C1", "YTO50-C1", "YTO50-C3", "YVR50-C1", "SCL50-C1", "HKG54-C1", 
        "HKG60-C1", "HKG62-C1", "HKG62-C2", "TPE50-C1", "TPE51-C1", "TPE52-C1", "BOG50-C1", 
        "ZAG50-C1", "PRG50-C1", "CPH50-C1", "CPH50-C2", "HEL50-C1", "HEL50-C2", "MRS52-C1", 
        "CDG3-C2", "CDG50-C1", "CDG50-C2", "TXL52-C1", "DUS51-C1", "FRA2-C1", "FRA2-C2", 
        "FRA6-C1", "FRA50-C1", "FRA56-C1", "HAM50-C1", "HAM50-C2", "HAM50-C3", "MUC50-C1", 
        "MUC51-C1", "ATH50-C1", "BUD50-C1", "BLR50-C2", "MAA50-C1", "MAA50-C2", "MAA51-C1", 
        "MAA51-C2", "HYD50-C1", "HYD50-C2", "HYD50-C3", "CCU50-C1", "CCU50-C2", "BOM50-C1", 
        "BOM51-C1", "BOM51-C2", "BOM52-C1", "DEL51-C1", "DEL54-C1", "DEL54-C3", "DUB2-C1", 
        "TLV50-C1", "MXP64-C1", "MXP64-C2", "MXP64-C3", "PMO50", "FCO50-C1", "NRT12-C2", 
        "NRT12-C3", "NRT12-C4", "NRT20-C1", "NRT20-C2", "NRT20-C3", "NRT20-C4", "NRT51-C1", 
        "NRT51-C2", "NRT51-C3", "NRT51-C4", "NRT57-C2", "NRT57-C4", "NBO50-C1", "KUL50-C1", 
        "KUL50-C2", "QRO50-C1", "QRO51-C1", "AKL50-C1", "OSL50-C1", "MNL50-C1", "WAW50-C1", 
        "LIS50-C1", "OTP50-C1", "SIN2-C1", "SIN5-C1", "SIN52-C2", "SIN52-C3", "CPT50", 
        "JNB50", "ICN51-C1", "ICN51-C2", "ICN54-C1", "ICN54-C2", "ICN54-C3", "ICN55-C1", 
        "MAD50-C1", "MAD51-C2", "ARN1-C1", "ARN53", "ARN54-C1", "ZRH50-C1", "BKK50-C2", 
        "AMS1-C1", "AMS50-C1", "AMS54-C1", "DXB50-C1", "FJR50-C1", "LHR3-C1", "LHR3-C2", 
        "LHR52-C1", "LHR61-C2", "LHR62-C1", "LHR62-C3", "LHR62-C4", "MAN50-C1", "MAN50-C3", 
        "IAD50-C2", "IAD66-C1", "IAD66-C2", "IAD79-C2", "IAD79-C3", "IAD89-C1", "ATL50-C1", 
        "ATL51-C1", "ATL56-C1", "ATL56-C2", "ATL56-C3", "BOS50-C1", "BOS50-C3", "ORD50-C1", 
        "ORD51-C2", "ORD51-C3", "ORD52-C2", "ORD53-C1", "DFW3-C1", "DFW50-C1", "DFW53-C1", 
        "DFW55-C3", "DEN50-C2", "DEN52-C1", "HIO50-C1", "HIO50-C2", "HIO51-C1", "IAH50-C1", 
        "IAH50-C3", "IAH50-C4", "JAX1-C1", "LAX3-C2", "LAX3-C4", "LAX50-C1", "LAX50-C3", 
        "MIA3-C1", "MIA3-C2", "MIA3-C3", "MIA3-C5", "MSP50-C1", "JFK51-C1", "EWR50-C1", 
        "EWR52-C2", "EWR52-C3", "EWR52-C4", "PHL50-C1", "PHX50-C1", "PHX50-C2", "SLC50-C1", 
        "SFO5-C1", "SFO5-C3", "SFO20-C1", "SFO53-C1", "SEA19-C1", "SEA19-C2", "IND6"
    ]

    try:
        # 解析输入的事件数据
        event_str = json.dumps(event)
        event_data = json.loads(event_str)
        
        file_name = event_data.get('filename')
        cloudfront_url = event_data.get('cloudfront_url')
        
        if not file_name or not cloudfront_url:
            logger.error("缺少必要的参数: 文件名或CloudFront URL")
            return {
                'statusCode': 400,
                'body': json.dumps('缺少必要的参数')
            }
        
        # 提取CloudFront分配ID
        distributions_id = cloudfront_url.split('.')[0]
        
        logger.info(f"开始预热文件: {file_name}")
        logger.info(f"CloudFront URL: {cloudfront_url}")
        logger.info(f"分配ID: {distributions_id}")
        
        # 使用线程池并行处理所有PoP节点的预热
        with ThreadPoolExecutor(max_workers=100) as executor:
            for pop in cloudfront_pops:
                executor.submit(warm, pop, distributions_id, cloudfront_url, file_name)
        
        return {
            'statusCode': 200,
            'body': json.dumps(f'成功为 {file_name} 提交预热请求')
        }
        
    except Exception as e:
        logger.error(f"预热过程中发生错误: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'预热过程中发生错误: {str(e)}')
        }

# 如果直接运行脚本，可以进行测试
if __name__ == "__main__":
    # 测试事件数据
    test_event = {
        'filename': '/test/example.jpg',
        'cloudfront_url': 'example.cloudfront.net'
    }
    lambda_handler(test_event, None)

import requests
import json
import time

class UMLSClient:
    AUTH_ENDPOINT = "https://utslogin.nlm.nih.gov"
    API_ENDPOINT = "https://uts-ws.nlm.nih.gov"

    def __init__(self, api_key):
        self.api_key = api_key
        print(f"=== 初始化UMLS客户端 ===")
        print(f"API Key: {api_key[:20]}...")
        self.tgt = self.get_tgt()

    def get_tgt(self):
        print(f"=== 获取TGT (Ticket Granting Ticket) ===")
        params = {'apikey': self.api_key}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        print(f"请求URL: {self.AUTH_ENDPOINT}/cas/v1/api-key")
        r = requests.post(f"{self.AUTH_ENDPOINT}/cas/v1/api-key", data=params, headers=headers)
        print(f"TGT请求状态码: {r.status_code}")
        print(f"TGT响应头: {dict(r.headers)}")
        if r.status_code != 201:
            print(f"TGT请求失败，响应内容: {r.text}")
            raise Exception("Failed to obtain TGT")
        tgt = r.headers['location']
        print(f"成功获取TGT: {tgt}")
        return tgt

    def get_service_ticket(self):
        print(f"=== 获取服务票据 ===")
        params = {'service': 'http://umlsks.nlm.nih.gov'}
        print(f"请求URL: {self.tgt}")
        r = requests.post(self.tgt, data=params)
        print(f"服务票据请求状态码: {r.status_code}")
        if r.status_code != 200:
            print(f"服务票据请求失败，响应内容: {r.text}")
            raise Exception("Failed to obtain service ticket")
        ticket = r.text
        print(f"成功获取服务票据: {ticket}")
        return ticket

    def get_codes_for_cui(self, cui, vocabularies):
        print(f"\n=== 开始处理CUI: {cui} ===")
        print(f"目标词汇表: {vocabularies}")
        
        ticket = self.get_service_ticket()
        headers = {'Accept': 'application/json'}
        params = {'ticket': ticket}
        api_url = f"{self.API_ENDPOINT}/rest/content/current/CUI/{cui}/atoms"
        print(f"API请求URL: {api_url}")
        print(f"请求参数: {params}")
        print(f"请求头: {headers}")
        
        r = requests.get(api_url, headers=headers, params=params)
        print(f"API响应状态码: {r.status_code}")
        print(f"API响应头: {dict(r.headers)}")
        
        if r.status_code != 200:
            print(f"Failed to retrieve atoms for CUI {cui}")
            print(f"错误响应内容: {r.text}")
            return {}
        
        # 打印原始API响应
        raw_response = r.json()
        print(f"=== 原始API响应 ===")
        print(json.dumps(raw_response, indent=2, ensure_ascii=False))
        
        results = raw_response.get('result', [])
        print(f"=== 解析结果 ===")
        print(f"结果数组长度: {len(results)}")
        
        if not results:
            print("警告: results数组为空")
            return {}
        
        codes = {}
        atom_count = 0
        matched_count = 0
        
        for atom in results:
            atom_count += 1
            print(f"\n--- Atom #{atom_count} ---")
            print(f"完整atom数据: {json.dumps(atom, indent=2, ensure_ascii=False)}")
            
            source = atom.get('rootSource')
            code = atom.get('code')
            name = atom.get('name', 'N/A')
            
            print(f"rootSource: {source}")
            print(f"code: {code}")
            print(f"name: {name}")
            print(f"是否在目标词汇表中: {source in vocabularies}")
            
            if source in vocabularies:
                matched_count += 1
                print(f"✓ 匹配词汇表 {source}")
                if source not in codes:
                    codes[source] = set()
                codes[source].add(code)
            else:
                print(f"✗ 不匹配任何目标词汇表")
        
        print(f"\n=== 处理总结 ===")
        print(f"总atom数: {atom_count}")
        print(f"匹配的atom数: {matched_count}")
        print(f"找到的词汇表: {list(codes.keys())}")
        
        # Convert sets to lists
        for source in codes:
            codes[source] = list(codes[source])
            print(f"{source}的代码: {codes[source]}")
        
        print(f"CUI {cui} 最终结果: {codes}")
        return codes

def convert_cuis_to_codes(cuis, vocabularies, api_key):
    print(f"=== 开始批量转换CUI ===")
    print(f"CUI列表: {cuis}")
    print(f"目标词汇表: {vocabularies}")
    
    client = UMLSClient(api_key)
    all_codes = {}
    
    for i, cui in enumerate(cuis, 1):
        print(f"\n{'='*50}")
        print(f"处理第 {i}/{len(cuis)} 个CUI: {cui}")
        print(f"{'='*50}")
        
        try:
            codes = client.get_codes_for_cui(cui, vocabularies)
            all_codes[cui] = codes
            print(f"✓ CUI {cui} 处理成功")
        except Exception as e:
            print(f"✗ 处理CUI {cui}时出错: {e}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            print(f"错误详情: {traceback.format_exc()}")
            all_codes[cui] = {}
        
        print(f"等待0.5秒以遵守API速率限制...")
        time.sleep(0.5)  # To respect API rate limits
    
    print(f"\n=== 批量处理完成 ===")
    print(f"处理结果概览:")
    for cui, result in all_codes.items():
        print(f"  {cui}: {len(result)} 个词汇表")
    
    return all_codes

# Example usage:
if __name__ == "__main__":
    print("=== UMLS CUI到其他编码系统转换工具 ===")
    API_KEY = '8a34672e-87c0-4110-b070-0a015d3509e9'  # Replace with your actual API key
    cuis = ['C0011849', 'C0015967']  # Example CUIs
    vocabularies = ['ICD10CM', 'RXNORM', 'LOINC']
    
    print(f"配置信息:")
    print(f"  API Key: {API_KEY[:20]}...")
    print(f"  CUIs: {cuis}")
    print(f"  词汇表: {vocabularies}")
    print()
    
    codes = convert_cuis_to_codes(cuis, vocabularies, API_KEY)
    
    print(f"\n=== 最终结果 ===")
    print(json.dumps(codes, indent=2, ensure_ascii=False))
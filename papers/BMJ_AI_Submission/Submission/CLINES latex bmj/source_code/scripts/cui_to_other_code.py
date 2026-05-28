import requests
import json
import time

class UMLSClient:
    AUTH_ENDPOINT = "https://utslogin.nlm.nih.gov"
    API_ENDPOINT = "https://uts-ws.nlm.nih.gov"

    def __init__(self, api_key):
        self.api_key = api_key
        print(f"=== Initializing UMLS Client ===")
        print(f"API Key: {api_key[:20]}...")
        self.tgt = self.get_tgt()

    def get_tgt(self):
        print(f"=== Getting TGT (Ticket Granting Ticket) ===")
        params = {'apikey': self.api_key}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        print(f"Request URL: {self.AUTH_ENDPOINT}/cas/v1/api-key")
        r = requests.post(f"{self.AUTH_ENDPOINT}/cas/v1/api-key", data=params, headers=headers)
        print(f"TGT request status code: {r.status_code}")
        print(f"TGT response headers: {dict(r.headers)}")
        if r.status_code != 201:
            print(f"TGT request failed, response content: {r.text}")
            raise Exception("Failed to obtain TGT")
        tgt = r.headers['location']
        print(f"Successfully obtained TGT: {tgt}")
        return tgt

    def get_service_ticket(self):
        print(f"=== Getting Service Ticket ===")
        params = {'service': 'http://umlsks.nlm.nih.gov'}
        print(f"Request URL: {self.tgt}")
        r = requests.post(self.tgt, data=params)
        print(f"Service ticket request status code: {r.status_code}")
        if r.status_code != 200:
            print(f"Service ticket request failed, response content: {r.text}")
            raise Exception("Failed to obtain service ticket")
        ticket = r.text
        print(f"Successfully obtained service ticket: {ticket}")
        return ticket

    def get_codes_for_cui(self, cui, vocabularies):
        print(f"\n=== Starting to process CUI: {cui} ===")
        print(f"Target vocabularies: {vocabularies}")
        
        ticket = self.get_service_ticket()
        headers = {'Accept': 'application/json'}
        params = {'ticket': ticket}
        api_url = f"{self.API_ENDPOINT}/rest/content/current/CUI/{cui}/atoms"
        print(f"API request URL: {api_url}")
        print(f"Request parameters: {params}")
        print(f"Request headers: {headers}")
        
        r = requests.get(api_url, headers=headers, params=params)
        print(f"API response status code: {r.status_code}")
        print(f"API response headers: {dict(r.headers)}")
        
        if r.status_code != 200:
            print(f"Failed to retrieve atoms for CUI {cui}")
            print(f"Error response content: {r.text}")
            return {}
        
        # Print raw API response
        raw_response = r.json()
        print(f"=== Raw API Response ===")
        print(json.dumps(raw_response, indent=2, ensure_ascii=False))
        
        results = raw_response.get('result', [])
        print(f"=== Parsing Results ===")
        print(f"Results array length: {len(results)}")
        
        if not results:
            print("Warning: results array is empty")
            return {}
        
        codes = {}
        atom_count = 0
        matched_count = 0
        
        for atom in results:
            atom_count += 1
            print(f"\n--- Atom #{atom_count} ---")
            print(f"Complete atom data: {json.dumps(atom, indent=2, ensure_ascii=False)}")
            
            source = atom.get('rootSource')
            code = atom.get('code')
            name = atom.get('name', 'N/A')
            
            print(f"rootSource: {source}")
            print(f"code: {code}")
            print(f"name: {name}")
            print(f"Is in target vocabularies: {source in vocabularies}")
            
            if source in vocabularies:
                matched_count += 1
                print(f"✓ Matches vocabulary {source}")
                if source not in codes:
                    codes[source] = set()
                codes[source].add(code)
            else:
                print(f"✗ Does not match any target vocabulary")
        
        print(f"\n=== Processing Summary ===")
        print(f"Total atoms: {atom_count}")
        print(f"Matched atoms: {matched_count}")
        print(f"Found vocabularies: {list(codes.keys())}")
        
        # Convert sets to lists
        for source in codes:
            codes[source] = list(codes[source])
            print(f"Codes for {source}: {codes[source]}")
        
        print(f"Final result for CUI {cui}: {codes}")
        return codes

def convert_cuis_to_codes(cuis, vocabularies, api_key):
    print(f"=== Starting Batch CUI Conversion ===")
    print(f"CUI list: {cuis}")
    print(f"Target vocabularies: {vocabularies}")
    
    client = UMLSClient(api_key)
    all_codes = {}
    
    for i, cui in enumerate(cuis, 1):
        print(f"\n{'='*50}")
        print(f"Processing CUI {i}/{len(cuis)}: {cui}")
        print(f"{'='*50}")
        
        try:
            codes = client.get_codes_for_cui(cui, vocabularies)
            all_codes[cui] = codes
            print(f"✓ CUI {cui} processed successfully")
        except Exception as e:
            print(f"✗ Error processing CUI {cui}: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")
            all_codes[cui] = {}
        
        print(f"Waiting 0.5 seconds to respect API rate limits...")
        time.sleep(0.5)  # To respect API rate limits
    
    print(f"\n=== Batch Processing Complete ===")
    print(f"Processing results overview:")
    for cui, result in all_codes.items():
        print(f"  {cui}: {len(result)} vocabularies")
    
    return all_codes

# Example usage:
if __name__ == "__main__":
    print("=== UMLS CUI to Other Coding Systems Conversion Tool ===")
    API_KEY = '8a34672e-87c0-4110-b070-0a015d3509e9'  # Replace with your actual API key
    cuis = ['C0203028', 'C4028586', 'C0332471']  # Example CUIs
    vocabularies = ['ICD10CM', 'RXNORM', 'LOINC']
    
    print(f"Configuration information:")
    print(f"  API Key: {API_KEY[:20]}...")
    print(f"  CUIs: {cuis}")
    print(f"  Vocabularies: {vocabularies}")
    print()
    
    codes = convert_cuis_to_codes(cuis, vocabularies, API_KEY)
    
    print(f"\n=== Final Results ===")
    print(json.dumps(codes, indent=2, ensure_ascii=False))
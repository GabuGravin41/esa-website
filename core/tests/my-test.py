from core.services import MpesaService

mpesa_service = MpesaService()

response = mpesa_service.initiate_stk_push(
    phone_number='254701606056',  
    amount=1,  
    reference='CompanyXLTD',  
    description='Payment of X'  
)

print(response)
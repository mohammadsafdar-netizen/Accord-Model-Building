from src.generated_schemas import FullFormsData, Acord125Data
from src.tools import form_population
import os

def test_full_fill():
    print("Testing Full Form Filling...")
    
    # 1. Create Data
    data = FullFormsData()
    
    # Set some Form 125 fields
    data.form_125.named_insured_full_name_a = "ACME Corp Test"
    data.form_125.named_insured_contact_primary_email_address_a = "test@acme.com"
    data.form_125.additional_interest_account_number_identifier_a = "ACC-12345"
    
    # Set some Form 127 fields
    data.form_127.vehicle_radius_of_use_a_0_ = "100"
    # Actually, 127 usually links to 125.
    
    
    # 2. Fill Forms
    results = form_population.fill_forms_from_full_data(data)
    
    print(f"Results: {results}")
    
    # 3. Verify Files
    for form_id, path in results.items():
        if os.path.exists(path) and path != "Error":
             pass

    
    print(f"Results: {results}")
    
    # 3. Verify Files
    for form_id, path in results.items():
        if os.path.exists(path) and path != "Error":
            print(f"✅ Success: {path} existed.")
        else:
            print(f"❌ Failed: {path} missing or error.")

if __name__ == "__main__":
    test_full_fill()

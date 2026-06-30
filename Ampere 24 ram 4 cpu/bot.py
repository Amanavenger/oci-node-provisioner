import oci
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Setup configuration from environment variables
config = {
    "user": os.getenv("OCI_USER_ID"),
    "key_content": os.getenv("OCI_PRIVATE_KEY"),
    "fingerprint": os.getenv("OCI_FINGERPRINT"),
    "tenancy": os.getenv("OCI_TENANCY_ID"),
    "region": os.getenv("OCI_REGION")
}

try:
    compute_client = oci.core.ComputeClient(config)
    print("OCI Authentication Successful. Initializing loop sequence with SSH validation...")
except Exception as e:
    print(f"Authentication Failed: {e}")
    exit(1)

# Execution parameters
compartment_id = os.getenv("OCI_TENANCY_ID")
subnet_id = os.getenv("OCI_SUBNET_ID")
image_id = os.getenv("OCI_IMAGE_ID")
public_ssh_key = os.getenv("OCI_PUBLIC_SSH_KEY") 

# Availability Domains to cycle through
ads = ["uufj:PHX-AD-1", "uufj:PHX-AD-2", "uufj:PHX-AD-3"]

# Changed to 60 to run for exactly an hour with the 60-second sleep timer
total_attempts = 60 

for i in range(1, total_attempts + 1):
    current_ad = ads[(i - 1) % len(ads)]
    print(f"\n[Attempt {i}/{total_attempts}] Requesting instance in {current_ad}...")
    
    try:
        request = oci.core.models.LaunchInstanceDetails(
            display_name="FX-Backend-Server",
            compartment_id=compartment_id,
            availability_domain=current_ad,
            shape="VM.Standard.A1.Flex",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=4,
                memory_in_gbs=24
            ),
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=image_id,
                boot_volume_size_in_gbs=100
            ),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=subnet_id,
                assign_public_ip=True,
                assign_private_dns_record=True,
                display_name="forexalertsvnic"
            ),
            # CRITICAL FIX: Explicitly cast the key variable to a string
            metadata={
                "ssh_authorized_keys": str(public_ssh_key)
            }
        )
        
        response = compute_client.launch_instance(request)
        if response.status == 200:
            print("SUCCESS! Authorized Server creation initialized perfectly.")
            exit(0)
            
    except oci.exceptions.ServiceError as e:
        if "Out of host capacity" in str(e) or e.status == 500:
            print(f"Capacity Unavailable in {current_ad}. Resting 60 seconds...")
        else:
            print(f"API Error encountered: {e.message}")
            
    if i < total_attempts:
        time.sleep(60)

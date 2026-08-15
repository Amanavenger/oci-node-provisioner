import oci
import os
import time
from dotenv import load_dotenv

load_dotenv()

ALWAYS_FREE_A1_MAX_OCPUS = 2.0
ALWAYS_FREE_A1_MAX_MEMORY_GB = 12.0
DEFAULT_BOOT_VOLUME_GB = 50
TERMINAL_INSTANCE_STATES = {"TERMINATED", "TERMINATING"}


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_float(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return float(default)
    return float(value)


def env_int(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return int(default)
    return int(value)


def require_env(name):
    value = os.getenv(name)
    if not value or value.strip() == "":
        raise RuntimeError(f"{name} is empty or missing")
    return value.strip()


def env_str(name, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


# Setup configuration from environment variables.
config = {
    "user": require_env("OCI_USER_ID"),
    "key_content": require_env("OCI_PRIVATE_KEY"),
    "fingerprint": require_env("OCI_FINGERPRINT"),
    "tenancy": require_env("OCI_TENANCY_ID"),
    "region": require_env("OCI_REGION"),
}

try:
    compute_client = oci.core.ComputeClient(config)
    identity_client = oci.identity.IdentityClient(config)
    print("OCI Authentication Successful. Initializing loop sequence...")
except Exception as e:
    print(f"Authentication Failed: {e}")
    exit(1)

# Execution parameters
compartment_id = env_str("OCI_COMPARTMENT_ID", config["tenancy"])
shape = env_str("OCI_SHAPE", "VM.Standard.A1.Flex")
ocpus = env_float("OCI_OCPUS", ALWAYS_FREE_A1_MAX_OCPUS)
memory_in_gbs = env_float("OCI_MEMORY_IN_GBS", ALWAYS_FREE_A1_MAX_MEMORY_GB)
boot_volume_size_in_gbs = env_int("OCI_BOOT_VOLUME_SIZE_IN_GBS", DEFAULT_BOOT_VOLUME_GB)
display_name = env_str("OCI_DISPLAY_NAME", "always-free-a1-node")
skip_existing_instance_check = env_bool("OCI_SKIP_EXISTING_INSTANCE_CHECK", False)
vnic_display_name = env_str("OCI_VNIC_DISPLAY_NAME", f"{display_name}-vnic")
assign_public_ip = env_bool("OCI_ASSIGN_PUBLIC_IP", True)
total_attempts = env_int("OCI_TOTAL_ATTEMPTS", 60)
sleep_seconds = env_int("OCI_RETRY_SLEEP_SECONDS", 60)
allow_paid_limits = env_bool("OCI_ALLOW_PAID_LIMITS", False)
image_id = env_str("OCI_IMAGE_ID", "")
default_os = env_str("OCI_IMAGE_OS", "Oracle Linux")
default_os_version = env_str("OCI_IMAGE_OS_VERSION", "")

if shape == "VM.Standard.A1.Flex" and not allow_paid_limits:
    if ocpus > ALWAYS_FREE_A1_MAX_OCPUS or memory_in_gbs > ALWAYS_FREE_A1_MAX_MEMORY_GB:
        print(
            "CRITICAL ERROR: Requested A1 shape exceeds current Always Free limits "
            f"({ALWAYS_FREE_A1_MAX_OCPUS:g} OCPUs / {ALWAYS_FREE_A1_MAX_MEMORY_GB:g} GB RAM). "
            "Set OCI_ALLOW_PAID_LIMITS=true only if you intentionally accept paid usage."
        )
        exit(1)


def find_existing_instance():
    response = oci.pagination.list_call_get_all_results(
        compute_client.list_instances,
        compartment_id,
        display_name=display_name,
    )
    for instance in response.data:
        state = (instance.lifecycle_state or "").upper()
        if state not in TERMINAL_INSTANCE_STATES:
            return instance
    return None


def exit_if_instance_exists():
    if skip_existing_instance_check:
        return

    instance = find_existing_instance()
    if instance:
        print(
            "Existing instance found; stopping without creating another server. "
            f"display_name={instance.display_name}, state={instance.lifecycle_state}, "
            f"id={instance.id}"
        )
        exit(0)


def get_availability_domains():
    configured_ads = os.getenv("OCI_AVAILABILITY_DOMAINS", "").strip()
    if configured_ads:
        return [ad.strip() for ad in configured_ads.split(",") if ad.strip()]

    response = identity_client.list_availability_domains(compartment_id)
    return [ad.name for ad in response.data]


def discover_latest_image_id():
    if image_id:
        return image_id

    kwargs = {
        "operating_system": default_os,
        "shape": shape,
        "sort_by": "TIMECREATED",
        "sort_order": "DESC",
    }
    if default_os_version:
        kwargs["operating_system_version"] = default_os_version

    images = compute_client.list_images(compartment_id, **kwargs).data
    if not images:
        version_msg = f" {default_os_version}" if default_os_version else ""
        raise RuntimeError(f"No compatible image found for {default_os}{version_msg} and {shape}")

    selected = images[0]
    print(
        "Selected image: "
        f"{selected.display_name} ({selected.operating_system} {selected.operating_system_version})"
    )
    return selected.id

try:
    exit_if_instance_exists()
    subnet_id = require_env("OCI_SUBNET_ID")
    public_ssh_key = require_env("OCI_PUBLIC_SSH_KEY")
    ads = get_availability_domains()
    if not ads:
        raise RuntimeError("No availability domains returned for this tenancy")
    selected_image_id = discover_latest_image_id()
except Exception as e:
    print(f"Configuration discovery failed: {e}")
    exit(1)

print(
    "Provisioning request: "
    f"shape={shape}, ocpus={ocpus:g}, memory={memory_in_gbs:g}GB, "
    f"boot_volume={boot_volume_size_in_gbs}GB, public_ip={assign_public_ip}"
)

for i in range(1, total_attempts + 1):
    current_ad = ads[(i - 1) % len(ads)]
    print(f"[Attempt {i}/{total_attempts}] Requesting instance in {current_ad}...")
    
    try:
        exit_if_instance_exists()
        request = oci.core.models.LaunchInstanceDetails(
            display_name=display_name,
            compartment_id=compartment_id,
            availability_domain=current_ad,
            shape=shape,
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=ocpus,
                memory_in_gbs=memory_in_gbs
            ),
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=selected_image_id,
                boot_volume_size_in_gbs=boot_volume_size_in_gbs
            ),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=subnet_id,
                assign_public_ip=assign_public_ip,
                assign_private_dns_record=True,
                display_name=vnic_display_name
            ),
            metadata={
                "ssh_authorized_keys": str(public_ssh_key).strip()
            }
        )
        
        response = compute_client.launch_instance(request)
        if response.status == 200:
            print("SUCCESS! Authorized Server creation initialized perfectly.")
            exit(0)
            
    except oci.exceptions.ServiceError as e:
        if "Out of host capacity" in str(e) or e.status == 500:
            print(f"-> Capacity Unavailable. Resting {sleep_seconds} seconds...")
        else:
            print(f"-> API Error: {e.message}")
            
    if i < total_attempts:
        time.sleep(sleep_seconds)

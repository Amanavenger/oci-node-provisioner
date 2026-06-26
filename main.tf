variable "tenancy_ocid" {}
variable "user_ocid" {}
variable "fingerprint" {}
variable "private_key" {}
variable "region" {}
variable "subnet_id" {}
variable "image_id" {}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key      = var.private_key
  region           = var.region
}

resource "oci_core_instance" "generated_oci_core_instance" {
  availability_domain = "uufj:PHX-AD-1"
  compartment_id      = var.tenancy_ocid
  display_name        = "fx-alerts-backend"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    memory_in_gbs = 24
    ocpus         = 4
  }

  source_details {
    source_type             = "image"
    source_id               = var.image_id
    boot_volume_size_in_gbs = 100
    boot_volume_vpus_per_gb = 10
  }

  create_vnic_details {
    assign_ipv6ip             = false
    assign_private_dns_record = true
    assign_public_ip          = true
    display_name              = "forexalertsvnic"
    subnet_id                 = var.subnet_id
  }

  instance_options {
    are_legacy_imds_endpoints_disabled = true
  }

  metadata = {
    "ssh_authorized_keys" = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDRtlB75hyJ+ou+F78sqYg3W5KAfwLxzIvscbIai6MStl2vnJECjCv8gAclWGUvBmA8snVG+/uEceSjAKQUUGhwdOYOADlv4tJkZvm5/wjfUY27Sfi3QJiYeP2PO50nexu+sjHY7xJfmX2jM2eIBKjB+ttAm0ASrSgt9UbI4s9xZF7cG1Ws0EqnfSOlKQo7V7ZGMZTF938OxkHV/D3DSq5uSU5huRQ6DIZjjOQRHiqxthY2/ojeFJnXA5eYvdPLbrVCORVhNTL478LKCmJjIqiHocF7AGAnLqlQLSb6PthvPAjYWYIGKj9ANO/utf5PVsSyjuVuT8RZSInXjB75xZOX ssh-key-2026-06-26"
  }

  availability_config {
    recovery_action = "RESTORE_INSTANCE"
  }

  agent_config {
    is_management_disabled = false
    is_monitoring_disabled = false

    plugins_config {
      desired_state = "ENABLED"
      name          = "Vulnerability Scanning"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "OS Management Hub Agent"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Management Agent"
    }
    plugins_config {
      desired_state = "ENABLED"
      name          = "Custom Logs Monitoring"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Compute RDMA GPU Monitoring"
    }
    plugins_config {
      desired_state = "ENABLED"
      name          = "Compute Instance Monitoring"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Compute HPC RDMA Auto-Configuration"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Compute HPC RDMA Authentication"
    }
    plugins_config {
      desired_state = "ENABLED"
      name          = "Cloud Guard Workload Protection"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Block Volume Management"
    }
    plugins_config {
      desired_state = "DISABLED"
      name          = "Bastion"
    }
  }
}

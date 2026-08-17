# OCI Ampere A1 Node Provisioner

An automated, lightweight Python and GitHub Actions provisioner that repeatedly
requests an Oracle Cloud Infrastructure Compute instance until capacity becomes
available.

The defaults in this fork are aligned with the current OCI Always Free Ampere A1
limits:

- Shape: `VM.Standard.A1.Flex`
- OCPUs: `2`
- Memory: `12 GB`
- Boot volume: `50 GB`
- Image: latest compatible `Oracle Linux` platform image

Oracle currently documents Always Free Ampere A1 as the first 1,500 OCPU hours
and 9,000 GB hours per month, equivalent to 2 OCPUs and 12 GB RAM for Always
Free tenancies. Boot volumes count against the shared 200 GB Always Free block
volume pool, so the default boot volume is kept at 50 GB.

## Why Oracle Linux by Default?

Ubuntu is also Always Free eligible on Ampere A1. The original repository used a
hard-coded Ubuntu 24.04 image OCID for Phoenix, probably because Ubuntu is a
familiar default for many cloud scripts.

This fork defaults to Oracle Linux because it is the native OCI image family,
works well with Oracle's cloud-init and OCI tooling, and avoids region-specific
Ubuntu image OCIDs. You can still request Ubuntu by setting:

```text
OCI_IMAGE_OS=Canonical Ubuntu
OCI_IMAGE_OS_VERSION=24.04
```

If image discovery does not find the desired platform image in your region, set
`OCI_IMAGE_ID` explicitly.

## Required GitHub Secrets

Configure these secrets in your forked repository:

```text
OCI_USER_ID
OCI_PRIVATE_KEY
OCI_FINGERPRINT
OCI_TENANCY_ID
OCI_REGION
OCI_SUBNET_ID
OCI_PUBLIC_SSH_KEY
```

Optional secrets or variables:

```text
OCI_COMPARTMENT_ID              # defaults to OCI_TENANCY_ID
OCI_IMAGE_ID                    # overrides automatic image discovery
OCI_IMAGE_OS                    # defaults to Oracle Linux
OCI_IMAGE_OS_VERSION            # optional, for example 9 or 24.04
OCI_SHAPE                       # defaults to VM.Standard.A1.Flex
OCI_OCPUS                       # defaults to 2
OCI_MEMORY_IN_GBS               # defaults to 12
OCI_BOOT_VOLUME_SIZE_IN_GBS     # defaults to 50
OCI_AVAILABILITY_DOMAINS        # optional comma-separated AD names
OCI_DISPLAY_NAME                # defaults to always-free-a1-node
OCI_SKIP_EXISTING_INSTANCE_CHECK # defaults to false
OCI_ASSIGN_PUBLIC_IP            # defaults to true
OCI_TOTAL_ATTEMPTS              # defaults to 60
OCI_RETRY_SLEEP_SECONDS         # defaults to 180 (3 min) to avoid API rate limiting
OCI_ALLOW_PAID_LIMITS           # defaults to false
```

## Always Free Guard

For `VM.Standard.A1.Flex`, the script refuses to request more than `2` OCPUs or
`12 GB` RAM unless `OCI_ALLOW_PAID_LIMITS=true` is set. This is intentional:
requesting the old `4 OCPU / 24 GB` configuration is no longer a safe Always
Free default.

## Existing Instance Guard

Before every provisioning attempt, the script checks whether a non-terminated
Compute instance already exists in the configured compartment with
`OCI_DISPLAY_NAME` (default: `always-free-a1-node`). If it finds one, including
an instance that is still `PROVISIONING`, it exits successfully without creating
another server.

If you intentionally want multiple instances with the same display name, set
`OCI_SKIP_EXISTING_INSTANCE_CHECK=true` or use a different `OCI_DISPLAY_NAME`.

## Availability Domains

The original script cycled through hard-coded Phoenix AD names. This fork lists
the tenancy's availability domains dynamically, so it can run in your selected
home region. If you need a fixed order, set `OCI_AVAILABILITY_DOMAINS` to a
comma-separated list.

## Run Locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python provisioner/bot.py
```

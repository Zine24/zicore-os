"""Create Oracle Cloud VPS — v3 fixed pagination"""
import oci
import time
import base64

config = {
    "user": "ocid1.user.oc1..aaaaaaaags4ummap62c354nlckxipkzgzo37auzhrowhay22hqyb72qvvcla",
    "key_file": "/tmp/oci_key.pem",
    "fingerprint": "26:0d:ae:f0:4a:e8:bf:ea:19:56:04:59:c4:8d:60:80",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaabl4b7gjes7ox4rwnwhsy7322nky3gglktbgxbyix655bclwkm2ja",
    "region": "mx-queretaro-1",
}

with open("/tmp/oracle-mail.pub", "r") as f:
    ssh_pub = f.read().strip()

cloud_init = """#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl wget git python3 python3-pip ufw
curl -fsSL https://ollama.com/install.sh | sh
echo "Installing Ollama models..."
ollama pull gemma3:1b || true
ollama pull tinyllama || true
apt-get install -y -qq postfix dovecot-core dovecot-imapd dovecot-pop3d opendkim opendkim-tools certbot mariadb-server
ufw allow 25/tcp; ufw allow 587/tcp; ufw allow 465/tcp
ufw allow 143/tcp; ufw allow 993/tcp; ufw allow 110/tcp; ufw allow 995/tcp
ufw allow 80/tcp; ufw allow 443/tcp; ufw allow 22/tcp
ufw --force enable
echo "ZICORE_VPS_READY" > /tmp/zicore-setup-status.txt
"""

def create():
    identity = oci.identity.IdentityClient(config)
    compute = oci.core.ComputeClient(config)
    network = oci.core.VirtualNetworkClient(config)
    tenancy = config["tenancy"]
    
    ads = identity.list_availability_domains(tenancy)
    ad = ads.data[0].name
    print(f"AD: {ad}")
    
    # VCN
    vcns = network.list_vcns(tenancy)
    vcn = vcns.data[0] if vcns.data else network.create_vcn(oci.core.models.CreateVcnDetails(
        compartment_id=tenancy, cidr_blocks=["10.0.0.0/16"],
        display_name="zicore-mail-vcn", dns_label="zicore",
    )).data
    print(f"VCN: {vcn.display_name}")
    
    # Subnet
    subnets = network.list_subnets(tenancy, vcn_id=vcn.id)
    subnet = subnets.data[0] if subnets.data else network.create_subnet(oci.core.models.CreateSubnetDetails(
        compartment_id=tenancy, vcn_id=vcn.id, display_name="zicore-mail-subnet",
        dns_label="mail", cidr_block="10.0.0.0/24", prohibit_public_ip_on_vnic=False,
    )).data
    print(f"Subnet: {subnet.display_name}")
    
    # Find image
    print("Searching for Ubuntu ARM image...")
    image = None
    page = None
    
    for _ in range(5):  # max 5 pages
        resp = compute.list_images(tenancy, sort_by="TIMECREATED", sort_order="DESC", page=page)
        for img in resp.data:
            name = img.display_name.lower()
            if "ubuntu" in name and ("aarch64" in name or "arm" in name):
                image = img
                print(f"  Found: {img.display_name}")
                break
        if image:
            break
        page = resp.next_page
        if not page:
            break
    
    if not image:
        # Try Oracle Linux ARM
        page = None
        for _ in range(5):
            resp = compute.list_images(tenancy, sort_by="TIMECREATED", sort_order="DESC", page=page)
            for img in resp.data:
                name = img.display_name.lower()
                if ("oracle" in name or "ol" in name) and ("aarch64" in name or "arm" in name):
                    image = img
                    print(f"  Found: {img.display_name}")
                    break
            if image:
                break
            page = resp.next_page
            if not page:
                break
    
    if not image:
        print("ERROR: No ARM images found")
        # Print what's available
        resp = compute.list_images(tenancy, sort_by="TIMECREATED", sort_order="DESC")
        for img in resp.data[:15]:
            print(f"  {img.display_name}")
        return None
    
    print(f"Image: {image.display_name}")
    
    # Create instance
    print("Creating instance (2 OCPU, 12GB RAM, 100GB disk)...")
    instance = compute.launch_instance(oci.core.models.LaunchInstanceDetails(
        compartment_id=tenancy, display_name="zicore-mail", availability_domain=ad,
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=2, memory_in_gbs=12),
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            source_type="image", image_id=image.id, boot_volume_size_in_gbs=100,
        ),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=subnet.id, display_name="zicore-mail-vnic",
            assign_public_ip=True, hostname_label="zicore-mail",
        ),
        metadata={
            "ssh_authorized_keys": ssh_pub,
            "user_data": base64.b64encode(cloud_init.encode()).decode(),
        },
    )).data
    
    print(f"Instance: {instance.id}")
    
    # Wait for RUNNING
    print("Waiting for RUNNING state (2-5 min)...")
    for i in range(90):
        time.sleep(10)
        inst = compute.get_instance(instance.id).data
        state = inst.lifecycle_state
        print(f"  [{i*10:3d}s] {state}")
        if state == "RUNNING":
            break
        if state in ("TERMINED", "ERROR"):
            return None
    
    # Get public IP
    time.sleep(5)
    vnic_atts = compute.list_vnic_attachments(tenancy, instance_id=instance.id)
    if vnic_atts.data:
        vnic = network.get_vnic(vnic_atts.data[0].vnic_id).data
        return {"id": instance.id, "ip": vnic.public_ip, "name": instance.display_name}
    return {"id": instance.id}

if __name__ == "__main__":
    print("=" * 50)
    print("  ZICORE VPS — Oracle Cloud Free Tier")
    print("  Mail + Ollama")
    print("=" * 50)
    result = create()
    if result:
        ip = result.get("ip", "pending")
        print()
        print("=" * 50)
        print("  VPS CREATED!")
        print("=" * 50)
        print(f"  IP: {ip}")
        print(f"  SSH: ssh -i C:\\Users\\zinem\\.ssh\\oracle-mail ubuntu@{ip}")
        print(f"  Shape: VM.Standard.A1.Flex")
        print(f"  Specs: 2 OCPU ARM, 12GB RAM, 100GB disk")
        print(f"  Cost: FREE forever")
        print()
        print("  Cloud-init is installing:")
        print("  - Ollama + gemma3:1b + tinyllama")
        print("  - Postfix + Dovecot + OpenDKIM + MariaDB")
        print("  - UFW firewall")
        print()
        print("  Next:")
        print("  1. Wait 3-5 min for cloud-init")
        print("  2. SSH in and verify: cat /tmp/zicore-setup-status.txt")
        print("  3. Configure Postfix/Dovecot properly")
        print("  4. Request port 25 exemption from Oracle")
        print("  5. Update Cloudflare DNS")
    else:
        print("\nFAILED")

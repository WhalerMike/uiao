# grid.tf
# ---------------------------------------------------------------------------
# vNIOS GRID path (deployment_model = "grid").
# Boundary-clean: the Grid control plane stays INSIDE the account/ATO boundary.
#
# Creates, gated on local.is_grid:
#   * aws_network_interface  — TWO ENIs per member: ENI0=MGMT, ENI1=LAN1 (contract
#                              §4 / ch.4). Source/dest check off by default so an
#                              anycast/HA service IP can be advertised (ch.9).
#   * aws_instance           — member_count vNIOS members, spread across AZs, from
#                              the Marketplace AMI (vnios_ami_id). First-boot config
#                              via user-data: temp license + admin password +
#                              grid-join params, pulled from Secrets Manager/SSM.
#
# All resources here have count = 0 when deployment_model = "universal_ddi".
#
# DO NOT hard-code the AMI ID or instance type — both come from variables
# (vnios_ami_id / vnios_instance_type). Discover the AMI with:
#   aws ec2 describe-images --owners aws-marketplace \
#     --filters 'Name=name,Values=*Infoblox*NIOS*' --query 'Images[].ImageId'
# You must subscribe to the Infoblox NIOS listing in AWS Marketplace first.
# ---------------------------------------------------------------------------

locals {
  grid_member_count = local.is_grid ? var.member_count : 0

  # vNIOS first-boot user-data ("#infoblox-config" YAML), passed as user_data and
  # consumed on first boot to install the temp license, set the admin password,
  # and (member) join the Grid to the Grid Master over 1194/udp + 2114/tcp.
  # Secrets come from Secrets Manager/SSM (main.tf) and are NEVER committed. The
  # exact schema is NIOS-version dependent — verify against the "vNIOS for AWS"
  # install guide for your build before relying on it.
  grid_user_data = local.is_grid ? {
    for i in local.member_indexes : i => <<-EOT
      #infoblox-config

      temp_license: ${local.temp_license}
      default_admin_password: ${local.admin_password}
      remote_console_enabled: y

      # Grid-join parameters. For the usual AWS pattern the Grid Master lives
      # on-prem (grid_master_vip); the AWS members join as Grid members. If
      # grid_master_vip is null the first member is treated as the Grid Master
      # (lab/greenfield only).
      %{if var.grid_master_vip != null~}
      gridmaster:
        ip_addr: ${var.grid_master_vip}
        grid_name: ${var.grid_name}
        shared_secret: ${local.grid_shared_secret}
      %{else~}
      # This member (index ${i}) initializes the Grid as Grid Master:
      gridmaster:
        grid_name: ${var.grid_name}
        shared_secret: ${local.grid_shared_secret}
      %{endif~}
    EOT
  } : {}
}

# --- MGMT ENIs (ENI0) --------------------------------------------------
resource "aws_network_interface" "grid_mgmt" {
  count             = local.grid_member_count
  subnet_id         = aws_subnet.ddi[local.member_zone_for[count.index]].id
  security_groups   = [aws_security_group.ddi.id]
  source_dest_check = true # MGMT ENI carries only its own address
  description       = "${local.member_base_name}-${local.member_label[count.index]} MGMT"
  tags              = merge(local.tags, { Name = "${local.member_base_name}-${local.member_label[count.index]}-mgmt" })
}

# --- LAN1 ENIs (ENI1) — DNS/DHCP data plane ---------------------------
# source_dest_check disabled (default) so an anycast/HA VIP not owned by this ENI
# can still be advertised through it (ch.9). Its private_ip is a dns_server_ips.
resource "aws_network_interface" "grid_lan1" {
  count             = local.grid_member_count
  subnet_id         = aws_subnet.ddi[local.member_zone_for[count.index]].id
  security_groups   = [aws_security_group.ddi.id]
  source_dest_check = var.enable_source_dest_check
  description       = "${local.member_base_name}-${local.member_label[count.index]} LAN1"
  tags              = merge(local.tags, { Name = "${local.member_base_name}-${local.member_label[count.index]}-lan1" })
}

# --- vNIOS member instances -------------------------------------------
resource "aws_instance" "grid" {
  count         = local.grid_member_count
  ami           = var.vnios_ami_id
  instance_type = var.vnios_instance_type
  key_name      = var.ssh_key_name

  # Discovery via instance profile (single-account mode) if selected; null in the
  # cross-account iam_role mode (see discovery.tf).
  iam_instance_profile = local.member_instance_profile_name

  # ENI0 = MGMT, ENI1 = LAN1 (contract §4 / ch.4).
  network_interface {
    network_interface_id = aws_network_interface.grid_mgmt[count.index].id
    device_index         = 0
  }
  network_interface {
    network_interface_id = aws_network_interface.grid_lan1[count.index].id
    device_index         = 1
  }

  # First-boot vNIOS configuration (temp_license + admin pw + grid join).
  user_data_base64 = base64encode(local.grid_user_data[count.index])

  # Encrypted root + a data volume for the NIOS DB (size per member role; ch.4/§9).
  root_block_device {
    encrypted   = true # EBS encryption at rest (KMS); SC-28
    volume_type = "gp3"
  }
  ebs_block_device {
    device_name = "/dev/sdb"
    encrypted   = true
    volume_type = "gp3"
    volume_size = 250 # NIOS DB / reporting — size to your query + lease volume
  }

  tags = merge(local.tags, {
    Name = "${local.member_base_name}-${local.member_label[count.index]}"
    role = "grid-member"
  })

  lifecycle {
    # user_data changes would force replacement; ignore post-bootstrap so a
    # secret rotation in the store doesn't silently recreate running members.
    # Remove this if you WANT re-bootstrap on user-data change.
    ignore_changes = [user_data_base64]
  }

  depends_on = [terraform_data.boundary_guard]
}

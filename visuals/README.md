# UIAO Vibrant Visualization Canon

This directory contains high-fidelity, presentation-grade architectural visualizations. These assets supplement the technical **PlantUML** diagrams in `generation-inputs/diagrams.yaml` for use in leadership briefings and FedRAMP authorized evidence.

> **Geographic Constraint:** All map-based imagery in this repository MUST depict only the United States and its territories (CONUS, Alaska, Hawaii, Puerto Rico, Guam, US Virgin Islands, and minor outlying islands). World maps are prohibited in a US Federal Government context.

## AI Generation Workflow

Images are generated using a **Parallel AI Orchestration** workflow:

1. **Blueprinting:** Gemini (Technical Foreman) defines architectural requirements.
2. **Rendering:** Perplexity/Gencraft (Creative Agent) generates the high-fidelity asset.
3. **Commit:** Assets are stored here and referenced in `templates/`.

---

## Visualization Inventory & Prompts

### V1: Identity-to-IP Mapping

- **File:** `uiao-vibrant-u-plus-a-mapping.png`
- **Pillar:** **U** (Identity) + **A** (Addressing)
- **Gencraft Prompt:**
  > High-fidelity 3D infographic, "Cyber-Neon" aesthetic. An image showing a FIDO2
  > Security Key glowing with a holographic Entra ID logo. A "Digital Thread" pulls
  > from the key into an Infoblox BloxOne cloud icon. Inside the cloud, a gear icon
  > labeled "Identity-to-IP Hash" converts the name "User_Alpha" into the IPv6
  > address `2001:db8:85a3::8a2e:370:7334`.

### V2: Cisco-Microsoft INR Fabric (US Federal Edition)

- **File:** `telemetry_fabric_mesh.png`
- **Pillar:** **O** (Overlay)
- **Geographic Constraint:** US-only map. No world maps.
- **Gencraft Prompt:**
  > High-fidelity 3D infographic, "Command Center" aesthetic with vibrant blue and
  > gold highlights. The visual is centered on a detailed map of the United States
  > of America and its territories (including Alaska, Hawaii, Puerto Rico, Guam, and
  > minor outlying islands). Stylized "Federal Data Center" icons are located at
  > domestic hubs (e.g., DC Metro, Denver, Dallas, Seattle, Honolulu, San Juan).
  > Silver "Overlay Tunnels" (Cisco Catalyst SD-WAN) create a domestic mesh network
  > connecting these sites. Glowing blue beacons sit atop these domestic tunnels
  > labeled "Microsoft INR Telemetry." These beacons send "Pulses" (symbolizing
  > Jitter/Latency metrics) to a centralized dashboard labeled "ServiceNow
  > Governance Hub." The overall aesthetic is clean, high-tech, and explicitly
  > limited to US sovereign territory.

### V3: 20x Governance Loop

- **File:** `atlas_vision_outcome.png`
- **Pillar:** **Governance**
- **Gencraft Prompt:**
  > A high-tech "Mission Control" center. In the center is a glowing holographic
  > orb labeled "ServiceNow AI Hub." Vibrant data streams (neon blue and gold) flow
  > into the orb from icons representing "Cisco SD-WAN Telemetry" and "GitHub
  > ScubaGear." The orb pushes a "Verified Compliance" signal to a dashboard.

### V4: Modernization Atlas

- **File:** `uiao-vibrant-modernization-atlas.png`
- **Pillar:** **Strategy**
- **Gencraft Prompt:**
  > A split-screen infographic. Left side (Legacy): Dark, cluttered network diagram
  > with red brick walls labeled "TIC 2.2 Perimeters." Right side (Modern): Bright,
  > open architectural map where a single "Identity Plane" (golden glowing beam)
  > allows seamless access to cloud applications.

### V5: Cryptographic Trust Chain

- **File:** `uiao-vibrant-cryptographic-trust-chain.png`
- **Pillar:** **Security (SC-8)**
- **Gencraft Prompt:**
  > A 3D cryptographic chain starting with a gold "Federal Root CA" seal.
  > Translucent "Trust Links" extend to a User Certificate and a Device
  > Certificate. Both certificates enter a Cisco Catalyst Edge gateway, which
  > lights up green with the text "mTLS Secured."

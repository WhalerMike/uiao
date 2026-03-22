# Vendor Overlays

UIAO uses a vendor-neutral core with optional technology overlays. The core data files
(`data/control-planes.yml`, etc.) use generic terms like "Identity Provider" and
"IPAM Platform". Overlays restore vendor-specific product names and configurations
when a particular technology stack is active.

## How It Works

1. `data/overlay-config.yml` lists which vendor overlays are active.
2. `scripts/generate_docs.py` loads core data first, then merges each active overlay on top.
3. When **all** overlays are active the generated output is identical to the original
   vendor-specific docs — full backward compatibility is preserved.
4. When only a subset of overlays are active, generic placeholder names appear for the
   omitted vendors, making the framework reusable for agencies with different tech stacks.

## Adding Your Own Overlay

1. Create a directory under `data/overlays/<vendor-name>/` (e.g., `data/overlays/okta/`).
2. Add one or more YAML files with vendor-specific control plane details using the format:

   ```yaml
   overlay_meta:
     vendor: okta
     product: workforce-identity
     description: "Okta Workforce Identity Cloud overlay"

   control_plane_overrides:
     - id: identity
       subtitle: "Okta Workforce Identity Cloud"
       components:
         - name: "Okta Identity Engine"
           role: "Primary Identity Provider"
           capabilities:
             - Adaptive MFA
             - Universal Directory
             - Lifecycle Management

   fedramp_alignment_overrides:
     - plane_id: identity
       evidence_source: "Okta System Log - authentication and policy events"
   ```

3. Update `data/overlay-config.yml` to include your vendor name:

   ```yaml
   active_overlays:
     - okta
   ```

4. Push — the pipeline will merge your overlay into generated docs and OSCAL artifacts.

## Overlay File Keys

| Key | Description |
|-----|-------------|
| `overlay_meta` | Metadata (vendor, product, description). Not merged into context. |
| `control_plane_overrides` | List of control plane patches matched by `id`. Each entry shallow-merges into the matching plane. |
| `fedramp_alignment_overrides` | List of FedRAMP alignment patches matched by `plane_id`. |

## Default Overlays

| Directory | Products Covered | Control Planes |
|-----------|-----------------|----------------|
| `microsoft/entra-id.yml` | Entra ID, Intune, Defender | Identity, Endpoint |
| `microsoft/sentinel.yml` | Sentinel, Splunk | Telemetry |
| `cisco/sd-wan.yml` | Catalyst SD-WAN (Viptela/vManage) | Network |
| `infoblox/ddi.yml` | BloxOne DDI | Addressing |

## Removing a Vendor

To replace a vendor (e.g., swap Cisco SD-WAN for a different SD-WAN platform):

1. Remove `cisco` from `active_overlays` in `data/overlay-config.yml`.
2. The Network control plane will show generic names ("SD-WAN Platform", etc.).
3. Create `data/overlays/<your-vendor>/sd-wan.yml` with your vendor's specifics.
4. Add your vendor name to `active_overlays`.

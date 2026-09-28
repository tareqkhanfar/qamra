# Runbook: the self-hosted GPU server (Addendum 4 §8)

Prepared, not active. Qamra Classic template edits run on fal's API. This runbook covers moving them to our own GPU server running ComfyUI, if the admin's cost card shows that it pays off. Magic books stay on the API providers.

## When to switch

- Open **Admin → Cost & conversion → Self-hosted GPU**. It compares the Classic image spend on the API over the last 30 days with the GPU server's monthly cost (a setting).
- Switch only when the API spend is clearly higher than the server's cost plus the time to run it.
- A model must be approved first: its license is recorded in `docs/licenses.md` and Tareq has approved it. Today the only candidate is FLUX.2 [klein] 4B (Apache 2.0).

## The server

- **GPU:** one data-center or workstation GPU with 24 GB of memory (NVIDIA L4, A10 or RTX 4090 class) is plenty for a 4B image-edit model. Check the model card for its exact needs.
- **Where:** a monthly GPU rental, e.g. RunPod, Vast.ai, Lambda, Hetzner GPU servers or Paperspace. Compare the monthly price with the admin card, and choose a region close to our VPS.
- **Software:** ComfyUI in Docker, pinned to a release. Install only the nodes the approved workflow needs, and no extension managers.
- **Model weights:** download them only from the model's official repository after approval, and record the file hash here.

## Privacy and security (child photos pass through this server)

- **Private network only.** Either connect the VPS and the GPU server with WireGuard or Tailscale, or allowlist only the VPS's IP in the firewall. ComfyUI is never exposed to the internet.
- **Token check.** Put Nginx in front of ComfyUI and require the bearer token from the admin setting «رمز الوصول لخادم الرسم» (`self_hosted_token`). Requests without it get 401.
- **Nothing kept.**
  - Mount ComfyUI's `input/`, `output/` and `temp/` folders on tmpfs.
  - Run a cleanup every 10 minutes that deletes files older than 15 minutes.
  - Qamra already deletes each job from ComfyUI's history after fetching the image.
- **No image data in logs.** Keep ComfyUI's logs at warning level, and never add request logging that records bodies.

## Deploy

1. Rent the server and install Docker and the NVIDIA container toolkit.
2. Start ComfyUI with the folders on tmpfs, behind Nginx with the token check, on the private network only.
3. Build the workflow in ComfyUI and save it with **Save (API Format)** as `packages/ai/src/qamra_ai/image/comfy_workflows/<name>.json`. Use the tokens from that folder's README: `{{prompt}}`, `{{seed}}`, `{{width}}`, `{{height}}` and `{{image_1}}`….
4. After license approval, add `<name>` to `APPROVED_WORKFLOWS` in `comfy.py` with the model and its license, in a reviewed commit.
5. In **Admin → Settings → Self-hosted GPU**, enter the server URL, the token and the workflow name. The cost card should show «يعمل» with the GPU and its free memory.
6. Run the Classic cost proof (5 synthetic children) with the self-hosted provider. Compare likeness, seams and text with fal, and time a book.
7. Only then set «مزوّد رسم «قمرة كلاسيك»» to the self-hosted server.

## Health and fallback

- The admin card calls ComfyUI's `/system_stats` through the token check and shows up or down, the GPUs and their free memory.
- **Fallback is automatic.** After 2 failed attempts (the server is down, times out, or rejects the workflow), each image goes to fal, and the switch is logged on the book. A server outage slows nothing down beyond those retries.
- Add an external uptime check on the private health URL, and alert when it has been down for more than 10 minutes.

## Roll back

Set «مزوّد رسم «قمرة كلاسيك»» back to fal. Nothing else changes; the server can then be stopped.

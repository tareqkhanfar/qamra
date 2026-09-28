# Self-hosted ComfyUI workflows

A workflow is a ComfyUI graph in API format (ComfyUI → *Save (API Format)*), saved here as `<name>.json`. `ComfyImageProvider` fills these tokens before queueing it:

| Token | Value |
|---|---|
| `{{prompt}}` | the image prompt |
| `{{seed}}` | the request's seed (a number) |
| `{{width}}`, `{{height}}` | the output size in pixels, from the aspect and resolution |
| `{{image_1}}`, `{{image_2}}`, … | the uploaded reference images, in order (use them in `LoadImage` nodes) |

A string that is exactly a token becomes the value itself, so numbers stay numbers.

**Licensing gate (Addendum 4 §8):** a workflow runs only when its name is in `APPROVED_WORKFLOWS` in `comfy.py`. Add it there only after its model's license is recorded in `docs/licenses.md` and Tareq has approved it. There is none yet. The only candidate is FLUX.2 [klein] 4B (Apache 2.0). No InsightFace, and no weights under a non-commercial license (e.g. klein 9B).

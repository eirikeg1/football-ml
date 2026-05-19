# User nudges

Append messages here to inject mid-search guidance without halting `/goal`.
The agent re-reads this file at the start of every iteration and treats new
content as the **highest-priority signal**.

Examples of useful nudges:

- "stop trying bigger d_model, try focal loss instead"
- "skip seeds, just sweep dropout 0.0/0.1/0.2/0.3"
- "force-try this exact config: `<inline YAML or path>`"
- "the GPU is going to be busy for the next hour — pause"

Format your nudges with a date so the agent can tell what's new:

## YYYY-MM-DD HH:MM

<your nudge here>

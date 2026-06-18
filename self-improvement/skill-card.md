## Description: <br>
Provides an agent memory and self-learning workflow that logs task history, extracts lessons and user preferences, verifies behavior changes, and proposes reusable improvements. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[brucetangc](https://clawhub.ai/user/brucetangc) <br>

### License/Terms of Use: <br>
MIT-0 <br>


## Use Case: <br>
Developers and agent operators use this skill to give an agent persistent memory for task history, corrections, preferences, and recurring lessons. It is intended for agents that should review past sessions, track improvement hypotheses, and surface proposed behavior or skill changes for review. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Conversation-derived memory may store sensitive personal data, secrets, or unwanted preferences over time. <br>
Mitigation: Review or disable automatic logging before use, avoid sharing secrets while enabled, and periodically inspect memory files and preference records. <br>
Risk: The learning cycle can change files that influence future agent behavior, including memory, tool notes, generated skill drafts, and hook context. <br>
Mitigation: Require human review for promoted patterns and core-file changes, inspect diffs before accepting proposed behavior changes, and disable hook or scheduled cycle behavior until trusted. <br>
Risk: Sync import and export can move memory data between environments or restore files from an archive. <br>
Mitigation: Use backups, validate archive provenance before import, inspect archive contents, and avoid overwrite mode unless the target workspace is prepared. <br>


## Reference(s): <br>
- [ClawHub skill release](https://clawhub.ai/brucetangc/self-improvement-llm) <br>
- [Reflection Frameworks](artifact/references/reflection_frameworks.md) <br>
- [pskoett/self-improving-agent](https://clawhub.ai/pskoett/self-improving-agent) <br>
- [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) <br>
- [Reflexion paper](https://arxiv.org/abs/2303.11366) <br>


## Skill Output: <br>
**Output Type(s):** [text, markdown, code, shell commands, configuration, guidance] <br>
**Output Format:** [Markdown guidance with Python and shell command examples; supporting scripts may create JSON, Markdown, text, and zip files in the agent workspace.] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [May write or update memory files, learning trail JSON, generated skill drafts, hook context, and backup archives when run by an agent.] <br>

## Skill Version(s): <br>
2.2.2 (source: server release evidence) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>

# Learning and implementation review: 20 October 2026

This batch adds two distinct learning resources and the ORBIT implementation,
approves the retained Intact paper annotation, and records a source-bound hold
for BizBench. The original paper bibliography remains intact. A separate
AI-assisted source review checked each decision; no course, code, model or
benchmark was executed.

| Resource | Reading basis | Boundary retained |
| --- | --- | --- |
| [Building AI Browser Agents](https://www.deeplearning.ai/courses/building-ai-browser-agents) | Public syllabus and two complete lesson transcripts. | The review does not cover the entire course, video frames, hosted notebooks or current service access. |
| [smolagents browser tutorial](https://huggingface.co/docs/smolagents/v1.26.0/examples/web_browser) | Version 1.26.0 and its commit-pinned Markdown; eight example blocks match statically. | Current runtime compatibility was not tested. Explicit document-license applicability was not established, so reuse terms remain unknown. |
| [ORBIT framework](https://github.com/wlanderson0/orbit/tree/588b3035f92450ec4f0496bb8b629daa205e84c7) | Pinned documentation, browser/desktop tools, selected scoring code, LICENSE and NOTICE. | Current implementation and paper results are separate snapshots. Scenario qualification and component license limits remain explicit. |
| [Intact](https://arxiv.org/html/2610.22697v1) | Browser instrumentation, architecture, evaluation and limitations. | Implemented browser machinery supports scope; planning assessments do not establish executed-task or general security success. |
| [BizBench](https://arxiv.org/html/2610.20424v1) | Business-state reconstruction, tool execution and customer-simulation methods. | The inspected protocol does not establish GUI/browser or concrete OS/terminal interaction. Metadata remains available pending scope evidence. |

Courses and tutorials are indexed once, separately from their parent software.
Individual lessons and version pages are not additional resources. Their
category, topic and platform views include the same source records as the
catalog and RAG exports. Unknown document terms are distinct from a project's
code license.

The ORBIT code record has one source-backed `documented_by` connection to the
existing paper. Its top-level Apache-2.0 declaration is scoped to Orbit-original
code; third-party components and external datasets retain separate terms.

The preceding recovery scan added six bibliographic records and five GitHub
candidate observations. Those remain distinct from this source-reviewed batch.
The scan honestly retains incomplete GitHub coverage; a successful quality
gate does not mean every discovery query completed.

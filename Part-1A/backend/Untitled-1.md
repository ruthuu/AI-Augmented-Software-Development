 
AI Augmented SDLC S1_2026 Akshaya Ganesan 
1 
 
AI Augmented SDLC -SEZG534 
 
ASSIGNMENT 1-SPEC-DRIVEN DEVELOPMENT & HARNESS 
ENGINEERING 
From specification-controlled coding agents to deterministic and non-deterministic validation 
Course AI-Augmented Software Development Life Cycle (SE* ZG534) 
Total Marks 25 
Part 1A SDD & Harnessing for Deterministic Applications — 10 Marks 
Part 1B SDD & Harnessing for Non-Deterministic AI Applications — 10 Marks 
Part 2 Reflection questions – 5 marks 
Mode Individual and submitted to LMS 
Submission Deadline November 15th 2026 
 
1. Assignment Objective 
Develop two small applications using the GitHub Spec Kit Spec-Driven Development workflow and demonstrate how 
a harness can constrain, validate and provide feedback on AI-generated software.  
I. Part 1A focuses on deterministic software behaviour.  
II. Part 1B extends the same approach to an application containing non-deterministic AI behavior. 
III. Part 2 Reflection questions 
 
• Apply Spec Kit artifacts as the authoritative basis for implementation. 
• Use an AI coding agent to implement approved specifications. 
• Create validation controls independent of the generated implementation. 
• Capture failures as structured evidence and use them to drive corrective generation. 
• Make a final human acceptance decision after automated verification. 
2. Required SDD Flow 
Both parts must follow the GitHub Spec Kit workflow practiced in Lab Sheet 1. Do not reproduce the detailed Lab 
Sheet 1 procedure in the submission. Use the lab as the operational reference and preserve the generated/reviewed 
artifacts as evidence. 
Problem statement 
   ↓ 
/speckit.constitution 
   ↓ 
/speckit.specify 
   ↓ 
 
AI Augmented SDLC S1_2026 Akshaya Ganesan 
2 
/speckit.clarify 
   ↓ 
/speckit.plan 
   ↓ 
/speckit.tasks 
   ↓ 
/speckit.analyze (where applicable) 
   ↓ 
/speckit.implement 
   ↓ 
Harness validation → feedback/repair → revalidation → human decision 
Expectation: Specifications and acceptance criteria must be established before implementation. If an ambiguity is 
discovered later, update the appropriate upstream Spec Kit artifact and preserve the change history.  
3. PART 1A — SDD & HARNESSING FOR DETERMINISTIC APPLICATIONS 
Marks: 10 
3.1 Objective 
Use GitHub Spec Kit to specify and implement a deterministic application, then engineer a local harness that 
independently checks code quality, security and exact functional behaviour. Harness failures must become 
actionable feedback for the coding agent. 
3.2 Select One Problem Statement 
Sample A — Smart Todo & Task CLI/API: Task CRUD, tag filtering, JSON persistence, priority sorting and task-status 
transitions. 
Sample B — Tiered Rate Limiter Microservice: Token-bucket or equivalent algorithm, in-memory adapter, 
configurable tiers/thresholds and appropriate HTTP rate-limit behaviour. 
An equivalent deterministic problem must be selected, provided its scope supports meaningful specification, 
testing and harness controls. 
3.3 SDD Requirement 
Follow the Spec Kit flow in Section 2 and refer to Lab Sheet 1 for detailed execution. Preserve the constitution, feature 
specification, clarifications, technical plan, tasks and implementation evidence generated during the workflow. 
3.4 Feedforward Expectations 
• The constitution/specification must state measurable engineering constraints relevant to the chosen application. 
• Acceptance criteria must be specific enough to derive binary tests. 
• The coding agent must receive the approved specification context before implementation. 
• The coding agent must not be allowed to weaken acceptance criteria, remove failing tests, expose secrets or 
bypass mandatory harness checks. 
• Preserve the first generated implementation before harness-driven correction. 
 
AI Augmented SDLC S1_2026 Akshaya Ganesan 
3 
3.5 Deterministic Harness Expectations 
• Syntax & Lint Guard: run a language-appropriate static check such as ESLint or Ruff and expose an 
unambiguous pass/fail result. 
• Security / SAST Guard: run a language-appropriate static security check for issues relevant to the chosen 
implementation. 
• Unit & Contract Tests: derive exact assertions from approved requirements and acceptance criteria. Mandatory 
deterministic tests must pass before acceptance. 
• Feedback Capture: record relevant stdout/stderr, failed test or rule, expected behaviour and observed behaviour. 
• Self-Healing: feed the failure evidence to the coding agent, repair the implementation, and rerun the same 
harness gates. 
• Human Review: record a final ACCEPT/REJECT decision after the automated harness result. 
Do not: Do not change the specification, delete difficult tests, lower assertions, disable security/lint checks, or 
manually edit the recorded harness result merely to obtain PASS. Any legitimate specification change must be 
made through the SDD artifacts and documented. 
3.6 Minimum Evidence Expected 
Part-1A/ 
├── Spec Kit project and generated/reviewed specification artifacts 
├── src/ 
├── tests/ 
├── .harness/ 
│   ├── lint/security/test runner scripts or configuration 
│   └── harness runner 
└── evidence/ 
    ├── initial-generation/ 
    ├── final-generation/ 
    ├── harness results 
    └── harness-log.md 
The exact folder names may vary with technology and Spec Kit output. The evidence must nevertheless make the 
specification-to-implementation-to-validation path easy to inspect. 
3.7 What harness-log.md Must Show 
• Initial coding-agent generation and the relevant task/specification context. 
• Each harness execution and its outcome. 
• At least one genuine failure-and-repair cycle if a failure occurs during development. Do not manufacture a failure 
solely for submission. 
• Failure evidence supplied back to the coding agent. 
• What changed after repair and whether the same checks passed on re-execution. 
• Final human ACCEPT/REJECT decision, known limitations and justification. 
3.8 Marking Scheme — Part 1A 
Assessment Criterion Marks 
GitHub Spec Kit SDD artifacts and quality of 
specification/acceptance criteria 
3.0 
2.0 
4 
Traceability from specification/tasks to AI-assisted 
implementation 
harness controls, Deterministic unit/contract tests 
derived from specification 
3.0 
Harness log, evidence quality and final human review 
2.0 
Total 
10.0 
4. PART 1B — SDD & HARNESSING FOR NON-DETERMINISTIC AI 
APPLICATIONS 
Marks: 10 
4.1 Objective 
Extend the same GitHub Spec Kit workflow to an application containing non-deterministic AI behaviour. The 
specification must define acceptable behavioural boundaries, and a single evaluation harness must determine 
whether generated outputs satisfy structural, invariant/property and semantic/quality expectations. 
4.2 Select One AI-Augmented Problem Statement 
Sample A — Natural-Language Reminder Agent: Parse unstructured reminder requests into structured reminders, 
interpret date/time information, support reschedule/snooze intent and request clarification when mandatory 
information is missing. 
Sample B — Semantic Code Review & Refactoring Assistant: Analyze supplied code or diffs, generate structured 
findings, identify selected issue categories and provide refactoring suggestions with rationale. 
An equivalent AI application may be selected if it contains meaningful non-deterministic behaviour that can be 
evaluated against specified boundaries. 
4.3 SDD Requirement 
Follow the same Spec Kit flow in Section 2 and refer to Lab Sheet 1 for detailed execution. For Part 1B, the 
specification must make non-deterministic behaviour testable instead of merely describing the desired AI feature. 
4.4 Additional Specification Expectations for Part 1B 
• Output Schema Contract: define the fields, types and allowed values that must remain stable despite variation in 
model wording. 
• Structural Invariants: define conditions that must always hold, such as valid schema, required fields, supported 
intents and safe tool-call arguments. 
• Behavioural Properties: define properties that can be checked without relying on exact generated text. 
• Safety/Guardrail Rules: define prohibited behaviours and conditions that require refusal, clarification or blocking 
of an action. 
• Evaluation Threshold: define the acceptance threshold before final evaluation and explain how the score is 
calculated. 
• Traceability: evaluation cases and checks must map back to requirements, invariants or acceptance criteria in 
the specification. 
AI Augmented SDLC 
S1_2026 
Akshaya Ganesan 
 
AI Augmented SDLC S1_2026 Akshaya Ganesan 
5 
Example: For a reminder agent, wording may vary, but the harness can require valid schema, a supported intent, 
safe/valid time representation, clarification when mandatory information is missing, and semantic fidelity to the 
requested task. 
4.5 Evaluation Dataset 
Create evals/dataset.json containing at least 15 meaningful evaluation cases. The dataset should exercise normal 
behaviour and failure boundaries rather than 15 minor variations of the same prompt. 
• Normal/representative inputs. 
• Boundary cases. 
• Ambiguous or underspecified inputs. 
• Missing mandatory information. 
• Malformed inputs. 
• Relevant adversarial or guardrail cases. 
Each test case must define ground truth, deterministic expected properties, or an explicit evaluation rubric sufficient 
to decide whether the outcome is acceptable. 
4.6 Single Non-Deterministic Harness Pipeline 
Evaluation dataset 
      ↓ 
AI application / model call 
      ↓ 
Generated output 
      ↓ 
Schema validation 
      ↓ 
Invariant & property checks 
      ↓ 
Semantic / quality evaluation 
      ↓ 
Aggregate score against specified threshold 
   ┌────────────┴────────────┐ 
 PASS                     FAIL 
   ↓                         ↓ 
Human review        Structured failure evidence 
                             ↓ 
                        Coding agent 
                             ↓ 
                           Repair 
                             ↓ 
                         Re-evaluate 
6 
4.7 Harness Validation Expectations 
Layer 1 — Structural validation: Validate JSON/schema conformance, required properties, data types, 
enumerations and other machine-checkable output constraints. 
Layer 2 — Property/invariant validation: Check deterministic behavioural rules derived from the specification, such 
as required clarification, date/range constraints, source-evidence requirements or tool-call restrictions. 
Layer 3 — Semantic/quality evaluation: Evaluate criteria that cannot be reduced to exact equality using an 
appropriate task-specific heuristic, ground-truth comparison, precision/recall, semantic scoring, rubric or LLM-as-a
Judge. If an LLM judge is used, it must not replace independent structural and invariant checks. 
Aggregate decision: Produce interpretable metrics and a final PASS/FAIL decision against the threshold declared in 
the specification. 
4.8 Harness-Driven Repair 
A failed evaluation must produce structured, inspectable evidence. Feed the relevant case, generated output, failed 
requirement/property and evaluation result back to the coding agent. The repair may modify application code, 
prompt construction, system instructions, parsers, validators or guardrails as appropriate to the identified failure. 
Do not: Do not remove difficult benchmark cases, change expected results without a legitimate specification 
revision, lower the previously declared threshold, or disable guardrails simply to obtain PASS. 
4.9 Minimum Evidence Expected 
Part-1B/ 
├── Spec Kit project and generated/reviewed specification artifacts 
├── src/ 
├── prompts/ (if used) 
├── tests/ 
├── evals/ 
│   
└── dataset.json   
# minimum 15 cases 
├── .harness/ 
│   
│   
├── schema/property/quality evaluators 
└── evaluation runner 
└── evidence/ 
├── initial-generation/ 
├── final-generation/ 
├── eval-results.json 
└── harness-log.md 
4.10 What harness-log.md Must Show 
• Model/configuration information necessary to interpret the evaluation. Do not include secrets. 
• Evaluation threshold and scoring method as specified before final evaluation. 
• Harness results, including structural, property/invariant and semantic/quality outcomes. 
• Meaningful failures encountered and the evidence supplied to the coding agent. Do not invent failures that did 
not occur. 
• Repair made to the application/prompt/parser/guardrail and the resulting re-evaluation outcome. 
• Final human ACCEPT/REJECT decision, known limitations and residual risks. 
S1_2026 
AI Augmented SDLC 
Akshaya Ganesan 
 
AI Augmented SDLC S1_2026 Akshaya Ganesan 
7 
4.11 Marking Scheme — Part 1B 
Assessment Criterion Marks 
GitHub Spec Kit SDD artifacts and specification of non
deterministic behaviour 
2 
Schema contracts, invariants, guardrails and 
measurable evaluation criteria 
2 
Evaluation dataset with at least 15 meaningful cases 2 
Single evaluation harness: structural + 
property/invariant + semantic/quality evaluation 
2 
Evaluation evidence, harness log and final human 
review 
2 
Total 10.0 
5. Common Expectations and Assessment Rules 
• Both applications Part 1A and Part 1B are compulsory. 
• The selected problem must be small enough to complete the full SDD and harness cycle. Feature count or UI 
sophistication does not earn marks by itself. 
• Spec Kit artifacts must show that implementation followed the approved specification, plan and tasks rather 
than being produced from a single unconstrained “build the app” prompt. 
• Tests/evaluations must be derived from specifications or explicitly stated evaluation criteria. 
• AI-generated production code must not be treated as correct merely because it executes. 
• Validation evidence should come from the harness and be preserved in the submission. 
• Secrets, API keys and credentials must not be committed or submitted. 
• Where external AI APIs are used, model/service failures must be distinguished from application/evaluation 
failures. 
• Any remaining limitation or failed requirement must be disclosed rather than hidden. 
• Automated PASS is followed by human review; the student remains responsible for the submitted software and 
evidence. 
6. Final Submission Structure in GITHUB 
Assignment-1/ 
├── README.md 
├── Part-1A/ 
│   ├── Spec Kit artifacts 
│   ├── source + tests 
│   ├── .harness/ 
│   └── evidence/ 
└── Part-1B/ 
    ├── Spec Kit artifacts 
    ├── source + prompts/tests 
    ├── evals/ 
    ├── .harness/ 
    └── evidence/ 
8 
7. Checklist for GIT REPO 
• ☐  Part 1A and Part 1B are both included 
• ☐  Each part follows the GitHub Spec Kit SDD flow and contains reviewed artifacts. 
• ☐  Part 1A contains working deterministic harness gates and specification-derived tests. 
• ☐  Part 1B contains at least 15 evaluation cases and one non-deterministic evaluation pipeline. 
• ☐  Harness results and available failure/repair evidence are preserved. 
• ☐  harness-log.md is included for both parts. 
• ☐  Final human acceptance/rejection and known limitations are recorded. 
• ☐  No API keys, credentials or local .env secrets are included. 
• ☐  The repository/archive contains instructions sufficient to run the submitted harness. 
8. PART 2 — ASSESSED REFLECTION QUESTIONS  
Answer all five questions. Each question carries 1 mark. Responses should be concise, evidence-based, and refer to 
your own specification artifacts, harness results, evaluation cases, or repair history. Generic descriptions of SDD or 
AI tools without evidence from your implementation will receive limited credit. 
1. Specification influence (1 mark)  
Identify one concrete decision in your implementation that was directly shaped by a Spec Kit artifact (constitution, 
specification, clarification, plan, or tasks). Explain the traceability from the artifact to the implemented decision. 
Response: __________________________________________________________________________________  
___________________________________________________________________________________________  
___________________________________________________________________________________________  
2. Harness value in Part 1A (1 mark)  
Describe one issue detected by the deterministic harness that would have been missed or less reliably detected by 
simply asking the coding agent to review its own output. State the relevant harness gate/evidence and how the issue 
was resolved. 
Response: __________________________________________________________________________________  
___________________________________________________________________________________________  
___________________________________________________________________________________________  
3. Evaluating non-determinism in Part 1B (1 mark)  
Choose one evaluation case where exact string matching would be inappropriate. Explain which schema constraint, 
invariant/property, and semantic/quality criterion you used instead, and why these checks were suitable.  
Response: __________________________________________________________________________________  
___________________________________________________________________________________________  
___________________________________________________________________________________________  
4. Feedback and self-healing (1 mark)  
S1_2026 
AI Augmented SDLC 
Akshaya Ganesan 
9 
Using one actual repair cycle from either part, explain what failure evidence was fed back to the coding agent, 
what changed in the next attempt, and whether the repair solved the root cause without weakening the 
specification or harness. 
Response: __________________________________________________________________________________  
___________________________________________________________________________________________  
___________________________________________________________________________________________  
5. Human accountability (1 mark)  
Identify one limitation or residual risk that remained even after the harness reported PASS. Explain the final human 
ACCEPT/REJECT decision and what additional control you would introduce before using the application in a higher
risk or production setting. 
Response: __________________________________________________________________________________  
___________________________________________________________________________________________  
___________________________________________________________________________________________ 
8. Overall Mark Distribution 
Assessment Criterion 
Marks 
Part 1A — Deterministic SDD & Harnessing 
10 
Part 1B — Non-Deterministic AI SDD & Harnessing 
10 
Part C- Reflection Questions 
5 
Total 
25 
10. Deliverables: 
1. Source Code in GitHub Repository: Complete Code in Github. Keep it a public repo to be 
accessible by all evaluators 
2. Demonstration Video: a short demo video of both applications (Keep it simple and short), in 
google drive/onedrive  or any accessible folder. 
3. Reflection Report: Format Attached reflection report (PART 1C — ASSESSED 
REFLECTION QUESTIONS) to be uploaded to LMS with GITHUB and Video Details 
Only Reflection Report to be uploaded to LMS 
11. Submission Instructions 
1. Upload the complete code only to the GitHub repositories. GitHub repository access is to be kept 
public and open for all evaluators.  
2. Upload the Demonstration Video to the Google Drive/One drive and Keep it accessible to all BITS 
email id. 
3. Upload only the Reflection documentation with the details to the LMS. 
4. AI Policy: 
Acceptable AI Uses 
S1_2026 
AI Augmented SDLC 
Akshaya Ganesan 
10 
• Generating example code snippets, boilerplate, or documentation. 
• Spec driven Development and Harness development 
Unacceptable AI Uses 
• Using AI to auto-generate your reflection or log entries. 
• Misrepresenting AI work as your own. 
5. Academic Honesty: You can discuss with peers and refer to the internet/ AI to understand the 
concept better. However, you may not share code with other students or do not do a verbatim copy 
from the Internet/GitHub repositories or AI response. Include appropriate references. If found 
guilty, no marks will be awarded.  
12. Note: 
• This is a take-home assignment to be carried out by each individual independently 
• In case of any further queries, use discussion forums, or reach out to me at 
akshaya.ganesan@pilani.bits-pilani.ac.in.  
S1_2026 
AI Augmented SDLC 
Akshaya Ganesan 
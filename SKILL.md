---
name: run-codebase-xray
description: This skill should be used as an optional deep-dive extension of the brownfield Assay — when the user asks to "x-ray the codebase", "map reachability", "find dead code before we modernize", "what's safe to drop", or when analyze-brownfield-context's hand-off flags this decision matrix as worth running — producing a class diagram, a stakeholder-facing I/O map, and an information-lifecycle diagram, each annotated active/dormant/orphaned, plus a reachability brief in context/brownfield/.
---

# Run Codebase X-Ray

The deep-dive half of the Assay. `analyze-brownfield-context` produces five text
documents — architecture, conventions, integrations, known issues, decision
history. None of them can answer *"does anything still call this?"* at the
class or stored-procedure level. This skill can, at the cost of a multi-agent
scan — which is exactly why it's optional, not a mandatory step of every
brownfield engagement.

## Decision matrix — is this worth running?

Read this before invoking. A small, well-documented brownfield repo doesn't
need a multi-agent Workflow pass; a large legacy system with departing authors
does. Weigh the signals, don't count them mechanically — one strong "yes"
signal (developers leaving next week) outweighs several weak "no" signals.

| Signal | Run it | Skip it (five-doc Assay is enough) |
|---|---|---|
| Original developers | Leaving, retiring, or already gone | Fully available for the whole engagement — just ask them |
| Codebase size | More modules/services than `existing-architecture-map.md`'s Component Inventory table can usefully summarize row-by-row | A handful of files/modules, already legible in a table |
| Client's actual question | "What can we safely remove before we modernize?" — cleanup-before-Transmutation is in scope | Narrow, one-off change to an otherwise well-understood, actively-maintained area |
| Business logic location | Suspected logic hidden in stored procedures/triggers, not just application code | Logic is entirely in application code, already covered by the conventions audit |
| Stakeholder need | Both technical and business stakeholders need a shared, visual picture to agree on cleanup scope | Only engineers are involved in scoping; a text register is enough |
| Existing documentation | Thin or absent — no ADRs, no architecture docs, code is the only source of truth | Strong existing docs already answer "what's load-bearing" |
| Budget/timeline | The engagement's stakes justify the extra pass (client deliverable, contractual scope decision) | A quick internal look where the overhead outweighs the value (`athanor.md`'s "honest boundaries") |

**Right-sizing without a separate "lite mode":** Phase 0 below already proposes
discrete modules and lets the human trim the list before the expensive part
runs. If only one subsystem is actually in question (e.g. "is the old billing
module still used?"), scope the module list to just that — there's no need to
scan the whole repo to answer a scoped question.

## When to Use

- `analyze-brownfield-context` has run (or is running) and its hand-off flags
  the decision matrix above as worth it for this engagement.
- Human asks directly: "x-ray the codebase", "map reachability", "what's dead
  code here", "what can we drop before modernizing", "before the developers
  leave, capture what this does".
- **Not** a substitute for `analyze-brownfield-context` — it extends the Assay,
  it doesn't replace the five-document set.

## Prerequisites

- Brownfield engagement; `context/brownfield/` exists (run
  `analyze-brownfield-context` first if it doesn't — this skill's synthesis is
  sharper with that context already in hand, though it can run standalone if
  the human specifically wants the diagrams first).
- Template: `${CLAUDE_PLUGIN_ROOT}/resources/templates/brownfield/reachability-brief.md`.
- Node.js, optional — enables SVG rendering in Phase 4; degrades gracefully without it.
- The `artifact-design` skill (invoked in Phase 5) and the `Workflow`, `Artifact`, and `Explore` tools.

## Phase 0 — Detect Stack and Propose Modules

Spawn an **Explore** subagent (breadth: "medium") to scan the working directory root and determine:

1. The primary programming language(s) and framework(s) in use.
2. The natural module boundaries for this stack. Use these heuristics:
   - **.NET (C#/VB.NET):** each `.csproj` or `.vbproj` project file = one module
   - **Java/Kotlin (Maven):** each Maven submodule or top-level `src/main/java` package group
   - **Node.js/TypeScript:** each directory with its own `package.json`
   - **Python:** each top-level directory containing `__init__.py`
   - **Ruby on Rails:** group by `app/models`, `app/controllers`, `app/services`, `lib/`
   - **Go:** each top-level package directory containing `.go` files
   - **Generic fallback:** top-level directories that contain source files
3. For each proposed module: its name, its absolute path, and a one-line description of its apparent purpose.

Present the proposed module list to the human as a numbered list. Then ask:

> "I've identified N modules. Reply **yes** to proceed, or tell me how you'd
> like to adjust the boundaries — including scoping this to just the
> subsystem in question, per the decision matrix above."

**Stop and wait for human confirmation. Do not invoke the Workflow until confirmed** — this is the same right-sizing lever the decision matrix points at, not a formality.

---

## Phase 1–3 — Analysis, Synthesis, Diagram Generation (Workflow)

Once the human confirms the module list, invoke the **Workflow** tool. Pass `args` as a JSON object:

```json
{
  "modules": [
    { "name": "ModuleName", "path": "/absolute/path/to/module" }
  ],
  "projectRoot": "/absolute/path/to/project/root",
  "todayDate": "<today's date, YYYY-MM-DD — the calling session fills this in; Workflow scripts cannot compute it>"
}
```

Use this as the `script` argument:

```javascript
export const meta = {
  name: 'run-codebase-xray',
  description: 'Parallel legacy codebase analysis: classes, I/O surfaces, data flows, SQL objects, config integrations, scheduled tasks',
  phases: [
    { title: 'Analyze', detail: 'Per-module parallel deep scan' },
    { title: 'Synthesize', detail: 'Cross-reference and annotate reachability' },
    { title: 'Diagram', detail: 'Generate three Mermaid diagrams in parallel' },
    { title: 'Write', detail: 'Save .mmd files and the reachability brief to context/brownfield/' },
  ]
}

const modules = args.modules
const projectRoot = args.projectRoot
const todayDate = args.todayDate

const MODULE_SCHEMA = {
  type: 'object',
  properties: {
    module_name: { type: 'string' },
    classes: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each entry: "ClassName (type:class|interface|enum|abstract, inherits:Base, implements:[I1,I2], methods:[m1,m2], properties:[p1,p2])"'
    },
    relationships: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each entry in Mermaid classDiagram syntax: "ClassA --|> ClassB" or "ClassA --> ClassB : uses"'
    },
    io_surfaces: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each entry: "SurfaceName (type:screen|api_endpoint|report|excel_export|email|file_output|scheduled_output|inbound_integration, description:one-line-purpose)"'
    },
    data_flows: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each entry: "OperationName: InputSource > BusinessLogicClass > DataAccessClass > DatabaseTable > OutputDestination"'
    },
    sql_objects: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each entry: "ObjectName (type:stored_procedure|trigger|view|function, tables:[T1,T2], called_from_code:true|false|unknown)"'
    },
    config_integrations: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each entry: "IntegrationName (type:database|external_api|smtp|queue|file_share, description:purpose-only)" — NEVER include credentials, server names, or connection strings'
    },
    scheduled_tasks: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each entry: "TaskName (trigger:schedule-description, description:what-it-does)"'
    }
  },
  required: ['module_name', 'classes', 'relationships', 'io_surfaces', 'data_flows', 'sql_objects', 'config_integrations', 'scheduled_tasks']
}

const SYNTHESIS_SCHEMA = {
  type: 'object',
  properties: {
    all_classes: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each: "ClassName (module:ModuleName, reachability:active|dormant|orphaned)"'
    },
    all_io_surfaces: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each: "SurfaceName (module:ModuleName, type:..., reachability:active|dormant|orphaned)"'
    },
    all_flows: {
      type: 'array',
      items: { type: 'string' },
      description: 'Deduplicated normalized flows: "OperationName: Source > Handler > DataAccess > Table > Output"'
    },
    all_sql_objects: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each: "ObjectName (module:ModuleName, type:..., called_from_code:true|false|unknown)"'
    },
    cross_module_relationships: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each: "ModuleA.ClassX --> ModuleB.ClassY : relationship-type"'
    },
    load_bearing: {
      type: 'array',
      items: { type: 'string' },
      description: '5-10 things that must work in any replacement system — based on flow activity and criticality'
    },
    safe_to_drop: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each entry: "Item: <what> — Evidence it is dormant: <reasoning>". Things that appear completely dormant and safe to not replicate — be conservative'
    },
    knowledge_capture_points: {
      type: 'array',
      items: { type: 'string' },
      description: 'Each entry: "Question: <what> — Category: Blocking|Non-blocking — Owner: <original author/role if known, else Unassigned>". Questions that need answers from the original authors before they leave'
    }
  },
  required: ['all_classes', 'all_io_surfaces', 'all_flows', 'all_sql_objects', 'cross_module_relationships', 'load_bearing', 'safe_to_drop', 'knowledge_capture_points']
}

phase('Analyze')
const moduleResultsRaw = await pipeline(
  modules,
  m => agent(
    `You are extracting an X-ray of a legacy codebase module for institutional knowledge preservation.
The original developers are retiring. Your job is to capture everything that exists — not to judge quality.

Module: "${m.name}"
Path: ${m.path}
Project root: ${projectRoot}

Read ALL source files in this module directory. Extract the following:

1. CLASSES — every class, interface, enum, and abstract class. Include:
   - Its type (class/interface/enum/abstract)
   - What it inherits from
   - Which interfaces it implements
   - Its public method names (list 3-8 most important)
   - Its key property names

2. RELATIONSHIPS — how classes relate. Use Mermaid classDiagram arrow syntax:
   - --|> for inheritance
   - o--> for composition (has-a)
   - --> for usage/dependency (uses/calls)

3. I/O SURFACES — every way data enters or exits the system through this module:
   - Screens/forms (WebForms .aspx, MVC views, Razor pages, React/Angular/Vue components)
   - API endpoints (REST controllers, WCF service operations, GraphQL resolvers, gRPC handlers)
   - Reports (Crystal Reports .rpt, RDLC, SSRS .rdl, PDF generation classes)
   - File exports (Excel via ClosedXML/NPOI, CSV, text, XML, JSON file writers)
   - Emails sent (any SmtpClient, SendGrid, etc. usage)
   - Scheduled job outputs
   - Integration outbound calls (HTTP clients calling external APIs, message queue producers)
   - Integration inbound handlers (message queue consumers, webhook receivers)

4. DATA FLOWS — trace each major business operation end-to-end. Format as a chain:
   "OperationName: InputSource > BusinessLogicClass > DataAccessClass > DatabaseTable > OutputDestination"
   Write one entry per distinct business operation (e.g., "Create Order", "Generate Monthly Report", "Export Customer Data").
   If a flow crosses module boundaries, trace as far as you can within this module.

5. SQL OBJECTS — scan all .sql files and look for inline SQL strings, ORM calls, stored procedure invocations:
   - List each stored procedure, trigger, view, and function by name
   - Which tables does it access?
   - Is it called from application code (true/false/unknown)?

6. CONFIG INTEGRATIONS — read all config files (*.config, appsettings*.json, .env, web.config, app.config):
   - List every external dependency: databases (purpose only), external HTTP/SOAP endpoints (purpose only),
     SMTP (yes/no + purpose), queues, file shares, external auth services
   - NEVER include passwords, usernames, connection strings, server names, or API keys

7. SCHEDULED TASKS — scan for:
   - Timer or polling classes (System.Threading.Timer, HostedService, IHostedService)
   - Cron expressions or scheduled task registration (Hangfire, Quartz, NCrontab, etc.)
   - Windows Task Scheduler XML files
   - Any code that appears to run on a recurring schedule

Be thorough. Incomplete capture now means lost knowledge later.`,
    {
      label: `analyze:${m.name}`,
      phase: 'Analyze',
      schema: MODULE_SCHEMA
    }
  )
)

const moduleResults = moduleResultsRaw.filter(Boolean)
const failedModules = modules.filter((m, i) => !moduleResultsRaw[i])
if (failedModules.length > 0) {
  log(`${failedModules.length} of ${modules.length} module(s) failed to analyze and are excluded from this scan: ${failedModules.map(m => m.name).join(', ')}. The brief will note this as an incomplete scan.`)
}

phase('Synthesize')
const synthesis = await agent(
  `You are synthesizing a full X-ray of a legacy codebase from ${moduleResults.length} per-module analyses.

Per-module results:
${JSON.stringify(moduleResults, null, 2)}

REACHABILITY ANNOTATION RULES:
- ACTIVE: appears in at least one complete data flow that connects an input source to an output destination
- DORMANT: exists in the code but never appears in any traced data flow
- ORPHANED: referenced in a data flow but no corresponding code implementation was found in any module

YOUR TASKS:

1. ALL_CLASSES — collect every class from every module. For each, determine reachability:
   Does this class appear in any data flow? If yes → active. If no → dormant.
   Was it referenced in a flow but not found as a class → orphaned.

2. ALL_IO_SURFACES — collect every I/O surface across all modules.
   Active if any flow reaches or originates from it. Dormant if nothing connects to it.
   Orphaned if a flow references an I/O surface (e.g. an output destination or input source)
   that has no corresponding surface found in any module's io_surfaces.

3. ALL_FLOWS — deduplicate and normalize data flows across all modules.
   Flows described in multiple modules should be merged into one complete chain where possible.

4. ALL_SQL_OBJECTS — collect all SQL objects from all modules.

5. CROSS_MODULE_RELATIONSHIPS — identify direct dependencies where a class in one module uses a class from another.

6. LOAD_BEARING — the 5-10 most critical items that must work in any replacement system.
   Base this on: how many active flows pass through them, whether they handle core business entities,
   whether they are the only path to a critical output.

7. SAFE_TO_DROP — items that are clearly dormant with no plausible reason to replicate.
   Be conservative. Only include items where dormancy is unambiguous. Format each entry
   "Item: <what> — Evidence it is dormant: <reasoning>" so the risk register can carry the
   evidence forward without re-deriving it.

8. KNOWLEDGE_CAPTURE_POINTS — questions for the original authors before they leave. Examples:
   - Dormant classes that might be temporarily disabled (feature flag? commented-out caller?)
   - SQL objects not called from any application code (called by a DBA? an external job? a legacy ETL?)
   - Config integrations whose purpose is not clear from the code
   - Broken flow chains (data enters a module, no output is traceable)
   - Business rules that exist only in SQL, not in any class
   Format each entry "Question: <what> — Category: Blocking|Non-blocking — Owner: <original
   author/role if known, else Unassigned>". Use Blocking when the question would change a
   load-bearing/safe-to-drop conclusion and the answering developer is leaving soon;
   Non-blocking otherwise.

When in doubt, mark as ACTIVE. Over-preservation is always safer than lost knowledge.`,
  {
    label: 'synthesize',
    phase: 'Synthesize',
    schema: SYNTHESIS_SCHEMA
  }
)

phase('Diagram')
const synthesisStr = JSON.stringify(synthesis, null, 2)
const moduleRelStr = JSON.stringify(
  moduleResults.map(m => ({ module_name: m.module_name, relationships: m.relationships, classes: m.classes })),
  null, 2
)

const [classDiagram, ioMap, lifecycle] = await parallel([
  () => agent(
    `Generate a Mermaid class diagram for a legacy codebase X-ray.

Synthesis (primary source — use this for reachability annotations):
${synthesisStr}

Per-module relationship detail:
${moduleRelStr}

RULES:
- Use classDiagram syntax
- Group classes by module using namespace blocks: namespace ModuleName { ... }
- Define these styles at the top of the diagram:
    classDef active fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    classDef dormant fill:#f5f5f5,stroke:#9e9e9e,color:#757575
    classDef orphaned fill:#fff8e1,stroke:#f9a825,color:#e65100
- Apply the correct style to each class: ClassName:::active
- Show relationships: --|> inheritance, o--> composition, --> dependency/usage
- Include methods and properties for ACTIVE classes only (max 5 per class)
- For large modules (more than 15 classes): show the 8 most connected, then add:
    %% N more classes in this module (dormant)
- Cross-module relationships go after all namespace blocks

Return ONLY the raw Mermaid code. No explanation, no markdown fences. First line must be: classDiagram`,
    { label: 'diagram:class', phase: 'Diagram' }
  ),

  () => agent(
    `Generate a Mermaid flowchart for the I/O map of a legacy codebase X-ray.

Synthesis:
${synthesisStr}

RULES:
- Use flowchart LR syntax
- Three subgraphs: Inputs (left), System (center), Outputs (right)
- Inputs: screens/forms, API endpoints, file imports, scheduled triggers, inbound integrations
- System: the module-level nodes that connect inputs to outputs (no internal class detail — module names only)
- Outputs: reports, Excel files, emails, API responses, file exports, outbound integrations
- Node shapes:
    Screens/UI: [Label] rectangles
    Databases: [(Label)] cylinders
    Reports/exports: [/Label/] parallelograms
    Emails/notifications: ([Label]) rounded rectangles
    API endpoints: [Label] rectangles
- Active surfaces: style with fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
- Dormant surfaces: style with fill:#f5f5f5,stroke:#bdbdbd,color:#9e9e9e
- Active connections: --> solid arrows
- Dormant connections: -.-> dashed arrows
- This diagram is for STAKEHOLDER conversations — including business stakeholders, not just
  engineers. Keep it readable. Group related outputs. Do not expose implementation details.
  Omit internal helper classes.

Return ONLY the raw Mermaid code. No explanation, no markdown fences. First line must be: flowchart LR`,
    { label: 'diagram:io', phase: 'Diagram' }
  ),

  () => agent(
    `Generate a Mermaid flowchart for the information lifecycle of a legacy codebase X-ray.

CRITICAL: Use flowchart TD (top-down directed graph). NOT sequenceDiagram. NOT gantt. NOT swim lanes.
This is a DAG showing how data physically moves through the system.

Synthesis:
${synthesisStr}

RULES:
- Use flowchart TD syntax
- Show data journeys: entry point → business logic → storage → output
- Each major data flow in the synthesis maps to one or more paths through the graph
- Node types (use these shapes):
    User input sources: [Label] rectangles
    Business logic classes: (Label) rounded rectangles
    Database tables: [(Label)] cylinders
    SQL stored procedures or triggers: [/Label\\] trapezoids — label includes "(proc)" or "(trigger)"
    Output destinations: [/Label/] parallelograms
- Group related flows into labeled subgraphs by business domain:
    subgraph OrderManagement ... end
    subgraph InvoiceTracking ... end
    subgraph Reporting ... end
- Hot active paths: ==> thick arrows
- Dormant/cold paths: -. .-> dashed arrows
- SQL objects not called from application code: add a comment on the same line:
    ProcName[/ProcName (proc)/] %% NOT CALLED FROM CODE — verify with DBA
- If there are too many flows to show clearly, keep active ones and add:
    %% N dormant flows omitted for clarity

Return ONLY the raw Mermaid code. No explanation, no markdown fences. First line must be: flowchart TD`,
    { label: 'diagram:lifecycle', phase: 'Diagram' }
  )
])

phase('Write')

const activeClasses = synthesis.all_classes.filter(c => c.includes('reachability:active')).length
const dormantClasses = synthesis.all_classes.filter(c => c.includes('reachability:dormant')).length
const orphanedClasses = synthesis.all_classes.filter(c => c.includes('reachability:orphaned')).length
const activeIO = synthesis.all_io_surfaces.filter(s => s.includes('reachability:active')).length
const dormantIO = synthesis.all_io_surfaces.filter(s => s.includes('reachability:dormant')).length
const orphanedIO = synthesis.all_io_surfaces.filter(s => s.includes('reachability:orphaned')).length
const notCalledSQL = synthesis.all_sql_objects.filter(s => s.includes('called_from_code:false'))
const unknownCallSQL = synthesis.all_sql_objects.filter(s => s.includes('called_from_code:unknown'))

const scanCompletenessNote = failedModules.length > 0
  ? `\n> **Incomplete scan** — ${failedModules.length} of ${modules.length} module(s) could not be analyzed and are excluded from every count and conclusion below: ${failedModules.map(m => m.name).join(', ')}. Re-run the x-ray for these modules before treating Safe-to-Drop conclusions as complete.\n`
  : ''

const reachabilityBrief = `---
Status: Draft
Approved By:
Approved Date:
Last Updated: ${todayDate}
Supersedes:
Derived From: run-codebase-xray — ${modules.length} module(s) scanned: ${modules.map(m => m.name).join(', ')}
---

# Reachability Brief

*Generated by \`run-codebase-xray\` — for modernization/cleanup scoping and stakeholder conversations.*
${scanCompletenessNote}
## Reachability Summary

| Category | Active | Dormant | Orphaned |
|---|---|---|---|
| Classes | ${activeClasses} | ${dormantClasses} | ${orphanedClasses} |
| I/O Surfaces | ${activeIO} | ${dormantIO} | ${orphanedIO} |

## Load-Bearing (must survive modernization)

${synthesis.load_bearing.map(x => '- ' + x).join('\n')}

## Safe to Drop (dormant — candidate for removal, not yet confirmed with client)

${synthesis.safe_to_drop.map(x => '- ' + x + ' — Confirmed with client: no').join('\n')}

## Questions for Retiring/Departing Developers

${synthesis.knowledge_capture_points.map(x => '- ' + x).join('\n')}

## SQL Objects Not Called From Application Code

${notCalledSQL.length > 0 ? notCalledSQL.map(x => '- ' + x).join('\n') : '- None found'}

## SQL Objects With Unknown Call Status (Needs Verification)

${unknownCallSQL.length > 0 ? unknownCallSQL.map(x => '- ' + x).join('\n') : '- None found'}

## Diagrams
- Class diagram: \`context/brownfield/diagrams/class-diagram.mmd\`
- System I/O map: \`context/brownfield/diagrams/io-map.mmd\`
- Information lifecycle: \`context/brownfield/diagrams/lifecycle.mmd\`
`

const cleanDiagram = d => d.replace(/^```mermaid\n?/, '').replace(/^```\n?/, '').replace(/\n?```$/, '')
const cleanClass = cleanDiagram(classDiagram)
const cleanIO = cleanDiagram(ioMap)
const cleanLifecycle = cleanDiagram(lifecycle)

await agent(
  `Create the directory ${projectRoot}/context/brownfield/diagrams/ if it does not exist (use Bash: mkdir -p "${projectRoot}/context/brownfield/diagrams/").
Then write these four files using the Write tool. Write each file exactly as provided below.

FILE 1 — ${projectRoot}/context/brownfield/diagrams/class-diagram.mmd
${cleanClass}

---END FILE 1---

FILE 2 — ${projectRoot}/context/brownfield/diagrams/io-map.mmd
${cleanIO}

---END FILE 2---

FILE 3 — ${projectRoot}/context/brownfield/diagrams/lifecycle.mmd
${cleanLifecycle}

---END FILE 3---

FILE 4 — ${projectRoot}/context/brownfield/reachability-brief.md
${reachabilityBrief}

---END FILE 4---

After writing all four files, output exactly: Wrote 4 files to context/brownfield/`,
  { label: 'write-files', phase: 'Write' }
)

return {
  diagrams: { classDiagram: cleanClass, ioMap: cleanIO, lifecycle: cleanLifecycle },
  synthesis,
  paths: {
    classDiagram: projectRoot + '/context/brownfield/diagrams/class-diagram.mmd',
    ioMap: projectRoot + '/context/brownfield/diagrams/io-map.mmd',
    lifecycle: projectRoot + '/context/brownfield/diagrams/lifecycle.mmd',
    reachabilityBrief: projectRoot + '/context/brownfield/reachability-brief.md'
  }
}
```

---

## Phase 4 — SVG Rendering

After the Workflow completes, check for Node.js availability:

```bash
which node 2>/dev/null && node --version || echo "MISSING"
```

**If Node.js is available**, run mmdc for each of the three `.mmd` files:

```bash
cd "<projectRoot>"
npx -y -p @mermaid-js/mermaid-cli@11.16.0 mmdc -i context/brownfield/diagrams/class-diagram.mmd -o context/brownfield/diagrams/class-diagram.svg --backgroundColor transparent
npx -y -p @mermaid-js/mermaid-cli@11.16.0 mmdc -i context/brownfield/diagrams/io-map.mmd -o context/brownfield/diagrams/io-map.svg --backgroundColor transparent
npx -y -p @mermaid-js/mermaid-cli@11.16.0 mmdc -i context/brownfield/diagrams/lifecycle.mmd -o context/brownfield/diagrams/lifecycle.svg --backgroundColor transparent
```

`@11.16.0` pins the exact package version — an unpinned `npx` command re-resolves to
whatever the registry currently publishes, which is a supply-chain risk. Bump this pin
deliberately, don't drop it.

If any command fails with a Chrome/sandbox error on Linux, first try installing the
missing sandbox dependencies (see mermaid-cli's own
[linux-sandbox-issue.md](https://github.com/mermaid-js/mermaid-cli/blob/master/docs/linux-sandbox-issue.md))
rather than disabling the sandbox. Only if that isn't possible — e.g. inside an
already-isolated, disposable CI container — retry with `--no-sandbox` as an explicit,
one-off opt-in, never as the default path on a developer's primary workstation:
```bash
npx -y -p @mermaid-js/mermaid-cli@11.16.0 mmdc -i context/brownfield/diagrams/<file>.mmd -o context/brownfield/diagrams/<file>.svg --puppeteerConfig '{"args":["--no-sandbox"]}'
```

**If Node.js is not available**, warn the human and continue to Phase 5 without SVGs:

> "Node.js not found — skipping SVG conversion. The Mermaid source files are at
> `context/brownfield/diagrams/*.mmd`. To convert them later, install Node.js and run:
> `npx -y -p @mermaid-js/mermaid-cli@11.16.0 mmdc -i context/brownfield/diagrams/<file>.mmd -o context/brownfield/diagrams/<file>.svg`"

---

## Phase 5 — HTML Artifacts

Before creating the artifacts, invoke the **artifact-design** skill using the Skill tool.
This calibrates the visual direction to the specific subject matter of the codebase being analyzed.
Apply the resulting design system consistently across all three artifacts.

Create three separate HTML artifacts using the Artifact tool — one per diagram. Each one is
built for a specific audience in the Assay's stakeholder conversations, not interchangeable:

For each artifact:
- If the corresponding `.svg` file was generated in Phase 4, read its contents with the Read tool
  and embed it **inline** in the HTML (as a raw `<svg>` block, not an `<img src>`).
- If the SVG was not generated, render the raw Mermaid source in a styled `<pre>` with a copy button.

### Artifact 1 — Class Diagram
- Title: `[Project Name] — Class Structure`
- Audience: developers and architects — use for the **technical stakeholder** conversation
  about what's touchable and what isn't.
- Include a color legend: green = active, grey = dormant, yellow = orphaned
- Include the reachability counts table from `reachability-brief.md`

### Artifact 2 — System I/O Map
- Title: `[Project Name] — System I/O Map`
- Audience: business stakeholders — this is the leave-behind for the **business stakeholder**
  conversation about what can be dropped, since it deliberately omits implementation detail.
- Include a short framing sentence at the top:
  *"This diagram maps everything the system consumes and produces. Use it to decide what outputs are still needed."*
- Include a summary table of all active outputs with their type

### Artifact 3 — Information Lifecycle
- Title: `[Project Name] — Information Lifecycle`
- Audience: modernization team — use this alongside the Load-Bearing / Safe-to-Drop lists when
  **scoping the cleanup-before-modernize work** with the technical stakeholders.
- Include the Load-Bearing and Questions for Retiring Developers sections from `reachability-brief.md`
- Include a short framing sentence:
  *"Thick arrows = active high-traffic paths. Dashed arrows = dormant. Trapezoids = SQL objects."*

---

## Hand-off — fold findings back into the five-document Assay set

This skill's output doesn't stand alone; it's evidence the rest of the Assay should reflect.

1. **Safe-to-drop candidates** → add them to `known-issues-risk-register.md`'s "Safe-to-Drop
   Candidates" section (present only when this skill has run), pointing back at
   `reachability-brief.md` for the full evidence. Don't just leave them in the brief — a risk
   register nobody cross-checks against the brief is how a finding gets lost.
2. **Load-bearing items** → cross-reference into `existing-architecture-map.md`'s Component
   Inventory: confirm the Reachability column reads `active` and tag the Notes column
   `load-bearing`, so the human-readable architecture doc and the reachability data don't drift
   into two disconnected pictures of the same system.
3. **Knowledge-capture questions** → don't leave them as a bullet list nobody is on the hook to
   resolve. Each one already carries a `Blocking`/`Non-blocking` category and an owner (see
   `knowledge_capture_points` in the synthesis schema) — surface it as an Open Question the same
   way `log-assumption`/`analyze-brownfield-context` already do; "developers retiring next
   month" is exactly the kind of urgency a Blocking marker exists to carry.
4. Present the executive summary — reachability counts, load-bearing list, and which stakeholder
   artifact to bring to which meeting — before the human decides whether Transmutation scoping
   can proceed or whether a knowledge-capture conversation with the outgoing team has to happen first.

## Output

```
context/brownfield/
  diagrams/
    class-diagram.mmd          Mermaid source — safe to commit and edit
    class-diagram.svg          Pre-rendered (if Node.js was available)
    io-map.mmd
    io-map.svg
    lifecycle.mmd
    lifecycle.svg
  reachability-brief.md        Status: Draft — the sixth brownfield document
```

Plus three HTML artifacts (one per stakeholder audience) and, per the hand-off section above,
edits to `known-issues-risk-register.md` and `existing-architecture-map.md` and/or new Open
Questions.

**Security note:** config integrations are captured by type and purpose only. No credentials,
server names, or connection strings are written to any output file — same discipline as
`brownfield-analysis`.

## Failure / Edge Cases

| Situation | Action |
|-----------|--------|
| Decision matrix comes back mostly "skip it" | Say so plainly and don't run it — `analyze-brownfield-context`'s five docs stand on their own. |
| Human wants only one subsystem scanned | Trim the Phase 0 module list to that subsystem — no need to scan the whole repo for a scoped question. |
| No Node.js available | Skip SVG rendering (Phase 4); artifacts fall back to styled raw Mermaid source. Say so once, don't re-warn every run. |
| `context/brownfield/` doesn't exist yet | Run `analyze-brownfield-context` first, or create the directory if the human specifically wants diagrams before the five-doc set. |
| A module's scan finds nothing reachable at all | Report it plainly as a knowledge-capture point — a module with zero active flows is itself a finding, not a scan failure. |
| Client disputes a "safe to drop" finding | Evidence-based claim stands as documented; record the disagreement, don't silently remove the finding (mirrors `brownfield-analysis`'s "client denies known issues" handling). |
| Re-running after code has changed | New Draft supersedes the old `reachability-brief.md` (`Supersedes:` link) — don't overwrite an Approved brief in place. |
| Workflow-tool agent budget concerns on a very large repo | Trim the module list (see decision matrix) rather than running the full scan speculatively. |

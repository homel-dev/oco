
# OBSERVABILITY CONSOLE
## Shared Telemetry Presentation Layer for Homel Projects
### Repository Entry Point
*Namespace: observability-console • Owner: platform*

---

## Navigation
**[Next: Document 01 (Architecture Overview)](docs/01_overview.md) →**

- [0. Status, Scope, and Authority](#0-status-scope-and-authority)
- [1. Purpose](#1-purpose)
- [2. Scope](#2-scope)
- [3. Served Projects](#3-served-projects)
- [4. Documentation](#4-documentation)
- [5. Closing Statement](#5-closing-statement)

---

## 0. Status, Scope, and Authority

**Status:** FOUNDATIONAL
**Audience:** Platform contributors, infrastructure contributors, consumer-project maintainers
**Change policy:**
- Append-only
- No silent edits

This repository provides the shared telemetry **presentation** layer for Homel projects. It owns how telemetry is viewed. It does not own telemetry collection, storage, or meaning.

Project identity: **OCO** — *"oko"*, the eye. All machine-facing identifiers (repository, namespace, DNS, labels) use `observability-console`.

[Back to top](#navigation)

---

## 1. Purpose

Multiple Homel projects emit telemetry. Without a shared presentation layer, each project tends to stand up its own viewer stack, duplicating the viewer while telemetry stays project-local.

This repository provides one presentation surface — dashboards now, alert and trace surfaces possible later — that reads from telemetry sources owned and operated by independent projects.

The viewer is shared. Collection, storage, and meaning remain with each project.

[Back to top](#navigation)

---

## 2. Scope

### 2.1 This Repository Owns
- the presentation surface (initially Grafana)
- the provisioning mechanism that loads consumer-published definitions
- the access contract by which consumers grant namespaced read
- the presentation ServiceAccount identity
- presentation availability and recovery

### 2.2 This Repository Does Not Own
- metric stores
- log stores
- collectors and exporters
- instrumentation
- telemetry retention and lifecycle

> **Hard Invariant:** This repository MUST NOT host a metric store, log store, or collector. Removing this project MUST cost the ability to *view* telemetry — never the telemetry itself.

Full architecture: see [Document 01 (Architecture Overview)](docs/01_overview.md).

[Back to top](#navigation)

---

## 3. Served Projects

A project is served only once it ships the consumption contract from its own namespace: labeled definition ConfigMaps, a Role granting namespaced read, and a RoleBinding to the console ServiceAccount. Intent is not consumption.

| Project | Namespace | Status |
|:--|:--|:-:|
| llm-runtime | `llm-runtime` | Migrating |
| Memory Steward | _to be defined_ | Planned |
| Relentless Rekrow | _to be defined_ | Planned |
| Intent Steward | _to be defined_ | Planned |
| The Dean | _to be defined_ | Planned |

**Status values:** `Consumer` (contract shipped) • `Migrating` (onboarding in progress) • `Planned` (intended, not onboarded).

> **Warning:** This table is a convenience and MAY drift from reality. The authoritative record of served projects is the set of RoleBindings naming the console ServiceAccount.

[Back to top](#navigation)

---

## 4. Documentation

- [docs/01_overview.md](docs/01_overview.md) — foundational architecture specification

Additional specifications MUST follow the documentation style guide and the `dd_topic_slug.md` naming convention.

[Back to top](#navigation)

---

## 5. Closing Statement

This repository formalizes a shared telemetry presentation layer. The presentation surface is shared; telemetry collection, storage, content, and meaning remain owned by independent projects. A reviewer MUST be able to remove this repository and lose visibility, never data.

---

**END OF DOCUMENT**

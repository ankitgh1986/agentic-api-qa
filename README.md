# Agentic API QA Framework

## Overview

The Agentic API QA Framework is a modular, agent-based API testing
platform that discovers APIs from an OpenAPI/Swagger specification,
generates payloads, executes APIs, validates responses, manages runtime
state, makes dependency-aware execution decisions, and produces
execution reports.

## Architecture

``` text
Swagger Specification
        │
        ▼
SwaggerParserAgent
        │
        ▼
SchemaResolverAgent
        │
        ▼
ExecutionDependencyAgent
        │
        ▼
ExecutionPlannerAgent
        │
        ▼
ExecutionDecisionAgent
        │
 ┌──────┴──────┐
 │             │
 ▼             ▼
Execute      Skip
 │
 ▼
SyntheticDataAgent
 │
 ▼
PayloadTemplateAgent
 │
 ▼
ExecutionAgent
 │
 ▼
ResponseCaptureAgent
 │
 ▼
StateManagerAgent
 │
 ▼
ResponseValidatorAgent
 │
 ▼
SwaggerResponseValidatorAgent
 │
 ▼
ReportingAgent
```

## Key Features

-   Swagger/OpenAPI parsing
-   Schema resolution
-   Synthetic payload generation
-   Payload templating with runtime values
-   Shared runtime state
-   Response capture
-   Dependency discovery
-   Execution planning
-   Adaptive dependency-aware execution
-   Response validation
-   Swagger response validation
-   CSV reporting

## Agents

  Agent                           Responsibility
  ------------------------------- ---------------------------------------
  SwaggerParserAgent              Parse Swagger/OpenAPI
  SchemaResolverAgent             Resolve request schemas
  SyntheticDataAgent              Generate payloads
  PayloadTemplateAgent            Apply runtime placeholders
  ExecutionDependencyAgent        Discover API dependencies
  ExecutionPlannerAgent           Plan execution order
  ExecutionDecisionAgent          Decide whether dependent APIs execute
  ExecutionAgent                  Execute HTTP requests
  ResponseCaptureAgent            Capture runtime values
  StateManagerAgent               Maintain shared runtime state
  ResponseValidatorAgent          Validate responses
  SwaggerResponseValidatorAgent   Validate Swagger contracts
  ReportingAgent                  Generate CSV reports

## Sprint Evolution

  Sprint   Capability
  -------- -------------------------------
  1        Swagger Parser
  2        Schema Resolver
  3        Synthetic Data Generation
  4        Execution Engine
  5        Response Validation
  6        Swagger Validation
  7        Reporting
  8        State Manager
  9        Response Capture
  10       Payload Templating
  11.0     Execution Planner
  11.1     Dependency Discovery
  11.2     Adaptive Dependency Execution

## Project Structure

``` text
agents/
targets/
reports/
orchestrator2.py
README.md
```

## Run

``` bash
python orchestrator2.py
```

Outputs: - Console execution summary - CSV report - Runtime state

## Roadmap

-   Sprint 12: Parallel Execution Engine
-   Sprint 13: AI-assisted Test Generation
-   Sprint 14: GitHub Actions CI/CD
-   Sprint 15: HTML Dashboard

## Technologies

Python, OpenAPI/Swagger, Requests, Logging, CSV Reporting

# Graph Report - Student_Visual_Carrer_Back  (2026-10-13)

## Corpus Check
- Corpus is ~7,771 words - fits in a single context window. You may not need a graph.

## Summary
- 182 nodes · 327 edges · 14 communities (8 shown, 6 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.94)
- Token cost: 1,250 input · 680 output

## Community Hubs (Navigation)
- Application Core & Routing
- Administration & Proposals Governance
- Authentication & Security Module
- Authentication & Registration Testing
- Test Fixtures & Async Infrastructure
- Configuration & Environment Settings
- Community Forum API
- Admin Endpoints Testing
- Institutional Email Verification
- Study Plans Curriculum API
- Database Connection Pool
- Database Seeding Scripts

## God Nodes (most connected - your core abstractions)
1. `register_user()` - 19 edges
2. `handle_auth()` - 11 edges
3. `format_proposal()` - 8 edges
4. `VotingService` - 8 edges
5. `handle_admin()` - 7 edges
6. `Settings` - 7 edges
7. `verify_password()` - 7 edges
8. `EmailService` - 7 edges
9. `make()` - 7 edges
10. `verify_email_endpoint()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `GitHub Actions CI Pipeline` --semantically_similar_to--> `PostgreSQL Dev Container Service`  [INFERRED] [semantically similar]
  .github/workflows/ci.yml → docker-compose.yml
- `test_format_proposal()` --calls--> `format_proposal()`  [EXTRACTED]
  tests/test_voting.py → app/api/routers/proposals.py
- `test_hash_email()` --calls--> `hash_email()`  [EXTRACTED]
  tests/test_security.py → app/security.py
- `test_pbkdf2_nodejs_compatibility()` --calls--> `verify_password()`  [EXTRACTED]
  tests/test_security.py → app/security.py
- `handle_auth()` --uses--> `EmailService`  [INFERRED]
  app/api/routers/auth.py → app/services/email_service.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Student Governance Proposal & Voting Flow** — readme_student_governance_system, app_api_routers_proposals, app_services_voting_service [INFERRED 0.85]
- **Authentication & Security Subsystem** — readme_security_model, app_security, app_api_routers_auth, app_api_routers_email_verify [INFERRED 0.85]

## Communities (14 total, 6 thin omitted)

### Community 0 - "Application Core & Routing"
Cohesion: 0.11
Nodes (11): GitHub Actions CI Pipeline, health_check(), lifespan(), EmailService, HunterService, FastAPI Backend Container Service, PostgreSQL Dev Container Service, Resend Email Service Integration (+3 more)

### Community 1 - "Administration & Proposals Governance"
Cohesion: 0.10
Nodes (12): AdminActionRequest, handle_admin(), create_proposal(), CreateProposalRequest, format_proposal(), get_proposal(), list_proposals(), vote_proposal() (+4 more)

### Community 2 - "Authentication & Security Module"
Cohesion: 0.13
Nodes (9): AuthRequest, handle_auth(), hash_email(), hash_password(), verify_password(), Security & PBKDF2 Password Model, test_hash_email(), test_password_hash_and_verify() (+1 more)

### Community 3 - "Authentication & Registration Testing"
Cohesion: 0.18
Nodes (15): register_user(), test_cannot_send_pin_to_registered_email(), test_full_registration_and_login_flow(), test_login_wrong_password(), test_register_rejects_duplicate_username_and_short_password(), _create_post(), test_create_list_like_and_comment(), test_create_post_validation_and_missing_post() (+7 more)

### Community 4 - "Test Fixtures & Async Infrastructure"
Cohesion: 0.14
Nodes (7): client(), database(), _ensure_test_database(), governance(), test_admin_wrong_password(), test_auth_domain_validation(), test_health_check()

### Community 5 - "Configuration & Environment Settings"
Cohesion: 0.19
Nodes (8): Settings, _clean_env(), make(), test_admin_password_defaults_in_dev_mode_and_explicit_wins(), test_admin_password_required_outside_dev_mode(), test_cors_origins_parsed_from_comma_separated_list(), test_database_url_has_priority_over_legacy_postgres(), test_legacy_postgres_used_only_when_database_url_not_set()

### Community 6 - "Community Forum API"
Cohesion: 0.21
Nodes (4): format_post(), ForumActionRequest, get_forum_posts(), handle_forum_action()

### Community 7 - "Admin Endpoints Testing"
Cohesion: 0.52
Nodes (6): _admin(), test_add_plan_then_visible_in_plans_list_and_plan(), test_add_plan_validation(), test_admin_unknown_action_and_missing_proposal(), test_admin_verify_and_wrong_password(), test_approve_and_reject_proposals()

## Knowledge Gaps
- **4 isolated node(s):** `seed_dev.sh script`, `Student Visual Carrer - Backend (FastAPI)`, `Resend Email Service Integration`, `Security & PBKDF2 Password Model`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 62 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `register_user()` connect `Authentication & Registration Testing` to `Test Fixtures & Async Infrastructure`, `Admin Endpoints Testing`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `Settings` connect `Configuration & Environment Settings` to `Application Core & Routing`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `EmailService` connect `Application Core & Routing` to `Administration & Proposals Governance`, `Authentication & Security Module`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `handle_auth()` (e.g. with `EmailService` and `HunterService`) actually correct?**
  _`handle_auth()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `VotingService` (e.g. with `handle_admin()` and `vote_proposal()`) actually correct?**
  _`VotingService` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `seed_dev.sh script`, `Student Visual Carrer - Backend (FastAPI)`, `Resend Email Service Integration` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Application Core & Routing` be split into smaller, more focused modules?**
  _Cohesion score 0.11428571428571428 - nodes in this community are weakly interconnected._
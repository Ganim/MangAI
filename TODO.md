# TODO

## Product

- [x] Confirm product name
- [x] Confirm target user personas
- [x] Confirm MVP scope
- [ ] Define success metrics for beta

## Planning

- [x] Write PRD
- [x] Write architecture overview
- [x] Write internationalization strategy
- [x] Write planning review
- [x] Write user flows
- [x] Write MVP definition
- [x] Write domain model
- [x] Define schema v1
- [x] Write pipeline design
- [x] Write editor UX guidance
- [x] Write quality standards
- [x] Write risk map
- [x] Write decisions log
- [x] Turn planning docs into implementation tickets
- [x] Define layer contracts between web, api, workers, and shared

## Monorepo

- [x] Create repository documentation base
- [x] Create monorepo root structure
- [x] Add Next.js app bootstrap
- [x] Add FastAPI API bootstrap
- [x] Add worker bootstrap
- [x] Add shared package contracts

## Architecture

- [x] Define canonical project JSON schema
- [x] Define page, region, dialogue, and export entities
- [x] Define internationalization and locale model
- [ ] Choose AI providers for cleanup and translation
- [ ] Decide PSD export strategy

## Frontend

- [x] Define UI locale strategy
- [x] Add app message catalog structure
- [x] Create initial `en-US` and `pt-BR` locale packs
- [x] Create project dashboard
- [x] Create upload flow
- [x] Create page editor shell
- [x] Create overlay and mask editing interactions
- [x] Create dialogue side panel
- [ ] Create dual text workspace for extracted and translated text
- [ ] Create script import UI with page markers
- [ ] Create project style preset library
- [ ] Create preset copy flow between projects

## Backend

- [x] Create project and page APIs
- [x] Create job API
- [x] Create asset storage layer
- [x] Create cleanup pipeline contract
- [ ] Create OCR pipeline contract
- [ ] Create script import parse/apply APIs
- [ ] Create style preset APIs
- [ ] Create typesetting apply/reflow APIs

## AI

- [x] Create region detection adapter
- [x] Create cleanup adapter
- [ ] Create OCR adapter
- [ ] Create translation adapter
- [ ] Create matching heuristics
- [ ] Create typesetting heuristics
- [ ] Create auto-fit typesetting engine
- [ ] Preserve manual placement locks during reflow

## Export

- [x] Define JPG renderer
- [x] Define PDF renderer
- [x] Define PSD renderer
- [ ] Define export manifest format
- [ ] Define font fallback and missing-font behavior
- [ ] Align export text rendering with preset library

## Operations

- [ ] Add linting and formatting
- [ ] Add CI
- [x] Add environment templates
- [ ] Add local dev orchestration

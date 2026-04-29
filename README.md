# RGProductUpdate
Redgate Product Update and Database Support Information Scraper

This project provides automated scraping of publicly available Redgate product information, including version updates and database engine support data.

**⚠️ Disclaimer:** All data is scraped from public Redgate documentation pages and is provided as-is. Accuracy and completeness cannot be guaranteed. Please refer to official Redgate documentation for authoritative information.

Status:
[![kirky-run-python-updated](https://github.com/rekirky/RGProductUpdate/actions/workflows/pythonaction.yml/badge.svg)](https://github.com/rekirky/RGProductUpdate/actions/workflows/pythonaction.yml)
[![AI-Assisted](https://img.shields.io/badge/Built%20with-Claude%20AI-blue?logo=anthropic)](https://claude.ai)

---

## Features

### 1. Product Updates
**Overview:** Tracks the latest versions and release dates for Redgate products across all platforms and deployments.

**What it does:**
- Monitors Redgate's S3 checkforupdates bucket for new product releases
- Extracts version numbers, download URLs, and release dates
- Automatically handles S3 pagination to find all available versions
- Stores data in `data/products.json` for quick reference

**Anticipated Usage:**
- Quick version checking without visiting release notes
- Automation of product update detection in CI/CD pipelines
- Integration with deployment tools to check for latest versions
- Tracking product update history and patterns

**Data source:** `https://redgate-download.s3.eu-west-1.amazonaws.com/`

---

### 2. Database Support
**Overview:** Comprehensive database engine and operating system support information for Redgate products, specifically Redgate Monitor.

**What it does:**
- Extracts supported database engine versions (SQL Server, PostgreSQL, Oracle, MySQL, MongoDB)
- Identifies supported Windows and Linux operating systems for each engine
- Automatically follows links to master support pages when available
- Stores platform support information with reference URLs
- Maintains support data in `data/db-support.json` for future reference

**Anticipated Usage:**
- Verifying database and OS compatibility before deployment
- Building compatibility matrices for documentation
- Integration with compatibility checking tools
- Pre-deployment validation of infrastructure requirements

**Data sources:**
- SQL Server: `https://documentation.red-gate.com/monitor/monitored-sql-servers-239667386.html`
- PostgreSQL: `https://documentation.red-gate.com/monitor/monitored-postgresql-instances-239667387.html`
- Oracle: `https://documentation.red-gate.com/monitor/monitored-oracle-285802540.html`
- MySQL: `https://documentation.red-gate.com/monitor/monitored-mysql-285802551.html`
- MongoDB: `https://documentation.red-gate.com/monitor/monitored-mongodb-285802548.html`
- Master Linux Support: `https://documentation.red-gate.com/monitor/monitored-instances-on-linux-machine-284069118.html`

---

## Usage

### Product Updates
Filter products by name or release date
e.g. entering '2022-10' into the date field will return all products updated in October

# Feature Requests
* ~~Sorting by release date, product name~~
* Include/Exclude specific products  
* ~~Release notes available on hover (V1.1)~~
* ~~Add link to download main site~~
* ~~Add links to product document site~~

---

# Version History
## V 0.1 
Testing and git setup
Configure automation 

## V 1.0 Oct 2022
Website automation implemented. 
Daily update

## V1.1 Nov 2022
Added patch notes as tooltip

## V1.2 Apr 2023
Added Flyway CLI - patch notes not there yet, working on scraping them  
Connected search boxes for dual-searching capabilities

## Ver 1.3 Jul 2023
Added links to main product download site & flyway cli

## Ver 1.4 Jul 2023
Added links to document site for products, defaults to main document site when no specific product site is found

## Ver 1.5 Apr 2024
Added Redgate Monitor

## Ver 1.6 Apr 2026
Enhanced database support scraping with AI assistance:
- Fixed SQL Toolbelt/Essentials redirect chain handling with S3 pagination
- Implemented Redgate Monitor OS/platform support detection
- Added automatic link following for master Linux support pages
- Smart extraction of Windows and Linux version data for SQL Server, PostgreSQL, Oracle, MySQL, and MongoDB
- Data storage with reference URLs for future updates
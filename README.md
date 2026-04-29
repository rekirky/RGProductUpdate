# RGProductUpdate
Redgate Product Update scraper
Can be used to get the latest version of a product quickly. 
Check when a product has been updated without checking the release notes, forum or in program.

Status:
[![kirky-run-python-updated](https://github.com/rekirky/RGProductUpdate/actions/workflows/pythonaction.yml/badge.svg)](https://github.com/rekirky/RGProductUpdate/actions/workflows/pythonaction.yml)
[![AI-Assisted](https://img.shields.io/badge/Built%20with-Claude%20AI-blue?logo=anthropic)](https://claude.ai)


# Usage
Filter products by name or release date
e.g. entering '2022-10' into the date field will return all products updated in October

# Feature Request
* ~~Sorting by release date, product name~~
* Include/Exclude specific products  
* ~~Release notes available on hover (V1.1)~~
* ~~Add link to download main site~~
* ~~Add links to product document site~~


# Versions
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
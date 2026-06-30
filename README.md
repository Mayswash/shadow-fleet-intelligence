# Shadow Fleet Intelligence Platform

Automated maritime sanctions evasion detection using satellite SAR imagery, 
AIS vessel tracking, and OFAC sanctions data.

## What it does
- Queries real Sentinel-1 SAR imagery via ESA Copernicus API
- Detects vessels using CFAR (Constant False Alarm Rate) algorithm
- Analyzes AIS position feeds to detect vessels going dark
- Matches vessel ownership chains against OFAC sanctions database
- Generates Shadow Score (0-100) per vessel fusing all signals
- Produces professional PDF intelligence reports

## Stack
Python · NumPy · GeoPandas · Rasterio · Scikit-learn · FastAPI · ReportLab

## Pipeline
SAR Acquisition → CFAR Detection → AIS Gap Analysis → OFAC Matching → Risk Scoring → PDF Report

## Applications
Maritime domain awareness · Sanctions enforcement · GEOINT analysis · 
Defense intelligence · Environmental monitoring

## About
Built as a portfolio project targeting careers in GEOINT, remote sensing, 
and defense intelligence. Part of an ongoing geospatial portfolio focused 
on satellite imagery analysis and intelligence automation.

## Portfolio
github.com/Mayswash/gis-portfolio
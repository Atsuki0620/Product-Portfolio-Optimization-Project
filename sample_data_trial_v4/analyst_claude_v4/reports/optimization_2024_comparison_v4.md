# Optimization Results Comparison (2024)

Generated on: 2025-11-30 08:44:33

## Overview

This report compares three scenarios:

1. **Current**: Baseline from actual sales data (sales_2024.csv)
2. **Greedy**: Greedy heuristic optimization
3. **LP**: Linear Programming optimization (optimal solution)

## Overall Performance Comparison

| Metric | Current | Greedy | LP | Best |
|--------|---------|--------|----|----- |
| Total Quantity | 504,000 | 504,000 | 504,000 | Current |
| Total Revenue (¥) | ¥34,394,204,255 | ¥40,624,964,426 | ¥40,835,425,434 | LP |
| Total Profit (¥) | ¥6,681,161,940 | ¥8,243,618,622 | ¥8,713,592,983 | LP |
| Overall Margin (%) | 19.43% | 20.29% | 21.34% | LP |

## Profit Improvement Analysis

**Greedy vs Current**:
- Profit increase: ¥1,562,456,682 (+23.39%)

**LP vs Current**:
- Profit increase: ¥2,032,431,043 (+30.42%)

**LP vs Greedy**:
- Profit difference: ¥469,974,360 (+5.70%)

## Plant Utilization Comparison

| Plant | Capacity | Current | Greedy | LP |
|-------|----------|---------|--------|----|
| A | 300,000 | 300,000 (100.0%) | 300,000 (100.0%) | 300,000 (100.0%) | 
| B | 204,000 | 204,000 (100.0%) | 204,000 (100.0%) | 204,000 (100.0%) | 

## Segment Mix Comparison

| Segment | Target Mix | Current | Greedy | LP |
|---------|------------|---------|--------|----|
| industrial | 40.0% | 39.9% | 40.0% | 37.0% | 
| electronics | 25.0% | 24.9% | 25.0% | 23.5% | 
| oil_gas | 10.0% | 9.9% | 10.0% | 13.0% | 
| others | 25.0% | 25.3% | 25.0% | 26.5% | 

## Segment Margin Rate Comparison

| Segment | Target Margin | Current | Greedy | LP |
|---------|---------------|---------|--------|----|
| industrial | 10.0% | 10.11% | 11.39% | 11.47% | 
| electronics | 20.0% | 20.55% | 21.61% | 21.39% | 
| oil_gas | 50.0% | 50.25% | 50.42% | 50.43% | 
| others | 20.0% | 19.86% | 19.97% | 20.47% | 

## Summary

### Key Findings

1. **LP optimization achieves the maximum profit** of ¥8,713,592,983
2. This represents an improvement of ¥2,032,431,043 (30.42%) over the current baseline
3. Greedy heuristic achieves ¥8,243,618,622, which is ¥469,974,360 (5.70%) below the LP optimum

### Constraint Satisfaction

All optimization scenarios satisfy:
- Total sales quantity: 504,000 units
- Plant capacity limits
- Segment mix targets (±3 percentage points)

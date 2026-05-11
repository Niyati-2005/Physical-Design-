# VLSI Physical Design Algorithms Documentation

## Introduction
This repository contains implementations and documentation for three fundamental **VLSI Physical Design Algorithms**:

1. **Cluster Growth Floorplanning**
2. **Fiduccia–Mattheyses (FM) Algorithm**
3. **Kernighan–Lin (KL) Algorithm**

The project includes:
- Algorithm theory and concepts
- Python implementations
- Command-line execution examples
- CSV input formats
- Reusable workflow and best practices

---

# 1. Cluster Growth Floorplanning

## Overview
The **Cluster Growth Floorplanning Algorithm** constructs a floorplan by:
- Generating a linear ordering of modules
- Iteratively placing modules based on a cost function
- Minimizing area and interconnect wire length

---

## Cost Function

\[
\text{Cost} = \alpha \times \text{Area} + \beta \times \text{HPWL}
\]

Where:
- **Area** → Bounding box area of the floorplan
- **HPWL** → Half-Perimeter Wire Length
- **α, β** → Weighting factors for optimization

---

## Command Line Usage

### Run using full file paths
```bash
python "C:\Niyati\Coding\Physical design\cluster_growth_floorplan.py" ^
    --modules-csv "C:\Niyati\Coding\Physical design\cluster_modules.csv" ^
    --nets-csv "C:\Niyati\Coding\Physical design\cluster_nets.csv" ^
    --start-module A
```

### Run inside project directory
```bash
cd "C:\Niyati\Coding\Physical design"

python cluster_growth_floorplan.py \
    --modules-csv cluster_modules.csv \
    --nets-csv cluster_nets.csv \
    --start-module A
```

### Run demo mode
```bash
python cluster_growth_floorplan.py --demo
```

---

# 2. Fiduccia–Mattheyses (FM) Algorithm

## Overview
The **FM Algorithm** is a linear-time heuristic used for **circuit bipartitioning**.

Its primary objective is to:
- Reduce cut size
- Maintain balanced partitions
- Improve placement quality

---

## Key Concepts

### Gain
Reduction in cut cost when moving a cell from one partition to another.

### Pass
One complete iteration of node movement.

### Balance Constraint
Ensures both partitions remain nearly equal in size.

---

## Objective
Minimize cut cost while maintaining partition balance.

---

## Command Line Usage

### Run using full file paths
```bash
python "C:\Niyati\Coding\Physical design\FM_algo.py" ^
    "C:\Niyati\Coding\Physical design\fm_input.csv"
```

### Generate output CSV
```bash
python "C:\Niyati\Coding\Physical design\FM_algo.py" ^
    "C:\Niyati\Coding\Physical design\fm_input.csv" ^
    -o "C:\Niyati\Coding\Physical design\fm_output.csv"
```

### Run inside project directory
```bash
cd "C:\Niyati\Coding\Physical design"

python FM_algo.py fm_input.csv
```

### Run with custom parameters
```bash
python FM_algo.py fm_input.csv \
    --max-passes 100 \
    --balance-tolerance 0
```

---

# 3. Kernighan–Lin (KL) Algorithm

## Overview
The **Kernighan–Lin (KL) Algorithm** partitions graphs by iteratively swapping node pairs to reduce edge cut cost.

---

## Key Concepts

### D-Value
Difference between:
- External connection cost
- Internal connection cost

### Pair Swapping
Node pairs are swapped to maximize partition gain.

---

## Requirement
The graph must contain an **even number of nodes**.

---

## Command Line Usage

### Run using full file paths
```bash
python "C:\Niyati\Coding\Physical design\KL_algo.py" ^
    "C:\Niyati\Coding\Physical design\graph.csv"
```

### Generate output CSV
```bash
python "C:\Niyati\Coding\Physical design\KL_algo.py" ^
    "C:\Niyati\Coding\Physical design\graph.csv" ^
    -o "C:\Niyati\Coding\Physical design\kl_output.csv"
```

### Run inside project directory
```bash
cd "C:\Niyati\Coding\Physical design"

python KL_algo.py graph.csv
```

### Run with custom parameters
```bash
python KL_algo.py graph.csv --max-passes 100
```

---

# Input File Formats

## Cluster Modules CSV
```csv
module,width,height
A,2,2
B,3,2
```

---

## Cluster Nets CSV
```csv
net,cells
N1,A B
N2,A C D
```

---

## FM Algorithm CSV
```csv
net,cells,weight
n1,A B
n2,B C D
```

---

## KL Algorithm CSV
```csv
source,target,weight
A,B,1
B,C,2
```

---

# Reusability & Best Practices

- Validate CSV files before execution
- Maintain consistent naming conventions across datasets
- Tune optimization parameters (`alpha`, `beta`, `max-passes`)
- Keep implementations modular for scalability
- Test algorithms on smaller datasets before large-scale execution
- Document intermediate outputs for debugging and analysis

---

# Applications

These algorithms are widely used in:
- Floorplanning
- Circuit partitioning
- Placement optimization
- Wire length minimization
- VLSI CAD tool development

---

# Tech Stack

- **Language:** Python
- **Data Format:** CSV
- **Domain:** VLSI Physical Design / Electronic Design Automation (EDA)

---

# Future Improvements

Potential extensions for this project:
- Simulated Annealing Floorplanning
- Multilevel Partitioning
- Hypergraph-based FM Optimization
- GUI-based visualization
- Benchmark circuit support (MCNC/ISPD)

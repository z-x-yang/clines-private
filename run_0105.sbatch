#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH -t 1-00:00:00
#SBATCH -J extract0105
#SBATCH -o logs/extract0105_%j.out
#SBATCH -e logs/extract0105_%j.err

set -euo pipefail

mkdir -p logs
bash run_0105.sh

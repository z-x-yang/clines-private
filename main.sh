#!/bin/bash

#SBATCH -c 10            # Number of cores requested
#SBATCH -t 10:00:00      # Wall-time
#SBATCH --mem=60G        # memory per node
#SBATCH -p gpu_quad
#SBATCH --gres=gpu:l40s:1
#SBATCH -o ./log/hongyi-%x_%j.out                 # File to which STDOUT will be written, including job ID (%j)
#SBATCH -e ./log/hongyi-%x_%j.err 




source setting_env.sh 

python main.py --model_name gpt4o --notes_file ../ehrllm/0821_model/coral/coral/unannotated/data/$1_unannotated.csv --marker $1




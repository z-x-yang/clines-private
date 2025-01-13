#!/bin/bash

#SBATCH -c 10            # Number of cores requested
#SBATCH -t 10:00:00      # Wall-time
#SBATCH --mem=60G        # memory per node
#SBATCH -p gpu_quad
#SBATCH --gres=gpu:l40s:1
#SBATCH -o ./log/hongyi-%x_%j.out                 # File to which STDOUT will be written, including job ID (%j)
#SBATCH -e ./log/hongyi-%x_%j.err 




source setting_env.sh 

python main_4ce.py --model_name gpt4o --notes_file /n/data1/hsph/biostat/celehs/lab/hongyi/language-into-clinical-data/data/4CE/ --marker $1 




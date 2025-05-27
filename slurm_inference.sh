#!/bin/bash
#SBATCH --job-name=CLINES_o3mini_inference       # 可选：作业名称
#SBATCH --time=48:00:00               # 运行时间上限（48小时）
#SBATCH --mem=128G                    # 内存要求
#SBATCH -c 4                          # CPU 核数
#SBATCH --gres=gpu:1                  # GPU 数量
#SBATCH -p gpu_dia                    # 分区
#SBATCH --mail-type=BEGIN,END,FAIL     # 邮件通知类型
#SBATCH --mail-user=zongxin_yang@hms.harvard.edu  # 邮件地址


bash run_inference.sh
bash run_inference.sh
bash run_inference.sh
bash run_inference.sh

# bash run_test.sh

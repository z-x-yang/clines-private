#!/bin/bash
#SBATCH --job-name=CLINES_DeepSeek             # 可选：作业名称
#SBATCH --time=48:00:00               # 运行时间上限（48小时）
#SBATCH --mem=256G                    # 内存要求
#SBATCH -c 8                          # CPU 核数
#SBATCH --gres=gpu:2                  # GPU 数量
#SBATCH -p gpu_dia                    # 分区
#SBATCH --mail-type=BEGIN,END,FAIL     # 邮件通知类型
#SBATCH --mail-user=zongxin_yang@hms.harvard.edu  # 邮件地址

export HUGGING_FACE_HUB_TOKEN=***REVOKED_OLD_HF_TOKEN***

bash deepseek_server.sh &

sleep 3m

bash keep_run_deepseek.sh

sleep 1m

bash keep_run_deepseek.sh
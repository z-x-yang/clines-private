# EXP-X_<short_name>

> **使用方法**：每个实验开跑前 cp 一份 `experiments/EXP-X_<short_name>.md`，填字段 1-7；跑完回填字段 8-13；同步更新 `EXPERIMENTS.md` index 的状态列 + 一句话结论。按 ~/.claude/experiments-rules.md §8.1（Phase 风格）执行完整 launch 流程：
>
> ```bash
> # 1. 复制模板 + 填字段 1-7（字段 1 commit hash 留 <COMMIT_HASH> placeholder）
> cp experiments/_template.md experiments/EXP-X_<short>.md
> $EDITOR experiments/EXP-X_<short>.md
>
> # 2. 切 branch
> git checkout -b exp/EXP-X_<short>     # 默认从 main 切，详见 experiments-rules.md §4.2
>
> # 3. commit "launch state"
> git add experiments/EXP-X_<short>.md  # + 任何代码改动
> git commit -m "exp(EXP-X): launch <short_name>"
>
> # 4. 回填字段 1 commit hash
> LAUNCH_HASH=$(git rev-parse HEAD)
> sed -i "s/<COMMIT_HASH>/$LAUNCH_HASH/" experiments/EXP-X_<short>.md
> git add experiments/EXP-X_<short>.md
> git commit -m "exp(EXP-X): backfill launch commit hash"
>
> # 5. push（若有 remote）
> git push -u origin "exp/EXP-X_<short>"
>
> # 6. 启动实验 / 提交 sbatch
> ```

---

## 1. 元数据

- **EXP-ID**：EXP-X
- **作战表 E#**：E# （在 Notion 作战表的哪一条）
- **日期**：YYYY-MM-DD
- **Job ID**：SLURM JobID（若无 SLURM 则填 hostname + PID）
- **Commit hash**：`<COMMIT_HASH>` （launch 时刻的 commit，**40 字符 full hash**，由 §8.1 步骤 4 自动回填）
- **Branch**：`exp/EXP-X_<short>`
- **Owner**：zongxin（如果是协作实验注明 owner）

## 2. 目的

这个实验回答什么问题？（一段话，简洁；指明对应哪个 reviewer / Notion 作战表里哪条 E#）

## 3. Baseline

- 上一个 EXP-ID 或 main 分支的 commit hash 是基线
- 明确链接到对应 .md 文件，或 main HEAD `<COMMIT_HASH>`

## 4. Diff（vs baseline）

精确到三类：
- **代码改动**：（哪些 file/function 改了）
- **超参改动**：（哪些 CLI args / config 改了）
- **数据改动**：（输入数据集 / 标注集 / chunk 大小有无变化）

## 5. 复现命令

一个完整可粘贴的 shell block，**未来直接复制就能重跑**（必须用 resolve 后的真路径，不留 placeholder）：

```bash
git checkout exp/EXP-X_<short>         # branch 是 primary ref，不要写 git checkout <hash>
conda activate sglang                  # 或 /home/zoy043/miniconda3/envs/sglang/bin/python
cd "/n/data1/hsph/biostat/celehs/lab/zoy043/My works/longwood_backup/LLM_Info_Extract/language-into-clinical-data"

# 具体复现命令（含所有 env var + 真实路径）
export OPENAIKEY="<KEY>"               # 实验当时使用的 key（若已 rotate 注明）
export OPENAIENDPOINT="https://azure-ai.hms.edu"
python main.py \
    --model_name <model> \
    --notes_dir <real_path> \
    --output_dir runs/EXP-X/preds \
    --schema <schema> \
    --max_retries <N> \
    --marker EXP-X
```

## 6. 配置快照

- **Config 文件 path**：（项目里哪个 yaml / 哪个 shell script）
- **关键超参 inline copy**（防止 yaml 后续被改）：

```yaml
# inline copy from configs/foo.yaml or run_inference.sh
model_name: ...
chunk_size: 768
max_retries: ...
schema: ...
# ... 其他关键超参
```

如 `runs/EXP-X/snapshot/config_resolved.yaml` 已落盘则附 path。

## 7. 数据 / 输入模型快照

- **Manifest path**：（用 `readlink -f` 解析 symlink 后的绝对路径）
- **输入 checkpoint**（若有）：base ckpt / resume from EXP-Y last ckpt 等
- **数据集**：4CE / CORAL-B / CORAL-P / MIMIC 哪些数据集，对应 path
- **Gold standard**：通常是 `outputs/reviewed_updated2/`（不带 historical assertion）
- **大小 / sha256**（可选）

---

## 8. 结果（TBD，跑完回填）

关键 metric（表格 / 数值 / loss 曲线 / TensorBoard 截图 / eval JSON 摘要）。

例：

| 数据集 | Metric | Precision | Recall | F1 |
|---|---|---|---|---|
| 4CE | mention | TBD | TBD | TBD |
| ... | ... | ... | ... | ... |

## 9. vs baseline 对比（TBD）

数值差 + 一句话定性（更好 / 更差 / 持平）。

## 10. 分析（TBD）

Confounds / 假设 / observations / failure mode。这块可以很长。

## 11. 结论（TBD）

`PASS` / `FAIL` / `INCONCLUSIVE` + 一句话总结。

## 12. 下一步（TBD）

候选下个实验的 EXP-ID + 方向。

## 13. Artifact pointers（TBD）

- `runs/EXP-X/eval/<file>.json` — metric / prediction 输出（含 abs path: `readlink -f`）
- `runs/EXP-X/eval/<file>.csv`
- `runs/EXP-X/ckpts/`（若有）
- `runs/EXP-X/tb/`（若有 TensorBoard）
- `runs/EXP-X/snapshot/config_resolved.yaml` — `N/A: snapshot writer 未实现，见 EXPERIMENTS.md banner；config 见字段 6 inline copy`
- `runs/EXP-X/snapshot/git_info.txt` — `N/A: snapshot writer 未实现；git 信息见字段 1`
- `runs/EXP-X/snapshot/env.txt` — `N/A: snapshot writer 未实现，无 fallback`
- `logs/slurm/<jobid>.out` / `logs/slurm/<jobid>.err`（若 SLURM）

---

## 更新日志

- YYYY-MM-DD：launch
- YYYY-MM-DD：跑完，回填字段 8-13
- ...

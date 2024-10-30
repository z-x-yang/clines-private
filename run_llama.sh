# CUDA_VISIBLE_DEVICES=7 python main.py > output_1029_1.log 2>&1
CUDA_VISIBLE_DEVICES=6,7 python main_llama3.py --ehr_dir ./llama3 --start_index 11 > output_1029_1.log 2>&1

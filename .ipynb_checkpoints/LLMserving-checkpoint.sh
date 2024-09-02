

python -m sglang.launch_server \
    --model-path $1 \
    --port 30000 \
    --tp $2 \
    --quantization fp8 

 # if multinode add:
 #    --nccl-init sgl-dev-0:50000 \
 #    --nnodes 2 \
 #    --node-rank 0
 
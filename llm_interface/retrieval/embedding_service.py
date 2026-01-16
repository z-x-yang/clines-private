import torch
from tqdm import tqdm


class EmbeddingService:
    def __init__(self, tokenizer, encoder, use_gpu=True, fp16=False):
        self.tokenizer = tokenizer
        self.encoder = encoder
        self.use_gpu = use_gpu
        self.fp16 = fp16

    def embed_term(self, names, batch_size=256):
        if not names:
            return torch.zeros((0, self.encoder.config.hidden_size))

        # Clean and prepare input
        names = [str(item).lower() for item in names if item is not None]
        if not names:
            return torch.zeros((0, self.encoder.config.hidden_size))

        # Determine optimal batch size based on input length and available memory
        if self.use_gpu:
            avg_length = sum(len(name.split())
                             for name in names) / len(names) if names else 0
            if avg_length > 15:
                batch_size = min(batch_size, 128)
            elif avg_length > 5:
                batch_size = min(batch_size, 192)

        self.encoder.eval()
        dense_embeds = []

        with torch.no_grad():
            for start in tqdm(range(0, len(names), batch_size)):
                end = min(start + batch_size, len(names))
                batch = names[start:end]
                batch_tokenized_names = self.tokenizer.batch_encode_plus(
                    batch, add_special_tokens=True,
                    truncation=True, max_length=25,
                    padding="max_length", return_tensors='pt',
                    num_threads=1)  # keep tokenization single-threaded to avoid rayon pool issues

                if self.use_gpu:
                    batch_tokenized_names = {
                        k: v.cuda() for k, v in batch_tokenized_names.items()}
                    if self.fp16:
                        batch_tokenized_names = {k: v.half() if v.dtype == torch.float32 else v
                                                 for k, v in batch_tokenized_names.items()}

                batch_dense_embeds = self.encoder(
                    **batch_tokenized_names).last_hidden_state[:, 0, :]

                batch_dense_embeds = batch_dense_embeds / \
                    torch.norm(batch_dense_embeds, p=2, dim=-1, keepdim=True)
                batch_dense_embeds = batch_dense_embeds.cpu()
                dense_embeds.append(batch_dense_embeds)

                if self.use_gpu:
                    torch.cuda.empty_cache()

        if dense_embeds:
            return torch.concat(dense_embeds, dim=0)
        else:
            return torch.zeros((0, self.encoder.config.hidden_size))

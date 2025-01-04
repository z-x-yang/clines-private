import tiktoken_ext.openai_public
import inspect

print(dir(tiktoken_ext.openai_public))
print(inspect.getsource(tiktoken_ext.openai_public.cl100k_base))

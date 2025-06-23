from transformers import pipeline
import torch
torch.cuda.empty_cache()


pipe = pipeline("text-generation", model="kakaocorp/kanana-1.5-2.1b-instruct-2505")

prompt = "User: 손흥민에 대해서 어떻게 생각해?\nAssistant:"
output = pipe(prompt, max_new_tokens=200, do_sample=True, temperature=0.7,return_full_text=False )

print(output[0]["generated_text"])

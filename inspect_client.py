import google.genai as genai

client = genai.Client(api_key="test")
print('dir(client) length', len(dir(client)))
print('models attr exists', hasattr(client, 'models'))
print('first 30 client attrs', dir(client)[:30])
print('client.models first 20 attrs', dir(client.models)[:20])
# Try to see if there is a method to generate content
if hasattr(client.models, 'generate'):
    print('has generate')
if hasattr(client.models, 'generate_text'):  # maybe
    print('has generate_text')

# Try introspection on Models class
from google.genai import models
print('models class methods', [m for m in dir(models.Models) if not m.startswith('_')])

import google.genai as genai
print('genai attributes:')
for name in sorted(dir(genai)):
    print(name)

print('\nCreating client instance...')
client = genai.Client(api_key='test')
print('client attrs:', [a for a in dir(client) if not a.startswith('_')])

print('\nHas GenerativeModel?:', hasattr(genai, 'GenerativeModel'))

print('\nClient class details:')
print(genai.Client)
print(genai.Client.__doc__)
print('\nDoes module have responses attribute? ', hasattr(genai, 'responses'))
print('genai.Client methods snapshot:')
print([m for m in dir(genai.Client) if not m.startswith('_')])
print('\nClient help:')
import inspect
print(inspect.getsource(genai.Client))

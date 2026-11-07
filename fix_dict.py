import re
with open('backend/app/api/drift.py', 'r') as f:
    content = f.read()
content = content.replace('d.dict()', 'd.model_dump()')
with open('backend/app/api/drift.py', 'w') as f:
    f.write(content)
print('Done')

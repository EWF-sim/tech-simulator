import xml.etree.ElementTree as ET

with open('ewf_tech_simulator.ghx', 'r', encoding='utf-8') as f:
    content = f.read()

tree = ET.fromstring(content)

print("Python 3 Script components in the definition:")
print("=" * 60)

# Navigate to DefinitionObjects
objects = tree.findall('.//chunk[@name="DefinitionObjects"]/chunks/chunk[@name="Object"]')

python_scripts = []
for obj in objects:
    index = obj.get('index')
    
    # Find Name and NickName items
    items = obj.findall('.//items/item')
    name = None
    nickname = None
    
    for item in items:
        if item.get('name') == 'Name':
            name = item.text
        elif item.get('name') == 'NickName':
            nickname = item.text
    
    if name == 'Python 3 Script' and nickname:
        python_scripts.append((int(index), nickname))
        print(f"[{index}] {nickname}")

python_scripts.sort()
print(f"\nTotal: {len(python_scripts)} Python 3 Script components")
print("\nOrdered by index:")
for idx, name in python_scripts:
    print(f"  [{idx}] {name}")

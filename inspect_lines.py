with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(30, 40):
        print(f"{i+1}: {repr(lines[i])}")
    for i in range(90, 100):
        print(f"{i+1}: {repr(lines[i])}")

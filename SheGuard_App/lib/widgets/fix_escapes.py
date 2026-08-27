import os
os.chdir(r'C:\Programs\codex\SheGuard\SheGuard_App\lib\widgets')
with open('emergency_action_panel.dart', 'r', encoding='utf-8') as f:
    content = f.read()
old_str = 'countdownSeconds.toString() + \ s\'
new_str = '\s'
content = content.replace(old_str, new_str)
with open('emergency_action_panel.dart', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')

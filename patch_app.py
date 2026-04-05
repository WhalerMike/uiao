path = r'src\uiao_core\cli\app.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
patched = []
for i, line in enumerate(lines):
    n = i + 1
    if n == 278 and 'Generate Mermaid' in line:
        patched.append('    """Generate PlantUML diagrams from visuals/ to PNG."""\n')
        continue
    if n == 280 and 'render_all_mermaid' in line:
        patched.append('    # render_all_mermaid removed\n')
        continue
    if n == 291 and 'Rendering all Mermaid' in line:
        patched.append('    # ' + line.lstrip())
        continue
    if n == 292 and 'render_all_mermaid' in line:
        patched.append('    # ' + line.lstrip())
        continue
    if n == 293 and 'total diagram' in line:
        patched.append('    # ' + line.lstrip())
        continue
    if n == 382 and 'render_all_mermaid' in line:
        patched.append('    from uiao_core.generators.plantuml import render_plantuml_dir\n')
        continue
    if n == 386 and 'Rendering Mermaid visuals' in line:
        patched.append('    console.print("[bold]Rendering PlantUML diagrams...[/bold]")\n')
        continue
    if n == 387 and 'render_all_mermaid' in line:
        patched.append('    from uiao_core.utils.context import get_settings as _gs\n')
        patched.append('    _s = _gs()\n')
        patched.append('    pngs = render_plantuml_dir(_s.project_root / "visuals", _s.project_root / "assets/images/mermaid", force=force_visuals)\n')
        continue
    if n == 633 and 'render_all_mermaid' in line:
        patched.append('    from uiao_core.generators.plantuml import render_plantuml_dir as _rpd\n')
        continue
    if n == 648 and 'Rendering Mermaid diagrams' in line:
        patched.append('    console.print("[bold][ 1/8 ] Rendering PlantUML diagrams...[/bold]")\n')
        continue
    if n == 650 and 'render_all_mermaid' in line:
        patched.append('        from uiao_core.utils.context import get_settings as _gs2\n')
        patched.append('        _s2 = _gs2()\n')
        patched.append('        pngs = _rpd(_s2.project_root / "visuals", _s2.project_root / "assets/images/mermaid", force=force_visuals)\n')
        continue
    patched.append(line)
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(patched)
changed = sum(1 for a, b in zip(lines, patched) if a != b)
print(f'Done. {changed} lines changed.')

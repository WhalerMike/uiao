@'
path = r'src\uiao_core\cli\app.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

patched = []
for i, line in enumerate(lines):
    n = i + 1

    # Fix 1: generate_diagrams docstring
    if n == 278 and 'Generate Mermaid' in line:
        patched.append('    """Generate PlantUML diagrams from visuals/ to PNG via plantweb."""\n')
        continue

    # Fix 1: remove mermaid import inside generate_diagrams
    if n == 280 and 'render_all_mermaid' in line and 'mermaid' in line:
        patched.append('    # render_all_mermaid removed -- PlantUML handled in generate_diagrams_from_canon\n')
        continue

    # Fix 1: comment out "Rendering all Mermaid files" console print
    if n == 291 and 'Rendering all Mermaid' in line:
        patched.append('    # ' + line.lstrip())
        continue

    # Fix 1: comment out render_all_mermaid call in generate_diagrams
    if n == 292 and 'render_all_mermaid' in line:
        patched.append('    # ' + line.lstrip())
        continue

    # Fix 1: comment out "Rendered X total" print
    if n == 293 and 'total diagram' in line:
        patched.append('    # ' + line.lstrip())
        continue

    # Fix 2: replace mermaid import in generate_artifacts with plantuml
    if n == 382 and 'render_all_mermaid' in line:
        patched.append('    from uiao_core.generators.plantuml import render_plantuml_dir\n')
        continue

    # Fix 2: replace "Rendering Mermaid visuals" print in generate_artifacts
    if n == 386 and 'Rendering Mermaid visuals' in line:
        patched.append('    console.print("[bold]Rendering PlantUML diagrams...[/bold]")\n')
        continue

    # Fix 2: replace render_all_mermaid call in generate_artifacts
    if n == 387 and 'render_all_mermaid' in line:
        patched.append('    from uiao_core.utils.context import get_settings as _gs\n')
        patched.append('    _s = _gs()\n')
        patched.append('    pngs = render_plantuml_dir(_s.project_root / "visuals", _s.project_root / "assets/images/mermaid", force=force_visuals)\n')
        continue

    # Fix 3: replace mermaid import in generate_all with plantuml
    if n == 633 and 'render_all_mermaid' in line:
        patched.append('    from uiao_core.generators.plantuml import render_plantuml_dir as _rpd\n')
        continue

    # Fix 3: replace "Rendering Mermaid diagrams" print in generate_all
    if n == 648 and 'Rendering Mermaid diagrams' in line:
        patched.append('    console.print("[bold][ 1/8 ] Rendering PlantUML diagrams...[/bold]")\n')
        continue

    # Fix 3: replace render_all_mermaid call in generate_all
    if n == 650 and 'render_all_mermaid' in line:
        patched.append('        from uiao_core.utils.context import get_settings as _gs2\n')
        patched.append('        _s2 = _gs2()\n')
        patched.append('        pngs = _rpd(_s2.project_root / "visuals", _s2.project_root / "assets/images/mermaid", force=force_visuals)\n')
        continue

    patched.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(patched)

changed = sum(1 for a, b in zip(lines, patched) if a != b)
print(f'Done. {changed} line(s) changed. Total lines: {len(patched)}')
'@ | Set-Content "patch_app.py" -Encoding UTF8
Write-Host "✅ patch_app.py written" -ForegroundColor Green